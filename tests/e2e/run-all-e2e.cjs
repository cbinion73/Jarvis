const fs = require("fs");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

const ROOT = process.cwd();
const ARTIFACT_DIR = path.join(ROOT, "artifacts", "qa");
const SUITE_REPORT_PATH = path.join(ARTIFACT_DIR, "jarvis-e2e-suite-report.json");
const SUITE_SUMMARY_PATH = path.join(ARTIFACT_DIR, "jarvis-e2e-suite-summary.md");
const BASE_URL = process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787";
const HEALTH_URL = `${BASE_URL.replace(/\/$/, "")}/health`;
const BASE_PORT = Number(new URL(BASE_URL).port || 80);

const BATTERIES = [
  {
    name: "platform",
    script: path.join(ROOT, "tests", "e2e", "jarvis-platform.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-platform-report.json"),
    runtime_group: "shell",
  },
  {
    name: "provider-layer",
    script: path.join(ROOT, "tests", "e2e", "jarvis-provider-layer.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-provider-layer-report.json"),
    runtime_group: "shell",
  },
  {
    name: "full-system",
    script: path.join(ROOT, "tests", "e2e", "jarvis-full-system.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-full-system-report.json"),
    runtime_group: "full-system",
  },
  {
    name: "workbench",
    script: path.join(ROOT, "tests", "e2e", "jarvis-workbench.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-workbench-report.json"),
    runtime_group: "shell",
  },
  {
    name: "identity-admin",
    script: path.join(ROOT, "tests", "e2e", "jarvis-identity-admin.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-identity-admin-report.json"),
    runtime_group: "governance",
  },
  {
    name: "memory-governance",
    script: path.join(ROOT, "tests", "e2e", "jarvis-memory-governance.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-memory-governance-report.json"),
    runtime_group: "governance",
  },
  {
    name: "approval-queue",
    script: path.join(ROOT, "tests", "e2e", "jarvis-approval-queue.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-approval-queue-report.json"),
    runtime_group: "governance",
  },
  {
    name: "workstream-kernel",
    script: path.join(ROOT, "tests", "e2e", "jarvis-workstream-kernel.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-workstream-kernel-report.json"),
    runtime_group: "governance",
  },
];

fs.mkdirSync(ARTIFACT_DIR, { recursive: true });

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function sleepAsync(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function healthcheck() {
  const result = spawnSync("curl", ["-sf", HEALTH_URL], {
    cwd: ROOT,
    env: process.env,
    encoding: "utf8",
    timeout: 3000,
  });
  return result.status === 0;
}

function waitForHealthyRuntime(timeoutMs = 45000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (healthcheck()) {
      return true;
    }
    sleep(1000);
  }
  return false;
}

function restartRuntime() {
  const restart = spawnSync("launchctl", ["kickstart", "-k", `gui/${process.getuid()}/com.chris.jarvis.dashboard`], {
    cwd: ROOT,
    env: process.env,
    encoding: "utf8",
    timeout: 5000,
  });
  return {
    ok: restart.status === 0 && waitForHealthyRuntime(60000),
    exit_code: restart.status,
    stdout: String(restart.stdout || "").trim(),
    stderr: String(restart.stderr || "").trim(),
  };
}

function summarizeBattery(report) {
  const summary = report.summary || {};
  return {
    passed: Number(summary.passed || 0),
    failed: Number(summary.failed || 0),
    warned: Number(summary.warned || 0),
    skipped: Number(summary.skipped || 0),
  };
}

function ensureHealthyRuntime() {
  if (healthcheck()) {
    return { ok: true, restarted: false, restart_reason: "none" };
  }
  const restarted = restartRuntime();
  return {
    ok: restarted.ok,
    restarted: true,
    restart_reason: "unhealthy-before-run",
    restart: restarted,
  };
}

async function runBattery(battery, context) {
  const reportStartedAt = Date.now();
  if (fs.existsSync(battery.report)) {
    fs.rmSync(battery.report, { force: true });
  }

  let runtimeState = ensureHealthyRuntime();
  if (battery.runtime_group !== context.currentGroup) {
    const restarted = restartRuntime();
    runtimeState = {
      ok: restarted.ok,
      restarted: true,
      restart_reason: context.currentGroup === null ? "initial-group" : `group-transition:${context.currentGroup}->${battery.runtime_group}`,
      restart: restarted,
    };
  }

  const child = spawn(process.execPath, [battery.script], {
    cwd: ROOT,
    env: process.env,
  });
  let stdout = "";
  let stderr = "";
  let exitCode = null;
  let signal = null;
  let closed = false;
  let reportFreshAt = 0;

  child.stdout.on("data", (chunk) => {
    stdout += String(chunk || "");
  });
  child.stderr.on("data", (chunk) => {
    stderr += String(chunk || "");
  });
  child.on("close", (code, closeSignal) => {
    exitCode = code;
    signal = closeSignal;
    closed = true;
  });

  const startedAt = Date.now();
  while (!closed) {
    const reportExists = fs.existsSync(battery.report);
    const reportFresh = reportExists && fs.statSync(battery.report).mtimeMs >= reportStartedAt;
    if (reportFresh) {
      if (!reportFreshAt) {
        reportFreshAt = Date.now();
      } else if (Date.now() - reportFreshAt >= 3000) {
        child.kill("SIGTERM");
      }
    }
    if (Date.now() - startedAt >= 10 * 60 * 1000) {
      child.kill("SIGKILL");
      break;
    }
    await sleepAsync(500);
  }
  const reportExists = fs.existsSync(battery.report);
  const reportFresh = reportExists && fs.statSync(battery.report).mtimeMs >= reportStartedAt;
  const report = reportFresh ? readJson(battery.report) : null;
  const runtimeHealthyAfterRun = healthcheck();

  return {
    name: battery.name,
    script: battery.script,
    report_path: battery.report,
    runtime_group: battery.runtime_group,
    exit_code: exitCode,
    signal,
    restarted_before_run: Boolean(runtimeState.restarted),
    restart_reason: runtimeState.restart_reason,
    runtime_healthy_before_run: Boolean(runtimeState.ok),
    runtime_healthy_after_run: runtimeHealthyAfterRun,
    stdout_tail: stdout.split("\n").slice(-20).join("\n").trim(),
    stderr_tail: stderr.split("\n").slice(-20).join("\n").trim(),
    report_fresh: reportFresh,
    summary: report ? summarizeBattery(report) : null,
    report,
  };
}

async function main() {
  const startedAt = new Date().toISOString();
  if (!waitForHealthyRuntime(20000)) {
    const suite = {
      started_at: startedAt,
      finished_at: new Date().toISOString(),
      base_url: process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787",
      batteries: [],
      totals: { passed: 0, failed: 0, warned: 0, skipped: 0 },
      failures: [
        {
          name: "suite-bootstrap",
          exit_code: 1,
          classification: "runtime-orchestration",
          stderr_tail: "Runtime was not healthy before suite start.",
          stdout_tail: "",
        },
      ],
    };
    fs.writeFileSync(SUITE_REPORT_PATH, JSON.stringify(suite, null, 2));
    fs.writeFileSync(SUITE_SUMMARY_PATH, renderMarkdownSummary(suite));
    process.stdout.write(`${SUITE_REPORT_PATH}\n`);
    process.stdout.write(JSON.stringify(suite, null, 2));
    process.exitCode = 1;
    return;
  }

  const context = { currentGroup: null };
  const runs = [];
  for (const battery of BATTERIES) {
    const run = await runBattery(battery, context);
    context.currentGroup = battery.runtime_group;
    runs.push(run);
  }
  const totals = runs.reduce(
    (acc, run) => {
      const summary = run.summary || {};
      acc.passed += Number(summary.passed || 0);
      acc.failed += Number(summary.failed || 0);
      acc.warned += Number(summary.warned || 0);
      acc.skipped += Number(summary.skipped || 0);
      return acc;
    },
    { passed: 0, failed: 0, warned: 0, skipped: 0 }
  );

  const suite = {
    started_at: startedAt,
    finished_at: new Date().toISOString(),
    base_url: process.env.JARVIS_BASE_URL || "http://127.0.0.1:8787",
    batteries: runs.map((run) => ({
      name: run.name,
      script: run.script,
      report_path: run.report_path,
      runtime_group: run.runtime_group,
      exit_code: run.exit_code,
      signal: run.signal,
      restarted_before_run: run.restarted_before_run,
      restart_reason: run.restart_reason,
      runtime_healthy_before_run: run.runtime_healthy_before_run,
      runtime_healthy_after_run: run.runtime_healthy_after_run,
      report_fresh: run.report_fresh,
      summary: run.summary,
    })),
    totals,
    failures: runs
      .filter((run) => (run.summary?.failed || 0) > 0 || run.exit_code || !run.report_fresh)
      .map((run) => ({
        name: run.name,
        exit_code: run.exit_code,
        restarted_before_run: run.restarted_before_run,
        restart_reason: run.restart_reason,
        runtime_healthy_before_run: run.runtime_healthy_before_run,
        runtime_healthy_after_run: run.runtime_healthy_after_run,
        report_fresh: run.report_fresh,
        classification: !run.report_fresh ? "harness" : run.runtime_healthy_after_run ? "product" : "runtime-orchestration",
        stderr_tail: run.stderr_tail,
        stdout_tail: run.stdout_tail,
      })),
  };

  fs.writeFileSync(SUITE_REPORT_PATH, JSON.stringify(suite, null, 2));
  fs.writeFileSync(SUITE_SUMMARY_PATH, renderMarkdownSummary(suite));
  process.stdout.write(`${SUITE_REPORT_PATH}\n`);
  process.stdout.write(JSON.stringify(suite, null, 2));

  if (suite.failures.length) {
    process.exitCode = 1;
  }
}

function renderMarkdownSummary(suite) {
  const lines = [
    "# JARVIS E2E Suite Summary",
    "",
    `- Started: \`${suite.started_at}\``,
    `- Finished: \`${suite.finished_at}\``,
    `- Base URL: \`${suite.base_url}\``,
    "",
    "## Totals",
    "",
    `- Passed: **${suite.totals.passed}**`,
    `- Failed: **${suite.totals.failed}**`,
    `- Warned: **${suite.totals.warned}**`,
    `- Skipped: **${suite.totals.skipped}**`,
    "",
    "## Batteries",
    "",
  ];

  for (const battery of suite.batteries) {
    const summary = battery.summary || { passed: 0, failed: 0, warned: 0, skipped: 0 };
    lines.push(`### ${battery.name}`);
    lines.push("");
    lines.push(`- Exit code: \`${battery.exit_code}\``);
    lines.push(`- Restarted runtime before run: \`${battery.restarted_before_run}\``);
    lines.push(`- Restart reason: \`${battery.restart_reason || "none"}\``);
    lines.push(`- Runtime healthy before run: \`${battery.runtime_healthy_before_run}\``);
    lines.push(`- Runtime healthy after run: \`${battery.runtime_healthy_after_run}\``);
    lines.push(`- Fresh report written: \`${battery.report_fresh}\``);
    lines.push(`- Passed: **${summary.passed}**`);
    lines.push(`- Failed: **${summary.failed}**`);
    lines.push(`- Warned: **${summary.warned}**`);
    lines.push(`- Skipped: **${summary.skipped}**`);
    lines.push(`- Report: [${battery.report_path}](${battery.report_path})`);
    lines.push("");
  }

  if (suite.failures.length) {
    lines.push("## Failures");
    lines.push("");
    for (const failure of suite.failures) {
      lines.push(`### ${failure.name}`);
      lines.push("");
      lines.push(`- Exit code: \`${failure.exit_code}\``);
      lines.push(`- Classification: \`${failure.classification || "product"}\``);
      if (failure.stdout_tail) {
        lines.push("- Stdout tail:");
        lines.push("```text");
        lines.push(failure.stdout_tail);
        lines.push("```");
      }
      if (failure.stderr_tail) {
        lines.push("- Stderr tail:");
        lines.push("```text");
        lines.push(failure.stderr_tail);
        lines.push("```");
      }
      lines.push("");
    }
  } else {
    lines.push("## Failures");
    lines.push("");
    lines.push("None.");
    lines.push("");
  }

  return `${lines.join("\n")}\n`;
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : String(error)}\n`);
  process.exit(1);
});
