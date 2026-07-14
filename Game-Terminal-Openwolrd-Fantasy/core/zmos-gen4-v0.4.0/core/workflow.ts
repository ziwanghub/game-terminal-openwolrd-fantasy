import type {
  WorkflowDiagnosticStatus,
  WorkflowDiagnosticsSummary,
  WorkflowName,
  WorkflowReportContract,
  WorkflowStepResult,
} from "../contracts/workflow.js";
import { evaluateDoctorDiagnostics } from "../cli/commands/doctor.js";
import { readManifest } from "./manifest.js";
import { loadNodeIdentity } from "./node.js";
import { readTruthRuntimeSnapshot } from "./truth-runtime.js";
import {
  getWorkflowPolicy,
  validateDeniedWorkflowActions,
  validateWorkflowAgainstPolicy,
} from "../governance/workflow-policy.js";
import { appendTraceRecord, getTraceFilePath } from "../trace/writer.js";
import { getWorkflowRegistry } from "./workflow-registry.js";
import { createAdvisoryBundle } from "./advisory-context.js";

export const SUPPORTED_WORKFLOWS: WorkflowName[] = [
  "runtime-check",
  "advisory-check",
  "ai-test",
  "ai-run",
];

export type WorkflowExecutionResult = {
  report: WorkflowReportContract;
  output: string;
};

export type WorkflowListResult = {
  output: string;
};

type WorkflowContext = {
  manifest: Awaited<ReturnType<typeof readManifest>>;
  truthRuntime: Awaited<ReturnType<typeof readTruthRuntimeSnapshot>>;
  nodeIdentity: Awaited<ReturnType<typeof loadNodeIdentity>>;
  doctorEvaluation: Awaited<ReturnType<typeof evaluateDoctorDiagnostics>>;
};

type WorkflowBuildResult = {
  report: WorkflowReportContract;
  traceDetails: Record<string, unknown>;
};

type WorkflowPlan = {
  stepNames: string[];
  advisoryAiInvoked: boolean;
};

function countStepStatuses(
  steps: WorkflowStepResult[],
): { stepsExecuted: number; stepsSkipped: number } {
  return {
    stepsExecuted: steps.filter((step) => step.status !== "skipped").length,
    stepsSkipped: steps.filter((step) => step.status === "skipped").length,
  };
}

function buildWorkflowReport(
  workflow: WorkflowName,
  overallResult: WorkflowDiagnosticStatus,
  readinessLevel: WorkflowReportContract["readinessLevel"],
  diagnosticsSummary: WorkflowDiagnosticsSummary,
  steps: WorkflowStepResult[],
  advisoryAiInvoked: boolean,
  advisoryCommand: string | null,
): WorkflowReportContract {
  const { stepsExecuted, stepsSkipped } = countStepStatuses(steps);

  return {
    workflow,
    overallResult,
    readinessLevel,
    steps,
    diagnosticsSummary,
    advisoryAiInvoked,
    advisoryCommand,
    stepsExecuted,
    stepsSkipped,
  };
}

function buildWorkflowReportLines(report: WorkflowReportContract): string[] {
  return [
    "Z-MOS Workflow Report",
    "",
    `Workflow: ${report.workflow}`,
    `Overall Result: ${report.overallResult}`,
    `Readiness Level: ${report.readinessLevel}`,
    `Advisory AI Invoked: ${report.advisoryAiInvoked ? "yes" : "no"}`,
    `Advisory Command: ${report.advisoryCommand ?? "(none)"}`,
    `Steps Executed: ${report.stepsExecuted}`,
    `Steps Skipped: ${report.stepsSkipped}`,
    "",
    "Steps",
    ...report.steps.map(
      (step) => `- ${step.step} — ${step.status}: ${step.detail}`,
    ),
    "",
    "Diagnostics Summary",
    `- healthy: ${report.diagnosticsSummary.healthy}`,
    `- warning: ${report.diagnosticsSummary.warning}`,
    `- blocking: ${report.diagnosticsSummary.blocking}`,
  ];
}

async function loadWorkflowContext(): Promise<WorkflowContext> {
  const [manifest, truthRuntime, nodeIdentity, doctorEvaluation] = await Promise.all([
    readManifest(),
    readTruthRuntimeSnapshot(),
    loadNodeIdentity(),
    evaluateDoctorDiagnostics(),
  ]);

  return {
    manifest,
    truthRuntime,
    nodeIdentity,
    doctorEvaluation,
  };
}

async function buildRuntimeCheckWorkflow(
  context: WorkflowContext,
): Promise<WorkflowBuildResult> {
  const { manifest, truthRuntime, nodeIdentity, doctorEvaluation } = context;
  const steps: WorkflowStepResult[] = [
    {
      step: "inspect runtime state",
      status: "success",
      detail: `repository=${manifest.repository.name}, truth_session=${truthRuntime.sessionState}`,
    },
    {
      step: "read status evidence",
      status: "success",
      detail: `readiness=${doctorEvaluation.governance.level}, node=${nodeIdentity.node_id}`,
    },
    {
      step: "read doctor diagnostics",
      status:
        doctorEvaluation.overallStatus === "blocking" ? "failed" : "success",
      detail: `healthy=${doctorEvaluation.diagnosticsSummary.healthy}, warning=${doctorEvaluation.diagnosticsSummary.warning}, blocking=${doctorEvaluation.diagnosticsSummary.blocking}`,
    },
    {
      step: "advisory AI invocation",
      status: "skipped",
      detail:
        "not invoked in runtime-check workflow; orchestration remains bounded to runtime evidence only",
    },
  ];

  return {
    report: buildWorkflowReport(
      "runtime-check",
      doctorEvaluation.overallStatus,
      doctorEvaluation.governance.level,
      doctorEvaluation.diagnosticsSummary,
      steps,
      false,
      null,
    ),
    traceDetails: {
      sessionState: truthRuntime.sessionState,
    },
  };
}

async function buildAdvisoryCheckWorkflow(
  context: WorkflowContext,
): Promise<WorkflowBuildResult> {
  const { manifest, truthRuntime, nodeIdentity, doctorEvaluation } = context;
  let advisorySucceeded = false;
  let advisoryAiInvoked = false;
  let advisoryDetail = "advisory bundle was not generated";
  let advisoryCommand = "zcl workflow advisory-check";

  try {
    const bundle = await createAdvisoryBundle(doctorEvaluation.diagnosticsSummary);
    advisorySucceeded = true;
    advisoryAiInvoked = bundle.advisoryMode === "external-code-agent";
    advisoryCommand =
      bundle.advisoryMode === "local-deterministic"
        ? "local-deterministic-advisory"
        : bundle.advisoryMode === "degraded"
          ? "degraded-advisory"
          : "external-code-agent-advisory";
    advisoryDetail = `bundle generated: mode=${bundle.advisoryMode}, input=${bundle.inputPath}, prompt=${bundle.promptPath}`;
  } catch (err) {
    const reason = err instanceof Error ? err.message : "unknown";
    advisoryDetail = `advisory generation degraded: ${reason}`;
  }

  const overallResult: WorkflowDiagnosticStatus =
    doctorEvaluation.overallStatus === "blocking"
      ? "blocking"
      : doctorEvaluation.overallStatus;

  const steps: WorkflowStepResult[] = [
    {
      step: "inspect runtime state",
      status: "success",
      detail: `repository=${manifest.repository.name}, truth_session=${truthRuntime.sessionState}`,
    },
    {
      step: "read status evidence",
      status: "success",
      detail: `readiness=${doctorEvaluation.governance.level}, node=${nodeIdentity.node_id}`,
    },
    {
      step: "read doctor diagnostics",
      status:
        doctorEvaluation.overallStatus === "blocking" ? "failed" : "success",
      detail: `healthy=${doctorEvaluation.diagnosticsSummary.healthy}, warning=${doctorEvaluation.diagnosticsSummary.warning}, blocking=${doctorEvaluation.diagnosticsSummary.blocking}`,
    },
    {
      step: "invoke advisory AI",
      status: advisorySucceeded ? "success" : "skipped",
      detail: advisoryDetail,
    },
  ];

  return {
    report: buildWorkflowReport(
      "advisory-check",
      overallResult,
      doctorEvaluation.governance.level,
      doctorEvaluation.diagnosticsSummary,
      steps,
      advisoryAiInvoked,
      advisoryCommand,
    ),
    traceDetails: {
      sessionState: truthRuntime.sessionState,
      advisoryDetail,
    },
  };
}

async function buildWorkflow(
  workflowName: WorkflowName,
  context: WorkflowContext,
): Promise<WorkflowBuildResult> {
  if (workflowName === "runtime-check") {
    return buildRuntimeCheckWorkflow(context);
  }

  return buildAdvisoryCheckWorkflow(context);
}

function getWorkflowPlan(workflowName: WorkflowName): WorkflowPlan {
  if (workflowName === "runtime-check") {
    return {
      stepNames: [
        "inspect runtime state",
        "read status evidence",
        "read doctor diagnostics",
        "advisory AI invocation",
      ],
      advisoryAiInvoked: false,
    };
  }

  return {
    stepNames: [
      "inspect runtime state",
      "read status evidence",
      "read doctor diagnostics",
      "invoke advisory AI",
    ],
    advisoryAiInvoked: true,
  };
}

export async function runWorkflow(
  workflowName: WorkflowName,
): Promise<WorkflowExecutionResult> {
  const context = await loadWorkflowContext();
  const workflowPolicy = await getWorkflowPolicy(workflowName);
  const workflowRegistry = await getWorkflowRegistry();
  const workflowPlan = getWorkflowPlan(workflowName);
  await validateDeniedWorkflowActions();
  await validateWorkflowAgainstPolicy(
    workflowName,
    workflowPlan.stepNames.map((step) => ({
      step,
      status: "success",
      detail: "policy pre-validation",
    })),
    workflowPlan.advisoryAiInvoked,
  );
  const { report, traceDetails } = await buildWorkflow(workflowName, context);
  const tracePath = await getTraceFilePath();

  await appendTraceRecord({
    command: `zcl workflow ${workflowName}`,
    status: report.overallResult === "blocking" ? "failed" : "success",
    actor: "system",
    details: {
      workflowName: report.workflow,
      stepsExecuted: report.steps
        .filter((step) => step.status !== "skipped")
        .map(({ step, status, detail }) => ({ step, status, detail })),
      stepsSkipped: report.steps
        .filter((step) => step.status === "skipped")
        .map(({ step, status, detail }) => ({ step, status, detail })),
      advisoryAiInvoked: report.advisoryAiInvoked,
      advisoryCommand: report.advisoryCommand,
      overallResult: report.overallResult,
      readinessLevel: report.readinessLevel,
      diagnosticsSummary: report.diagnosticsSummary,
      workflowPolicyValidated: true,
      workflowRegistryVisible: true,
      deniedActionsValidated: true,
      governedWorkflowCount: workflowRegistry.length,
      workflowPolicy: {
        workflowName: workflowPolicy.workflowName,
        advisoryAiAllowed: workflowPolicy.advisoryAiAllowed,
        mutationAllowed: workflowPolicy.mutationAllowed,
        delegationAllowed: workflowPolicy.delegationAllowed,
      },
      nodeId: context.nodeIdentity.node_id,
      nodeRole: context.nodeIdentity.node_role,
      tracePath,
      ...traceDetails,
    },
  });

  return {
    report,
    output: buildWorkflowReportLines(report).join("\n"),
  };
}

export async function listGovernedWorkflows(): Promise<WorkflowListResult> {
  const registry = await getWorkflowRegistry();

  const lines = [
    "Z-MOS Workflow Registry",
    "",
    ...registry.flatMap((entry) => [
      `Workflow: ${entry.workflowName}`,
      `- Advisory AI Allowed: ${entry.advisoryAiAllowed ? "yes" : "no"}`,
      `- Mutation Allowed: ${entry.mutationAllowed ? "yes" : "no"}`,
      `- Delegation Allowed: ${entry.delegationAllowed ? "yes" : "no"}`,
      "",
    ]),
  ];

  if (lines[lines.length - 1] === "") {
    lines.pop();
  }

  return { output: lines.join("\n") };
}

export function assertSupportedWorkflowName(
  workflowName: string | undefined,
): WorkflowName | null {
  if (workflowName && SUPPORTED_WORKFLOWS.includes(workflowName as WorkflowName)) {
    return workflowName as WorkflowName;
  }

  return null;
}
