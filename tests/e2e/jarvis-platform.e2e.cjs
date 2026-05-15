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
  const page = await context.newPage();

  await check("HTTP root responds", async (entry) => {
    const response = await fetch(`${BASE_URL}/`);
    const body = await response.text();
    assert(response.ok, `Expected 200 from /, got ${response.status}`);
    assert(body.includes("JARVIS Voice Shell"), "Root HTML did not include JARVIS Voice Shell");
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

  await check("Voice shell loads", async (entry) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector("#command-input");
    await page.waitForSelector("#voice-command");
    await page.waitForSelector("#open-settings", { state: "attached" });
    await page.waitForSelector("#packet-strip-toggle", { state: "attached" });
    await page.waitForSelector(".core-stage");
    await page.waitForTimeout(1200);
    const stateLabel = await page.locator("#state-label").textContent();
    assert(/idle/i.test(stateLabel || ""), `Expected state label to start idle, got ${stateLabel}`);
    entry.screenshot = await recordShot(page, "voice-shell-home");
  });

  await check("Packet rail expands", async (entry) => {
    await page.evaluate(() => {
      const button = document.getElementById("packet-strip-toggle");
      if (!button) throw new Error("packet-strip-toggle not found");
      button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    });
    await page.waitForTimeout(250);
    const strip = page.locator("#packet-strip");
    await strip.waitFor();
    const text = await strip.textContent();
    assert((text || "").includes("Approvals"), "Packet strip did not show packet buttons");
    entry.screenshot = await recordShot(page, "packet-strip-expanded");
  });

  await check("Settings modal opens with platform controls", async (entry) => {
    await page.click("#open-settings", { force: true });
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Settings"));
    await page.waitForSelector("#save-location");
    await page.waitForSelector("#save-google-client-secret");
    await page.waitForSelector("#launch-google-connect");
    const bodyClass = await page.locator("body").getAttribute("class");
    assert((bodyClass || "").includes("modal-open"), "Body did not enter modal-open state");
    entry.screenshot = await recordShot(page, "settings-modal");
  });

  await check("Mode panel can change household mode", async (entry) => {
    await page.click("#close-modal");
    await page.waitForTimeout(200);
    const before = await fetchJson("/api/mode");
    assert(before.ok, "Could not read initial mode");
    await page.click("#mode-toggle");
    await page.waitForSelector("#mode-panel.open");
    const options = await page.locator("#mode-select option").evaluateAll((nodes) =>
      nodes.map((node) => ({ value: node.value, text: node.textContent }))
    );
    const current = before.data.mode;
    const next = options.find((item) => item.value !== current) || options[0];
    assert(next && next.value, "Could not find alternate mode option");
    await page.selectOption("#mode-select", next.value);
    await page.fill("#mode-reason", "Automated E2E mode transition check.");
    await page.click("#mode-panel-apply");
    await page.waitForTimeout(500);
    const after = await fetchJson("/api/mode");
    assert(after.ok, "Could not read updated mode");
    assert(after.data.mode === next.value, `Expected mode ${next.value}, got ${after.data.mode}`);
    entry.screenshot = await recordShot(page, "mode-panel-updated");
  });

  await check("Location settings persist a saved location", async (entry) => {
    await page.click("#open-settings", { force: true });
    await page.waitForSelector("#modal-layer.open");
    const label = `QA Location ${Date.now()}`;
    await page.fill("#location-label", label);
    await page.fill("#location-geography", "Alexandria, Kentucky");
    await page.fill("#location-latitude", "38.9598");
    await page.fill("#location-longitude", "-84.3877");
    await page.fill("#location-notes", "Automated QA location check.");
    await page.click("#save-location");
    await page.waitForTimeout(700);
    const settings = await fetchJson("/api/location-settings");
    assert(settings.ok, "Location settings POST did not leave endpoint readable");
    assert(
      Array.isArray(settings.data.saved_locations) &&
        settings.data.saved_locations.some((item) => item.label === label),
      `Saved locations did not include ${label}`
    );
    assert(settings.data.active_location?.label === label, "Saved location was not made active");
    entry.screenshot = await recordShot(page, "location-settings-saved");
  });

  await check("Catalyst workspace opens as modal app", async (entry) => {
    await page.click("#close-modal");
    await page.waitForTimeout(200);
    await page.evaluate(() => {
      if (typeof window.__jarvisOpenPacket !== "function") throw new Error("openPacket helper not available");
      window.__jarvisOpenPacket("catalyst");
    });
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Catalyst Workspace"));
    await page.waitForSelector("#catalyst-workspace-frame");
    const frame = page.locator("#catalyst-workspace-frame");
    await page.waitForTimeout(1200);
    const src = await frame.getAttribute("src");
    assert(src && src.includes("/catalyst/view/home"), `Expected catalyst home iframe, got ${src}`);
    const calendarTab = page.locator('[data-catalyst-page="calendar"]').first();
    await calendarTab.click();
    await page.waitForTimeout(400);
    const nextSrc = await frame.getAttribute("src");
    assert(nextSrc && nextSrc.includes("/catalyst/view/calendar"), `Expected calendar iframe, got ${nextSrc}`);
    entry.screenshot = await recordShot(page, "catalyst-workspace");
  });

  await check("Modal state hides packet rail and shrinks core", async (entry) => {
    const packetToggleBox = await page.locator("#packet-strip-toggle").boundingBox();
    assert(packetToggleBox === null, "Packet toggle should be hidden while modal is open");
    const coreStage = page.locator(".core-stage");
    const transform = await coreStage.evaluate((node) => getComputedStyle(node).transform);
    assert(transform && transform !== "none", "Core stage transform did not change during modal state");
    entry.details = `Core transform during modal: ${transform}`;
  });

  await check("Talk button remains interactive", async (entry) => {
    await page.click("#close-modal");
    await page.waitForTimeout(300);
    await page.click("#voice-command");
    await page.waitForTimeout(800);
    const stateLabel = (await page.locator("#state-label").textContent()) || "";
    assert(stateLabel.trim().length > 0, "State label cleared after Talk click");
    entry.details = `State after Talk click: ${stateLabel}`;
    entry.screenshot = await recordShot(page, "talk-button-state");
  });

  await browser.close();

  report.finished_at = new Date().toISOString();
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));

  process.stdout.write(`${REPORT_PATH}\n`);
  process.stdout.write(JSON.stringify(report, null, 2));

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
    summary: { passed: 0, failed: 1 },
  };
  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  fs.writeFileSync(REPORT_PATH, JSON.stringify(fallback, null, 2));
  console.error(error);
  process.exit(1);
});
