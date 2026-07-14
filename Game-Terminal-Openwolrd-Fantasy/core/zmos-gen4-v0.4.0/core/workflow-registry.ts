import type { WorkflowName } from "../contracts/workflow.js";
import { loadWorkflowPolicy } from "../governance/workflow-policy.js";

export type WorkflowRegistryEntry = {
  workflowName: WorkflowName;
  advisoryAiAllowed: boolean;
  mutationAllowed: boolean;
  delegationAllowed: boolean;
};

export async function getWorkflowRegistry(): Promise<WorkflowRegistryEntry[]> {
  const policy = await loadWorkflowPolicy();
  return policy.workflows.map((workflow) => ({
    workflowName: workflow.workflowName,
    advisoryAiAllowed: workflow.advisoryAiAllowed,
    mutationAllowed: workflow.mutationAllowed,
    delegationAllowed: workflow.delegationAllowed,
  }));
}

export async function getWorkflowRegistrySummary(): Promise<{
  scope: "bounded-local";
  governedWorkflowCount: number;
  disallowedActions: string[];
}> {
  const registry = await getWorkflowRegistry();
  const disallowedActions = new Set<string>();

  if (registry.every((entry) => !entry.mutationAllowed)) {
    disallowedActions.add("mutation");
  }

  if (registry.every((entry) => !entry.delegationAllowed)) {
    disallowedActions.add("delegation");
  }

  return {
    scope: "bounded-local",
    governedWorkflowCount: registry.length,
    disallowedActions: Array.from(disallowedActions),
  };
}
