import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const ROOT_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..");
const METRICS_DIR = path.join(ROOT_DIR, ".z-mos", "metrics");
const DATE_STAMP = new Date().toISOString().slice(0, 10).replace(/-/g, "");

function findLatestMatrixFile() {
  const files = readdirSync(METRICS_DIR).filter((name) =>
    /^phase3-test-matrix-\d{8}\.json$/u.test(name),
  );
  if (files.length === 0) {
    throw new Error("No phase3 test matrix file found in .z-mos/metrics.");
  }
  files.sort();
  return path.join(METRICS_DIR, files[files.length - 1]);
}

function runScopeCheck() {
  const result = spawnSync(
    "rg",
    ["-n", "runtime queue|scheduler|planner|autonomous", "cli/commands/budget.ts", "core/budget.ts"],
    {
      cwd: ROOT_DIR,
      encoding: "utf8",
    },
  );
  const output = `${result.stdout || ""}${result.stderr || ""}`.trim();
  return {
    pass: output.length === 0,
    output,
    note:
      output.length === 0
        ? "No runtime/planner contamination found in Phase 3 implementation scope."
        : "Potential runtime/planner contamination detected in Phase 3 scope.",
  };
}

function main() {
  mkdirSync(METRICS_DIR, { recursive: true });
  const matrixPath = findLatestMatrixFile();
  const matrix = JSON.parse(readFileSync(matrixPath, "utf8"));

  const results = Array.isArray(matrix.results) ? matrix.results : [];
  const byName = Object.fromEntries(results.map((entry) => [entry.name, Boolean(entry.pass)]));
  const phase1Pass = Boolean(matrix.regressions?.phase1?.pass);
  const phase2Pass = Boolean(matrix.regressions?.phase2?.pass);
  const scope = runScopeCheck();

  const kpiResult = {
    profile_selection_correctness: byName["group-2-prompt-profile-tests"] || false,
    budget_decision_correctness: byName["group-1-budget-decision-tests"] || false,
    compact_fallback_correctness: byName["group-2-prompt-profile-tests"] || false,
    block_behavior_correctness: byName["group-1-budget-decision-tests"] || false,
    trace_audit_completeness: byName["group-3-trace-audit-tests"] || false,
    phase1_phase2_backward_compatibility: phase1Pass && phase2Pass,
    no_runtime_planner_contamination: scope.pass,
  };

  const allPass = Object.values(kpiResult).every(Boolean);
  const exitGateDecision = allPass ? "pass" : "fail";

  const summary = {
    task_id: "ZMOS-PHASE3-EXIT-025",
    generated_at: new Date().toISOString(),
    evidence: {
      matrix_file: matrixPath,
      phase3_test_report: path.join(METRICS_DIR, `phase3-test-report-${DATE_STAMP}.md`),
      phase3_matrix_json: matrixPath,
    },
    test_matrix_summary: results,
    non_regression_summary: {
      phase1_pass: phase1Pass,
      phase2_pass: phase2Pass,
    },
    enforcement_summary: {
      telemetry_enforcement_active: byName["group-1-budget-decision-tests"] || false,
      trace_rule_id_present: byName["group-3-trace-audit-tests"] || false,
      compact_fallback_active: byName["group-2-prompt-profile-tests"] || false,
      block_path_active: byName["group-1-budget-decision-tests"] || false,
    },
    kpi_result: kpiResult,
    exit_gate_decision: exitGateDecision,
    scope_check: scope,
  };

  const summaryJsonPath = path.join(METRICS_DIR, `phase3-exit-summary-${DATE_STAMP}.json`);
  const summaryMdPath = path.join(METRICS_DIR, `phase3-exit-report-${DATE_STAMP}.md`);
  writeFileSync(summaryJsonPath, `${JSON.stringify(summary, null, 2)}\n`);

  const lines = [
    "# Phase 3 Exit Report",
    "",
    "## KPI Result",
    `- profile selection correctness: ${kpiResult.profile_selection_correctness ? "PASS" : "FAIL"}`,
    `- budget decision correctness: ${kpiResult.budget_decision_correctness ? "PASS" : "FAIL"}`,
    `- compact fallback correctness: ${kpiResult.compact_fallback_correctness ? "PASS" : "FAIL"}`,
    `- block behavior correctness: ${kpiResult.block_behavior_correctness ? "PASS" : "FAIL"}`,
    `- trace/audit completeness: ${kpiResult.trace_audit_completeness ? "PASS" : "FAIL"}`,
    `- phase1/phase2 backward compatibility: ${kpiResult.phase1_phase2_backward_compatibility ? "PASS" : "FAIL"}`,
    `- no runtime/planner contamination: ${kpiResult.no_runtime_planner_contamination ? "PASS" : "FAIL"}`,
    "",
    "## Exit Gate Decision",
    `- decision: ${exitGateDecision}`,
    "",
    "## Notes",
    `- ${scope.note}`,
    `- source matrix: ${path.basename(matrixPath)}`,
  ];
  writeFileSync(summaryMdPath, `${lines.join("\n")}\n`);

  console.log("Phase3 Exit Summary Completed");
  console.log(`matrix_file=${matrixPath}`);
  console.log(`summary_json=${summaryJsonPath}`);
  console.log(`summary_report=${summaryMdPath}`);
  console.log(`exit_gate_decision=${exitGateDecision}`);
}

main();
