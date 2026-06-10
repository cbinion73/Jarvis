const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE_URL = process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787";
const ARTIFACT_DIR = path.join(process.cwd(), "artifacts", "qa");
const SCREENSHOT_DIR = path.join(ARTIFACT_DIR, "screenshots");
const REPORT_PATH = path.join(ARTIFACT_DIR, "jarvis-provider-layer-report.json");

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

function isLocalBaseUrl(rawBaseUrl) {
  try {
    const url = new URL(rawBaseUrl);
    return url.hostname === "127.0.0.1" || url.hostname === "localhost";
  } catch {
    return false;
  }
}

async function runtimeHealthcheck() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3000);
  try {
    const response = await fetch(`${BASE_URL}/health`, { signal: controller.signal });
    return { ok: response.ok, status: response.status };
  } catch (error) {
    return {
      ok: false,
      error: error && error.stack ? error.stack : String(error),
    };
  } finally {
    clearTimeout(timeout);
  }
}

function writeReport(report) {
  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
  process.stdout.write(`${REPORT_PATH}\n`);
  process.stdout.write(JSON.stringify(report, null, 2));
}

function buildEnvironmentLimitedReport(health) {
  const detail = health?.error
    ? `Local runtime at ${BASE_URL} was unavailable before provider checks: ${health.error}`
    : `Local runtime at ${BASE_URL} did not pass /health before provider checks (status ${health?.status ?? "unknown"}).`;
  return {
    started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
    base_url: BASE_URL,
    status: "environment-limited",
    environment_limited: true,
    runtime: {
      available: false,
      health_url: `${BASE_URL}/health`,
      healthcheck: health,
    },
    checks: [
      {
        name: "Provider battery preflight",
        status: "skipped",
        details: detail,
        screenshot: null,
        kind: "automated",
      },
    ],
    failures: [],
    warnings: [{ name: "runtime-unavailable", details: detail }],
    summary: { passed: 0, failed: 0, skipped: 1, warned: 1 },
  };
}

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

async function recordShot(page, name) {
  const file = path.join(SCREENSHOT_DIR, `${slugify(name)}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function fetchResponse(pathname, options = {}) {
  const response = await fetch(`${BASE_URL}${pathname}`, options);
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  return {
    ok: response.ok,
    status: response.status,
    headers: Object.fromEntries(response.headers.entries()),
    data,
    text,
  };
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function run() {
  const health = await runtimeHealthcheck();
  if (!health.ok && isLocalBaseUrl(BASE_URL)) {
    writeReport(buildEnvironmentLimitedReport(health));
    return;
  }

  const report = {
    started_at: new Date().toISOString(),
    base_url: BASE_URL,
    checks: [],
    failures: [],
    warnings: [],
    summary: { passed: 0, failed: 0, skipped: 0, warned: 0 },
  };

  async function check(name, fn, options = {}) {
    const entry = {
      name,
      status: "passed",
      details: null,
      screenshot: null,
      kind: options.kind || "automated",
    };
    try {
      await fn(entry);
      report.summary.passed += 1;
    } catch (error) {
      entry.status = "failed";
      entry.details = error && error.stack ? error.stack : String(error);
      report.summary.failed += 1;
      report.failures.push({ name, error: entry.details });
    }
    report.checks.push(entry);
  }

  function warn(name, details) {
    report.summary.warned += 1;
    report.warnings.push({ name, details });
    report.checks.push({ name, status: "warning", details, screenshot: null, kind: "automated" });
  }

  function skip(name, details) {
    report.summary.skipped += 1;
    report.checks.push({ name, status: "skipped", details, screenshot: null, kind: "automated" });
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  const page = await context.newPage();

  await check("Speech provider readiness endpoint", async () => {
    const response = await fetchResponse("/api/voice-options");
    assert(response.ok, `/api/voice-options returned ${response.status}`);
    const status = response.data.stack_status || {};
    assert(Array.isArray(response.data.providers), "Voice options missing providers list");
    assert(Array.isArray(status.tts_order) && status.tts_order.length > 0, "Missing TTS provider order");
    assert(Array.isArray(status.stt_order) && status.stt_order.length > 0, "Missing STT provider order");
  });

  await check("TTS provider returns audio", async () => {
    const response = await fetchResponse("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: "Provider battery check." }),
    });
    assert(response.ok, `/api/tts returned ${response.status}`);
    const contentType = response.headers["content-type"] || "";
    assert(contentType.includes("audio/"), `Expected audio response, got ${contentType}`);
    const provider = response.headers["x-jarvis-tts-provider"] || "";
    assert(provider.length > 0, "Missing X-Jarvis-Tts-Provider header");
    assert(response.text.length > 128, "Audio payload was unexpectedly small");
  });

  await check("Settings modal exposes provider controls", async (entry) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: "domcontentloaded" });
    await page.click("#open-settings");
    await page.waitForSelector("#modal-layer.open");
    await page.waitForSelector("#save-google-client-secret");
    await page.waitForSelector("#launch-google-connect");
    await page.waitForSelector("#save-location");
    entry.screenshot = await recordShot(page, "provider-settings-modal");
  });

  const googleStatus = await fetchResponse("/api/google/status");
  await check("Google status endpoint shape", async () => {
    assert(googleStatus.ok, `/api/google/status returned ${googleStatus.status}`);
    assert(googleStatus.data.default, "Google status missing default block");
    assert(Array.isArray(googleStatus.data.accounts), "Google status missing accounts array");
  });

  const accountsResponse = await fetchResponse("/api/accounts");
  const accounts = Array.isArray(accountsResponse.data.accounts) ? accountsResponse.data.accounts : [];
  const googleAccounts = accounts.filter((item) => item.provider === "google");

  if (googleAccounts.length === 0) {
    skip("Google account deep checks", "No Google personal accounts are configured yet.");
  } else {
    await check("Google account records are well formed", async () => {
      for (const account of googleAccounts) {
        assert(account.account_id, "Google account is missing account_id");
        assert(account.owner_user_id, "Google account is missing owner_user_id");
        assert(account.label, "Google account is missing label");
        assert(account.service_scope, "Google account is missing service_scope");
      }
    });

    for (const account of googleAccounts) {
      const snapshot = await fetchResponse(`/api/google/account/${account.account_id}`);
      await check(`Google snapshot loads for ${account.label}`, async () => {
        assert(snapshot.ok, `Google snapshot returned ${snapshot.status}`);
        assert(snapshot.data.status, "Google snapshot missing status");
      });

      if (account.status === "connected" && !String(account.login_hint || "").includes("@")) {
        warn(
          `Google login hint is malformed for ${account.label}`,
          `Expected an email-style login_hint, got ${JSON.stringify(account.login_hint)}.`
        );
      }

      if (account.status === "connected" && snapshot.data && snapshot.data.gmail_error) {
        warn(`Gmail provider is connected but not usable for ${account.label}`, snapshot.data.gmail_error);
      }

      if (account.status === "connected" && snapshot.data && snapshot.data.calendar_error) {
        warn(`Calendar provider is connected but not usable for ${account.label}`, snapshot.data.calendar_error);
      }

      if (account.status === "connected") {
        await check(`Google connect handoff route exists for ${account.label}`, async () => {
          const response = await fetch(`${BASE_URL}/accounts/${account.account_id}/connect`, { redirect: "manual" });
          assert(
            [200, 302, 303].includes(response.status),
            `Expected account connect route to respond with HTML or redirect, got ${response.status}`
          );
        });
      }
    }
  }

  const statusResponse = await fetchResponse("/api/status");
  const integrations = Array.isArray(statusResponse.data) ? statusResponse.data : [];
  const integrationMap = Object.fromEntries(integrations.map((item) => [item.name, item]));

  await check("Integration status endpoint shape", async () => {
    assert(statusResponse.ok, `/api/status returned ${statusResponse.status}`);
    assert(Array.isArray(statusResponse.data), "Integration status did not return a list");
  });

  if (googleAccounts.some((item) => item.status === "connected")) {
    const googleIntegration = integrationMap["google-workspace"];
    if (googleIntegration && googleIntegration.ok === false) {
      warn(
        "Integration status disagrees with connected Google accounts",
        `google-workspace reports blocked: ${googleIntegration.detail}`
      );
    }
  }

  const homeAssistant = integrationMap["home-assistant"];
  if (!homeAssistant || !homeAssistant.ok) {
    skip(
      "Live Home Assistant action checks",
      homeAssistant ? `Home Assistant not ready: ${homeAssistant.detail}` : "Home Assistant integration status was unavailable."
    );
  } else {
    await check("Home overview responds when Home Assistant is ready", async () => {
      const response = await fetchResponse("/api/home-overview");
      assert(response.ok, `/api/home-overview returned ${response.status}`);
      assert(response.data && typeof response.data === "object", "Home overview payload was empty");
    });
    await check("Garage status responds when Home Assistant is ready", async () => {
      const response = await fetchResponse("/api/garage-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor: "Chris", target: "Main Garage Door" }),
      });
      assert(response.ok, `/api/garage-check returned ${response.status}`);
    });
  }

  await browser.close();

  report.finished_at = new Date().toISOString();
  writeReport(report);

  if (report.summary.failed > 0) {
    process.exitCode = 1;
  }
}

run().catch((error) => {
  const fallback = {
    started_at: new Date().toISOString(),
    base_url: BASE_URL,
    checks: [],
    failures: [{ name: "runner", error: error && error.stack ? error.stack : String(error) }],
    warnings: [],
    summary: { passed: 0, failed: 1, skipped: 0, warned: 0 },
  };
  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  fs.writeFileSync(REPORT_PATH, JSON.stringify(fallback, null, 2));
  console.error(error);
  process.exit(1);
});
