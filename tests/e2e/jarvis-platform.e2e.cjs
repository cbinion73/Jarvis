const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE_URL = process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787";
const ARTIFACT_DIR = path.join(process.cwd(), "artifacts", "qa");
const SCREENSHOT_DIR = path.join(ARTIFACT_DIR, "screenshots");
const REPORT_PATH = path.join(ARTIFACT_DIR, "jarvis-platform-report.json");

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

async function recordShot(page, name) {
  const file = path.join(SCREENSHOT_DIR, `${slugify(name)}.png`);
  await page.screenshot({ path: file, fullPage: true, timeout: 60000, animations: "disabled" });
  return file;
}

async function fetchJson(pathname, options = {}) {
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
    data,
    text,
  };
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
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

async function closeModalIfOpen(page) {
  await page.evaluate(() => {
    const layer = document.getElementById("modal-layer");
    const close = document.getElementById("close-modal");
    if (layer?.classList.contains("open") && close instanceof HTMLElement) {
      close.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    }
  });
}

async function run() {
  const startedAt = new Date().toISOString();
  const report = {
    started_at: startedAt,
    base_url: BASE_URL,
    checks: [],
    failures: [],
    summary: { passed: 0, failed: 0 },
  };

  async function check(name, fn) {
    const entry = { name, status: "passed", details: null, screenshot: null };
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

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 1000 } });
  await context.addInitScript(() => {
    window.localStorage.setItem("jarvis-claimed-user-v1", "e2e");
    window.sessionStorage.setItem("jarvis-wau-skipped", "1");
  });
  const page = await context.newPage();

  await check("HTTP root responds", async (entry) => {
    const response = await fetch(`${BASE_URL}/`);
    const body = await response.text();
    assert(response.ok, `Expected 200 from /, got ${response.status}`);
    assert(
      body.includes("JARVIS DAILY BRIEF") || body.includes("command-sidebar"),
      "Root HTML did not include expected glass-shell markers"
    );
    entry.details = "Root responded with the glass shell.";
  });

  await check("Core API smoke", async () => {
    const endpoints = [
      ["/api/dashboard", (data) => assert(Boolean(data.active_mode), "Dashboard missing active_mode")],
      ["/api/mode", (data) => assert(Boolean(data.mode), "Mode endpoint missing mode")],
      ["/api/location-settings", (data) => assert(Array.isArray(data.saved_locations), "Location settings missing saved_locations")],
      ["/api/voice-settings", (data) => assert(Boolean(data.settings || data.preferred_source || data.stack_status), "Voice settings shape unexpected")],
      ["/api/voice-options", (data) => assert(Boolean(data.stack_status), "Voice options missing stack_status")],
      ["/api/agents", (data) => {
        assert(data && typeof data.agents === "object", "Agents endpoint missing agents object");
        assert(Array.isArray(data.statuses), "Agents endpoint missing statuses array");
      }],
      ["/api/agent-registry", (data) => assert(Array.isArray(data.agents), "Agent registry missing agents array")],
      ["/api/memory-curator", (data) => assert(Boolean(data.rules || data.candidates), "Memory curator shape unexpected")],
      ["/api/accounts", (data) => assert(Array.isArray(data.accounts), "Accounts endpoint missing accounts array")],
      ["/api/catalyst-overview", (data) => assert(Boolean(data.counts), "Catalyst overview missing counts")],
      ["/catalyst/view/home", (html) => assert(String(html).includes("Catalyst"), "Catalyst home HTML did not render")],
    ];

    for (const [pathname, verify] of endpoints) {
      const response = await fetch(`${BASE_URL}${pathname}`);
      const text = await response.text();
      assert(response.ok, `${pathname} returned ${response.status}`);
      let data = text;
      if (response.headers.get("content-type")?.includes("application/json")) {
        data = JSON.parse(text);
      }
      verify(data);
    }
  });

  await check("Glass shell loads on root", async (entry) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".command-sidebar", { state: "attached" });
    await page.waitForSelector(".dailybrief-card", { state: "attached" });
    const bodyText = await page.locator("body").textContent();
    assert(/daily brief/i.test(bodyText || ""), "Glass root did not surface Daily Brief content");
    entry.screenshot = await recordShot(page, "glass-shell-root");
  });

  await check("Daily Brief module route loads", async (entry) => {
    await page.goto(`${BASE_URL}/briefing-center`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("body.module-surface", { state: "attached" });
    await page.waitForFunction(() => /JARVIS Daily Brief/i.test(document.body?.innerText || ""));
    await page.waitForFunction(() => /First Light/i.test(document.body?.innerText || ""));
    entry.screenshot = await recordShot(page, "glass-briefing-center");
  });

  await check("Calendar glass route starts calendar view", async (entry) => {
    await page.goto(`${BASE_URL}/calendar-center`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => window.__JARVIS_START_VIEW === "calendar");
    await page.waitForSelector(".calendar-sidebar");
    const text = await page.locator("body").textContent();
    assert(/calendar/i.test(text || ""), "Calendar glass route did not render calendar content");
    entry.screenshot = await recordShot(page, "glass-calendar-center");
  });

  await check("Email glass route starts email view", async (entry) => {
    await page.goto(`${BASE_URL}/email-center`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => window.__JARVIS_START_VIEW === "email");
    await page.waitForSelector(".email-sidebar");
    const text = await page.locator("body").textContent();
    assert(/email/i.test(text || ""), "Email glass route did not render email content");
    entry.screenshot = await recordShot(page, "glass-email-center");
  });

  await check("News glass route starts news view", async (entry) => {
    await page.goto(`${BASE_URL}/news-center`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => window.__JARVIS_START_VIEW === "news");
    const text = await page.locator("body").textContent();
    assert(/news/i.test(text || ""), "News glass route did not render news content");
    entry.screenshot = await recordShot(page, "glass-news-center");
  });

  await check("Social glass route starts social view", async (entry) => {
    await page.goto(`${BASE_URL}/social-center`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => window.__JARVIS_START_VIEW === "social");
    await page.waitForSelector(".social-sidebar");
    const text = await page.locator("body").textContent();
    assert(/social/i.test(text || ""), "Social glass route did not render social content");
    entry.screenshot = await recordShot(page, "glass-social-center");
  });

  await check("Voice shell remains explicitly available", async (entry) => {
    await page.goto(`${BASE_URL}/?theme=voice`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#command-input", { state: "attached" });
    await page.waitForSelector("#voice-command", { state: "attached" });
    await page.waitForSelector("#open-settings", { state: "attached" });
    await page.waitForSelector("#packet-strip-toggle", { state: "attached" });
    await page.waitForSelector(".core-stage", { state: "attached" });
    const stateLabel = await page.locator("#state-label").textContent();
    assert(/idle/i.test(stateLabel || ""), `Expected state label to start idle, got ${stateLabel}`);
    entry.screenshot = await recordShot(page, "voice-shell-explicit-route");
  });

  await context.close();
  await browser.close();

  report.finished_at = new Date().toISOString();
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));

  process.stdout.write(`${REPORT_PATH}\n`);
  process.stdout.write(JSON.stringify(report, null, 2));

  process.exit(report.summary.failed > 0 ? 1 : 0);
}

run().catch((error) => {
  const fallback = {
    started_at: new Date().toISOString(),
    base_url: BASE_URL,
    checks: [],
    failures: [{ name: "runner", error: error && error.stack ? error.stack : String(error) }],
    summary: { passed: 0, failed: 1 },
  };
  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  fs.writeFileSync(REPORT_PATH, JSON.stringify(fallback, null, 2));
  console.error(error);
  process.exit(1);
});
