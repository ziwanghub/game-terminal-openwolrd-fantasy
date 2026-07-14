import { promises as fs } from "node:fs";
import * as path from "node:path";

import type {
  CriticalCommandPolicyContract,
  WorkflowPolicyContract,
  WorkflowPolicyFileContract,
} from "../contracts/workflow-policy.js";
import type { WorkflowName, WorkflowStepResult } from "../contracts/workflow.js";

const ROOT_DIR = process.cwd();
const WORKFLOW_POLICY_PATH = path.join(ROOT_DIR, ".z-mos", "workflow-policy.json");

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function assertString(value: unknown, fieldPath: string): asserts value is string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(
      `Invalid workflow policy: ${fieldPath} must be a non-empty string`,
    );
  }
}

function assertBoolean(
  value: unknown,
  fieldPath: string,
): asserts value is boolean {
  if (typeof value !== "boolean") {
    throw new Error(`Invalid workflow policy: ${fieldPath} must be a boolean`);
  }
}

function assertStringArray(
  value: unknown,
  fieldPath: string,
): asserts value is string[] {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== "string")) {
    throw new Error(
      `Invalid workflow policy: ${fieldPath} must be an array of strings`,
    );
  }
}

function validateWorkflowName(value: unknown, fieldPath: string): WorkflowName {
  assertString(value, fieldPath);

  const allowed: WorkflowName[] = ["runtime-check", "advisory-check", "ai-test", "ai-run"];
  if (!allowed.includes(value as WorkflowName)) {
    throw new Error(
      `Invalid workflow policy: ${fieldPath} must be one of: ${allowed.join(", ")}`,
    );
  }

  return value as WorkflowName;
}

function validateWorkflowPolicy(value: unknown): WorkflowPolicyContract {
  if (!isObject(value)) {
    throw new Error("Invalid workflow policy: each workflow entry must be an object");
  }

  assertBoolean(value.advisoryAiAllowed, "advisoryAiAllowed");
  assertBoolean(value.mutationAllowed, "mutationAllowed");
  assertBoolean(value.delegationAllowed, "delegationAllowed");
  assertStringArray(value.allowedSteps, "allowedSteps");

  const entry: WorkflowPolicyContract = {
    workflowName: validateWorkflowName(value.workflowName, "workflowName"),
    advisoryAiAllowed: value.advisoryAiAllowed,
    mutationAllowed: value.mutationAllowed,
    delegationAllowed: value.delegationAllowed,
    allowedSteps: value.allowedSteps,
  };

  if (value.allowedTasks !== undefined) {
    assertStringArray(value.allowedTasks, "allowedTasks");
    entry.allowedTasks = value.allowedTasks;
  }

  if (value.forbiddenPatterns !== undefined) {
    assertStringArray(value.forbiddenPatterns, "forbiddenPatterns");
    entry.forbiddenPatterns = value.forbiddenPatterns;
  }

  if (value.trustTier !== undefined) {
    assertString(value.trustTier, "trustTier");
    const allowedTiers = ["TIER_0", "TIER_1", "TIER_2", "TIER_3"];
    if (!allowedTiers.includes(value.trustTier)) {
      throw new Error(
        `Invalid workflow policy: trustTier must be one of ${allowedTiers.join(", ")}`,
      );
    }
    entry.trustTier = value.trustTier as WorkflowPolicyContract["trustTier"];
  }

  return entry;
}

function validateCriticalCommand(value: unknown): CriticalCommandPolicyContract {
  if (!isObject(value)) {
    throw new Error("Invalid workflow policy: criticalCommands entry must be an object");
  }
  assertString(value.command, "criticalCommands.command");
  const command = value.command;
  const allowedCommands = [
    "runtime-check",
    "advisory-check",
    "ai-run",
    "ai-test",
    "start",
    "preflight",
  ];
  if (!allowedCommands.includes(command)) {
    throw new Error(
      `Invalid workflow policy: criticalCommands.command must be one of ${allowedCommands.join(", ")}`,
    );
  }
  const workflowName = validateWorkflowName(
    value.workflowName,
    "criticalCommands.workflowName",
  );
  return {
    command: command as CriticalCommandPolicyContract["command"],
    workflowName,
  };
}

function validateWorkflowPolicyFile(value: unknown): WorkflowPolicyFileContract {
  if (!isObject(value)) {
    throw new Error("Invalid workflow policy: root value must be an object");
  }

  if (!Array.isArray(value.workflows)) {
    throw new Error("Invalid workflow policy: workflows must be an array");
  }

  const workflows = value.workflows.map(validateWorkflowPolicy);
  const criticalCommands = Array.isArray(value.criticalCommands)
    ? value.criticalCommands.map(validateCriticalCommand)
    : undefined;
  return { workflows, criticalCommands };
}

export async function loadWorkflowPolicy(): Promise<WorkflowPolicyFileContract> {
  const rawPolicy = await fs.readFile(WORKFLOW_POLICY_PATH, "utf8");
  let parsedPolicy: unknown;

  try {
    parsedPolicy = JSON.parse(rawPolicy) as unknown;
  } catch {
    throw new Error(`Invalid workflow policy: ${WORKFLOW_POLICY_PATH} is not valid JSON`);
  }

  return validateWorkflowPolicyFile(parsedPolicy);
}

export function getWorkflowPolicyPath(): string {
  return WORKFLOW_POLICY_PATH;
}

export async function getWorkflowPolicy(
  workflowName: WorkflowName,
): Promise<WorkflowPolicyContract> {
  const policy = await loadWorkflowPolicy();
  const workflowPolicy = policy.workflows.find(
    (entry) => entry.workflowName === workflowName,
  );

  if (!workflowPolicy) {
    throw new Error(`Workflow governance error: no policy defined for ${workflowName}`);
  }

  return workflowPolicy;
}

export async function validateWorkflowAgainstPolicy(
  workflowName: WorkflowName,
  steps: WorkflowStepResult[],
  advisoryAiInvoked: boolean,
): Promise<void> {
  const policy = await getWorkflowPolicy(workflowName);

  if (policy.mutationAllowed) {
    throw new Error(
      `Workflow governance error: mutation is not supported for ${workflowName}`,
    );
  }

  if (policy.delegationAllowed) {
    throw new Error(
      `Workflow governance error: delegation is not supported for ${workflowName}`,
    );
  }

  if (advisoryAiInvoked && !policy.advisoryAiAllowed) {
    throw new Error(
      `Workflow governance error: advisory AI is not allowed for ${workflowName}`,
    );
  }

  const invalidSteps = steps
    .map((step) => step.step)
    .filter((stepName) => !policy.allowedSteps.includes(stepName));

  if (invalidSteps.length > 0) {
    throw new Error(
      `Workflow governance error: disallowed steps for ${workflowName}: ${invalidSteps.join(", ")}`,
    );
  }
}

export async function validateDeniedWorkflowActions(): Promise<void> {
  const policy = await loadWorkflowPolicy();

  const mutationEnabled = policy.workflows.filter((entry) => entry.mutationAllowed);
  if (mutationEnabled.length > 0) {
    throw new Error(
      `Workflow governance error: mutation must remain disallowed for current workflows: ${mutationEnabled
        .map((entry) => entry.workflowName)
        .join(", ")}`,
    );
  }

  const delegationEnabled = policy.workflows.filter((entry) => entry.delegationAllowed);
  if (delegationEnabled.length > 0) {
    throw new Error(
      `Workflow governance error: delegation must remain disallowed for current workflows: ${delegationEnabled
        .map((entry) => entry.workflowName)
        .join(", ")}`,
    );
  }
}
