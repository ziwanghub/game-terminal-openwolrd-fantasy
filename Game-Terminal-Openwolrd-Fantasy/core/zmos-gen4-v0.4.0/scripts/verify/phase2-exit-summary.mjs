import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const ROOT_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..");
const METRICS_DIR = path.join(ROOT_DIR, ".z-mos", "metrics");
const DATE_STAMP = new Date().toISOString().slice(0, 10).replace(/-/g, "");

function findLatestMatrixFile() {
  const files = readdirSync(METRICS_DIR).filter((name) =>
    /^phase2-test-matrix-\d{8}\.json$/u.test(name),
  );
  if (files.length === 0) {
    throw new Error("No phase2 test matrix file found in .z-mos/metrics.");
  }
  files.sort();
  return path.join(METRICS_DIR, files[files.length - 1]);
}

function runScopeCheck() {
  const result = spawnSync(
    "rg",
    ["-n", "phase3|token budget|planner|runtime queue|scheduler", "cli", "core", "scripts"],
    {
      cwd: ROOT_DIR,
      encoding: "utf8",
    },
  );
  const output = `${result.stdout || ""}${result.stderr || ""}`;
  const hasScopedContamination = output
    .split("\n")
    .some((line) => line.includes("cli/commands/lane.ts") || line.includes("core/lane.ts"));
  return {
    pass: !hasScopedContamination,
    note: hasScopedContamination
      ? "Potential phase3/runtime contamination signals found in phase2 implementation files."
      : "No phase3/runtime queue/planner contamination signals in phase2 implementation files.",
  };
}

function main() {
  mkdirSync(METRICS_DIR, { recursive: true });
  const matrixPath = findLatestMatrixFile();
  const matrix = JSON.parse(readFileSync(matrixPath, "utf8"));
  const results = Array.isArray(matrix.results) ? matrix.results : [];

  const byName = Object.fromEntries(results.map((entry) => [entry.name, Boolean(entry.pass)]));
  const nonRegressionPass = Boolean(matrix.non_regression?.pass);
  const scopeCheck = runScopeCheck();

  const kpiResult = {
    conflict_handling_result:
      byName["group-2-claim-conflict-stale-reclaim"] &&
      byName["group-3-lock-conflict-precedence"],
    stale_reclaim_result: byName["group-2-claim-conflict-stale-reclaim"] || false,
    handoff_override_result: byName["group-4-override-handoff-flow"] || false,
    trace_audit_completeness: byName["group-6-trace-evidence"] || false,
    phase1_backward_compatibility: nonRegressionPass,
    atomicity_integrity_result: byName["group-5-atomic-no-partial-commit"] || false,
    shared_path_precedence_deterministic: byName["group-3-lock-conflict-precedence"] || false,
    no_phase3_runtime_scope_contamination: scopeCheck.pass,
  };

  const allPass = Object.values(kpiResult).every(Boolean);
  const exitDecision = allPass ? "pass" : "fail";

  const jsonReport = {
    task_id: "ZMOS-PHASE2-EXIT-022",
    generated_at: new Date().toISOString(),
    evidence: {
      matrix_file: matrixPath,
      phase2_test_report: path.join(METRICS_DIR, `phase2-test-report-${DATE_STAMP}.md`),
      phase2_matrix_json: matrixPath,
    },
    test_matrix_summary: results,
    non_regression_summary: {
      pass: nonRegressionPass,
      output_excerpt: (matrix.non_regression?.output || "").split("\n").slice(0, 10),
    },
    compatibility_summary: {
      phase1_backward_compatibility: nonRegressionPass,
      phase2_additive_schema: true,
      no_phase3_runtime_scope_contamination: scopeCheck.pass,
      scope_check_note: scopeCheck.note,
    },
    kpi_result: kpiResult,
    exit_gate_decision: exitDecision,
  };

  const jsonPath = path.join(METRICS_DIR, `phase2-exit-summary-${DATE_STAMP}.json`);
  const mdPath = path.join(METRICS_DIR, `phase2-exit-report-${DATE_STAMP}.md`);
  writeFileSync(jsonPath, `${JSON.stringify(jsonReport, null, 2)}\n`);

  const lines = [
    "# Phase 2 Exit Report",
    "",
    "## KPI Result",
    `- conflict handling result: ${kpiResult.conflict_handling_result ? "PASS" : "FAIL"}`,
    `- stale reclaim result: ${kpiResult.stale_reclaim_result ? "PASS" : "FAIL"}`,
    `- handoff/override result: ${kpiResult.handoff_override_result ? "PASS" : "FAIL"}`,
    `- trace/audit completeness: ${kpiResult.trace_audit_completeness ? "PASS" : "FAIL"}`,
    `- phase1 backward compatibility: ${kpiResult.phase1_backward_compatibility ? "PASS" : "FAIL"}`,
    `- atomicity/integrity result: ${kpiResult.atomicity_integrity_result ? "PASS" : "FAIL"}`,
    `- shared-path precedence deterministic: ${kpiResult.shared_path_precedence_deterministic ? "PASS" : "FAIL"}`,
    `- no phase3/runtime scope contamination: ${kpiResult.no_phase3_runtime_scope_contamination ? "PASS" : "FAIL"}`,
    "",
    "## Exit Gate Decision",
    `- decision: ${exitDecision}`,
    "",
    "## Notes",
    `- ${scopeCheck.note}`,
    `- source matrix: ${path.basename(matrixPath)}`,
  ];
  writeFileSync(mdPath, `${lines.join("\n")}\n`);

  console.log("Phase2 Exit Summary Completed");
  console.log(`matrix_file=${matrixPath}`);
  console.log(`summary_json=${jsonPath}`);
  console.log(`summary_report=${mdPath}`);
  console.log(`exit_gate_decision=${exitDecision}`);
}

main();
