import { loadWorkflowPolicy } from "../governance/workflow-policy.js";

type CriticalPolicyCommand = "runtime-check" | "advisory-check" | "ai-run" | "ai-test" | "start" | "preflight";

const DEFAULT_CRITICAL_COMMANDS: CriticalPolicyCommand[] = [
  "runtime-check",
  "advisory-check",
  "ai-run",
  "ai-test",
  "start",
  "preflight",
];

export type WorkflowCoverageReport = {
  status: "healthy" | "warning" | "blocking";
  inventory: {
    governedWorkflows: string[];
    criticalCommands: CriticalPolicyCommand[];
    policyCriticalCommands: string[];
  };
  missingCriticalCommands: string[];
  unresolvedCriticalWorkflows: string[];
};

export async function evaluateWorkflowCoverage(): Promise<WorkflowCoverageReport> {
  const policy = await loadWorkflowPolicy();
  const governedWorkflows = policy.workflows.map((entry) => entry.workflowName);
  const policyCriticalCommands = (policy.criticalCommands ?? []).map((entry) => entry.command);

  const missingCriticalCommands = DEFAULT_CRITICAL_COMMANDS.filter(
    (command) => !policyCriticalCommands.includes(command),
  );
  const unresolvedCriticalWorkflows = (policy.criticalCommands ?? [])
    .filter((entry) => !governedWorkflows.includes(entry.workflowName))
    .map((entry) => `${entry.command} -> ${entry.workflowName}`);

  const blocking = unresolvedCriticalWorkflows.length > 0;
  const warning = missingCriticalCommands.length > 0;

  return {
    status: blocking ? "blocking" : warning ? "warning" : "healthy",
    inventory: {
      governedWorkflows,
      criticalCommands: DEFAULT_CRITICAL_COMMANDS,
      policyCriticalCommands,
    },
    missingCriticalCommands,
    unresolvedCriticalWorkflows,
  };
}
