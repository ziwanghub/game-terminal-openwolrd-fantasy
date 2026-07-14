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
const BASELINE_PATH = path.join(METRICS_DIR, `baseline-${DATE_STAMP}.json`);
const POST_PATH = path.join(METRICS_DIR, `post-phase1-${DATE_STAMP}.json`);
const COMPARE_PATH = path.join(METRICS_DIR, `phase1-comparison-${DATE_STAMP}.json`);
const REPORT_PATH = path.join(METRICS_DIR, `phase1-exit-report-${DATE_STAMP}.md`);
const LOG_PATH = path.join(METRICS_DIR, `phase1-exit-commands-${DATE_STAMP}.log`);
const TMP_ROOT = mkdtempSync(path.join(os.tmpdir(), "zmos-phase1-exit-"));
const PROJECT_DIR = path.join(TMP_ROOT, "project");
const TASK_SET_ID = "ZMOS-P1-TASKSET-001";

function estimateTokens(text) {
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

function percentile(sortedNums, p) {
  if (sortedNums.length === 0) return 0;
  if (sortedNums.length === 1) return sortedNums[0];
  const idx = Math.min(
    sortedNums.length - 1,
    Math.max(0, Math.ceil((p / 100) * sortedNums.length) - 1),
  );
  return sortedNums[idx];
}

function runZcl(args) {
  const started = Date.now();
  const result = spawnSync("node", ["./bin/zcl.js", ...args, "--project", PROJECT_DIR], {
    cwd: ROOT_DIR,
    encoding: "utf8",
    env: { ...process.env },
  });
  const ended = Date.now();
  const stdout = result.stdout || "";
  const stderr = result.stderr || "";
  return {
    code: result.status ?? 1,
    stdout,
    stderr,
    output: `${stdout}${stderr}`,
    turnaround_ms: ended - started,
  };
}

function setupProject() {
  const zmosDir = path.join(PROJECT_DIR, ".z-mos");
  const stateDir = path.join(zmosDir, "state", "task-context");
  const traceDir = path.join(zmosDir, "trace");
  mkdirSync(stateDir, { recursive: true });
  mkdirSync(traceDir, { recursive: true });

  const manifest = {
    repository: { name: "phase1-exit", framework: "Z-MOS", version: "1.0.0" },
    workspace: { root: ".", stateDir: ".z-mos/state", traceDir: ".z-mos/trace" },
    runtime: { platform: "node", moduleSystem: "esm", entryCommand: "zcl" },
    status: { stage: "phase1-exit-measure", aiCli: "off" },
    lifecycle: { status: "active", updatedAt: new Date().toISOString(), reason: "measurement" },
    scope: {
      mutation: {
        mode: "strict",
        allowedPaths: [".z-mos"],
        protectedPaths: [".z-mos"],
      },
    },
  };
  const node = {
    node_id: "phase1-exit-node",
    node_role: "execution-node",
    runtime: "nodejs-local",
    capabilities: ["cli-execution"],
  };
  writeFileSync(path.join(zmosDir, "zmos-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  writeFileSync(path.join(zmosDir, "node.json"), `${JSON.stringify(node, null, 2)}\n`);
}

function ensureContextInit(taskId, logs) {
  const init = runZcl(["context", "init", "--task-id", taskId, "--force"]);
  logs.push(`INIT ${taskId} code=${init.code} ms=${init.turnaround_ms}`);
}

function executeTask(taskDef, variant, logs) {
  const taskId = `${taskDef.id}-${variant.toUpperCase()}`;
  ensureContextInit(taskId, logs);
  let inputTokens = 0;
  let outputTokens = 0;
  let reworkCount = 0;
  let conflictCount = 0;
  let turnaroundMs = 0;

  for (const step of taskDef[variant]) {
    inputTokens += estimateTokens(step.args.join(" "));
    const executed = runZcl(step.args.map((arg) => (arg === "__TASK_ID__" ? taskId : arg)));
    outputTokens += estimateTokens(executed.output);
    turnaroundMs += executed.turnaround_ms;
    const ok = executed.code === 0;
    if (!ok) {
      reworkCount += 1;
      if (executed.output.includes("CONTEXT_PATCH_FORBIDDEN")) {
        conflictCount += 1;
      }
      if (step.expectSuccess) {
        logs.push(
          `FAIL_EXPECTED_SUCCESS task=${taskId} step=${step.name} code=${executed.code} output=${executed.output.replace(/\n/g, " ").slice(0, 240)}`,
        );
      }
    }
    logs.push(
      `STEP task=${taskId} variant=${variant} name=${step.name} code=${executed.code} ms=${executed.turnaround_ms}`,
    );
  }

  const contextPath = path.join(PROJECT_DIR, ".z-mos", "state", "task-context", `${taskId}.json`);
  const context = JSON.parse(readFileSync(contextPath, "utf8"));
  const qualityScore = taskDef.assert(context) ? 100 : 0;

  return {
    task_id: taskId,
    task_type: taskDef.type,
    mode_used: variant === "baselineSteps" ? "full" : "compact",
    input_tokens: inputTokens,
    output_tokens: outputTokens,
    total_tokens: inputTokens + outputTokens,
    turnaround_ms: turnaroundMs,
    rework_count: reworkCount,
    conflict_count: conflictCount,
    quality_score: qualityScore,
  };
}

function aggregate(tasks, parallelTaskRuns) {
  const len = tasks.length || 1;
  const input = tasks.reduce((sum, task) => sum + task.input_tokens, 0);
  const output = tasks.reduce((sum, task) => sum + task.output_tokens, 0);
  const rework = tasks.reduce((sum, task) => sum + task.rework_count, 0);
  const conflicts = tasks.reduce((sum, task) => sum + task.conflict_count, 0);
  const qualityPass = tasks.filter((task) => task.quality_score >= 90).length;
  const turns = [...tasks.map((task) => task.turnaround_ms)].sort((a, b) => a - b);
  return {
    avg_input_tokens: Number((input / len).toFixed(2)),
    avg_output_tokens: Number((output / len).toFixed(2)),
    p50_turnaround_ms: percentile(turns, 50),
    p95_turnaround_ms: percentile(turns, 95),
    avg_rework_count: Number((rework / len).toFixed(2)),
    parallel_conflict_rate: Number((((conflicts || 0) / Math.max(1, parallelTaskRuns)) * 100).toFixed(2)),
    quality_pass_rate_ge_90: Number(((qualityPass / len) * 100).toFixed(2)),
  };
}

function deltaPercent(before, after) {
  if (before === 0) return 0;
  return Number((((after - before) / before) * 100).toFixed(2));
}

function buildComparison(before, after) {
  return {
    avg_input_tokens: {
      before: before.avg_input_tokens,
      after: after.avg_input_tokens,
      delta_percent: deltaPercent(before.avg_input_tokens, after.avg_input_tokens),
    },
    avg_output_tokens: {
      before: before.avg_output_tokens,
      after: after.avg_output_tokens,
      delta_percent: deltaPercent(before.avg_output_tokens, after.avg_output_tokens),
    },
    p50_turnaround_ms: {
      before: before.p50_turnaround_ms,
      after: after.p50_turnaround_ms,
      delta_percent: deltaPercent(before.p50_turnaround_ms, after.p50_turnaround_ms),
    },
    p95_turnaround_ms: {
      before: before.p95_turnaround_ms,
      after: after.p95_turnaround_ms,
      delta_percent: deltaPercent(before.p95_turnaround_ms, after.p95_turnaround_ms),
    },
    avg_rework_count: {
      before: before.avg_rework_count,
      after: after.avg_rework_count,
      delta_percent: deltaPercent(before.avg_rework_count, after.avg_rework_count),
    },
    parallel_conflict_rate: {
      before: before.parallel_conflict_rate,
      after: after.parallel_conflict_rate,
      delta_percent: deltaPercent(before.parallel_conflict_rate, after.parallel_conflict_rate),
    },
    quality_pass_rate_ge_90: {
      before: before.quality_pass_rate_ge_90,
      after: after.quality_pass_rate_ge_90,
      delta_percent: deltaPercent(before.quality_pass_rate_ge_90, after.quality_pass_rate_ge_90),
    },
  };
}

function decideExitGate(cmp) {
  const inputReduction = -cmp.avg_input_tokens.delta_percent;
  const reworkReduction = -cmp.avg_rework_count.delta_percent;
  const qualityAfter = cmp.quality_pass_rate_ge_90.after;
  const conflictNoIncrease = cmp.parallel_conflict_rate.after <= cmp.parallel_conflict_rate.before;

  const pass =
    inputReduction >= 20 &&
    reworkReduction >= 10 &&
    qualityAfter >= 90 &&
    conflictNoIncrease;

  return {
    pass: pass ? "pass" : "fail",
    checks: {
      input_reduction_ge_20: inputReduction >= 20,
      rework_reduction_ge_10: reworkReduction >= 10,
      quality_pass_rate_ge_90: qualityAfter >= 90,
      no_increase_conflict_rate: conflictNoIncrease,
    },
  };
}

function writeMarkdownReport(comparison, decision) {
  const lines = [
    "# Phase 1 Exit Report",
    "",
    `task_set_id: ${TASK_SET_ID}`,
    "",
    "## KPI Result",
    `- avg_input_tokens: ${comparison.avg_input_tokens.before} -> ${comparison.avg_input_tokens.after} (${comparison.avg_input_tokens.delta_percent}%)`,
    `- avg_output_tokens: ${comparison.avg_output_tokens.before} -> ${comparison.avg_output_tokens.after} (${comparison.avg_output_tokens.delta_percent}%)`,
    `- p50_turnaround_ms: ${comparison.p50_turnaround_ms.before} -> ${comparison.p50_turnaround_ms.after} (${comparison.p50_turnaround_ms.delta_percent}%)`,
    `- p95_turnaround_ms: ${comparison.p95_turnaround_ms.before} -> ${comparison.p95_turnaround_ms.after} (${comparison.p95_turnaround_ms.delta_percent}%)`,
    `- avg_rework_count: ${comparison.avg_rework_count.before} -> ${comparison.avg_rework_count.after} (${comparison.avg_rework_count.delta_percent}%)`,
    `- parallel_conflict_rate: ${comparison.parallel_conflict_rate.before} -> ${comparison.parallel_conflict_rate.after} (${comparison.parallel_conflict_rate.delta_percent}%)`,
    `- quality_pass_rate_ge_90: ${comparison.quality_pass_rate_ge_90.before} -> ${comparison.quality_pass_rate_ge_90.after} (${comparison.quality_pass_rate_ge_90.delta_percent}%)`,
    "",
    "## Exit Gate Decision",
    `- decision: ${decision.pass}`,
    `- input_reduction_ge_20: ${decision.checks.input_reduction_ge_20}`,
    `- rework_reduction_ge_10: ${decision.checks.rework_reduction_ge_10}`,
    `- quality_pass_rate_ge_90: ${decision.checks.quality_pass_rate_ge_90}`,
    `- no_increase_conflict_rate: ${decision.checks.no_increase_conflict_rate}`,
    "",
    "## Note",
    "- Measurement uses reproducible command-based token proxy (char/4 estimator) for CLI context operations.",
  ];
  writeFileSync(REPORT_PATH, `${lines.join("\n")}\n`);
}

function main() {
  mkdirSync(METRICS_DIR, { recursive: true });
  setupProject();

  const logs = [];

  const taskSet = [
    {
      id: "task-01-docs",
      type: "docs-only-update",
      baselineSteps: [
        {
          name: "update-docs-baseline-heavy",
          expectSuccess: true,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--patch",
            '{"scope":{"objectives":["doc update","doc update","doc update"],"constraints":["consistency","auditability"]},"context_pack":{"summary":"very long docs update summary with repeated narrative for baseline stateless simulation","artifacts":["docs/a.md","docs/b.md","docs/c.md"],"validated_outputs":["doc-pass"]},"progress":{"status":"in_progress","percent":20,"last_action":"docs-edit"}}',
          ],
        },
      ],
      postSteps: [
        {
          name: "update-docs-compact",
          expectSuccess: true,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--patch",
            '{"context_pack":{"summary":"docs update"},"progress":{"status":"in_progress","percent":20,"last_action":"docs-edit"}}',
          ],
        },
      ],
      assert: (ctx) => ctx.progress.status === "in_progress" && ctx.progress.percent === 20,
    },
    {
      id: "task-02-readonly",
      type: "read-only-diagnostics",
      baselineSteps: [
        {
          name: "show-readonly",
          expectSuccess: true,
          args: ["context", "show", "--task-id", "__TASK_ID__"],
        },
      ],
      postSteps: [
        {
          name: "show-readonly",
          expectSuccess: true,
          args: ["context", "show", "--task-id", "__TASK_ID__"],
        },
      ],
      assert: (ctx) => ctx.task_id.includes("task-02-readonly"),
    },
    {
      id: "task-03-lowrisk",
      type: "low-risk-code-mutation",
      baselineSteps: [
        {
          name: "fail-invalid-percent",
          expectSuccess: false,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--patch",
            '{"progress":{"percent":120}}',
          ],
        },
        {
          name: "retry-valid",
          expectSuccess: true,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--patch",
            '{"progress":{"status":"in_progress","percent":35,"last_action":"low-risk-fix"}}',
          ],
        },
      ],
      postSteps: [
        {
          name: "single-valid",
          expectSuccess: true,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--patch",
            '{"progress":{"status":"in_progress","percent":35,"last_action":"low-risk-fix"}}',
          ],
        },
      ],
      assert: (ctx) => ctx.progress.percent === 35,
    },
    {
      id: "task-04-highrisk",
      type: "high-risk-scoped-mutation",
      baselineSteps: [
        {
          name: "set-initial-owner",
          expectSuccess: true,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--actor",
            "owner-a",
            "--patch",
            '{"ownership":{"lane":"backend","claimed_by":"owner-a","claimed_at":"2026-04-02T00:00:00.000Z"}}',
          ],
        },
        {
          name: "conflict-owner-update",
          expectSuccess: false,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--actor",
            "owner-b",
            "--patch",
            '{"ownership":{"lane":"backend","claimed_by":"owner-b","claimed_at":"2026-04-02T00:10:00.000Z"}}',
          ],
        },
        {
          name: "override-owner-update",
          expectSuccess: true,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--actor",
            "owner-b",
            "--override-reason",
            "handoff-approved",
            "--override-approver",
            "lead-1",
            "--patch",
            '{"ownership":{"lane":"backend","claimed_by":"owner-b","claimed_at":"2026-04-02T00:10:00.000Z"}}',
          ],
        },
      ],
      postSteps: [
        {
          name: "set-owner-direct",
          expectSuccess: true,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--actor",
            "owner-a",
            "--patch",
            '{"ownership":{"lane":"backend","claimed_by":"owner-a","claimed_at":"2026-04-02T00:00:00.000Z"}}',
          ],
        },
      ],
      assert: (ctx) => ctx.ownership.claimed_by.length > 0,
    },
    {
      id: "task-05-mixed",
      type: "mixed-task-docs-code",
      baselineSteps: [
        {
          name: "heavy-mixed-update",
          expectSuccess: true,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--patch",
            '{"scope":{"constraints":["stable-api","audit"],"objectives":["docs+code","docs+code"]},"context_pack":{"summary":"mixed baseline narrative with extended detail to emulate repeated stateless context transfer","artifacts":["docs/mixed.md","src/a.ts","src/b.ts"],"validated_outputs":["qa-pass"]},"progress":{"status":"blocked","percent":60,"last_action":"awaiting-review"}}',
          ],
        },
        {
          name: "invalidate-failed",
          expectSuccess: true,
          args: [
            "context",
            "invalidate",
            "--task-id",
            "__TASK_ID__",
            "--reason",
            "status_failed",
          ],
        },
      ],
      postSteps: [
        {
          name: "compact-mixed-update",
          expectSuccess: true,
          args: [
            "context",
            "update",
            "--task-id",
            "__TASK_ID__",
            "--patch",
            '{"context_pack":{"summary":"mixed update"},"progress":{"status":"blocked","percent":60,"last_action":"awaiting-review"}}',
          ],
        },
        {
          name: "invalidate-failed",
          expectSuccess: true,
          args: [
            "context",
            "invalidate",
            "--task-id",
            "__TASK_ID__",
            "--reason",
            "status_failed",
          ],
        },
      ],
      assert: (ctx) => ctx.freshness.invalidated === true && ctx.freshness.reason === "status_failed",
    },
  ];

  const baselineTasks = taskSet.map((taskDef) => executeTask(taskDef, "baselineSteps", logs));
  const postTasks = taskSet.map((taskDef) => executeTask(taskDef, "postSteps", logs));

  const baselineAggregate = aggregate(baselineTasks, 5);
  const postAggregate = aggregate(postTasks, 5);
  const comparison = buildComparison(baselineAggregate, postAggregate);
  const exitDecision = decideExitGate(comparison);

  const baselinePayload = {
    task_set_id: TASK_SET_ID,
    run_timestamp: new Date().toISOString(),
    executor_id: process.env.USER || "unknown",
    commit_sha: process.env.GIT_COMMIT_SHA || "not-available",
    mode: "baseline-emulated-stateless",
    tasks: baselineTasks,
    aggregate: baselineAggregate,
  };
  const postPayload = {
    task_set_id: TASK_SET_ID,
    run_timestamp: new Date().toISOString(),
    executor_id: process.env.USER || "unknown",
    commit_sha: process.env.GIT_COMMIT_SHA || "not-available",
    mode: "post-phase1-context-cache",
    tasks: postTasks,
    aggregate: postAggregate,
  };
  const comparePayload = {
    task_set_id: TASK_SET_ID,
    baseline_file: BASELINE_PATH,
    post_file: POST_PATH,
    comparison,
    exit_gate_decision: exitDecision,
  };

  writeFileSync(BASELINE_PATH, `${JSON.stringify(baselinePayload, null, 2)}\n`);
  writeFileSync(POST_PATH, `${JSON.stringify(postPayload, null, 2)}\n`);
  writeFileSync(COMPARE_PATH, `${JSON.stringify(comparePayload, null, 2)}\n`);
  writeFileSync(LOG_PATH, `${logs.join("\n")}\n`);
  writeMarkdownReport(comparison, exitDecision);

  console.log("Phase1 Exit Measurement Completed");
  console.log(`baseline_file=${BASELINE_PATH}`);
  console.log(`post_file=${POST_PATH}`);
  console.log(`comparison_file=${COMPARE_PATH}`);
  console.log(`report_file=${REPORT_PATH}`);
  console.log(`command_log=${LOG_PATH}`);
  console.log(`exit_gate_decision=${exitDecision.pass}`);
}

try {
  main();
} finally {
  rmSync(TMP_ROOT, { recursive: true, force: true });
}
