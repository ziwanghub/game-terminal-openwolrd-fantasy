import { promises as fs } from "node:fs";
import * as path from "node:path";

import {
  TaskContextError,
  normalizeTaskId,
  readTaskContext,
} from "./task-context.js";

export type BudgetRisk = "low" | "medium" | "high";
export type PromptProfile = "compact" | "balanced" | "full";
export type BudgetDecision = "allow" | "warn" | "block";

export type BudgetThreshold = {
  warn: number;
  block: number;
};

export type BudgetPolicy = {
  low: BudgetThreshold;
  medium: BudgetThreshold;
  high: BudgetThreshold;
};

export type BudgetEvaluationInput = {
  taskId: string;
  risk: BudgetRisk;
  estimatedInputTokens: number;
  mode: "full" | "compact" | "unknown";
  overrideReason?: string;
  overrideApprover?: string;
};

export type BudgetEvaluation = {
  decision: BudgetDecision;
  recommendedProfile: PromptProfile;
  ruleId: string;
  explanation: string;
  budgetLimit: number;
  warningLimit: number;
  estimatedInputTokens: number;
};

export type BudgetState = {
  task_id: string;
  current_profile: PromptProfile;
  updated_at: string;
  last_evaluation: {
    decision: BudgetDecision;
    recommended_profile: PromptProfile;
    risk: BudgetRisk;
    estimated_input_tokens: number;
    warning_limit: number;
    budget_limit: number;
    rule_id: string;
    explanation: string;
    override_used: boolean;
  } | null;
};

const ROOT_DIR = process.cwd();

export const DEFAULT_BUDGET_POLICY: BudgetPolicy = {
  low: { warn: 1200, block: 1800 },
  medium: { warn: 2000, block: 2800 },
  high: { warn: 3200, block: 4200 },
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function ensureRisk(value: string): BudgetRisk {
  if (value === "low" || value === "medium" || value === "high") {
    return value;
  }
  throw new TaskContextError("BUDGET_VALIDATION_FAIL", `Unsupported risk: ${value}`);
}

export function ensureProfile(value: string): PromptProfile {
  if (value === "compact" || value === "balanced" || value === "full") {
    return value;
  }
  throw new TaskContextError("BUDGET_VALIDATION_FAIL", `Unsupported profile: ${value}`);
}

export function getBudgetStateDir(rootDir = ROOT_DIR): string {
  return path.join(rootDir, ".z-mos", "state", "budget");
}

export function getBudgetStatePath(taskId: string, rootDir = ROOT_DIR): string {
  return path.join(getBudgetStateDir(rootDir), `${normalizeTaskId(taskId)}.json`);
}

function isBudgetThreshold(value: unknown): value is BudgetThreshold {
  if (!isRecord(value)) return false;
  return (
    typeof value.warn === "number" &&
    Number.isFinite(value.warn) &&
    value.warn >= 0 &&
    typeof value.block === "number" &&
    Number.isFinite(value.block) &&
    value.block >= 0 &&
    value.block >= value.warn
  );
}

export async function loadBudgetPolicy(policyFilePath?: string): Promise<BudgetPolicy> {
  if (!policyFilePath) {
    return DEFAULT_BUDGET_POLICY;
  }
  try {
    const data = await readPolicyFile(policyFilePath);
    if (!isRecord(data)) {
      throw new Error("Policy root must be object.");
    }
    if (!isBudgetThreshold(data.low) || !isBudgetThreshold(data.medium) || !isBudgetThreshold(data.high)) {
      throw new Error("Policy must define low/medium/high with warn/block numbers.");
    }
    return {
      low: data.low,
      medium: data.medium,
      high: data.high,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown budget policy read error";
    throw new TaskContextError("BUDGET_READ_FAIL", message);
  }
}

async function readPolicyFile(policyFilePath: string): Promise<unknown> {
  const resolved = path.resolve(ROOT_DIR, policyFilePath);
  const raw = await fs.readFile(resolved, "utf8");
  return JSON.parse(raw) as unknown;
}

function deriveDefaultProfile(risk: BudgetRisk, mode: "full" | "compact" | "unknown"): PromptProfile {
  if (mode === "compact") return "compact";
  if (risk === "high") return "full";
  return "balanced";
}

export function evaluateBudgetPolicy(
  input: BudgetEvaluationInput,
  policy: BudgetPolicy = DEFAULT_BUDGET_POLICY,
): BudgetEvaluation {
  const threshold = policy[input.risk];
  const overrideUsed = Boolean(input.overrideReason?.trim() && input.overrideApprover?.trim());
  const baseProfile = deriveDefaultProfile(input.risk, input.mode);

  if (input.estimatedInputTokens < threshold.warn) {
    return {
      decision: "allow",
      recommendedProfile: baseProfile,
      ruleId: "BUDGET-RULE-ALLOW-UNDER-WARN",
      explanation: "Estimated input is below warning threshold.",
      budgetLimit: threshold.block,
      warningLimit: threshold.warn,
      estimatedInputTokens: input.estimatedInputTokens,
    };
  }

  if (input.estimatedInputTokens < threshold.block) {
    return {
      decision: "warn",
      recommendedProfile: input.risk === "high" ? "balanced" : "compact",
      ruleId: "BUDGET-RULE-WARN-RANGE",
      explanation: "Estimated input is between warning and block thresholds.",
      budgetLimit: threshold.block,
      warningLimit: threshold.warn,
      estimatedInputTokens: input.estimatedInputTokens,
    };
  }

  if (input.risk === "high" && overrideUsed) {
    return {
      decision: "warn",
      recommendedProfile: "balanced",
      ruleId: "BUDGET-RULE-HIGH-OVERRIDE-DOWNGRADE",
      explanation: "High-risk override accepted; downgraded from block to warn.",
      budgetLimit: threshold.block,
      warningLimit: threshold.warn,
      estimatedInputTokens: input.estimatedInputTokens,
    };
  }

  return {
    decision: "block",
    recommendedProfile: "compact",
    ruleId: "BUDGET-RULE-BLOCK-OVER-LIMIT",
    explanation: "Estimated input exceeds block threshold.",
    budgetLimit: threshold.block,
    warningLimit: threshold.warn,
    estimatedInputTokens: input.estimatedInputTokens,
  };
}

export function buildDefaultBudgetState(taskId: string): BudgetState {
  return {
    task_id: normalizeTaskId(taskId),
    current_profile: "balanced",
    updated_at: new Date().toISOString(),
    last_evaluation: null,
  };
}

export async function readBudgetState(taskId: string): Promise<BudgetState> {
  const filePath = getBudgetStatePath(taskId);
  try {
    const raw = await fs.readFile(filePath, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    return validateBudgetState(parsed);
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT") {
      return buildDefaultBudgetState(taskId);
    }
    if (error instanceof TaskContextError) throw error;
    throw new TaskContextError("BUDGET_READ_FAIL", `Cannot read budget state: ${filePath}`);
  }
}

function validateBudgetState(value: unknown): BudgetState {
  if (!isRecord(value)) {
    throw new TaskContextError("BUDGET_VALIDATION_FAIL", "Budget state must be object.");
  }
  if (typeof value.task_id !== "string") {
    throw new TaskContextError("BUDGET_VALIDATION_FAIL", "task_id must be string.");
  }
  normalizeTaskId(value.task_id);
  if (typeof value.current_profile !== "string") {
    throw new TaskContextError("BUDGET_VALIDATION_FAIL", "current_profile must be string.");
  }
  ensureProfile(value.current_profile);
  if (typeof value.updated_at !== "string") {
    throw new TaskContextError("BUDGET_VALIDATION_FAIL", "updated_at must be string.");
  }
  if (value.last_evaluation !== null && value.last_evaluation !== undefined && !isRecord(value.last_evaluation)) {
    throw new TaskContextError("BUDGET_VALIDATION_FAIL", "last_evaluation must be object|null.");
  }
  return value as BudgetState;
}

export async function writeBudgetStateAtomic(taskId: string, state: BudgetState): Promise<string> {
  const filePath = getBudgetStatePath(taskId);
  const dirPath = path.dirname(filePath);
  try {
    await fs.mkdir(dirPath, { recursive: true });
  } catch {
    throw new TaskContextError("BUDGET_WRITE_FAIL", `Cannot create budget directory: ${dirPath}`);
  }
  const tmpPath = path.join(
    dirPath,
    `.${path.basename(filePath)}.${Date.now()}.${Math.random().toString(16).slice(2)}.tmp`,
  );
  try {
    await fs.writeFile(tmpPath, `${JSON.stringify(state, null, 2)}\n`, "utf8");
    await fs.rename(tmpPath, filePath);
    return filePath;
  } catch {
    try {
      await fs.unlink(tmpPath);
    } catch {
      // ignore cleanup error
    }
    throw new TaskContextError("BUDGET_WRITE_FAIL", `Cannot write budget state: ${filePath}`);
  }
}

export async function getBudgetStatus(taskId: string): Promise<{
  taskId: string;
  budget: BudgetState;
  telemetry: {
    last_mode: string;
    last_input_tokens: number;
    last_output_tokens: number;
    last_turnaround_ms: number;
  };
}> {
  const normalizedTaskId = normalizeTaskId(taskId);
  const [context, budget] = await Promise.all([
    readTaskContext(normalizedTaskId),
    readBudgetState(normalizedTaskId),
  ]);
  return {
    taskId: normalizedTaskId,
    budget,
    telemetry: {
      last_mode: context.telemetry.last_mode,
      last_input_tokens: context.telemetry.last_input_tokens,
      last_output_tokens: context.telemetry.last_output_tokens,
      last_turnaround_ms: context.telemetry.last_turnaround_ms,
    },
  };
}
