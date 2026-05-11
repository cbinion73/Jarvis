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

async function closeModalIfVisible(page) {
  const close = page.locator("#close-modal");
  if (await close.isVisible().catch(() => false)) {
    await close.click({ force: true });
    await page.waitForTimeout(200);
  }
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
  const response = await fetch(`${BASE_URL}${pathname}`, {
    ...options,
    signal: AbortSignal.timeout(API_TIMEOUT_MS),
  });
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
        assert(Array.isArray(data.devices), "Connected devices missing devices array");
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
        if (data.assistant_actions.length) {
          assert(typeof data.assistant_actions[0].action_class === "string", "Explainability assistant action missing action_class");
          assert(typeof data.assistant_actions[0].policy_basis === "string", "Explainability assistant action missing policy_basis");
          assert(typeof data.assistant_actions[0].confidence === "string", "Explainability assistant action missing confidence");
          assert(typeof data.assistant_actions[0].result_summary === "string", "Explainability assistant action missing result_summary");
        }
      }],
      ["/api/open-loops", (data) => {
        assert(data.summary && typeof data.summary.total === "number", "Open loops missing summary");
        assert(Array.isArray(data.items), "Open loops missing items array");
        assert(Array.isArray(data.task_lanes), "Open loops missing task_lanes");
        assert(data.task_lanes.some((item) => item.domain === "growth"), "Open loops missing growth task lane");
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
        assert(Boolean(data.freshness), "Cadence review missing freshness metadata");
        assert(data.freshness.surface === "cadence_review", "Cadence review freshness surface mismatch");
      }],
      ["/api/cognitive?actor=Chris&include_graph=false", (data) => {
        assert(Boolean(data.self_model), "Cognitive snapshot missing self_model");
        assert(Boolean(data.world_state), "Cognitive snapshot missing world_state");
        assert(Boolean(data.growth_state), "Cognitive snapshot missing growth_state");
        assert(Boolean(data.goal_stack), "Cognitive snapshot missing goal_stack");
        assert(Boolean(data.cadence), "Cognitive snapshot missing cadence");
        assert(Array.isArray(data.cadence.loops), "Cognitive cadence missing loops");
        assert(data.cadence.loops.every((item) => Array.isArray(item.completion_criteria) && item.completion_criteria.length > 0), "Cognitive cadence loops missing completion criteria");
        assert(Boolean(data.deliberation), "Cognitive snapshot missing deliberation");
        assert(Boolean(data.internal_council), "Cognitive snapshot missing internal_council");
        assert(Array.isArray(data.growth_state.lanes), "Growth state missing lanes");
        assert(Boolean(data.freshness), "Cognitive snapshot missing freshness metadata");
        assert(data.freshness.surface === "cognitive", "Cognitive freshness surface mismatch");
      }],
      ["/api/cognitive/world-state?actor=Chris", (data) => {
        assert(Boolean(data.summary), "World state missing summary");
        assert(Boolean(data.delta), "World state missing delta");
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
    });

    await checkApiResponse("/api/persona-snapshot?actor=Chris&refresh=true", (data) => {
      assert(data.digital_twin, "Persona snapshot missing digital_twin");
    });

    await checkApiResponse("/api/learning-review?viewer=Chris&subject_user_id=chris", (data) => {
      assert(Array.isArray(data.profile_facts), "Learning review missing profile_facts");
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
    await page.waitForSelector("#open-settings");
    await page.waitForSelector("#packet-strip-toggle");
    await page.waitForSelector(".core-stage");
    const stateLabel = await page.locator("#state-label").textContent();
    assert((stateLabel || "").trim().length > 0, "State label was empty on initial load");
    entry.screenshot = await recordShot(page, "full-system-home-shell");
  });

  await check("Packet rail expands with current packet set", async (entry) => {
    await page.click("#packet-strip-toggle");
    await page.waitForTimeout(300);
    await page.waitForSelector('[data-packet="today"]');
    await page.waitForSelector('[data-packet="connected-devices"]');
    await page.waitForSelector('[data-packet="catalyst"]');
    await page.waitForSelector('[data-packet="model-forge"]');
    entry.screenshot = await recordShot(page, "full-system-packet-strip");
  });

  await check("Settings modal opens with identity controls", async (entry) => {
    await page.click("#open-settings");
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Settings"));
    await page.waitForSelector("#save-identity-member");
    await page.waitForSelector("#save-identity-device");
    await page.waitForSelector("#save-identity-service");
    entry.screenshot = await recordShot(page, "full-system-settings-modal");
  });

  await check("Connected devices admin view opens and renders registry", async (entry) => {
    await page.click("#close-modal");
    await page.waitForTimeout(200);
    await page.click('[data-packet="connected-devices"]');
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
    entry.screenshot = await recordShot(page, "full-system-connected-devices");
  });

  await check("Tasks packet opens and renders assistant-core queue", async (entry) => {
    await closeModalIfVisible(page);
    await page.locator('[data-packet="tasks"]').click({ force: true });
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Assistant Core"));
    const body = page.locator("#modal-body");
    await body.waitFor();
    const bodyText = (await body.textContent()) || "";
    assert(/Open Loops/i.test(bodyText), "Tasks packet did not render the open-loops block");
    assert(/Proactive Surface/i.test(bodyText), "Tasks packet did not render proactive surface");
    assert(/Task Lanes/i.test(bodyText), "Tasks packet did not render task lanes");
    assert(/Autonomy Audit/i.test(bodyText), "Tasks packet did not render autonomy audit");
    assert(/Waiting on you|Needs revisit|Staged/i.test(bodyText), "Tasks packet did not render queue metrics");
    entry.screenshot = await recordShot(page, "full-system-tasks-packet");
  });

  await check("Approval Queue packet opens and renders autonomy audit", async (entry) => {
    await closeModalIfVisible(page);
    await page.locator('[data-packet="approvals"]').click({ force: true });
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

  await check("Today Board packet opens and renders autonomy surface", async (entry) => {
    await closeModalIfVisible(page);
    await page.evaluate(() => {
      const button = document.querySelector('[data-packet="today"]');
      if (!button) {
        throw new Error("Today packet button not found");
      }
      button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    });
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Today Board"));
    const body = page.locator("#modal-body");
    const bodyText = (await body.textContent()) || "";
    assert(/Priorities/i.test(bodyText), "Today Board did not render priorities");
    assert(/Carry Today/i.test(bodyText), "Today Board did not render carry section");
    assert(/Autonomy Boundary/i.test(bodyText), "Today Board did not render autonomy boundary");
    assert(/Cognitive Posture/i.test(bodyText), "Today Board did not render cognitive posture");
    assert(/Cadence/i.test(bodyText), "Today Board did not render cognitive cadence");
    assert(/Active loop/i.test(bodyText), "Today Board did not render the active loop");
    assert(/World state/i.test(bodyText), "Today Board did not render world state");
    assert(/Growth pressure/i.test(bodyText), "Today Board did not render growth pressure");
    assert(/Growth Lanes/i.test(bodyText), "Today Board did not render growth lanes");
    assert(/Active review/i.test(bodyText), "Today Board did not render growth active review");
    assert(/Council consensus/i.test(bodyText), "Today Board did not render council consensus");
    assert(/Browser alerts/i.test(bodyText), "Today Board did not render browser alert controls");
    assert(/Inbox state/i.test(bodyText), "Today Board did not render inbox state metrics");
    assert(/Priority mix/i.test(bodyText), "Today Board did not render inbox priority metrics");
    entry.screenshot = await recordShot(page, "full-system-today-board");
  });

  await check("Cadence Review packet opens with phase-aware review content", async (entry) => {
    await closeModalIfVisible(page);
    await page.locator('[data-packet="review"]').click({ force: true });
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => {
      const title = document.getElementById("modal-title")?.textContent || "";
      const body = document.getElementById("modal-body")?.textContent || "";
      return title.trim().length > 0 && title !== "Packet" && /Cadence|Current Loop/i.test(body) && !/Loading Cadence Review/i.test(body);
    }, undefined, { timeout: 120000 });
    const body = page.locator("#modal-body");
    const bodyText = (await body.textContent()) || "";
    assert(/Cadence/i.test(bodyText), "Cadence Review did not render cadence section");
    assert(/Digest/i.test(bodyText), "Cadence Review did not render digest text");
    assert(/Completion Criteria/i.test(bodyText), "Cadence Review did not render completion criteria");
    assert(/Loop History/i.test(bodyText), "Cadence Review did not render loop history");
    assert(/Growth Review/i.test(bodyText), "Cadence Review did not render growth review section");
    assert(/Priority Tasks/i.test(bodyText), "Cadence Review did not render priority tasks");
    assert(/Assistant Inbox/i.test(bodyText), "Cadence Review did not render assistant inbox");
    assert(/Why this surfaced/i.test(bodyText), "Cadence Review did not render why-this-surfaced explanation");
    const reviewButtons = page.locator(".review-action-button");
    const reviewButtonCount = await reviewButtons.count();
    if (reviewButtonCount > 0) {
      const label = (await reviewButtons.first().textContent()) || "";
      assert(label.trim().length > 0, "Review action button was rendered without a label");
      entry.details = `Review action available: ${label.trim()}`;
    }
    entry.screenshot = await recordShot(page, "full-system-cadence-review");
  }, { timeout_ms: 120000 });

  await check("Catalyst workspace packet opens and routes", async (entry) => {
    await closeModalIfVisible(page);
    await page.locator('[data-packet="catalyst"]').click({ force: true });
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Catalyst Workspace"));
    await page.waitForSelector("#catalyst-workspace-frame");
    const frame = page.locator("#catalyst-workspace-frame");
    const src = await frame.getAttribute("src");
    assert(src && src.includes("/catalyst/view/home"), `Expected catalyst home iframe, got ${src}`);
    await page.click('[data-catalyst-page="calendar"]');
    await page.waitForTimeout(400);
    const nextSrc = await frame.getAttribute("src");
    assert(nextSrc && nextSrc.includes("/catalyst/view/calendar"), `Expected calendar iframe, got ${nextSrc}`);
    entry.screenshot = await recordShot(page, "full-system-catalyst");
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
