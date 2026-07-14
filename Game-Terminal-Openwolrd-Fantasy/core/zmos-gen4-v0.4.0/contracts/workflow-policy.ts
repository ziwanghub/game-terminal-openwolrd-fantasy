import type { WorkflowName } from "./workflow.js";
import type { TrustTier } from "./trust-tier.js";

export type WorkflowPolicyContract = {
  workflowName: WorkflowName;
  advisoryAiAllowed: boolean;
  mutationAllowed: boolean;
  delegationAllowed: boolean;
  allowedSteps: string[];
  allowedTasks?: string[];
  forbiddenPatterns?: string[];
  // trustTier: the maximum Trust Tier ceiling for AI tasks in this workflow.
  // If absent, defaults to TIER_2 (bounded task execution, no code mutation).
  trustTier?: TrustTier;
};

export type CriticalCommandPolicyContract = {
  command: "runtime-check" | "advisory-check" | "ai-run" | "ai-test" | "start" | "preflight";
  workflowName: WorkflowName;
};

export type WorkflowPolicyFileContract = {
  workflows: WorkflowPolicyContract[];
  criticalCommands?: CriticalCommandPolicyContract[];
};
