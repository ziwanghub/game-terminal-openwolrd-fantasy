import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const ROOT_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..");
const TMP_ROOT = mkdtempSync(path.join(os.tmpdir(), "zmos-context-phase1-"));
const PROJECT_DIR = path.join(TMP_ROOT, "project");
const ZMOS_DIR = path.join(PROJECT_DIR, ".z-mos");
const STATE_DIR = path.join(ZMOS_DIR, "state");
const TRACE_DIR = path.join(ZMOS_DIR, "trace");
const CONTEXT_DIR = path.join(STATE_DIR, "task-context");

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

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function setupProject() {
  mkdirSync(CONTEXT_DIR, { recursive: true });
  mkdirSync(TRACE_DIR, { recursive: true });

  const manifest = {
    repository: { name: "context-test", framework: "Z-MOS", version: "1.0.0" },
    workspace: { root: ".", stateDir: ".z-mos/state", traceDir: ".z-mos/trace" },
    runtime: { platform: "node", moduleSystem: "esm", entryCommand: "zcl" },
    status: { stage: "test", aiCli: "off" },
    lifecycle: { status: "active", updatedAt: new Date().toISOString(), reason: "test" },
    scope: {
      mutation: {
        mode: "strict",
        allowedPaths: [".z-mos"],
        protectedPaths: [".z-mos"],
      },
    },
  };

  const node = {
    node_id: "test-node",
    node_role: "execution-node",
    runtime: "nodejs-local",
    capabilities: ["cli-execution"],
  };

  writeFileSync(path.join(ZMOS_DIR, "zmos-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  writeFileSync(path.join(ZMOS_DIR, "node.json"), `${JSON.stringify(node, null, 2)}\n`);
}

function readContext(taskId) {
  return JSON.parse(readFileSync(path.join(CONTEXT_DIR, `${taskId}.json`), "utf8"));
}

function readTraceLines() {
  const tracePath = path.join(TRACE_DIR, "runtime-trace.jsonl");
  const raw = readFileSync(tracePath, "utf8").trim();
  if (!raw) return [];
  return raw.split("\n").map((line) => JSON.parse(line));
}

function runSuite() {
  setupProject();

  const results = [];

  // Group 1: happy path
  {
    const taskId = "CTX-HAPPY-001";
    const init = run(["context", "init", "--task-id", taskId]);
    const show = run(["context", "show", "--task-id", taskId]);
    const update = run([
      "context",
      "update",
      "--task-id",
      taskId,
      "--patch",
      '{"progress":{"status":"in_progress","percent":25},"context_pack":{"summary":"ok"}}',
      "--mode",
      "compact",
      "--input-tokens",
      "111",
      "--output-tokens",
      "222",
      "--turnaround-ms",
      "333",
    ]);
    const invalidate = run([
      "context",
      "invalidate",
      "--task-id",
      taskId,
      "--reason",
      "manual_purge",
    ]);
    const context = readContext(taskId);

    const pass =
      init.code === 0 &&
      show.code === 0 &&
      update.code === 0 &&
      invalidate.code === 0 &&
      context.progress.status === "in_progress" &&
      context.freshness.invalidated === true &&
      context.freshness.reason === "manual_purge";
    results.push({ name: "group-1-happy-path", pass, detail: pass ? "ok" : init.output + show.output + update.output + invalidate.output });
  }

  // Group 2: validation fail / forbidden patch
  {
    const taskId = "CTX-VALIDATE-002";
    assert(run(["context", "init", "--task-id", taskId]).code === 0, "init failed in group2");
    const invalidReason = run(["context", "invalidate", "--task-id", taskId, "--reason", "not-valid"]);
    const forbiddenPatch = run([
      "context",
      "update",
      "--task-id",
      taskId,
      "--patch",
      '{"task_id":"hijack"}',
    ]);
    const pass = invalidReason.code !== 0 && forbiddenPatch.code !== 0;
    results.push({ name: "group-2-validation-forbidden", pass, detail: pass ? "ok" : invalidReason.output + forbiddenPatch.output });
  }

  // Group 3: atomic write no partial commit on failure
  {
    const taskId = "CTX-ATOMIC-003";
    assert(run(["context", "init", "--task-id", taskId]).code === 0, "init failed in group3");
    const before = readContext(taskId);
    const failed = run([
      "context",
      "update",
      "--task-id",
      taskId,
      "--patch",
      '{"progress":{"percent":101}}',
    ]);
    const after = readContext(taskId);
    const pass = failed.code !== 0 && JSON.stringify(before) === JSON.stringify(after);
    results.push({ name: "group-3-atomic-no-partial-commit", pass, detail: pass ? "ok" : failed.output });
  }

  // Group 4: telemetry + trace emission
  {
    const taskId = "CTX-TRACE-004";
    assert(run(["context", "init", "--task-id", taskId]).code === 0, "init failed in group4");
    assert(
      run([
        "context",
        "update",
        "--task-id",
        taskId,
        "--patch",
        '{"progress":{"last_action":"telemetry-check"}}',
        "--mode",
        "full",
        "--input-tokens",
        "10",
        "--output-tokens",
        "20",
        "--turnaround-ms",
        "30",
      ]).code === 0,
      "update failed in group4",
    );
    assert(run(["context", "show", "--task-id", taskId]).code === 0, "show failed in group4");
    const context = readContext(taskId);
    const traces = readTraceLines();
    const hasInitTrace = traces.some((entry) => entry.command === "zcl context init");
    const hasUpdateTrace = traces.some((entry) => entry.command === "zcl context update");
    const hasShowTrace = traces.some((entry) => entry.command === "zcl context show");
    const pass =
      context.telemetry.update_count >= 1 &&
      context.telemetry.last_mode === "full" &&
      context.telemetry.last_input_tokens === 10 &&
      context.telemetry.last_output_tokens === 20 &&
      context.telemetry.last_turnaround_ms === 30 &&
      hasInitTrace &&
      hasUpdateTrace &&
      hasShowTrace;
    results.push({ name: "group-4-telemetry-trace", pass, detail: pass ? "ok" : JSON.stringify(context) });
  }

  const failed = results.filter((entry) => !entry.pass);
  const lines = [
    "Context Phase1 Verification",
    ...results.map((entry) => `- ${entry.name}: ${entry.pass ? "PASS" : "FAIL"}`),
  ];
  console.log(lines.join("\n"));
  if (failed.length > 0) {
    console.error("\nFailure details:");
    for (const entry of failed) {
      console.error(`- ${entry.name}: ${entry.detail}`);
    }
    process.exit(1);
  }
}

try {
  runSuite();
} finally {
  rmSync(TMP_ROOT, { recursive: true, force: true });
}
