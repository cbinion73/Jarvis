const fs = require("fs");
const path = require("path");

const BASE_URL = process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787";
const ARTIFACT_DIR = path.join(process.cwd(), "artifacts", "qa");
const REPORT_PATH = path.join(ARTIFACT_DIR, "jarvis-identity-admin-report.json");

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

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function postJson(pathname, payload) {
  return fetchResponse(pathname, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
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

  const identityResponse = await fetchResponse("/api/identity");
  assert(identityResponse.ok, `/api/identity returned ${identityResponse.status}`);
  const identity = identityResponse.data;
  const originalMember = identity.members.find((item) => item.user_id === "chris") || identity.members[0];
  const originalDevice = identity.devices.find((item) => !item.shared) || identity.devices[0];
  const originalService = identity.service || {};

  assert(originalMember, "No identity member available for admin mutation test");
  assert(originalDevice, "No identity device available for admin mutation test");

  const memberMutation = {
    ...originalMember,
    notes: `QA identity member round-trip ${Date.now()}`,
    morning_room: originalMember.morning_room || "office",
  };
  const memberRestore = { ...originalMember };

  const deviceMutation = {
    ...originalDevice,
    notes: `QA device mapping round-trip ${Date.now()}`,
    room: originalDevice.room || "office",
  };
  const deviceRestore = { ...originalDevice };

  const serviceMutation = {
    ...originalService,
    hostname: `jarvis-qa-${Date.now()}.local`,
  };
  const serviceRestore = { ...originalService };

  await check("Identity member save persists and restores", async (entry) => {
    const mutate = await postJson("/api/identity/member", memberMutation);
    assert(mutate.ok, `/api/identity/member mutate returned ${mutate.status}`);
    assert(mutate.data.member.notes === memberMutation.notes, "Mutated member notes were not persisted");

    const restore = await postJson("/api/identity/member", memberRestore);
    assert(restore.ok, `/api/identity/member restore returned ${restore.status}`);
    assert((restore.data.member.notes || "") === (memberRestore.notes || ""), "Member notes did not restore cleanly");
    entry.details = `Mutated and restored member ${originalMember.user_id}`;
  });

  await check("Identity device save preserves mapping fields and restores", async (entry) => {
    const mutate = await postJson("/api/identity/device", deviceMutation);
    assert(mutate.ok, `/api/identity/device mutate returned ${mutate.status}`);
    assert(mutate.data.device.notes === deviceMutation.notes, "Mutated device notes were not persisted");
    assert(mutate.data.device.device_id === originalDevice.device_id, "Device mutation changed device_id");

    const restore = await postJson("/api/identity/device", deviceRestore);
    assert(restore.ok, `/api/identity/device restore returned ${restore.status}`);
    assert((restore.data.device.notes || "") === (deviceRestore.notes || ""), "Device notes did not restore cleanly");
    entry.details = `Mutated and restored device ${originalDevice.device_id}`;
  });

  await check("Session binding resolves actor and can be restored", async (entry) => {
    const sharedPayload = {
      ...originalDevice,
      shared: true,
      owner_user_id: "",
      default_actor_id: "",
    };
    const sharedSave = await postJson("/api/identity/device", sharedPayload);
    assert(sharedSave.ok, `/api/identity/device shared-save returned ${sharedSave.status}`);

    const bind = await postJson("/api/identity/session", {
      device_id: originalDevice.device_id,
      label: originalDevice.label,
      device_type: originalDevice.device_type,
      shared: true,
      session_actor_id: "caleb",
      user_agent: originalDevice.user_agent || "QA Browser",
      fingerprint: originalDevice.fingerprint || "qa-fingerprint",
      room: originalDevice.room || "office",
    });
    assert(bind.ok, `/api/identity/session returned ${bind.status}`);
    assert(bind.data.resolved_actor_id === "caleb", `Expected resolved_actor_id caleb, got ${bind.data.resolved_actor_id}`);
    assert(bind.data.actor_source === "session-override", `Expected session-override actor source, got ${bind.data.actor_source}`);

    const restore = await postJson("/api/identity/device", deviceRestore);
    assert(restore.ok, `/api/identity/device restore after bind returned ${restore.status}`);
    assert(restore.data.device.shared === deviceRestore.shared, "Device shared flag did not restore cleanly");
    entry.details = `Session override resolved to ${bind.data.resolved_actor_label || bind.data.resolved_actor_id}`;
  });

  await check("Service identity save persists and restores", async (entry) => {
    const mutate = await postJson("/api/identity/service", serviceMutation);
    assert(mutate.ok, `/api/identity/service mutate returned ${mutate.status}`);
    assert(mutate.data.service.hostname === serviceMutation.hostname, "Service hostname mutation did not persist");

    const runtimeStatus = await fetchResponse("/api/runtime-service");
    assert(runtimeStatus.ok, `/api/runtime-service returned ${runtimeStatus.status}`);
    assert(runtimeStatus.data.service_plan.hostname === serviceMutation.hostname, "Runtime service did not reflect mutated hostname");

    const restore = await postJson("/api/identity/service", serviceRestore);
    assert(restore.ok, `/api/identity/service restore returned ${restore.status}`);
    assert((restore.data.service.hostname || "") === (serviceRestore.hostname || ""), "Service hostname did not restore cleanly");
    entry.details = `Mutated and restored service hostname`;
  });

  await check("Connected devices snapshot stays consistent after admin round-trip", async (entry) => {
    const devices = await fetchResponse("/api/connected-devices");
    assert(devices.ok, `/api/connected-devices returned ${devices.status}`);
    assert(devices.data.summary && typeof devices.data.summary.total === "number", "Connected devices summary missing total");
    const listed = devices.data.devices.find((item) => item.device_id === originalDevice.device_id);
    assert(listed, "Original device disappeared from connected devices snapshot");
    entry.details = `Connected devices total ${devices.data.summary.total}`;
  });

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
    failures: [{ name: "identity-admin-battery-bootstrap", error: error && error.stack ? error.stack : String(error) }],
    warnings: [],
    summary: { passed: 0, failed: 1, warned: 0, skipped: 0 },
  };
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
  console.error(error);
  process.exit(1);
});
