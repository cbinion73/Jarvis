const fs = require("fs");
const path = require("path");

const BASE_URL = process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787";
const ARTIFACT_DIR = path.join(process.cwd(), "artifacts", "qa");
const REPORT_PATH = path.join(ARTIFACT_DIR, "jarvis-memory-governance-report.json");
const MEMORY_DIR = path.join(process.cwd(), "data", "memory");
const MEMORY_FILES = ["entries.json", "proposals.json", "profile_facts.json"];

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

function snapshotMemoryFiles() {
  const snapshot = new Map();
  for (const file of MEMORY_FILES) {
    const fullPath = path.join(MEMORY_DIR, file);
    snapshot.set(fullPath, fs.existsSync(fullPath) ? fs.readFileSync(fullPath, "utf8") : null);
  }
  return snapshot;
}

function restoreMemoryFiles(snapshot) {
  for (const [fullPath, content] of snapshot.entries()) {
    if (content === null) {
      if (fs.existsSync(fullPath)) {
        fs.unlinkSync(fullPath);
      }
    } else {
      fs.mkdirSync(path.dirname(fullPath), { recursive: true });
      fs.writeFileSync(fullPath, content, "utf8");
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

  const snapshot = snapshotMemoryFiles();

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
    const approvedSummary = `QA learning approval ${seed}`;
    const rejectedSummary = `QA learning rejection ${seed}`;
    let approvedProposalId = "";
    let approvedFactId = "";
    let approvedEntryId = "";

    await check("Sensitive memory creates a pending proposal", async (entry) => {
      const response = await postJson("/api/memory-remember", {
        actor: "Chris",
        memory_type: "personal",
        scope: "personal",
        owner: "Chris",
        subject_user_id: "chris",
        summary: approvedSummary,
        detail: `${approvedSummary} should round-trip through the learning governance API.`,
        sensitivity: "sensitive",
        access_policy: "personal",
        source_type: "user-stated",
        confidence: "confirmed",
        tags: ["qa", "learning-review"],
      });
      assert(response.ok, `/api/memory-remember returned ${response.status}`);
      assert(response.data && response.data.needs_approval === true, "Sensitive memory did not require approval");
      approvedProposalId = response.data.proposal?.proposal_id || "";
      assert(approvedProposalId, "Pending proposal did not include a proposal_id");
      entry.details = `Proposal ${approvedProposalId}`;
    });

    await check("Approved learning proposal becomes entry and profile fact", async (entry) => {
      const decision = await postJson(`/api/learning/proposals/${encodeURIComponent(approvedProposalId)}`, {
        decision: "approved",
      });
      assert(decision.ok, `Learning approval returned ${decision.status}`);
      assert(decision.data.status === "approved", `Expected approved status, got ${decision.data.status}`);
      approvedEntryId = decision.data.entry?.entry_id || "";
      approvedFactId = decision.data.profile_promotion?.fact?.fact_id || "";
      assert(approvedEntryId, "Approved proposal did not produce an entry_id");
      assert(approvedFactId, "Approved proposal did not produce a profile fact");

      const review = await fetchResponse("/api/learning-review?viewer=Chris&subject_user_id=chris");
      assert(review.ok, `/api/learning-review returned ${review.status}`);
      const fact = (review.data.profile_facts || []).find((item) => item.fact_id === approvedFactId);
      assert(fact, "Approved learning fact did not appear in learning review");
      assert(String(fact.summary || "").includes(approvedSummary), "Approved fact summary did not match the new proposal");
      entry.details = `Entry ${approvedEntryId}, fact ${approvedFactId}`;
    });

    await check("Retiring and reactivating a profile fact updates visibility", async (entry) => {
      const retire = await postJson(`/api/learning/facts/${encodeURIComponent(approvedFactId)}`, {
        viewer: "Chris",
        status: "retired",
      });
      assert(retire.ok, `Retire fact returned ${retire.status}`);
      assert(retire.data.fact && retire.data.fact.status === "retired", "Fact did not enter retired state");

      const afterRetire = await fetchResponse("/api/learning-review?viewer=Chris&subject_user_id=chris");
      assert(afterRetire.ok, `/api/learning-review after retire returned ${afterRetire.status}`);
      const visibleAfterRetire = (afterRetire.data.profile_facts || []).find((item) => item.fact_id === approvedFactId);
      assert(!visibleAfterRetire, "Retired fact was still visible in active profile facts");

      const reactivate = await postJson(`/api/learning/facts/${encodeURIComponent(approvedFactId)}`, {
        viewer: "Chris",
        status: "active",
      });
      assert(reactivate.ok, `Reactivate fact returned ${reactivate.status}`);
      assert(reactivate.data.fact && reactivate.data.fact.status === "active", "Fact did not return to active state");

      const afterReactivate = await fetchResponse("/api/learning-review?viewer=Chris&subject_user_id=chris");
      assert(afterReactivate.ok, `/api/learning-review after reactivate returned ${afterReactivate.status}`);
      const visibleAfterReactivate = (afterReactivate.data.profile_facts || []).find((item) => item.fact_id === approvedFactId);
      assert(visibleAfterReactivate, "Reactivated fact did not return to visible profile facts");
      entry.details = `Fact ${approvedFactId} retired and restored`;
    });

    await check("Rejected learning proposal stays out of stored memory", async (entry) => {
      const create = await postJson("/api/memory-remember", {
        actor: "Chris",
        memory_type: "personal",
        scope: "personal",
        owner: "Chris",
        subject_user_id: "chris",
        summary: rejectedSummary,
        detail: `${rejectedSummary} should be rejected and never become a stored entry.`,
        sensitivity: "sensitive",
        access_policy: "personal",
        source_type: "user-stated",
        confidence: "confirmed",
        tags: ["qa", "learning-review"],
      });
      assert(create.ok, `/api/memory-remember reject-case returned ${create.status}`);
      const proposalId = create.data.proposal?.proposal_id || "";
      assert(proposalId, "Reject-case proposal did not include a proposal_id");

      const reject = await postJson(`/api/learning/proposals/${encodeURIComponent(proposalId)}`, {
        decision: "rejected",
      });
      assert(reject.ok, `Reject proposal returned ${reject.status}`);
      assert(reject.data.status === "rejected", `Expected rejected status, got ${reject.data.status}`);

      const review = await fetchResponse("/api/memory-review?viewer=Chris&type=personal&owner=Chris");
      assert(review.ok, `/api/memory-review returned ${review.status}`);
      const rejectedEntry = (review.data || []).find((item) => String(item.summary || "").includes(rejectedSummary));
      assert(!rejectedEntry, "Rejected proposal still appeared in stored memory review");
      entry.details = `Proposal ${proposalId} rejected cleanly`;
    });

    await check("Memory curation API remains healthy after governance mutations", async (entry) => {
      const curation = await postJson("/api/memory-curation/run", {});
      assert(curation.ok, `/api/memory-curation/run returned ${curation.status}`);
      assert(typeof curation.data.promoted_count === "number", "Memory curation response missing promoted_count");
      entry.details = `promoted_count=${curation.data.promoted_count}`;
    });
  } finally {
    restoreMemoryFiles(snapshot);
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
    failures: [{ name: "memory-governance-battery-bootstrap", error: error && error.stack ? error.stack : String(error) }],
    warnings: [],
    summary: { passed: 0, failed: 1, warned: 0, skipped: 0 },
  };
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
  console.error(error);
  process.exit(1);
});
