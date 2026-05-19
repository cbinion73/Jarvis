const fs = require("fs");
const path = require("path");

const BASE_URL = process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787";
const ARTIFACT_DIR = path.join(process.cwd(), "artifacts", "qa");
const REPORT_PATH = path.join(ARTIFACT_DIR, "jarvis-approval-queue-report.json");

const SNAPSHOT_FILES = [
  path.join(process.cwd(), "data", "approvals", "pending.json"),
  path.join(process.cwd(), "data", "family", "message_drafts.json"),
  path.join(process.cwd(), "data", "workshop", "vendor_preps.json"),
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
    headers: Object.fromEntries(response.headers.entries()),
    data,
    text,
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
    } else {
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, content, "utf8");
    }
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
    const seed = Date.now();
    let parentApprovalId = "";
    let vendorApprovalId = "";
    let vendorPrepId = "";
    let draftId = "";

    await check("Parent message path creates draft and pending approval", async (entry) => {
      const response = await postJson("/api/parent-message", {
        actor: "Chris",
        audience: `Troop Families QA ${seed}`,
        purpose: "schedule change",
        context: "Testing approval queue mutation and rollback.",
        tone: "warm",
      });
      assert(response.ok, `/api/parent-message returned ${response.status}`);
      draftId = response.data.draft_id || "";
      parentApprovalId = response.data.approval_request_id || "";
      assert(draftId, "Parent message did not return draft_id");
      assert(parentApprovalId, "Parent message did not return approval_request_id");

      const approvals = await fetchResponse("/api/approvals");
      assert(approvals.ok, `/api/approvals returned ${approvals.status}`);
      const pending = (approvals.data || []).find((item) => item.request_id === parentApprovalId);
      assert(pending, "Parent message approval was not visible in pending approvals");
      entry.details = `Draft ${draftId}, approval ${parentApprovalId}`;
    });

    await check("Vendor prep path creates record and pending approval", async (entry) => {
      const response = await postJson("/api/vendor-prep", {
        actor: "Chris",
        part: `Validation Bracket ${seed}`,
        vendor: "Xometry",
        process: "CNC",
        material: "6061 aluminum",
        notes: "Testing vendor approval round-trip.",
      });
      assert(response.ok, `/api/vendor-prep returned ${response.status}`);
      vendorPrepId = response.data.prep_id || "";
      vendorApprovalId = response.data.approval_request_id || "";
      assert(vendorPrepId, "Vendor prep did not return prep_id");
      assert(vendorApprovalId, "Vendor prep did not return approval_request_id");
      assert(response.data.status === "pending-approval", `Expected pending-approval status, got ${response.data.status}`);
      entry.details = `Vendor prep ${vendorPrepId}, approval ${vendorApprovalId}`;
    });

    await check("Approving and rejecting queue items updates status", async (entry) => {
      const approve = await postJson(`/api/approvals/${encodeURIComponent(parentApprovalId)}`, {
        status: "approved",
      });
      assert(approve.ok, `Approve request returned ${approve.status}`);
      assert(approve.data.status === "approved", `Expected approved status, got ${approve.data.status}`);

      const reject = await postJson(`/api/approvals/${encodeURIComponent(vendorApprovalId)}`, {
        status: "rejected",
      });
      assert(reject.ok, `Reject request returned ${reject.status}`);
      assert(reject.data.status === "rejected", `Expected rejected status, got ${reject.data.status}`);

      const pending = await fetchResponse("/api/approvals");
      assert(pending.ok, `/api/approvals after decisions returned ${pending.status}`);
      const stillPending = new Set((pending.data || []).map((item) => item.request_id));
      assert(!stillPending.has(parentApprovalId), "Approved request was still pending");
      assert(!stillPending.has(vendorApprovalId), "Rejected request was still pending");
      entry.details = `Approved ${parentApprovalId}, rejected ${vendorApprovalId}`;
    });

    await check("Approval history reflects both decisions", async (entry) => {
      const history = await fetchResponse("/api/approval-history");
      assert(history.ok, `/api/approval-history returned ${history.status}`);
      const approved = (history.data || []).find((item) => item.request_id === parentApprovalId);
      const rejected = (history.data || []).find((item) => item.request_id === vendorApprovalId);
      assert(approved && approved.status === "approved", "Approval history missing approved parent message");
      assert(rejected && rejected.status === "rejected", "Approval history missing rejected vendor prep");
      entry.details = "Approval history captured both transitions";
    });

    await check("Draft and vendor records remain reachable after queue updates", async (entry) => {
      const drafts = await fetchResponse("/api/message-drafts");
      assert(drafts.ok, `/api/message-drafts returned ${drafts.status}`);
      const draft = (drafts.data || []).find((item) => item.draft_id === draftId);
      assert(draft, "Parent draft disappeared after approval transition");

      const vendorPreps = await fetchResponse("/api/vendor-preps");
      assert(vendorPreps.ok, `/api/vendor-preps returned ${vendorPreps.status}`);
      const prep = (vendorPreps.data || []).find((item) => item.prep_id === vendorPrepId);
      assert(prep, "Vendor prep disappeared after rejection transition");
      entry.details = `Draft ${draftId} and vendor prep ${vendorPrepId} still reachable`;
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
    failures: [{ name: "approval-queue-battery-bootstrap", error: error && error.stack ? error.stack : String(error) }],
    warnings: [],
    summary: { passed: 0, failed: 1, warned: 0, skipped: 0 },
  };
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
  console.error(error);
  process.exit(1);
});
