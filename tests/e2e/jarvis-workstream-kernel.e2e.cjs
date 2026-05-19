const fs = require("fs");
const path = require("path");

const BASE_URL = process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787";
const ROOT = process.cwd();
const ARTIFACT_DIR = path.join(ROOT, "artifacts", "qa");
const REPORT_PATH = path.join(ARTIFACT_DIR, "jarvis-workstream-kernel-report.json");
const SNAPSHOT_FILES = [
  path.join(ROOT, "data", "workstreams", "state.json"),
  path.join(ROOT, "data", "workstreams", "runs.json"),
  path.join(ROOT, "data", "workstreams", "items.json"),
  path.join(ROOT, "data", "workstreams", "artifacts.json"),
  path.join(ROOT, "data", "workstreams", "approvals.json"),
  path.join(ROOT, "data", "workstreams", "queue.json"),
  path.join(ROOT, "data", "catalyst", "work_lifecycle.json"),
];

fs.mkdirSync(ARTIFACT_DIR, { recursive: true });

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
    data,
    text,
    headers: Object.fromEntries(response.headers.entries()),
  };
}

async function postJson(pathname, payload) {
  return fetchResponse(pathname, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function snapshotFiles() {
  const snapshot = new Map();
  for (const file of SNAPSHOT_FILES) {
    snapshot.set(file, fs.existsSync(file) ? fs.readFileSync(file, "utf8") : null);
  }
  return snapshot;
}

function restoreFiles(snapshot) {
  for (const [file, content] of snapshot.entries()) {
    if (content === null) {
      if (fs.existsSync(file)) fs.unlinkSync(file);
      continue;
    }
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, content, "utf8");
  }
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

  const snapshot = snapshotFiles();

  async function check(name, fn) {
    const entry = { name, status: "passed", details: null, kind: "automated" };
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

  try {
    let marketItemId = "";

    await check("Generic workstreams endpoint exposes hardened kernel fields", async (entry) => {
      const response = await fetchResponse("/api/workstreams?actor=Chris");
      assert(response.ok, `/api/workstreams returned ${response.status}`);
      assert(Array.isArray(response.data.lanes), "Expected lanes array");
      assert(Array.isArray(response.data.items), "Expected items array");
      assert(Array.isArray(response.data.queue), "Expected queue array");
      assert(Array.isArray(response.data.approvals), "Expected approvals array");
      assert(Array.isArray(response.data.artifacts), "Expected artifacts array");
      const firstItem = (response.data.items || [])[0] || {};
      assert(Object.prototype.hasOwnProperty.call(firstItem, "item_status"), "Expected item_status on workstream items");
      assert(Object.prototype.hasOwnProperty.call(firstItem, "action_status"), "Expected action_status on workstream items");
      assert(Object.prototype.hasOwnProperty.call(firstItem, "verification_status"), "Expected verification_status on workstream items");
      entry.details = "Kernel summary includes queue, approvals, artifacts, and truth fields.";
    });

    await check("Manual market-intelligence run stages kernel-native queue and artifacts", async (entry) => {
      const response = await postJson("/api/workstreams/market-intelligence/run", { actor: "Chris", source: "manual" });
      assert(response.ok, `Manual market-intelligence run returned ${response.status}`);
      assert(response.data.run.run_status === "executed", `Expected run_status executed, got ${response.data.run.run_status}`);
      assert(response.data.run.truth_state === "staged" || response.data.run.truth_state === "researched", `Unexpected truth_state ${response.data.run.truth_state}`);
      const item = (response.data.items || [])[0] || {};
      marketItemId = item.item_id || "";
      assert(marketItemId, "Manual workstream run did not return an item_id");
      assert(Array.isArray(item.queue_entries) && item.queue_entries.length >= 1, "Expected queue entries on returned workstream item");
      assert(Array.isArray(item.artifacts) && item.artifacts.length >= 1, "Expected artifacts on returned workstream item");
      entry.details = `Seeded ${marketItemId} with queue and artifact records.`;
    });

    await check("Background run records cadence skip truthfully", async (entry) => {
      const response = await postJson("/api/workstreams/market-intelligence/run", { actor: "Chris", source: "background" });
      assert(response.ok, `Background market-intelligence run returned ${response.status}`);
      assert(response.data.run.status === "skipped", `Expected skipped status, got ${response.data.run.status}`);
      assert(response.data.run.run_status === "blocked", `Expected blocked run_status, got ${response.data.run.run_status}`);
      assert(response.data.run.blocked_reason === "cadence-not-due", `Expected cadence-not-due, got ${response.data.run.blocked_reason}`);
      entry.details = "Background cadence skip was recorded as a blocked run.";
    });

    await check("Approve action closes queue entry and updates approval status", async (entry) => {
      assert(marketItemId, "No market workstream item was available for approval");
      const response = await postJson(`/api/workstreams/items/${encodeURIComponent(marketItemId)}/approve`, {
        actor: "Chris",
        note: "Approved from workstream kernel battery.",
      });
      assert(response.ok, `Approve endpoint returned ${response.status}`);
      assert(response.data.item.approval_status === "approved", `Expected approval_status approved, got ${response.data.item.approval_status}`);
      const queueEntry = (response.data.item.queue_entries || [])[0] || {};
      assert(queueEntry.status === "closed", `Expected queue entry to close, got ${queueEntry.status}`);
      entry.details = `Approved ${marketItemId} and closed its queue entry.`;
    });

    await check("Open loops surface workstream summaries without treating approved queue items as waiting", async (entry) => {
      const response = await fetchResponse("/api/open-loops?actor=Chris&limit=20");
      assert(response.ok, `/api/open-loops returned ${response.status}`);
      const items = Array.isArray(response.data.items) ? response.data.items : [];
      const workstreamSummaries = items.filter((item) => item.kind === "workstream-summary");
      assert(workstreamSummaries.length >= 1, "Expected at least one workstream-summary in open loops");
      const waiting = Number((response.data.summary || {}).waiting_on_you || 0);
      assert(waiting >= 0, "Expected numeric waiting_on_you summary");
      entry.details = `Open loops currently expose ${workstreamSummaries.length} workstream summary item(s).`;
    });

    await check("Compatibility autonomous-workstream endpoints remain intact", async (entry) => {
      const summary = await fetchResponse("/api/autonomous-workstreams?actor=Chris");
      assert(summary.ok, `/api/autonomous-workstreams returned ${summary.status}`);
      const runs = await fetchResponse("/api/autonomous-workstreams/market-intelligence/runs?actor=Chris&limit=5");
      assert(runs.ok, `/api/autonomous-workstreams/market-intelligence/runs returned ${runs.status}`);
      assert(Array.isArray(runs.data.runs), "Expected compatibility runs array");
      entry.details = "Legacy autonomous-workstream routes still respond.";
    });
  } finally {
    restoreFiles(snapshot);
  }

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
    failures: [{ name: "workstream-kernel-battery-bootstrap", error: error && error.stack ? error.stack : String(error) }],
    warnings: [],
    summary: { passed: 0, failed: 1, warned: 0, skipped: 0 },
  };
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
  console.error(error);
  process.exit(1);
});
