import { spawnSync } from "node:child_process";
import {
  chmodSync,
  mkdtempSync,
  mkdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import os from "node:os";
import path from "node:path";

const ROOT_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..");
const DATE_STAMP = new Date().toISOString().slice(0, 10).replace(/-/g, "");
const METRICS_DIR = path.join(ROOT_DIR, ".z-mos", "metrics");
const REPORT_PATH = path.join(METRICS_DIR, `phase3-test-report-${DATE_STAMP}.md`);
const MATRIX_JSON_PATH = path.join(METRICS_DIR, `phase3-test-matrix-${DATE_STAMP}.json`);
const TMP_ROOT = mkdtempSync(path.join(os.tmpdir(), "zmos-phase3-budget-"));
const PROJECT_DIR = path.join(TMP_ROOT, "project");
const TRACE_PATH = path.join(PROJECT_DIR, ".z-mos", "trace", "runtime-trace.jsonl");

function run(args) {
  const result = spawnSync("node", ["./bin/zcl.js", ...args, "--project", PROJECT_DIR], {
    cwd: ROOT_DIR,
    encoding: "utf8",
    env: { ...process.env },
  });
  return {
    code: result.status ?? 1,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
    output: `${result.stdout || ""}${result.stderr || ""}`,
  };
}

function setupProject() {
  const zmosDir = path.join(PROJECT_DIR, ".z-mos");
  const stateDir = path.join(zmosDir, "state", "task-context");
  const traceDir = path.join(zmosDir, "trace");
  mkdirSync(stateDir, { recursive: true });
  mkdirSync(traceDir, { recursive: true });
  const manifest = {
    repository: { name: "budget-test", framework: "Z-MOS", version: "1.0.0" },
    workspace: { root: ".", stateDir: ".z-mos/state", traceDir: ".z-mos/trace" },
    runtime: { platform: "node", moduleSystem: "esm", entryCommand: "zcl" },
    status: { stage: "phase3-test", aiCli: "off" },
    lifecycle: { status: "active", updatedAt: new Date().toISOString(), reason: "phase3 test" },
    scope: {
      mutation: {
        mode: "strict",
        allowedPaths: [".z-mos"],
        protectedPaths: [".z-mos"],
      },
    },
  };
  const node = {
    node_id: "budget-test-node",
    node_role: "execution-node",
    runtime: "nodejs-local",
    capabilities: ["cli-execution"],
  };
  writeFileSync(path.join(zmosDir, "zmos-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  writeFileSync(path.join(zmosDir, "node.json"), `${JSON.stringify(node, null, 2)}\n`);
}

function initContext(taskId, mode = "compact", inputTokens = 500) {
  run(["context", "init", "--task-id", taskId, "--force"]);
  run([
    "context",
    "update",
    "--task-id",
    taskId,
    "--patch",
    '{"progress":{"status":"in_progress","percent":10,"last_action":"seed"}}',
    "--mode",
    mode,
    "--input-tokens",
    String(inputTokens),
    "--output-tokens",
    "100",
    "--turnaround-ms",
    "50",
  ]);
}

function parseJsonSafe(result) {
  try {
    return JSON.parse(result.stdout || result.output);
  } catch {
    return null;
  }
}

function testGroup1BudgetDecision() {
  initContext("B3-G1-A", "compact", 400);
  const allow = run([
    "budget",
    "evaluate",
    "--task-id",
    "B3-G1-A",
    "--risk",
    "low",
    "--mode",
    "compact",
    "--estimated-input",
    "500",
  ]);
  const allowJson = parseJsonSafe(allow);

  initContext("B3-G1-B", "full", 1500);
  const warn = run([
    "budget",
    "evaluate",
    "--task-id",
    "B3-G1-B",
    "--risk",
    "low",
    "--mode",
    "full",
    "--estimated-input",
    "1500",
  ]);
  const warnJson = parseJsonSafe(warn);

  initContext("B3-G1-C", "full", 1900);
  const block = run([
    "budget",
    "evaluate",
    "--task-id",
    "B3-G1-C",
    "--risk",
    "low",
    "--mode",
    "full",
    "--estimated-input",
    "1900",
  ]);
  const blockJson = parseJsonSafe(block);

  initContext("B3-G1-D", "full", 4300);
  const overrideWarn = run([
    "budget",
    "evaluate",
    "--task-id",
    "B3-G1-D",
    "--risk",
    "high",
    "--mode",
    "full",
    "--estimated-input",
    "4500",
    "--override-reason",
    "critical-task",
    "--override-approver",
    "lead-1",
  ]);
  const overrideJson = parseJsonSafe(overrideWarn);

  return (
    allow.code === 0 &&
    allowJson?.decision === "allow" &&
    warn.code === 0 &&
    warnJson?.decision === "warn" &&
    block.code === 0 &&
    blockJson?.decision === "block" &&
    overrideWarn.code === 0 &&
    overrideJson?.decision === "warn"
  );
}

function testGroup2ProfileTests() {
  initContext("B3-G2-A", "compact", 1000);
  const telemetryFallback = run([
    "budget",
    "evaluate",
    "--task-id",
    "B3-G2-A",
    "--risk",
    "low",
    "--mode",
    "unknown",
  ]);
  const telemetryJson = parseJsonSafe(telemetryFallback);
  const manual = run([
    "budget",
    "profile",
    "--task-id",
    "B3-G2-A",
    "--profile",
    "full",
  ]);
  const status = run(["budget", "status", "--task-id", "B3-G2-A"]);
  const statusJson = parseJsonSafe(status);
  return (
    telemetryFallback.code === 0 &&
    telemetryJson?.recommended_profile === "compact" &&
    manual.code === 0 &&
    status.code === 0 &&
    statusJson?.budget?.current_profile === "full"
  );
}

function testGroup3TraceAudit() {
  initContext("B3-G3", "full", 4600);
  run([
    "budget",
    "evaluate",
    "--task-id",
    "B3-G3",
    "--risk",
    "high",
    "--mode",
    "full",
    "--estimated-input",
    "4600",
    "--override-reason",
    "critical",
    "--override-approver",
    "lead-2",
  ]);
  const raw = readFileSync(TRACE_PATH, "utf8").trim();
  const lines = raw ? raw.split("\n").map((line) => JSON.parse(line)) : [];
  const evalEntry = [...lines]
    .reverse()
    .find(
      (entry) =>
        entry.command === "zcl budget evaluate" && entry.details?.task_id === "B3-G3",
    );
  return (
    Boolean(evalEntry) &&
    evalEntry.details?.policy_rule_id &&
    evalEntry.details?.override_used === true &&
    typeof evalEntry.details?.decision === "string"
  );
}

function testGroup4IntegritySafety() {
  initContext("B3-G4", "compact", 200);
  const malformed = run([
    "budget",
    "evaluate",
    "--task-id",
    "B3-G4",
    "--risk",
    "wrong",
    "--mode",
    "compact",
    "--estimated-input",
    "100",
  ]);

  const badPolicyPath = path.join(PROJECT_DIR, "bad-policy.json");
  writeFileSync(badPolicyPath, "{broken-json");
  const policyReadFail = run([
    "budget",
    "evaluate",
    "--task-id",
    "B3-G4",
    "--risk",
    "low",
    "--mode",
    "compact",
    "--estimated-input",
    "100",
    "--policy-file",
    badPolicyPath,
  ]);

  const budgetDir = path.join(PROJECT_DIR, ".z-mos", "state", "budget");
  run(["budget", "profile", "--task-id", "B3-G4", "--profile", "compact"]);
  chmodSync(budgetDir, 0o500);
  const writeFail = run([
    "budget",
    "profile",
    "--task-id",
    "B3-G4",
    "--profile",
    "compact",
  ]);
  chmodSync(budgetDir, 0o700);
  return (
    malformed.code !== 0 &&
    malformed.output.includes("BUDGET_VALIDATION_FAIL") &&
    policyReadFail.code !== 0 &&
    policyReadFail.output.includes("BUDGET_READ_FAIL") &&
    writeFail.code !== 0 &&
    writeFail.output.includes("BUDGET_WRITE_FAIL")
  );
}

function runNonRegression() {
  const phase1 = spawnSync("node", ["./scripts/verify/context-phase1.mjs"], {
    cwd: ROOT_DIR,
    encoding: "utf8",
    env: { ...process.env },
  });
  const phase2 = spawnSync("node", ["./scripts/verify/lane-phase2.mjs"], {
    cwd: ROOT_DIR,
    encoding: "utf8",
    env: { ...process.env },
  });
  return {
    phase1: { pass: (phase1.status ?? 1) === 0, output: `${phase1.stdout || ""}${phase1.stderr || ""}` },
    phase2: { pass: (phase2.status ?? 1) === 0, output: `${phase2.stdout || ""}${phase2.stderr || ""}` },
  };
}

function scopeCheck() {
  const result = spawnSync(
    "rg",
    ["-n", "runtime queue|scheduler|planner|autonomous", "cli/commands/budget.ts", "core/budget.ts"],
    {
      cwd: ROOT_DIR,
      encoding: "utf8",
    },
  );
  return {
    pass: (result.stdout || "").trim().length === 0,
    output: `${result.stdout || ""}${result.stderr || ""}`,
  };
}

function writeReport(results, regressions, scope) {
  const lines = [
    "# Phase 3 Test Report",
    "",
    ...results.map((entry) => `- ${entry.name}: ${entry.pass ? "PASS" : "FAIL"}`),
    `- phase1_non_regression: ${regressions.phase1.pass ? "PASS" : "FAIL"}`,
    `- phase2_non_regression: ${regressions.phase2.pass ? "PASS" : "FAIL"}`,
    `- no_runtime_planner_scope: ${scope.pass ? "PASS" : "FAIL"}`,
  ];
  writeFileSync(REPORT_PATH, `${lines.join("\n")}\n`);
  writeFileSync(
    MATRIX_JSON_PATH,
    `${JSON.stringify({ results, regressions, scope }, null, 2)}\n`,
  );
}

function main() {
  mkdirSync(METRICS_DIR, { recursive: true });
  setupProject();

  const results = [
    { name: "group-1-budget-decision-tests", pass: testGroup1BudgetDecision() },
    { name: "group-2-prompt-profile-tests", pass: testGroup2ProfileTests() },
    { name: "group-3-trace-audit-tests", pass: testGroup3TraceAudit() },
    { name: "group-4-integrity-safety-tests", pass: testGroup4IntegritySafety() },
  ];
  const regressions = runNonRegression();
  const scope = scopeCheck();
  writeReport(results, regressions, scope);

  console.log("Phase3 Budget Verification");
  for (const result of results) {
    console.log(`- ${result.name}: ${result.pass ? "PASS" : "FAIL"}`);
  }
  console.log(`- phase1_non_regression: ${regressions.phase1.pass ? "PASS" : "FAIL"}`);
  console.log(`- phase2_non_regression: ${regressions.phase2.pass ? "PASS" : "FAIL"}`);
  console.log(`- no_runtime_planner_scope: ${scope.pass ? "PASS" : "FAIL"}`);
  console.log(`phase3_report=${REPORT_PATH}`);
  console.log(`phase3_matrix_json=${MATRIX_JSON_PATH}`);

  if (
    results.some((entry) => !entry.pass) ||
    !regressions.phase1.pass ||
    !regressions.phase2.pass ||
    !scope.pass
  ) {
    process.exit(1);
  }
}

try {
  main();
} finally {
  rmSync(TMP_ROOT, { recursive: true, force: true });
}
