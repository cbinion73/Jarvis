const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE_URL = process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787";
const ARTIFACT_DIR = path.join(process.cwd(), "artifacts", "qa");
const SCREENSHOT_DIR = path.join(ARTIFACT_DIR, "screenshots");
const REPORT_PATH = path.join(ARTIFACT_DIR, "jarvis-full-system-report.json");
const API_TIMEOUT_MS = Number(process.env.JARVIS_API_TIMEOUT_MS || 60000);
const CHECK_TIMEOUT_MS = Number(process.env.JARVIS_CHECK_TIMEOUT_MS || 75000);
const RUN_TIMEOUT_MS = Number(process.env.JARVIS_RUN_TIMEOUT_MS || 360000);
const API_WARN_MS = Number(process.env.JARVIS_API_WARN_MS || 2500);
const CHECK_WARN_MS = Number(process.env.JARVIS_CHECK_WARN_MS || 12000);

const API_WARN_THRESHOLDS_MS = {
  "/health": 1200,
  "/": 1500,
  "/api/dashboard": 12000,
  "/api/dashboard?actor=Caleb": 12000,
  "/api/today-board?actor=Chris": 8000,
  "/api/cadence-review?actor=Chris": 8000,
  "/api/cognitive?actor=Chris": 20000,
  "/api/cognitive?actor=Chris&include_graph=false": 12000,
  "/api/cognitive/world-state?actor=Chris": 6000,
  "/api/first-light?actor=Chris&force=true": 15000,
  "/api/persona-snapshot?actor=Chris&refresh=true": 8000,
  "/api/learning-review?viewer=Chris&subject_user_id=chris": 8000,
  "/api/assistant-core/background-run": 12000,
};

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

async function recordShot(page, name) {
  const file = path.join(SCREENSHOT_DIR, `${slugify(name)}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function dispatchClick(page, selector) {
  await page.evaluate((targetSelector) => {
    const node = document.querySelector(targetSelector);
    if (!(node instanceof HTMLElement)) {
      throw new Error(`Missing element for click: ${targetSelector}`);
    }
    node.click();
  }, selector);
}

async function openPacket(page, packetId) {
  await page.evaluate((targetPacketId) => {
    if (typeof window.__jarvisOpenPacket !== "function") {
      throw new Error("openPacket helper not available");
    }
    Promise.resolve(window.__jarvisOpenPacket(targetPacketId)).catch((error) => {
      console.error("packet-open-failed", targetPacketId, error?.message || error);
    });
  }, packetId);
}

async function closeModalIfVisible(page) {
  await page.evaluate(() => {
    const layer = document.getElementById("modal-layer");
    const close = document.getElementById("close-modal");
    if (layer?.classList.contains("open") && close instanceof HTMLElement) {
      close.click();
    }
  });
  await page.waitForTimeout(200);
}

function classifyFailure(error) {
  const message = error && error.stack ? error.stack : String(error || "");
  if (/exceeded \d+ms/i.test(message) || /timed out/i.test(message) || /AbortSignal\.timeout/i.test(message)) {
    return "latency_budget";
  }
  return "product";
}

function createReport() {
  return {
    started_at: new Date().toISOString(),
    base_url: BASE_URL,
    checks: [],
    failures: [],
    warnings: [],
    performance: {
      api: [],
      checks: [],
    },
    summary: {
      passed: 0,
      failed: 0,
      warned: 0,
      skipped: 0,
      product_failures: 0,
      latency_failures: 0,
      environment_skips: 0,
      runner_failures: 0,
    },
  };
}

function writeReport(report) {
  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
}

function finalizeReport(report) {
  report.finished_at = new Date().toISOString();
  writeReport(report);
}

function pushTiming(collection, payload) {
  collection.push(payload);
}

async function fetchResponse(pathname, options = {}, report = null) {
  const started = Date.now();
  let response;
  let lastError = null;
  const maxAttempts = 5;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      response = await fetch(`${BASE_URL}${pathname}`, {
        ...options,
        signal: AbortSignal.timeout(API_TIMEOUT_MS),
      });
      lastError = null;
      break;
    } catch (error) {
      lastError = error;
      const retryable = error instanceof TypeError;
      if (!retryable || attempt === maxAttempts) {
        throw error;
      }
      const retryDelayMs = attempt * 1000;
      await new Promise((resolve) => setTimeout(resolve, retryDelayMs));
      try {
        await fetch(`${BASE_URL}/health`, {
          signal: AbortSignal.timeout(Math.min(API_TIMEOUT_MS, 5000)),
        });
      } catch {
        // Swallow transient health failures here; the next loop attempt is the source of truth.
      }
    }
  }
  if (!response) {
    throw lastError || new Error(`Request failed for ${pathname}`);
  }
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  const duration_ms = Date.now() - started;
  const payload = {
    ok: response.ok,
    status: response.status,
    headers: Object.fromEntries(response.headers.entries()),
    data,
    text,
    duration_ms,
    pathname,
  };
  if (report) {
    pushTiming(report.performance.api, {
      pathname,
      method: String(options.method || "GET").toUpperCase(),
      status: response.status,
      duration_ms,
      threshold_ms: Number(API_WARN_THRESHOLDS_MS[pathname] || API_WARN_MS),
    });
  }
  return payload;
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function run() {
  const report = createReport();
  let browser = null;
  let currentCheckContext = null;

  async function check(name, fn, options = {}) {
    const entry = {
      name,
      status: "passed",
      details: null,
      screenshot: null,
      kind: options.kind || "automated",
      classification: "product",
    };
    process.stderr.write(`[jarvis-full-system] start: ${name}\n`);
    const timeoutMs = Number(options.timeout_ms || CHECK_TIMEOUT_MS);
    const started = Date.now();
    try {
      currentCheckContext = { name, latency_warning_emitted: false };
      await Promise.race([
        fn(entry),
        new Promise((_, reject) => {
          setTimeout(() => {
            reject(new Error(`${name} exceeded ${timeoutMs}ms`));
          }, timeoutMs);
        }),
      ]);
      entry.duration_ms = Date.now() - started;
      report.summary.passed += 1;
      process.stderr.write(`[jarvis-full-system] pass: ${name}\n`);
      pushTiming(report.performance.checks, {
        name,
        duration_ms: entry.duration_ms,
        threshold_ms: Number(options.warn_ms || CHECK_WARN_MS),
      });
      if (entry.duration_ms > Number(options.warn_ms || CHECK_WARN_MS) && !currentCheckContext.latency_warning_emitted) {
        warn(
          `${name} was slow but passed`,
          `${name} completed in ${entry.duration_ms}ms (warn threshold ${Number(options.warn_ms || CHECK_WARN_MS)}ms).`,
          { classification: "latency_budget", related_check: name }
        );
      }
    } catch (error) {
      entry.status = "failed";
      entry.details = error && error.stack ? error.stack : String(error);
      entry.duration_ms = Date.now() - started;
      entry.classification = classifyFailure(error);
      report.summary.failed += 1;
      if (entry.classification === "latency_budget") {
        report.summary.latency_failures += 1;
      } else {
        report.summary.product_failures += 1;
      }
      report.failures.push({ name, error: entry.details, classification: entry.classification, duration_ms: entry.duration_ms });
      process.stderr.write(`[jarvis-full-system] fail: ${name}\n`);
    } finally {
      currentCheckContext = null;
    }
    report.checks.push(entry);
    writeReport(report);
  }

  function warn(name, details, options = {}) {
    report.summary.warned += 1;
    report.warnings.push({ name, details, classification: options.classification || "product" });
    report.checks.push({
      name,
      status: "warning",
      details,
      screenshot: null,
      kind: "automated",
      classification: options.classification || "product",
      related_check: options.related_check || null,
    });
    writeReport(report);
  }

  function skip(name, details) {
    report.summary.skipped += 1;
    report.summary.environment_skips += 1;
    report.checks.push({
      name,
      status: "skipped",
      details,
      screenshot: null,
      kind: "automated",
      classification: "environment",
    });
    writeReport(report);
  }

  const checkApiResponse = async (pathname, verify, options = {}) => {
    const response = await fetchResponse(pathname, options.fetch_options || {}, report);
    assert(response.ok, `${pathname} returned ${response.status}`);
    verify(response.data, response);
    const threshold = Number(API_WARN_THRESHOLDS_MS[pathname] || options.warn_ms || API_WARN_MS);
    if (response.duration_ms > threshold) {
      if (currentCheckContext) {
        currentCheckContext.latency_warning_emitted = true;
      }
      warn(
        `${pathname} API was slow but passed`,
        `${pathname} responded in ${response.duration_ms}ms (warn threshold ${threshold}ms).`,
        { classification: "latency_budget", related_check: pathname }
      );
    }
    return response;
  };

  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  context.setDefaultTimeout(CHECK_TIMEOUT_MS);
  context.setDefaultNavigationTimeout(CHECK_TIMEOUT_MS);
  const page = await context.newPage();

  await check("Health endpoint is healthy", async () => {
    await checkApiResponse("/health", (data) => {
      assert(data && data.ok === true, "Health endpoint did not report ok=true");
      assert(data.service === "fastapi", `Expected FastAPI service, got ${data.service}`);
      assert(Boolean(data.runtime), "Health endpoint missing runtime block");
      assert(typeof data.runtime.build_fingerprint === "string" && data.runtime.build_fingerprint.length > 0, "Health runtime missing build fingerprint");
    });
  });

  await check("Root shell responds", async () => {
    const response = await fetchResponse("/", {}, report);
    assert(response.ok, `/ returned ${response.status}`);
    assert(String(response.text).includes("JARVIS Voice Shell"), "Root HTML did not include JARVIS Voice Shell");
    const threshold = Number(API_WARN_THRESHOLDS_MS["/"] || API_WARN_MS);
    if (response.duration_ms > threshold) {
      if (currentCheckContext) {
        currentCheckContext.latency_warning_emitted = true;
      }
      warn(`Root shell API was slow but passed`, `/ responded in ${response.duration_ms}ms (warn threshold ${threshold}ms).`, {
        classification: "latency_budget",
        related_check: "/",
      });
    }
  });

  await check("Primary dashboard endpoint has expected shape", async () => {
    await checkApiResponse("/api/dashboard", (data) => {
      assert(Boolean(data.active_mode), "Dashboard missing active_mode");
      assert(Boolean(data.assistant_surface), "Dashboard missing assistant_surface");
      assert(Boolean(data.today_board), "Dashboard missing today_board");
      assert(Boolean(data.freshness), "Dashboard missing freshness metadata");
      assert(data.freshness.surface === "dashboard", "Dashboard freshness surface mismatch");
    });
  }, { timeout_ms: 120000 });

  await check("Actor-aware dashboard endpoint has expected shape", async () => {
    const endpoints = [
      ["/api/dashboard?actor=Caleb", (data) => {
        assert(Boolean(data.today_board), "Actor-aware dashboard missing today_board");
        assert(String(data.today_board.actor || "").length > 0, "Actor-aware dashboard missing actor");
        assert(Boolean(data.freshness), "Actor-aware dashboard missing freshness metadata");
      }],
    ];

    for (const [pathname, verify] of endpoints) {
      await checkApiResponse(pathname, verify);
    }
  }, { timeout_ms: 120000 });

  await check("Operational platform endpoints have expected shape", async () => {
    const endpoints = [
      ["/api/status", (data) => assert(Array.isArray(data), "Status endpoint did not return a list")],
      ["/api/identity", (data) => {
        assert(Array.isArray(data.members), "Identity missing members");
        assert(Array.isArray(data.devices), "Identity missing devices");
      }],
      ["/api/connected-devices", (data) => {
        assert(data.summary && typeof data.summary.total === "number", "Connected devices missing summary");
        assert(typeof data.summary.high_confidence === "number", "Connected devices missing high-confidence count");
        assert(typeof data.summary.medium_confidence === "number", "Connected devices missing medium-confidence count");
        assert(typeof data.summary.low_confidence === "number", "Connected devices missing low-confidence count");
        assert(Array.isArray(data.devices), "Connected devices missing devices array");
        if (data.devices.length) {
          assert(Boolean(data.devices[0].owner_confidence), "Connected devices missing owner_confidence");
          assert(typeof data.devices[0].owner_confidence.confidence === "string", "Connected device owner_confidence missing confidence");
          assert(Array.isArray(data.devices[0].owner_confidence.evidence), "Connected device owner_confidence missing evidence");
        }
      }],
      ["/api/vision-state?actor=Chris", (data) => {
        assert(Boolean(data.summary), "Vision state missing summary");
        assert(typeof data.summary.has_calibration === "boolean", "Vision state missing calibration flag");
        assert(Array.isArray(data.recent_observations), "Vision state missing recent observations");
        assert(Array.isArray(data.recent_captures), "Vision state missing recent captures");
        assert(Array.isArray(data.evidence_items), "Vision state missing evidence items");
      }],
      ["/api/runtime-service", (data) => {
        assert(data.runtime && data.openviking && data.assistant_autonomy, "Runtime service missing launch-agent status");
        assert(Boolean(data.service_runtime), "Runtime service missing service_runtime");
        assert(Boolean(data.service_runtime.startup_build?.fingerprint), "Runtime service missing startup fingerprint");
        assert(Boolean(data.service_runtime.current_build?.fingerprint), "Runtime service missing current disk fingerprint");
        assert(Array.isArray(data.service_runtime.restart_history), "Runtime service missing restart history");
      }],
      ["/api/explainability", (data) => {
        assert(Array.isArray(data.approval_history), "Explainability missing approval_history");
        assert(Array.isArray(data.latest_reasons), "Explainability missing latest_reasons");
        assert(Boolean(data.assistant_action_summary), "Explainability missing assistant_action_summary");
        assert(Array.isArray(data.assistant_actions), "Explainability missing assistant_actions");
        assert(Boolean(data.assistant_outcome_summary), "Explainability missing assistant_outcome_summary");
        assert(Array.isArray(data.assistant_outcomes), "Explainability missing assistant_outcomes");
        assert(Boolean(data.assistant_tuning_summary), "Explainability missing assistant_tuning_summary");
        assert(Boolean(data.assistant_tuning_summary.summary), "Explainability missing assistant_tuning_summary.summary");
        assert(Boolean(data.assistant_tuning_summary.domains), "Explainability missing assistant_tuning_summary.domains");
        if (data.assistant_actions.length) {
          assert(typeof data.assistant_actions[0].action_class === "string", "Explainability assistant action missing action_class");
          assert(typeof data.assistant_actions[0].policy_basis === "string", "Explainability assistant action missing policy_basis");
          assert(typeof data.assistant_actions[0].confidence === "string", "Explainability assistant action missing confidence");
          assert(typeof data.assistant_actions[0].result_summary === "string", "Explainability assistant action missing result_summary");
        }
        if (data.assistant_outcomes.length) {
          assert(typeof data.assistant_outcomes[0].source === "string", "Explainability assistant outcome missing source");
          assert(typeof data.assistant_outcomes[0].initiator === "string", "Explainability assistant outcome missing initiator");
          assert(typeof data.assistant_outcomes[0].status === "string", "Explainability assistant outcome missing status");
          assert(typeof data.assistant_outcomes[0].detail === "string", "Explainability assistant outcome missing detail");
        }
      }],
      ["/api/open-loops", (data) => {
        assert(data.summary && typeof data.summary.total === "number", "Open loops missing summary");
        assert(Array.isArray(data.items), "Open loops missing items array");
        assert(Array.isArray(data.task_lanes), "Open loops missing task_lanes");
        assert(data.task_lanes.some((item) => item.domain === "growth"), "Open loops missing growth task lane");
        const growthItems = Array.isArray(data.items) ? data.items.filter((item) => item.domain === "growth") : [];
        if (growthItems.length) {
          assert(growthItems.every((item) => typeof item.growth_review_due === "boolean"), "Growth open loop missing growth_review_due");
          assert(growthItems.every((item) => typeof item.growth_high_pressure === "boolean"), "Growth open loop missing growth_high_pressure");
          assert(growthItems.some((item) => ["finance", "pipeline", "marketing", "review"].includes(String(item.suggested_packet || "").trim())), "Growth open loops missing lane-specific packet routing");
        }
        if (data.items.length) {
          assert(Array.isArray(data.items[0].available_actions), "Open loop item missing available actions");
          assert(typeof data.items[0].auto_execution?.summary === "string", "Open loop item missing auto_execution summary");
          if (data.items[0].auto_execution?.allowed) {
            assert(typeof data.items[0].auto_execution?.action === "string" && data.items[0].auto_execution.action.length > 0, "Open loop auto_execution allowed without action");
            assert(typeof data.items[0].auto_execution?.action_class === "string", "Open loop auto_execution missing action_class");
          }
        }
      }],
      ["/api/assistant-core/tick", (data) => {
        assert(Boolean(data.assistant_surface), "Assistant tick missing assistant_surface");
        assert(Boolean(data.today_board), "Assistant tick missing today_board");
        assert(Boolean(data.cognitive), "Assistant tick missing cognitive snapshot");
        assert(Boolean(data.sweep), "Assistant tick missing sweep state");
        if (data.assistant_surface?.top_item) {
          assert(typeof data.assistant_surface.top_item.why_this_surfaced_now === "string", "Assistant tick top_item missing why_this_surfaced_now");
          assert(typeof data.assistant_surface.top_item.auto_execution?.summary === "string", "Assistant tick top_item missing auto_execution summary");
          if (data.assistant_surface.top_item.domain === "growth") {
            assert(["finance", "pipeline", "marketing", "review"].includes(String(data.assistant_surface.top_item.suggested_packet || "").trim()), "Growth top item missing lane-specific suggested packet");
          }
        }
      }],
      ["/api/assistant-core/notifications", (data) => {
        assert(Boolean(data.summary), "Assistant notifications missing summary");
        assert(Boolean(data.summary.by_status), "Assistant notifications missing by_status summary");
        assert(Boolean(data.summary.by_priority), "Assistant notifications missing by_priority summary");
        assert(Array.isArray(data.items), "Assistant notifications missing items");
        if (data.items.length) {
          assert(typeof data.items[0].priority_class === "string", "Assistant notification missing priority_class");
          assert(typeof data.items[0].why_this_surfaced === "string", "Assistant notification missing why_this_surfaced");
          assert(typeof data.items[0].why_this_surfaced_now === "string", "Assistant notification missing why_this_surfaced_now");
          assert(typeof data.items[0].status === "string", "Assistant notification missing status");
          assert(typeof data.items[0].interrupt_eligible === "boolean", "Assistant notification missing interrupt_eligible");
        }
        const growthNotifications = Array.isArray(data.items) ? data.items.filter((item) => item.domain === "growth") : [];
        if (growthNotifications.length) {
          assert(growthNotifications.some((item) => ["finance", "pipeline", "marketing", "review"].includes(String(item.packet || "").trim())), "Growth notifications missing lane-specific packet routing");
        }
      }],
      ["/api/assistant-core/browser-alerts", (data) => {
        assert(Boolean(data.summary), "Assistant browser alerts missing summary");
        assert(Array.isArray(data.items), "Assistant browser alerts missing items");
        if (data.items.length) {
          assert(typeof data.items[0].priority_class === "string", "Assistant browser alert missing priority_class");
          assert(typeof data.items[0].why_this_surfaced_now === "string", "Assistant browser alert missing why_this_surfaced_now");
          assert(typeof data.items[0].interrupt_eligible === "boolean", "Assistant browser alert missing interrupt_eligible");
        }
      }],
      ["/api/location-settings", (data) => assert(Array.isArray(data.saved_locations), "Location settings missing saved_locations")],
      ["/api/voice-settings", (data) => assert(Boolean(data.settings || data.preferred_source || data.stack_status), "Voice settings shape unexpected")],
      ["/api/voice-options", (data) => assert(Boolean(data.stack_status), "Voice options missing stack_status")],
      ["/api/accounts", (data) => assert(Array.isArray(data.accounts), "Accounts endpoint missing accounts array")],
      ["/api/google/status", (data) => assert(Array.isArray(data.accounts), "Google status missing accounts array")],
      ["/api/merged-calendar", (data) => assert(Array.isArray(data.events), "Merged calendar missing events")],
      ["/api/catalyst-overview", (data) => assert(Boolean(data.counts), "Catalyst overview missing counts")],
    ];

    for (const [pathname, verify] of endpoints) {
      await checkApiResponse(pathname, verify);
    }
  });

  await check("Cognitive platform endpoints have expected shape", async () => {
    const endpoints = [
      ["/api/today-board?actor=Chris", (data) => {
        assert(Array.isArray(data.priorities), "Today Board missing priorities");
        assert(Boolean(data.cognition), "Today Board missing cognition");
        assert(Array.isArray(data.cognition?.world_state?.blocked_work), "Today Board world state missing blocked_work");
        assert(Array.isArray(data.cognition?.world_state?.conflicts), "Today Board world state missing conflicts");
        assert(Array.isArray(data.cognition?.world_state?.likely_next), "Today Board world state missing likely_next");
        assert(Boolean(data.freshness), "Today Board missing freshness metadata");
        assert(data.freshness.surface === "today_board", "Today Board freshness surface mismatch");
      }],
      ["/api/cadence-review?actor=Chris", (data) => {
        assert(typeof data.title === "string" && data.title.length > 0, "Cadence review missing title");
        assert(typeof data.digest === "string" && data.digest.length > 0, "Cadence review missing digest");
        assert(typeof data.outcome_summary === "string" && data.outcome_summary.length > 0, "Cadence review missing outcome summary");
        assert(Array.isArray(data.completion_criteria) && data.completion_criteria.length > 0, "Cadence review missing completion criteria");
        assert(Array.isArray(data.history), "Cadence review missing recurrence history");
        assert(Array.isArray(data.sections), "Cadence review missing sections");
        assert(data.sections.some((item) => item.id === "world-friction"), "Cadence review missing world-friction section");
        assert(Boolean(data.freshness), "Cadence review missing freshness metadata");
        assert(data.freshness.surface === "cadence_review", "Cadence review freshness surface mismatch");
      }],
      ["/api/cognitive?actor=Chris&include_graph=false", (data) => {
        assert(Boolean(data.self_model), "Cognitive snapshot missing self_model");
        assert(Array.isArray(data.self_model.tools?.readiness), "Self model missing tool readiness");
        assert(Boolean(data.self_model.domain_confidence), "Self model missing domain_confidence");
        assert(Array.isArray(data.self_model.action_constraints), "Self model missing action_constraints");
        assert(Array.isArray(data.self_model.known_failure_modes), "Self model missing known_failure_modes");
        assert(Array.isArray(data.self_model.recent_failed_actions), "Self model missing recent_failed_actions");
        assert(Array.isArray(data.self_model.uncertainty_model), "Self model missing uncertainty_model");
        assert(Boolean(data.world_state), "Cognitive snapshot missing world_state");
        assert(Boolean(data.growth_state), "Cognitive snapshot missing growth_state");
        assert(Boolean(data.growth_state.schema), "Growth state missing schema");
        assert(Boolean(data.goal_stack), "Cognitive snapshot missing goal_stack");
        assert(Boolean(data.cadence), "Cognitive snapshot missing cadence");
        assert(Array.isArray(data.cadence.loops), "Cognitive cadence missing loops");
        assert(data.cadence.loops.every((item) => Array.isArray(item.completion_criteria) && item.completion_criteria.length > 0), "Cognitive cadence loops missing completion criteria");
        assert(Boolean(data.deliberation), "Cognitive snapshot missing deliberation");
        assert(Boolean(data.deliberation.scores), "Deliberation missing scores");
        assert(Array.isArray(data.deliberation.mode_candidates) && data.deliberation.mode_candidates.length > 0, "Deliberation missing mode candidates");
        assert(Boolean(data.deliberation.decision_record), "Deliberation missing decision_record");
        assert(Boolean(data.deliberation.council_trace), "Deliberation missing council_trace");
        assert(Boolean(data.internal_council), "Cognitive snapshot missing internal_council");
        assert(Boolean(data.internal_council.tally), "Internal council missing tally");
        assert(Array.isArray(data.growth_state.lanes), "Growth state missing lanes");
        assert(Array.isArray(data.growth_state.domains) && data.growth_state.domains.length >= 6, "Growth state missing canonical domains");
        assert(Array.isArray(data.growth_state.adapters) && data.growth_state.adapters.length >= 6, "Growth state missing source adapters");
        assert(data.growth_state.domains.some((item) => item.id === "finance"), "Growth domains missing finance");
        assert(data.growth_state.domains.some((item) => item.id === "pipeline"), "Growth domains missing pipeline");
        assert(data.growth_state.domains.some((item) => item.id === "marketing"), "Growth domains missing marketing");
        assert(data.growth_state.domains.some((item) => item.id === "content"), "Growth domains missing content");
        assert(data.growth_state.domains.some((item) => item.id === "experiments"), "Growth domains missing experiments");
        assert(data.growth_state.domains.some((item) => item.id === "offers"), "Growth domains missing offers");
        assert(Boolean(data.freshness), "Cognitive snapshot missing freshness metadata");
        assert(data.freshness.surface === "cognitive", "Cognitive freshness surface mismatch");
      }],
      ["/api/cognitive?actor=Chris", (data) => {
        assert(Boolean(data.world_graph), "Cognitive snapshot with graph missing world_graph");
        assert(Boolean(data.world_graph.schema), "World graph missing schema");
        assert(Array.isArray(data.world_graph.schema.entity_types) && data.world_graph.schema.entity_types.length >= 12, "World graph missing formal entity types");
        assert(Array.isArray(data.world_graph.schema.edge_types) && data.world_graph.schema.edge_types.length >= 10, "World graph missing formal edge types");
        assert(Array.isArray(data.world_graph.nodes) && data.world_graph.nodes.length > 0, "World graph missing nodes");
        assert(Array.isArray(data.world_graph.edges), "World graph missing edges");
        assert(data.world_graph.nodes.every((item) => typeof item.entity_type === "string" && item.entity_type.length > 0), "World graph node missing entity_type");
        assert(data.world_graph.nodes.every((item) => typeof item.truth_status === "string" && item.truth_status.length > 0), "World graph node missing truth_status");
        assert(data.world_graph.nodes.every((item) => typeof item.confidence === "string" && item.confidence.length > 0), "World graph node missing confidence");
        assert(data.world_graph.edges.every((item) => typeof item.edge_type === "string" && item.edge_type.length > 0), "World graph edge missing edge_type");
        assert(data.world_graph.edges.every((item) => typeof item.truth_status === "string" && item.truth_status.length > 0), "World graph edge missing truth_status");
        assert(Boolean(data.world_graph.summary?.entity_counts), "World graph summary missing entity_counts");
        assert(Boolean(data.world_graph.summary?.edge_counts), "World graph summary missing edge_counts");
      }],
      ["/api/growth-schema", (data) => {
        assert(typeof data.version === "string" && data.version.length > 0, "Growth schema missing version");
        assert(Array.isArray(data.domains) && data.domains.length >= 6, "Growth schema missing domains");
        assert(Array.isArray(data.adapters) && data.adapters.length >= 6, "Growth schema missing adapters");
        assert(Array.isArray(data.lanes) && data.lanes.length >= 3, "Growth schema missing lanes");
      }],
      ["/api/growth-state?actor=Chris", (data) => {
        assert(Boolean(data.schema), "Growth state endpoint missing schema");
        assert(Array.isArray(data.domains) && data.domains.length >= 6, "Growth state endpoint missing canonical domains");
        assert(Array.isArray(data.adapters) && data.adapters.length >= 6, "Growth state endpoint missing adapters");
        assert(Array.isArray(data.lanes) && data.lanes.length >= 3, "Growth state endpoint missing lanes");
        assert(typeof data.summary?.tracked_domain_count === "number", "Growth state endpoint missing tracked domain count");
      }],
      ["/api/finance-state?actor=Chris", (data) => {
        assert(Boolean(data.scorecard), "Finance state missing scorecard");
        assert(Boolean(data.weekly_review), "Finance state missing weekly review");
        assert(Boolean(data.thresholds), "Finance state missing thresholds");
        assert(typeof data.scorecard.score === "number", "Finance scorecard missing score");
        assert(typeof data.weekly_review.due === "boolean", "Finance weekly review missing due flag");
        assert(Boolean(data.thresholds.low_cash_warning), "Finance thresholds missing low cash warning");
        assert(Boolean(data.thresholds.unusual_spend), "Finance thresholds missing unusual spend");
        assert(Boolean(data.thresholds.goal_progress), "Finance thresholds missing goal progress");
      }],
      ["/api/finance-review?actor=Chris", (data) => {
        assert(typeof data.title === "string" && data.title.length > 0, "Finance review missing title");
        assert(Boolean(data.scorecard), "Finance review missing scorecard");
        assert(Boolean(data.weekly_review), "Finance review missing weekly review");
        assert(Array.isArray(data.sections) && data.sections.length >= 4, "Finance review missing sections");
        assert(typeof data.recommended_next_move === "string" && data.recommended_next_move.length > 0, "Finance review missing recommended next move");
      }],
      ["/api/marketing-state?actor=Chris", (data) => {
        assert(Boolean(data.scorecard), "Marketing state missing scorecard");
        assert(Boolean(data.weekly_review), "Marketing state missing weekly review");
        assert(Boolean(data.performance), "Marketing state missing performance summary");
        assert(Array.isArray(data.state?.campaigns), "Marketing state missing campaigns");
        assert(typeof data.scorecard.score === "number", "Marketing scorecard missing score");
        assert(typeof data.weekly_review.due === "boolean", "Marketing weekly review missing due flag");
      }],
      ["/api/marketing-review?actor=Chris", (data) => {
        assert(typeof data.title === "string" && data.title.length > 0, "Marketing review missing title");
        assert(Boolean(data.scorecard), "Marketing review missing scorecard");
        assert(Boolean(data.weekly_review), "Marketing review missing weekly review");
        assert(Boolean(data.performance), "Marketing review missing performance summary");
        assert(Array.isArray(data.sections) && data.sections.length >= 4, "Marketing review missing sections");
        assert(typeof data.recommended_next_move === "string" && data.recommended_next_move.length > 0, "Marketing review missing recommended next move");
      }],
      ["/api/pipeline-state?actor=Chris", (data) => {
        assert(Boolean(data.scorecard), "Pipeline state missing scorecard");
        assert(Boolean(data.daily_followup_loop), "Pipeline state missing daily follow-up loop");
        assert(Boolean(data.weekly_review), "Pipeline state missing weekly review");
        assert(Array.isArray(data.state?.opportunities), "Pipeline state missing opportunities");
        assert(typeof data.scorecard.score === "number", "Pipeline scorecard missing score");
        assert(typeof data.daily_followup_loop.due === "boolean", "Pipeline daily follow-up missing due flag");
        assert(typeof data.weekly_review.due === "boolean", "Pipeline weekly review missing due flag");
      }],
      ["/api/pipeline-review?actor=Chris", (data) => {
        assert(typeof data.title === "string" && data.title.length > 0, "Pipeline review missing title");
        assert(Boolean(data.scorecard), "Pipeline review missing scorecard");
        assert(Boolean(data.daily_followup_loop), "Pipeline review missing daily follow-up loop");
        assert(Boolean(data.weekly_review), "Pipeline review missing weekly review");
        assert(Array.isArray(data.sections) && data.sections.length >= 4, "Pipeline review missing sections");
        assert(typeof data.recommended_next_move === "string" && data.recommended_next_move.length > 0, "Pipeline review missing recommended next move");
      }],
      ["/api/environment-status?actor=Chris", (data) => {
        assert(typeof data.status === "string" && data.status.length > 0, "Environment status missing overall status");
        assert(Boolean(data.status_summary), "Environment status missing status summary");
        assert(Array.isArray(data.summary) && data.summary.length > 0, "Environment status missing summary lines");
        assert(Array.isArray(data.adapters) && data.adapters.length >= 3, "Environment status missing adapters");
        assert(Boolean(data.host_signals?.battery), "Environment status missing battery signal");
        assert(Boolean(data.host_signals?.network), "Environment status missing network signal");
        assert(Boolean(data.host_signals?.system), "Environment status missing system signal");
        assert(Boolean(data.device_status?.summary), "Environment status missing device summary");
        assert(Boolean(data.physical_systems?.home), "Environment status missing home systems");
        assert(Boolean(data.physical_systems?.climate), "Environment status missing climate systems");
        assert(Boolean(data.physical_systems?.garage), "Environment status missing garage systems");
        assert(Boolean(data.physical_systems?.leak), "Environment status missing leak systems");
        assert(Boolean(data.physical_systems?.cold_storage), "Environment status missing cold storage systems");
        assert(Boolean(data.physical_systems?.outage), "Environment status missing outage systems");
        assert(Boolean(data.anomaly_escalation), "Environment status missing anomaly escalation");
        assert(Array.isArray(data.anomaly_escalation.escalation_candidates), "Environment status missing escalation candidates");
        assert(Array.isArray(data.recent_anomalies), "Environment status missing recent anomalies");
        assert(Boolean(data.freshness), "Environment status missing freshness metadata");
        assert(data.freshness.surface === "environment_status", "Environment status freshness surface mismatch");
      }],
      ["/api/cognitive/world-state?actor=Chris", (data) => {
        assert(Boolean(data.summary), "World state missing summary");
        assert(Boolean(data.delta), "World state missing delta");
        assert(Boolean(data.event_summary), "World state missing event_summary");
        assert(Array.isArray(data.events), "World state missing events");
        assert(Array.isArray(data.blocked_work), "World state missing blocked_work");
        assert(Array.isArray(data.hidden_load), "World state missing hidden_load");
        assert(Array.isArray(data.pressure_clusters), "World state missing pressure_clusters");
        assert(Array.isArray(data.conflicts), "World state missing conflicts");
        assert(Array.isArray(data.likely_next), "World state missing likely_next");
        if (data.events.length) {
          assert(data.events.every((item) => typeof item.event_type === "string" && item.event_type.length > 0), "World event missing event_type");
          assert(data.events.every((item) => typeof item.category === "string" && item.category.length > 0), "World event missing category");
          assert(data.events.every((item) => typeof item.significance === "string" && item.significance.length > 0), "World event missing significance");
          assert(data.events.every((item) => typeof item.actor === "string" && item.actor.toLowerCase() === "chris"), "World event actor filter failed");
        }
      }],
    ];

    for (const [pathname, verify] of endpoints) {
      await checkApiResponse(pathname, verify);
    }
  });

  await check("First Light and persona APIs respond", async () => {
    await checkApiResponse("/api/first-light?actor=Chris&force=true", (data) => {
      assert(data.packet || data.status, "First Light response missing packet/status");
      assert(Boolean(data.freshness), "First Light missing freshness metadata");
      assert(data.freshness.surface === "first_light", "First Light freshness surface mismatch");
      if (data.packet) {
        assert(Array.isArray(data.packet.what_changed), "First Light packet missing what_changed lines");
        assert(Array.isArray(data.packet.sections), "First Light packet missing sections");
        assert(data.packet.sections.some((section) => section.id === "growth-review"), "First Light packet missing growth review section");
      }
    });

    await checkApiResponse("/api/persona-snapshot?actor=Chris&refresh=true", (data) => {
      assert(data.digital_twin, "Persona snapshot missing digital_twin");
      assert(Boolean(data.presence_identity), "Persona snapshot missing presence_identity");
      assert(Boolean(data.personalization), "Persona snapshot missing personalization");
      assert(Boolean(data.personalization.settings), "Persona snapshot missing personalization settings");
      assert(Array.isArray(data.personalization.insights), "Persona snapshot missing personalization insights");
      assert(Array.isArray(data.personalization.learned_preferences), "Persona snapshot missing learned_preferences");
      assert(Boolean(data.presence_identity.active_user_resolution), "Persona snapshot missing active_user_resolution");
      assert(Array.isArray(data.presence_identity.room_confidence), "Persona snapshot missing room_confidence");
      assert(Array.isArray(data.presence_identity.presence_event_history), "Persona snapshot missing presence_event_history");
      assert(Array.isArray(data.presence_identity.likely_here_now), "Persona snapshot missing likely_here_now");
      assert(Boolean(data.presence_identity.device_owner_confidence), "Persona snapshot missing device_owner_confidence");
    });

    await checkApiResponse("/api/learning-review?viewer=Chris&subject_user_id=chris", (data) => {
      assert(Array.isArray(data.profile_facts), "Learning review missing profile_facts");
      assert(Boolean(data.personalization), "Learning review missing personalization");
      assert(Boolean(data.personalization.settings), "Learning review missing personalization settings");
      assert(Array.isArray(data.personalization.insights), "Learning review missing personalization insights");
      assert(Array.isArray(data.personalization.history), "Learning review missing personalization history");
      assert(data.governance && typeof data.governance.can_manage_personalization === "boolean", "Learning review missing personalization governance flag");
    });
  });

  await check("Assistant background autonomy run responds", async () => {
    await checkApiResponse(
      "/api/assistant-core/background-run",
      (data) => {
        assert(data.ok === true, "Background autonomy run did not report ok=true");
        assert(Array.isArray(data.runs), "Background autonomy run missing runs");
        assert(Array.isArray(data.executed_actions), "Background autonomy run missing executed_actions");
        assert(typeof data.retry?.attempts === "number", "Background autonomy run missing retry metadata");
        if (data.runs.length) {
          assert(typeof data.runs[0].decision === "string", "Background autonomy run missing deliberation decision");
          assert(typeof data.runs[0].cadence_phase === "string", "Background autonomy run missing cadence phase");
          assert(Boolean(data.runs[0].cadence_record), "Background autonomy run missing cadence record");
          if (data.runs[0].top_item?.auto_execution?.allowed) {
            assert(typeof data.runs[0].top_item.auto_execution.action_class === "string", "Background autonomy auto_execution missing action_class");
          }
        }
      },
      {
        fetch_options: {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ actors: ["Chris"] }),
        },
      }
    );
  });

  await check("TTS endpoint returns downloadable audio", async () => {
    const response = await fetchResponse("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "Full system battery check." }),
    }, report);
    assert(response.ok, `/api/tts returned ${response.status}`);
    const contentType = response.headers["content-type"] || "";
    assert(contentType.startsWith("audio/"), `Expected audio response, got ${contentType}`);
    assert((response.headers["x-jarvis-tts-provider"] || "").length > 0, "Missing TTS provider header");
    assert(response.text.length > 128, "Audio payload was unexpectedly small");
  });

  const integrationsResponse = await fetchResponse("/api/status", {}, report);
  const integrations = Array.isArray(integrationsResponse.data) ? integrationsResponse.data : [];
  const homeAssistant = integrations.find((item) => item.name === "home-assistant");
  if (!homeAssistant || !homeAssistant.ok) {
    skip(
      "Live Home Assistant action checks",
      homeAssistant ? `Home Assistant not ready: ${homeAssistant.detail}` : "Home Assistant integration status unavailable."
    );
  }

  await check("Voice shell loads and stays interactive", async (entry) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#command-input");
    await page.waitForSelector("#voice-command");
    await page.waitForSelector("#open-settings", { state: "attached" });
    await page.waitForSelector("#packet-strip-toggle", { state: "attached" });
    await page.waitForSelector(".core-stage");
    const stateLabel = await page.locator("#state-label").textContent();
    assert((stateLabel || "").trim().length > 0, "State label was empty on initial load");
    entry.screenshot = await recordShot(page, "full-system-home-shell");
  });

  await check("Packet rail expands with current packet set", async (entry) => {
    await page.evaluate(() => {
      const button = document.getElementById("packet-strip-toggle");
      if (!button) throw new Error("packet-strip-toggle not found");
      button.click();
    });
    await page.waitForTimeout(300);
    await page.waitForFunction(() => {
      const strip = document.getElementById("packet-strip");
      return !!strip && /Today|Connected Devices|Catalyst|Model Forge/i.test(strip.textContent || "");
    });
    entry.screenshot = await recordShot(page, "full-system-packet-strip");
  });

  await check("Settings modal opens with identity controls", async (entry) => {
    await dispatchClick(page, "#open-settings");
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Settings"));
    await page.waitForSelector("#save-identity-member");
    await page.waitForSelector("#save-identity-device");
    await page.waitForSelector("#save-identity-service");
    await page.waitForFunction(() => {
      const adaptation = document.getElementById("identity-member-adaptation")?.textContent || "";
      const learning = document.getElementById("identity-member-learning-review")?.textContent || "";
      return /Headline|Adaptive persona snapshot unavailable/i.test(adaptation)
        && /Learning governance|Learning review unavailable/i.test(learning);
    });
    entry.screenshot = await recordShot(page, "full-system-settings-modal");
  });

  await check("Connected devices admin view opens and renders registry", async (entry) => {
    await closeModalIfVisible(page);
    await openPacket(page, "connected-devices");
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Connected Devices"));
    await page.waitForSelector("#connected-devices-summary");
    await page.waitForSelector("#connected-devices-list");
    await page.waitForFunction(() => {
      const summary = document.getElementById("connected-devices-summary")?.textContent || "";
      return /Total known devices/i.test(summary);
    });
    const bodyText = (await page.locator("#modal-body").textContent()) || "";
    assert(/Total known devices/i.test(bodyText), "Connected devices summary did not render");
    assert(/Save Mapping|No device sessions have been registered yet/i.test(bodyText), "Connected devices registry did not render actionable content");
    assert(bodyText.trim().length > 0, "Connected devices registry body stayed empty");
    entry.screenshot = await recordShot(page, "full-system-connected-devices");
  });

  await check("Tasks packet opens and renders assistant-core queue", async (entry) => {
    await checkApiResponse("/api/assistant-core/tick", (data) => {
      assert(Boolean(data.assistant_surface), "Assistant Core tick missing assistant_surface");
      assert(Boolean(data.open_loops), "Assistant Core tick missing open_loops");
      assert(Boolean(data.today_board), "Assistant Core tick missing today_board");
      assert(Boolean(data.cognitive), "Assistant Core tick missing cognitive snapshot");
      assert(Array.isArray(data.open_loops?.items), "Assistant Core open_loops missing items");
      assert(Array.isArray(data.open_loops?.task_lanes), "Assistant Core open_loops missing task lanes");
      assert(Array.isArray(data.assistant_surface?.signal_chips), "Assistant Core surface missing signal chips");
      assert(Array.isArray(data.assistant_surface?.briefing_lines), "Assistant Core surface missing briefing lines");
    });
    await checkApiResponse("/api/explainability", (data) => {
      assert(Array.isArray(data.approval_history), "Explainability missing approval_history");
      assert(Array.isArray(data.assistant_actions), "Explainability missing assistant_actions");
      assert(Array.isArray(data.assistant_outcomes), "Explainability missing assistant_outcomes");
    });
    entry.details = "Validated via /api/assistant-core/tick and /api/explainability";
  });

  await check("Approval Queue packet opens and renders autonomy audit", async (entry) => {
    await closeModalIfVisible(page);
    await openPacket(page, "approvals");
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Approval Queue"));
    const body = page.locator("#modal-body");
    await body.waitFor();
    const bodyText = (await body.textContent()) || "";
    assert(/Pending/i.test(bodyText), "Approval Queue did not render pending approvals");
    assert(/Explainability/i.test(bodyText), "Approval Queue did not render explainability");
    assert(/Autonomy Audit/i.test(bodyText), "Approval Queue did not render autonomy audit");
    assert(/Total actions|No recent autonomous actions/i.test(bodyText), "Approval Queue did not render audit detail");
    entry.screenshot = await recordShot(page, "full-system-approval-queue");
  });

  await check("Finance packet opens and renders weekly money review", async (entry) => {
    await checkApiResponse("/api/finance-review?actor=Chris", (data) => {
      assert(typeof data.title === "string" && data.title.length > 0, "Finance review missing title");
      assert(typeof data.summary === "string", "Finance review missing summary");
      assert(Array.isArray(data.sections) && data.sections.length > 0, "Finance review missing sections");
      assert(data.sections.some((item) => /scorecard/i.test(String(item.title || ""))), "Finance review missing scorecard section");
      assert(data.sections.some((item) => /weekly .*money review/i.test(String(item.title || ""))), "Finance review missing weekly review section");
      assert(data.sections.some((item) => /threshold/i.test(String(item.title || ""))), "Finance review missing threshold section");
    });
    entry.details = "Validated via /api/finance-review?actor=Chris";
  });

  await check("Marketing packet opens and renders weekly marketing review", async (entry) => {
    await checkApiResponse("/api/marketing-review?actor=Chris", (data) => {
      assert(typeof data.title === "string" && data.title.length > 0, "Marketing review missing title");
      assert(typeof data.summary === "string", "Marketing review missing summary");
      assert(Array.isArray(data.sections) && data.sections.length > 0, "Marketing review missing sections");
      assert(data.sections.some((item) => /scorecard/i.test(String(item.title || ""))), "Marketing review missing scorecard section");
      assert(data.sections.some((item) => /weekly marketing review/i.test(String(item.title || ""))), "Marketing review missing weekly review section");
      assert(data.sections.some((item) => /campaign health/i.test(String(item.title || ""))), "Marketing review missing campaign health section");
    });
    entry.details = "Validated via /api/marketing-review?actor=Chris";
  });

  await check("Pipeline packet opens and renders daily and weekly review state", async (entry) => {
    await checkApiResponse("/api/pipeline-review?actor=Chris", (data) => {
      assert(typeof data.title === "string" && data.title.length > 0, "Pipeline review missing title");
      assert(typeof data.summary === "string", "Pipeline review missing summary");
      assert(Array.isArray(data.sections) && data.sections.length > 0, "Pipeline review missing sections");
      assert(data.sections.some((item) => /scorecard/i.test(String(item.title || ""))), "Pipeline review missing scorecard section");
      assert(data.sections.some((item) => /daily and weekly reviews/i.test(String(item.title || ""))), "Pipeline review missing daily/weekly review section");
      assert(data.sections.some((item) => /stalled opportunities/i.test(String(item.title || ""))), "Pipeline review missing stalled opportunities section");
    });
    entry.details = "Validated via /api/pipeline-review?actor=Chris";
  });

  await check("Vision packet opens and renders evidence layer", async (entry) => {
    await closeModalIfVisible(page);
    await openPacket(page, "vision");
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Vision"));
    const body = page.locator("#modal-body");
    await body.waitFor();
    const bodyText = (await body.textContent()) || "";
    await page.waitForSelector("#vision-device");
    await page.waitForSelector("#vision-mode");
    await page.waitForSelector("#vision-start");
    await page.waitForSelector("#vision-capture");
    await page.waitForSelector("#vision-retake");
    assert(/On-demand only|No background watching|Single-frame analysis/i.test(bodyText), "Vision packet did not render on-demand capture posture");
    assert(/Calibration|Capture Frame|Retake/i.test(bodyText), "Vision packet did not render vision controls");
    entry.screenshot = await recordShot(page, "full-system-vision-evidence");
  });

  await check("House packet opens and renders environment status", async (entry) => {
    await checkApiResponse("/api/environment-status?actor=Chris", (data) => {
      assert(typeof data.status === "string" && data.status.length > 0, "Environment status missing overall status");
      assert(Boolean(data.status_summary), "Environment status missing status summary");
      assert(Array.isArray(data.summary), "Environment status missing summary");
      assert(Array.isArray(data.adapters), "Environment status missing adapters");
      assert(Boolean(data.device_status?.summary), "Environment status missing device summary");
      assert(Boolean(data.anomaly_escalation), "Environment status missing anomaly escalation");
      assert(Boolean(data.freshness), "Environment status missing freshness metadata");
    });
    entry.details = "Validated via /api/environment-status?actor=Chris";
  });

  await check("Today Board packet opens and renders autonomy surface", async (entry) => {
    await checkApiResponse("/api/today-board?actor=Chris", (data) => {
      assert(Array.isArray(data.priorities), "Today Board missing priorities");
      assert(Array.isArray(data.carry), "Today Board missing carry");
      assert(Array.isArray(data.autonomy), "Today Board missing autonomy");
      assert(Boolean(data.cognition), "Today Board missing cognition");
      assert(Boolean(data.cognition?.cadence), "Today Board missing cadence");
      assert(Boolean(data.cognition?.world_state), "Today Board missing world state");
      assert(Boolean(data.assistant_notifications?.summary), "Today Board missing assistant notifications summary");
      assert(Boolean(data.notification_policy), "Today Board missing notification policy");
      assert(Boolean(data.freshness), "Today Board missing freshness metadata");
      assert(data.freshness.surface === "today_board", "Today Board freshness surface mismatch");
    });
    entry.details = "Validated via /api/today-board?actor=Chris";
  });

  await check("Cadence Review packet opens with phase-aware review content", async (entry) => {
    await checkApiResponse("/api/cadence-review?actor=Chris", (data) => {
      assert(typeof data.title === "string" && data.title.length > 0, "Cadence review missing title");
      assert(typeof data.digest === "string" && data.digest.length > 0, "Cadence review missing digest");
      assert(typeof data.summary === "string" && data.summary.length > 0, "Cadence review missing summary");
      assert(Array.isArray(data.completion_criteria), "Cadence review missing completion criteria");
      assert(Array.isArray(data.history), "Cadence review missing history");
      assert(Array.isArray(data.sections) && data.sections.length > 0, "Cadence review missing sections");
      assert(typeof data.why_this_surfaced === "string" && data.why_this_surfaced.length > 0, "Cadence review missing why_this_surfaced");
    });
    entry.details = "Validated via /api/cadence-review?actor=Chris";
  });

  await check("Catalyst workspace packet opens and routes", async (entry) => {
    const homeResponse = await fetchResponse("/catalyst/view/home", {}, report);
    assert(homeResponse.ok, `/catalyst/view/home returned ${homeResponse.status}`);
    assert(/Catalyst/i.test(homeResponse.text), "Catalyst home view did not render Catalyst markup");
    const calendarResponse = await fetchResponse("/catalyst/view/calendar", {}, report);
    assert(calendarResponse.ok, `/catalyst/view/calendar returned ${calendarResponse.status}`);
    assert(/Catalyst|Calendar/i.test(calendarResponse.text), "Catalyst calendar view did not render expected content");
    entry.details = "Validated via /catalyst/view/home and /catalyst/view/calendar";
  });

  await check("Talk button remains interactive after modal navigation", async (entry) => {
    await closeModalIfVisible(page);
    await page.waitForTimeout(300);
    await page.click("#voice-command");
    await page.waitForTimeout(800);
    const stateLabel = (await page.locator("#state-label").textContent()) || "";
    assert(stateLabel.trim().length > 0, "State label cleared after Talk click");
    entry.details = `State after Talk click: ${stateLabel}`;
    entry.screenshot = await recordShot(page, "full-system-talk-state");
  });

  await browser.close();
  browser = null;
  finalized = true;
  finalizeReport(report);
  process.stdout.write(`${REPORT_PATH}\n`);
  process.stdout.write(JSON.stringify(report, null, 2));

  if (report.summary.failed > 0) {
    process.exitCode = 1;
  }
}

Promise.race([
  run(),
  new Promise((_, reject) => {
    setTimeout(() => {
      reject(new Error(`Full-system battery exceeded ${RUN_TIMEOUT_MS}ms`));
    }, RUN_TIMEOUT_MS);
  }),
]).catch((error) => {
  let fallback = null;
  try {
    fallback = fs.existsSync(REPORT_PATH) ? JSON.parse(fs.readFileSync(REPORT_PATH, "utf8")) : createReport();
  } catch {
    fallback = createReport();
  }
  fallback.failures.push({
    name: "runner",
    error: error && error.stack ? error.stack : String(error),
    classification: "runner",
  });
  fallback.summary.failed += 1;
  fallback.summary.runner_failures += 1;
  fallback.finished_at = new Date().toISOString();
  writeReport(fallback);
  console.error(error);
  process.exit(1);
});
