const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const ROOT = process.cwd();
const ARTIFACT_DIR = path.join(ROOT, "artifacts", "qa");
const SUITE_REPORT_PATH = path.join(ARTIFACT_DIR, "jarvis-e2e-suite-report.json");
const SUITE_SUMMARY_PATH = path.join(ARTIFACT_DIR, "jarvis-e2e-suite-summary.md");

const BATTERIES = [
  {
    name: "platform",
    script: path.join(ROOT, "tests", "e2e", "jarvis-platform.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-platform-report.json"),
  },
  {
    name: "provider-layer",
    script: path.join(ROOT, "tests", "e2e", "jarvis-provider-layer.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-provider-layer-report.json"),
  },
  {
    name: "full-system",
    script: path.join(ROOT, "tests", "e2e", "jarvis-full-system.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-full-system-report.json"),
  },
  {
    name: "workbench",
    script: path.join(ROOT, "tests", "e2e", "jarvis-workbench.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-workbench-report.json"),
  },
  {
    name: "identity-admin",
    script: path.join(ROOT, "tests", "e2e", "jarvis-identity-admin.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-identity-admin-report.json"),
  },
  {
    name: "memory-governance",
    script: path.join(ROOT, "tests", "e2e", "jarvis-memory-governance.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-memory-governance-report.json"),
  },
  {
    name: "approval-queue",
    script: path.join(ROOT, "tests", "e2e", "jarvis-approval-queue.e2e.cjs"),
    report: path.join(ARTIFACT_DIR, "jarvis-approval-queue-report.json"),
  },
];

fs.mkdirSync(ARTIFACT_DIR, { recursive: true });

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
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

function runBattery(battery) {
  const result = spawnSync(process.execPath, [battery.script], {
    cwd: ROOT,
    env: process.env,
    encoding: "utf8",
  });

  const stdout = result.stdout || "";
  const stderr = result.stderr || "";
  const reportExists = fs.existsSync(battery.report);
  const report = reportExists ? readJson(battery.report) : null;

  return {
    name: battery.name,
    script: battery.script,
    report_path: battery.report,
    exit_code: result.status,
    signal: result.signal,
    stdout_tail: stdout.split("\n").slice(-20).join("\n").trim(),
    stderr_tail: stderr.split("\n").slice(-20).join("\n").trim(),
    summary: report ? summarizeBattery(report) : null,
    report,
  };
}

function main() {
  const startedAt = new Date().toISOString();
  const runs = BATTERIES.map(runBattery);
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
      exit_code: run.exit_code,
      signal: run.signal,
      summary: run.summary,
    })),
    totals,
    failures: runs
      .filter((run) => (run.summary?.failed || 0) > 0 || run.exit_code)
      .map((run) => ({
        name: run.name,
        exit_code: run.exit_code,
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

main();
