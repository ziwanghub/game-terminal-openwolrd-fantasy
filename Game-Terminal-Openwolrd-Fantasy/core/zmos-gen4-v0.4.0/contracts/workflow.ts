import type { ReadinessLevel } from "../governance/readiness.js";

export type WorkflowName = "runtime-check" | "advisory-check" | "ai-test" | "ai-run";

export type WorkflowDiagnosticStatus = "healthy" | "warning" | "blocking";

export type WorkflowStepStatus = "success" | "failed" | "skipped";

export type WorkflowStepResult = {
  step: string;
  status: WorkflowStepStatus;
  detail: string;
};

export type WorkflowDiagnosticsSummary = {
  healthy: number;
  warning: number;
  blocking: number;
};

export type WorkflowReportContract = {
  workflow: WorkflowName;
  overallResult: WorkflowDiagnosticStatus;
  readinessLevel: ReadinessLevel;
  steps: WorkflowStepResult[];
  diagnosticsSummary: WorkflowDiagnosticsSummary;
  advisoryAiInvoked: boolean;
  advisoryCommand: string | null;
  stepsExecuted: number;
  stepsSkipped: number;
};
