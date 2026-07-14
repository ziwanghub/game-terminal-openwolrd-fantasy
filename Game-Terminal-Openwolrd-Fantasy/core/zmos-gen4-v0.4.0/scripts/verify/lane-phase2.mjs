import { spawnSync } from "node:child_process";
import {
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
const REPORT_PATH = path.join(METRICS_DIR, `phase2-test-report-${DATE_STAMP}.md`);
const MATRIX_JSON_PATH = path.join(METRICS_DIR, `phase2-test-matrix-${DATE_STAMP}.json`);
const TMP_ROOT = mkdtempSync(path.join(os.tmpdir(), "zmos-phase2-lane-"));
const PROJECT_DIR = path.join(TMP_ROOT, "project");
const CONTEXT_DIR = path.join(PROJECT_DIR, ".z-mos", "state", "task-context");
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

function containsError(result, code) {
  return result.code !== 0 && result.output.includes(code);
}

function setupProject() {
  const zmosDir = path.join(PROJECT_DIR, ".z-mos");
  mkdirSync(path.join(zmosDir, "state", "task-context"), { recursive: true });
  mkdirSync(path.join(zmosDir, "trace"), { recursive: true });
  const manifest = {
    repository: { name: "lane-test", framework: "Z-MOS", version: "1.0.0" },
    workspace: { root: ".", stateDir: ".z-mos/state", traceDir: ".z-mos/trace" },
    runtime: { platform: "node", moduleSystem: "esm", entryCommand: "zcl" },
    status: { stage: "phase2-test", aiCli: "off" },
    lifecycle: { status: "active", updatedAt: new Date().toISOString(), reason: "phase2 test" },
    scope: {
      mutation: {
        mode: "strict",
        allowedPaths: [".z-mos"],
        protectedPaths: [".z-mos"],
      },
    },
  };
  const node = {
    node_id: "lane-test-node",
    node_role: "execution-node",
    runtime: "nodejs-local",
    capabilities: ["cli-execution"],
  };
  writeFileSync(path.join(zmosDir, "zmos-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  writeFileSync(path.join(zmosDir, "node.json"), `${JSON.stringify(node, null, 2)}\n`);
}

function initContext(taskId) {
  return run(["context", "init", "--task-id", taskId, "--force"]);
}

function readContext(taskId) {
  return JSON.parse(readFileSync(path.join(CONTEXT_DIR, `${taskId}.json`), "utf8"));
}

function readTrace() {
  const raw = readFileSync(TRACE_PATH, "utf8").trim();
  if (!raw) return [];
  return raw.split("\n").map((line) => JSON.parse(line));
}

function testGroup1() {
  const task = "LANE-G1";
  initContext(task);
  const claim = run(["lane", "claim", "--task-id", task, "--lane", "backend", "--actor", "a1"]);
  const refresh = run([
    "lane",
    "claim",
    "--task-id",
    task,
    "--lane",
    "backend",
    "--actor",
    "a1",
  ]);
  const release = run(["lane", "release", "--task-id", task, "--actor", "a1"]);
  return claim.code === 0 && refresh.code === 0 && release.code === 0;
}

function testGroup2() {
  const task = "LANE-G2";
  initContext(task);
  const claim1 = run(["lane", "claim", "--task-id", task, "--lane", "backend", "--actor", "a1"]);
  const claim2 = run(["lane", "claim", "--task-id", task, "--lane", "backend", "--actor", "b1"]);
  const shortClaim = run([
    "lane",
    "claim",
    "--task-id",
    task,
    "--lane",
    "backend",
    "--actor",
    "a1",
    "--timeout-minutes",
    "0.0001",
  ]);
  const reclaim = run(["lane", "claim", "--task-id", task, "--lane", "backend", "--actor", "b1"]);
  return (
    claim1.code === 0 &&
    containsError(claim2, "LANE_CLAIM_CONFLICT") &&
    shortClaim.code === 0 &&
    reclaim.code === 0
  );
}

function testGroup3() {
  const task = "LANE-G3";
  initContext(task);
  run(["lane", "lock-artifact", "--task-id", task, "--lane", "backend", "--actor", "a1", "--artifact", "build-v1"]);
  const precedenceConflict = run([
    "lane",
    "lock-path",
    "--task-id",
    task,
    "--lane",
    "backend",
    "--actor",
    "b1",
    "--path",
    "/api/users",
  ]);
  run(["lane", "release", "--task-id", task, "--actor", "a1"]);
  run(["lane", "lock-path", "--task-id", task, "--lane", "backend", "--actor", "a1", "--path", "/api/users"]);
  const overlapConflict = run([
    "lane",
    "lock-path",
    "--task-id",
    task,
    "--lane",
    "backend",
    "--actor",
    "b1",
    "--path",
    "/api",
  ]);
  return containsError(precedenceConflict, "LANE_LOCK_CONFLICT") && containsError(overlapConflict, "LANE_LOCK_CONFLICT");
}

function testGroup4() {
  const task = "LANE-G4";
  initContext(task);
  run(["lane", "claim", "--task-id", task, "--lane", "backend", "--actor", "a1"]);
  const noOverride = run([
    "lane",
    "lock-path",
    "--task-id",
    task,
    "--lane",
    "backend",
    "--actor",
    "b1",
    "--path",
    "/core/x",
  ]);
  const handoff = run([
    "lane",
    "handoff",
    "--task-id",
    task,
    "--to-lane",
    "docs",
    "--actor",
    "a1",
    "--summary",
    "handoff-to-docs",
  ]);
  const pendingBlock = run([
    "lane",
    "lock-artifact",
    "--task-id",
    task,
    "--lane",
    "backend",
    "--actor",
    "a1",
    "--artifact",
    "x",
  ]);
  const ack = run(["lane", "ack", "--task-id", task, "--actor", "b1"]);
  const postAck = run([
    "lane",
    "lock-path",
    "--task-id",
    task,
    "--lane",
    "docs",
    "--actor",
    "b1",
    "--path",
    "/docs/a",
  ]);
  return (
    containsError(noOverride, "LANE_OVERRIDE_REQUIRED") &&
    handoff.code === 0 &&
    containsError(pendingBlock, "LANE_HANDOFF_PENDING") &&
    ack.code === 0 &&
    postAck.code === 0
  );
}

function testGroup5() {
  const task = "LANE-G5";
  initContext(task);
  const before = readFileSync(path.join(CONTEXT_DIR, `${task}.json`), "utf8");
  const failed = run(["lane", "lock-path", "--task-id", task, "--lane", "backend", "--actor", "a1"]);
  const after = readFileSync(path.join(CONTEXT_DIR, `${task}.json`), "utf8");
  return failed.code !== 0 && before === after;
}

function testGroup6() {
  const task = "LANE-G6";
  initContext(task);
  run(["lane", "claim", "--task-id", task, "--lane", "backend", "--actor", "a1"]);
  run([
    "lane",
    "handoff",
    "--task-id",
    task,
    "--to-lane",
    "docs",
    "--actor",
    "a1",
    "--summary",
    "handoff",
  ]);
  run(["lane", "ack", "--task-id", task, "--actor", "b1"]);
  run(["lane", "release", "--task-id", task, "--actor", "b1"]);
  const trace = readTrace();
  const commands = trace.map((entry) => entry.command);
  return (
    commands.includes("zcl lane claim") &&
    commands.includes("zcl lane handoff") &&
    commands.includes("zcl lane ack") &&
    commands.includes("zcl lane release")
  );
}

function testGroup7() {
  const result = spawnSync("node", ["./scripts/verify/context-phase1.mjs"], {
    cwd: ROOT_DIR,
    encoding: "utf8",
    env: { ...process.env },
  });
  return {
    pass: (result.status ?? 1) === 0,
    output: `${result.stdout || ""}${result.stderr || ""}`,
  };
}

function writeReport(results, nonRegression) {
  const lines = [
    "# Phase 2 Test Report",
    "",
    ...results.map((entry) => `- ${entry.name}: ${entry.pass ? "PASS" : "FAIL"}`),
    `- phase1_non_regression: ${nonRegression.pass ? "PASS" : "FAIL"}`,
  ];
  writeFileSync(REPORT_PATH, `${lines.join("\n")}\n`);
  writeFileSync(
    MATRIX_JSON_PATH,
    `${JSON.stringify({ results, non_regression: nonRegression }, null, 2)}\n`,
  );
}

function main() {
  mkdirSync(METRICS_DIR, { recursive: true });
  setupProject();
  const results = [
    { name: "group-1-claim-release-happy-path", pass: testGroup1() },
    { name: "group-2-claim-conflict-stale-reclaim", pass: testGroup2() },
    { name: "group-3-lock-conflict-precedence", pass: testGroup3() },
    { name: "group-4-override-handoff-flow", pass: testGroup4() },
    { name: "group-5-atomic-no-partial-commit", pass: testGroup5() },
    { name: "group-6-trace-evidence", pass: testGroup6() },
  ];
  const nonRegression = testGroup7();
  writeReport(results, nonRegression);

  console.log("Phase2 Lane Verification");
  for (const result of results) {
    console.log(`- ${result.name}: ${result.pass ? "PASS" : "FAIL"}`);
  }
  console.log(`- phase1_non_regression: ${nonRegression.pass ? "PASS" : "FAIL"}`);
  console.log(`phase2_report=${REPORT_PATH}`);
  console.log(`phase2_matrix_json=${MATRIX_JSON_PATH}`);

  if (results.some((entry) => !entry.pass) || !nonRegression.pass) {
    console.error("\nNon-regression output:");
    console.error(nonRegression.output);
    process.exit(1);
  }
}

try {
  main();
} finally {
  rmSync(TMP_ROOT, { recursive: true, force: true });
}
