const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const BASE_URL = process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787";
const ARTIFACT_DIR = path.join(process.cwd(), "artifacts", "qa");
const SCREENSHOT_DIR = path.join(ARTIFACT_DIR, "screenshots");
const REPORT_PATH = path.join(ARTIFACT_DIR, "jarvis-workbench-report.json");

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

async function ensureModelForgePackage() {
  const existing = await fetchResponse("/api/cad-packages");
  assert(existing.ok, `/api/cad-packages returned ${existing.status}`);
  if (Array.isArray(existing.data) && existing.data.length) {
    return existing.data[0];
  }

  const create = await fetchResponse("/api/cad-package", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      actor: "Chris",
      part: "QA bracket",
      family: "bracket",
      printer: "bambu-x1c",
      profile: "functional-prototype",
      dimensions: "hole spacing 110 mm, plate width 30 mm, thickness 8 mm, bend radius 12 mm",
      constraints: "Preserve mounting geometry and ensure a fit-check STL is exported.",
    }),
  });
  assert(create.ok, `/api/cad-package returned ${create.status}`);
  assert(create.data && create.data.package_id, "CAD package create did not return a package_id");

  const detail = await fetchResponse(`/api/model-forge/package/${encodeURIComponent(create.data.package_id)}`);
  assert(detail.ok, `Model forge detail returned ${detail.status}`);
  return detail.data;
}

async function run() {
  const report = {
    started_at: new Date().toISOString(),
    base_url: BASE_URL,
    checks: [],
    failures: [],
    warnings: [],
    summary: { passed: 0, failed: 0, warned: 0, skipped: 0 },
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

  const packageSeed = await ensureModelForgePackage();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1680, height: 1080 } });
  await context.grantPermissions(["camera"], { origin: BASE_URL });
  const page = await context.newPage();

  await page.addInitScript(() => {
    const mediaDevices = {
      async enumerateDevices() {
        return [{ kind: "videoinput", deviceId: "stub-camera-1", label: "Workbench Camera" }];
      },
      async getUserMedia() {
        const canvas = document.createElement("canvas");
        canvas.width = 1280;
        canvas.height = 720;
        const context = canvas.getContext("2d");
        if (context) {
          context.fillStyle = "#0b1730";
          context.fillRect(0, 0, canvas.width, canvas.height);
          context.fillStyle = "#78f0ff";
          context.fillRect(80, 80, 420, 180);
          context.fillStyle = "#d9f6ff";
          context.font = "48px sans-serif";
          context.fillText("Workbench Camera", 110, 180);
        }
        const stream = canvas.captureStream(1);
        const [track] = stream.getVideoTracks();
        if (track) {
          track.getSettings = () => ({ deviceId: "stub-camera-1" });
        }
        return stream;
      },
    };
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: mediaDevices,
    });
    HTMLMediaElement.prototype.play = async function play() {
      return Promise.resolve();
    };
    Object.defineProperty(HTMLVideoElement.prototype, "videoWidth", {
      configurable: true,
      get() {
        return 1280;
      },
    });
    Object.defineProperty(HTMLVideoElement.prototype, "videoHeight", {
      configurable: true,
      get() {
        return 720;
      },
    });
  });

  await page.goto(`${BASE_URL}/`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("#packet-strip-toggle", { state: "attached" });

  await check("Model Forge endpoints expose a complete package", async () => {
    const machineOptions = await fetchResponse("/api/workshop-machine-options");
    assert(machineOptions.ok, `/api/workshop-machine-options returned ${machineOptions.status}`);
    assert(Array.isArray(machineOptions.data.families), "Machine options missing families");
    assert(Array.isArray(machineOptions.data.printers), "Machine options missing printers");

    const detail = await fetchResponse(`/api/model-forge/package/${encodeURIComponent(packageSeed.package_id)}`);
    assert(detail.ok, `Package detail returned ${detail.status}`);
    assert(detail.data.part_name, "Package detail missing part_name");
    assert(detail.data.script_path, "Package detail missing script_path");

    const stl = await fetchResponse(`/api/model-forge/package/${encodeURIComponent(packageSeed.package_id)}/download/stl`);
    assert(stl.ok, `STL download returned ${stl.status}`);
    assert((stl.headers["content-type"] || "").includes("model/stl"), `Unexpected STL content type: ${stl.headers["content-type"]}`);

    const step = await fetchResponse(`/api/model-forge/package/${encodeURIComponent(packageSeed.package_id)}/download/step`);
    assert(step.ok, `STEP download returned ${step.status}`);

    const mesh3mf = await fetchResponse(`/api/model-forge/package/${encodeURIComponent(packageSeed.package_id)}/download/3mf`);
    assert(mesh3mf.ok, `3MF download returned ${mesh3mf.status}`);

    const slicerPack = await fetchResponse(`/api/model-forge/package/${encodeURIComponent(packageSeed.package_id)}/download/slicer-pack`);
    assert(slicerPack.ok, `Slicer pack download returned ${slicerPack.status}`);
    assert((slicerPack.headers["content-type"] || "").includes("zip"), `Unexpected slicer pack content type: ${slicerPack.headers["content-type"]}`);
  });

  await check("Model Forge modal renders controls and viewer state", async (entry) => {
    await page.evaluate(() => {
      if (typeof window.__jarvisOpenPacket !== "function") throw new Error("openPacket helper not available");
      window.__jarvisOpenPacket("model-forge");
    });
    await page.waitForSelector("#modal-layer.open");
    await page.evaluate(() => {
      const activate = (name) => {
        document.querySelectorAll(".model-forge-tab").forEach((node) => node.classList.remove("active"));
        document.querySelectorAll(".model-forge-tab-panel").forEach((node) => node.classList.remove("active"));
        document.querySelector(`[data-model-forge-tab="${name}"]`)?.classList.add("active");
        document.querySelector(`[data-model-forge-panel="${name}"]`)?.classList.add("active");
      };
      activate("create");
    });
    await page.waitForSelector("#model-forge-family", { state: "attached" });
    await page.waitForSelector("#model-forge-printer", { state: "attached" });
    await page.waitForSelector("#model-forge-profile", { state: "attached" });
    await page.waitForSelector("#model-forge-slicer", { state: "attached" });
    await page.waitForFunction(() => {
      const family = document.getElementById("model-forge-family");
      const printer = document.getElementById("model-forge-printer");
      const profile = document.getElementById("model-forge-profile");
      return Boolean(
        family instanceof HTMLSelectElement &&
        family.options.length > 0 &&
        printer instanceof HTMLSelectElement &&
        printer.options.length > 0 &&
        profile instanceof HTMLSelectElement &&
        profile.options.length > 0
      );
    });

    await page.evaluate(() => {
      const field = document.getElementById("model-forge-family");
      if (!(field instanceof HTMLSelectElement)) throw new Error("model-forge-family missing");
      field.value = "spacer";
      field.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await page.waitForFunction(() => {
      const family = document.getElementById("model-forge-family");
      const guidance = document.getElementById("model-forge-guidance")?.textContent || "";
      const part = document.getElementById("model-forge-part");
      return (
        family instanceof HTMLSelectElement &&
        family.value === "spacer" &&
        guidance.includes("Spacer workflow") &&
        part instanceof HTMLInputElement &&
        part.value.trim().length > 0
      );
    });

    const viewerStatus = (await page.locator("#model-forge-viewer-status").textContent()) || "";
    assert(viewerStatus.trim().length > 0, "Model forge viewer status was empty");

    await page.evaluate(() => {
      document.querySelectorAll(".model-forge-tab").forEach((node) => node.classList.remove("active"));
      document.querySelectorAll(".model-forge-tab-panel").forEach((node) => node.classList.remove("active"));
      document.querySelector('[data-model-forge-tab="details"]')?.classList.add("active");
      document.querySelector('[data-model-forge-panel="details"]')?.classList.add("active");
    });
    await page.waitForSelector("#model-forge-package", { state: "attached" });

    await page.evaluate(() => {
      document.querySelectorAll(".model-forge-tab").forEach((node) => node.classList.remove("active"));
      document.querySelectorAll(".model-forge-tab-panel").forEach((node) => node.classList.remove("active"));
      document.querySelector('[data-model-forge-tab="source"]')?.classList.add("active");
      document.querySelector('[data-model-forge-panel="source"]')?.classList.add("active");
    });
    await page.waitForSelector("#model-forge-script", { state: "attached" });

    const detailsText = (await page.locator("#model-forge-details-content").textContent()) || "";
    const packageCount = await page.locator("#model-forge-package").count();
    assert(packageCount === 1, "Model forge package selector did not render");
    assert(detailsText !== null, "Model forge details panel failed to render");
    const scriptText = (await page.locator("#model-forge-script").textContent()) || "";
    assert(scriptText.trim().length > 0, "Model forge script panel stayed empty");
    entry.screenshot = await recordShot(page, "workbench-model-forge-modal");
  });

  await check("Model Forge can generate a package from the modal", async (entry) => {
    await page.evaluate(() => {
      document.querySelectorAll(".model-forge-tab").forEach((node) => node.classList.remove("active"));
      document.querySelectorAll(".model-forge-tab-panel").forEach((node) => node.classList.remove("active"));
      document.querySelector('[data-model-forge-tab="create"]')?.classList.add("active");
      document.querySelector('[data-model-forge-panel="create"]')?.classList.add("active");
    });
    const mountName = `QA Camera Mount ${Date.now()}`;
    await page.evaluate((name) => {
      const setValue = (id, value) => {
        const field = document.getElementById(id);
        if (!(field instanceof HTMLInputElement) && !(field instanceof HTMLTextAreaElement) && !(field instanceof HTMLSelectElement)) {
          throw new Error(`${id} missing`);
        }
        field.value = value;
        field.dispatchEvent(new Event("input", { bubbles: true }));
        field.dispatchEvent(new Event("change", { bubbles: true }));
      };
      setValue("model-forge-family", "mount");
      setValue("model-forge-part", name);
      setValue("model-forge-dimensions", "base length 90 mm, width 40 mm, thickness 6 mm, riser height 35 mm");
      setValue("model-forge-constraints", "Keep fastener access clear and export a printable fit-check.");
    }, mountName);
    const generationResponse = page.waitForResponse((response) => {
      return response.url().includes("/api/cad-package") && response.request().method() === "POST";
    });
    await page.evaluate(() => {
      const button = document.getElementById("model-forge-generate");
      if (!(button instanceof HTMLElement)) throw new Error("model-forge-generate missing");
      button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    });
    const response = await generationResponse;
    assert(response.ok(), `Model forge generate request returned ${response.status()}`);
    const responseBody = await response.json();
    assert(responseBody && responseBody.package_id, "Model forge generate response did not include a package_id");

    await page.waitForFunction(() => {
      const output = document.getElementById("model-forge-generation-output")?.textContent || "";
      return output.trim().length > 0 && !/awaiting generation request/i.test(output);
    }, { timeout: 60000 });

    const output = (await page.locator("#model-forge-generation-output").textContent()) || "";
    assert(output.trim().length > 0, "Model forge generation output stayed empty");
    entry.screenshot = await recordShot(page, "workbench-model-forge-generated");
  });

  await check("Vision modal renders on-demand camera controls with stubbed device", async (entry) => {
    await page.click("#close-modal");
    await page.waitForTimeout(200);
    await page.evaluate(() => {
      if (typeof window.__jarvisOpenPacket !== "function") throw new Error("openPacket helper not available");
      window.__jarvisOpenPacket("vision");
    });
    await page.waitForSelector("#modal-layer.open");
    await page.waitForFunction(() => document.getElementById("modal-title")?.textContent?.includes("Vision"));
    await page.waitForSelector("#vision-device");
    await page.waitForSelector("#vision-mode");
    await page.waitForSelector("#vision-start");
    await page.waitForSelector("#vision-capture");
    await page.waitForSelector("#vision-retake");

    await page.waitForFunction(() => {
      const picker = document.getElementById("vision-device");
      return !!picker && picker.options.length > 0;
    });
    const deviceText = await page.locator("#vision-device option").first().textContent();
    assert((deviceText || "").includes("Workbench Camera"), `Unexpected vision device label: ${deviceText}`);

    await page.click("#vision-start");
    await page.waitForFunction(() => {
      const status = document.getElementById("vision-status")?.textContent || "";
      return /Live preview active/i.test(status);
    });

    await page.selectOption("#vision-mode", "compare");
    await page.waitForFunction(() => {
      const status = document.getElementById("vision-status")?.textContent || "";
      return /need one earlier capture first/i.test(status);
    });

    await page.selectOption("#vision-mode", "measure");
    await page.waitForFunction(() => {
      const status = document.getElementById("vision-status")?.textContent || "";
      return /calibrate first|measure mode ready/i.test(status);
    });

    const cropLabelBefore = (await page.locator("#vision-toggle-crop").textContent()) || "";
    assert(/Crop On|Selection On/i.test(cropLabelBefore), "Vision crop toggle did not enter selection state during measure mode");
    await page.click("#vision-toggle-crop");
    const cropLabelAfter = await page.locator("#vision-toggle-crop").textContent();
    assert(/Crop Before Analyze/i.test(cropLabelAfter || ""), "Vision crop toggle did not return to the off state");

    await page.click("#vision-retake");
    const analysis = (await page.locator("#vision-analysis").textContent()) || "";
    assert(/No frame captured yet/i.test(analysis), "Vision retake did not reset analysis text");
    entry.screenshot = await recordShot(page, "workbench-vision-modal");
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
  const report = {
    started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
    base_url: BASE_URL,
    checks: [],
    failures: [{ name: "workbench-battery-bootstrap", error: error && error.stack ? error.stack : String(error) }],
    warnings: [],
    summary: { passed: 0, failed: 1, warned: 0, skipped: 0 },
  };
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
  console.error(error);
  process.exit(1);
});
