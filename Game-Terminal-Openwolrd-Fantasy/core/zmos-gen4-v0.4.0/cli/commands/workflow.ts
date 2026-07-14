import type { WorkflowName } from "../../contracts/workflow.js";
import { listGovernedWorkflows, runWorkflow } from "../../core/workflow.js";
import { renderCommandExecutionResult } from "../../core/execution-contract.js";
import { evaluateMutationGuard } from "../../core/mutation-guard.js";
import { evaluateCanonicalStateIntegrity } from "../../core/state-integrity.js";
import { evaluateWorkflowCoverage } from "../../core/workflow-coverage.js";

export async function runWorkflowCommand(workflowName: WorkflowName): Promise<void> {
  const canonicalIntegrity = await evaluateCanonicalStateIntegrity();
  const commandName =
    workflowName === "runtime-check"
      ? "workflow-runtime-check"
      : "workflow-advisory-check";

  if (canonicalIntegrity.status === "blocking") {
    const topFinding = canonicalIntegrity.findings[0];
    const policyBlocked = canonicalIntegrity.recoveryClass === "policy-rebuild-required";
    console.log(
      renderCommandExecutionResult({
        command: commandName,
        status: "blocked",
        resultClass: policyBlocked
          ? "blocked-policy"
          : "blocked-canonical-integrity",
        reason: topFinding?.reason || "Canonical integrity is blocking workflow execution.",
        traceExpectation: "required-if-business-logic",
        traceResult: "not-emitted-blocked-before-logic",
        nextAction:
          topFinding?.action || "Repair canonical integrity before workflow execution.",
      }),
    );
    process.exitCode = 1;
    return;
  }

  try {
    const traceMutationGuard = await evaluateMutationGuard({
      command: `zcl workflow ${workflowName}`,
      targetPaths: [".z-mos/trace/runtime-trace.jsonl"],
      allowProtectedPrefixes: [".z-mos"],
    });
    if (!traceMutationGuard.allowed) {
      console.log(
        renderCommandExecutionResult({
          command: commandName,
          status: "blocked",
          resultClass: "blocked-policy",
          reason: traceMutationGuard.reason,
          warningReason:
            traceMutationGuard.warnings.length > 0
              ? traceMutationGuard.warnings.join(" | ")
              : undefined,
          traceExpectation: "required-if-business-logic",
          traceResult: "not-emitted-blocked-before-logic",
          nextAction:
            "Set lifecycle.status=active and align manifest scope.mutation before workflow mutation.",
        }),
      );
      process.exitCode = 1;
      return;
    }

    const result = await runWorkflow(workflowName);
    const status =
      result.report.overallResult === "blocking"
        ? "blocked"
        : result.report.overallResult === "warning"
          ? "warning"
          : "success";
    const resultClass =
      result.report.overallResult === "blocking"
        ? "blocked-policy"
        : result.report.overallResult === "warning"
          ? "warning-execution"
          : "success";
    const nextAction =
      result.report.overallResult === "blocking"
        ? "Resolve workflow policy or runtime blockers before rerunning workflow."
        : undefined;

    console.log(
      [
        result.output,
        "",
        renderCommandExecutionResult({
          command: commandName,
          status,
          resultClass,
          traceExpectation: "required-if-business-logic",
          traceResult: "emitted",
          nextAction,
        }),
      ].join("\n"),
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown workflow runtime error";
    const isPolicyBlock = message.includes("Workflow governance error");
    console.log(
      renderCommandExecutionResult({
        command: commandName,
        status: isPolicyBlock ? "blocked" : "failed",
        resultClass: isPolicyBlock ? "blocked-policy" : "failed-runtime",
        reason: message,
        traceExpectation: "required-if-business-logic",
        traceResult: "not-emitted-blocked-before-logic",
        nextAction: isPolicyBlock
          ? "Review workflow policy and denied-action rules before rerunning workflow."
          : "Review runtime error and rerun after recovery.",
      }),
    );
    process.exitCode = 1;
  }
}

export async function runWorkflowListCommand(): Promise<void> {
  try {
    const result = await listGovernedWorkflows();
    console.log(
      [
        result.output,
        "",
        renderCommandExecutionResult({
          command: "workflow-list",
          status: "success",
          resultClass: "success",
          traceExpectation: "optional-by-design",
          traceResult: "not-emitted-by-design",
        }),
      ].join("\n"),
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown workflow list error";
    console.log(
      renderCommandExecutionResult({
        command: "workflow-list",
        status: "failed",
        resultClass: "failed-runtime",
        reason: message,
        traceExpectation: "optional-by-design",
        traceResult: "not-emitted-due-failure",
        nextAction: "Review workflow registry availability and retry.",
      }),
    );
    process.exitCode = 1;
  }
}

export async function runWorkflowCoverageCheckCommand(): Promise<void> {
  try {
    const coverage = await evaluateWorkflowCoverage();
    const status =
      coverage.status === "blocking"
        ? "blocked"
        : coverage.status === "warning"
          ? "warning"
          : "success";
    const resultClass =
      coverage.status === "blocking"
        ? "blocked-policy"
        : coverage.status === "warning"
          ? "warning-execution"
          : "success";
    const lines = [
      "Z-MOS Workflow Coverage Report",
      "",
      `status: ${coverage.status.toUpperCase()}`,
      `governed_workflows: ${coverage.inventory.governedWorkflows.join(", ")}`,
      `critical_commands_expected: ${coverage.inventory.criticalCommands.join(", ")}`,
      `critical_commands_in_policy: ${coverage.inventory.policyCriticalCommands.join(", ")}`,
      `missing_critical_commands: ${coverage.missingCriticalCommands.length > 0 ? coverage.missingCriticalCommands.join(", ") : "(none)"}`,
      `unresolved_critical_workflows: ${coverage.unresolvedCriticalWorkflows.length > 0 ? coverage.unresolvedCriticalWorkflows.join(", ") : "(none)"}`,
      "",
      renderCommandExecutionResult({
        command: "workflow-coverage-check",
        status,
        resultClass,
        traceExpectation: "optional-by-design",
        traceResult: "not-emitted-by-design",
        nextAction:
          coverage.status === "healthy"
            ? undefined
            : "Update .z-mos/workflow-policy.json criticalCommands/workflows to close governance gaps.",
      }),
    ];
    console.log(lines.join("\n"));
    if (coverage.status === "blocking") {
      process.exitCode = 1;
    }
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown workflow coverage runtime error";
    console.log(
      renderCommandExecutionResult({
        command: "workflow-coverage-check",
        status: "failed",
        resultClass: "failed-runtime",
        reason: message,
        traceExpectation: "optional-by-design",
        traceResult: "not-emitted-due-failure",
        nextAction: "Review workflow policy schema and rerun coverage check.",
      }),
    );
    process.exitCode = 1;
  }
}
