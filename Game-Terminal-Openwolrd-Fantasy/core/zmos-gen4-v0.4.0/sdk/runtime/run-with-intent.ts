import { promises as fs } from "node:fs";
import * as path from "node:path";
import { SCHEMA_VERSION_AGENT } from "../version.js";
import type { AgentAction } from "../types/agent-action.js";
import type { IntentCardV300Agent } from "../types/intent-card-v3.0.1.js";
import type {
  GovernanceBlockReason,
  GovernanceDecision,
  RunWithIntentOptions,
  RunWithIntentResult,
  RunWithIntentTraceEvent,
} from "../types/run-with-intent.js";
import type { TruthContract } from "../types/truth-contract.js";

function nowIso(): string {
  return new Date().toISOString();
}

function normalizePath(input: string): string {
  return path.normalize(input).replace(/^\.\//, "");
}

function globToRegExp(glob: string): RegExp {
  const escaped = glob.replace(/[.+^${}()|[\]\\]/g, "\\$&");
  const regexStr = escaped.replace(/\\\*\\\*/g, ".*").replace(/\\\*/g, "[^/]*");
  return new RegExp(`^${regexStr}$`);
}

function pushTrace(
  trace: RunWithIntentTraceEvent[],
  step: string,
  action: string,
  decision: GovernanceDecision,
  details?: Record<string, unknown>,
  reason?: string,
  blockedBy?: GovernanceBlockReason,
): void {
  trace.push({
    step,
    action,
    decision,
    reason,
    blocked_by: blockedBy,
    timestamp: nowIso(),
    details,
  });
}

async function readJsonFile<T>(filePath: string): Promise<T> {
  const raw = await fs.readFile(filePath, "utf8");
  return JSON.parse(raw) as T;
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === "string");
}

function validateIntentCardShape(intent: unknown): intent is IntentCardV300Agent {
  if (typeof intent !== "object" || intent === null) {
    return false;
  }

  const record = intent as Record<string, unknown>;
  if (record.schema_version !== SCHEMA_VERSION_AGENT) {
    return false;
  }

  const intentBlock = record.intent as Record<string, unknown> | undefined;
  const systemBlock = record.system as Record<string, unknown> | undefined;
  const agentBlock = record.agent as Record<string, unknown> | undefined;

  if (!intentBlock || !systemBlock || !agentBlock) {
    return false;
  }

  if (
    !isString(intentBlock.objective) ||
    !isString(intentBlock.strategy) ||
    !isString(intentBlock.risk_acknowledgement)
  ) {
    return false;
  }

  if (
    !isStringArray(systemBlock.scope_files) ||
    !isStringArray(systemBlock.required_tests) ||
    !isStringArray(systemBlock.stop_conditions) ||
    !isString(systemBlock.rollback_plan) ||
    !isString(systemBlock.truth_snapshot_ref)
  ) {
    return false;
  }

  if (
    !isStringArray(agentBlock.allowed_tools) ||
    !isStringArray(agentBlock.allowed_actions) ||
    typeof agentBlock.max_steps !== "number" ||
    !Number.isInteger(agentBlock.max_steps) ||
    agentBlock.max_steps < 1 ||
    !isStringArray(agentBlock.termination_conditions) ||
    agentBlock.enforcement !== "hard-block"
  ) {
    return false;
  }

  return true;
}

function validateTruthContractShape(truth: unknown): truth is TruthContract {
  if (typeof truth !== "object" || truth === null) {
    return false;
  }

  const record = truth as Record<string, unknown>;
  return isString(record.schema_version) && isString(record.generated_at) && isString(record.verdict);
}

function resolveMatchedConditions(
  conditions: string[],
  action: AgentAction,
): string[] {
  const metadata = (action.metadata ?? {}) as Record<string, unknown>;
  const triggered = metadata.triggeredConditions;

  if (!Array.isArray(triggered)) {
    return [];
  }

  const triggeredSet = new Set(
    triggered.filter((item): item is string => typeof item === "string").map((item) => item.trim()),
  );
  if (triggeredSet.size === 0) {
    return [];
  }

  return conditions.filter((condition) => triggeredSet.has(condition.trim()));
}

function areTargetPathsInScope(scopeFiles: string[], targetPaths: string[] | undefined): boolean {
  if (!targetPaths || targetPaths.length === 0) {
    return true;
  }

  const exactScope = new Set(scopeFiles.map((entry) => normalizePath(entry)));
  const scopePatterns = scopeFiles.map((entry) => globToRegExp(normalizePath(entry)));

  return targetPaths.every((target) => {
    const normalizedTarget = normalizePath(target);
    if (exactScope.has(normalizedTarget)) {
      return true;
    }
    return scopePatterns.some((pattern) => pattern.test(normalizedTarget));
  });
}

function blockResult<TResult>(
  params: {
    reason: GovernanceBlockReason;
    error: string;
    trace: RunWithIntentTraceEvent[];
    intentCard?: IntentCardV300Agent;
    truthContract?: TruthContract;
  },
): RunWithIntentResult<TResult> {
  return {
    success: false,
    blocked: true,
    exitCode: 1,
    decision: "BLOCK",
    reason: params.reason,
    trace: params.trace,
    intentSummary: params.intentCard
      ? {
          schema_version: params.intentCard.schema_version,
          max_steps: params.intentCard.agent.max_steps,
          enforcement: params.intentCard.agent.enforcement,
        }
      : undefined,
    truthSummary: params.truthContract
      ? {
          verdict: params.truthContract.verdict,
          generated_at: params.truthContract.generated_at,
        }
      : undefined,
    error: params.error,
  };
}

export async function runWithIntent<TContext = unknown, TResult = unknown>(
  options: RunWithIntentOptions<TContext, TResult>,
): Promise<RunWithIntentResult<TResult>> {
  const trace: RunWithIntentTraceEvent[] = [];
  const stepIndex = options.stepIndex ?? 1;
  const intentPath = options.intentPath ?? path.join(options.workspaceDir, ".z-mos", "intent.card.json");
  const truthPath = options.truthPath ?? path.join(options.workspaceDir, ".z-mos", "truth.contract.json");

  pushTrace(trace, "load", "resolve-paths", "ALLOW", {
    intentPath,
    truthPath,
    workspaceDir: options.workspaceDir,
    stepIndex,
    hasAgentContext: Boolean(options.agentContext),
  });

  let intentCard: IntentCardV300Agent;
  try {
    intentCard = await readJsonFile<IntentCardV300Agent>(intentPath);
    pushTrace(trace, "load", "intent.card.json", "ALLOW", { path: intentPath });
  } catch (error) {
    pushTrace(
      trace,
      "block",
      "intent-load-failed",
      "BLOCK",
      { path: intentPath },
      "Unable to load intent.card.json",
      "INTENT_LOAD_FAILED",
    );
    return blockResult({
      reason: "INTENT_LOAD_FAILED",
      error: error instanceof Error ? error.message : String(error),
      trace,
    });
  }

  if (!validateIntentCardShape(intentCard)) {
    pushTrace(
      trace,
      "block",
      "intent-validation-failed",
      "BLOCK",
      { path: intentPath },
      "Intent card shape/schema is invalid",
      "INTENT_VALIDATION_FAILED",
    );
    return blockResult({
      reason: "INTENT_VALIDATION_FAILED",
      error: `intent.card.json failed schema validation for ${SCHEMA_VERSION_AGENT}`,
      trace,
      intentCard,
    });
  }

  pushTrace(trace, "validate", "intent-card", "ALLOW", {
    schema_version: intentCard.schema_version,
    enforcement: intentCard.agent.enforcement,
    max_steps: intentCard.agent.max_steps,
  });

  let truthContract: TruthContract;
  try {
    truthContract = await readJsonFile<TruthContract>(truthPath);
    pushTrace(trace, "load", "truth.contract.json", "ALLOW", { path: truthPath });
  } catch (error) {
    pushTrace(
      trace,
      "block",
      "truth-load-failed",
      "BLOCK",
      { path: truthPath },
      "Unable to load truth.contract.json",
      "TRUTH_LOAD_FAILED",
    );
    return blockResult({
      reason: "TRUTH_LOAD_FAILED",
      error: error instanceof Error ? error.message : String(error),
      trace,
      intentCard,
    });
  }

  if (!validateTruthContractShape(truthContract)) {
    pushTrace(
      trace,
      "block",
      "truth-validation-failed",
      "BLOCK",
      { path: truthPath },
      "Truth contract shape is invalid",
      "TRUTH_LOAD_FAILED",
    );
    return blockResult({
      reason: "TRUTH_LOAD_FAILED",
      error: "truth.contract.json failed minimum validation",
      trace,
      intentCard,
      truthContract,
    });
  }

  pushTrace(trace, "validate", "truth-contract", "ALLOW", {
    verdict: truthContract.verdict,
    generated_at: truthContract.generated_at,
  });

  if (truthContract.verdict !== "SAFE_TO_CONTINUE") {
    pushTrace(
      trace,
      "block",
      "truth-verdict-blocked",
      "BLOCK",
      { verdict: truthContract.verdict },
      "Truth verdict is not SAFE_TO_CONTINUE",
      "TRUTH_VERDICT_BLOCKED",
    );
    return blockResult({
      reason: "TRUTH_VERDICT_BLOCKED",
      error: `Execution blocked by truth verdict: ${truthContract.verdict}`,
      trace,
      intentCard,
      truthContract,
    });
  }

  const declaredTruthRef = normalizePath(intentCard.system.truth_snapshot_ref);
  const effectiveTruthPath = normalizePath(path.relative(options.workspaceDir, truthPath));
  if (declaredTruthRef !== effectiveTruthPath) {
    pushTrace(
      trace,
      "block",
      "truth-snapshot-mismatch",
      "BLOCK",
      {
        truth_snapshot_ref: intentCard.system.truth_snapshot_ref,
        effective_truth_path: effectiveTruthPath,
      },
      "truth_snapshot_ref does not match runtime truth path",
      "INTENT_VALIDATION_FAILED",
    );
    return blockResult({
      reason: "INTENT_VALIDATION_FAILED",
      error: "Intent truth_snapshot_ref mismatch",
      trace,
      intentCard,
      truthContract,
    });
  }

  if (intentCard.agent.enforcement !== "hard-block") {
    pushTrace(
      trace,
      "block",
      "enforcement-not-hard-block",
      "BLOCK",
      { enforcement: intentCard.agent.enforcement },
      "Only hard-block enforcement is allowed",
      "INTENT_VALIDATION_FAILED",
    );
    return blockResult({
      reason: "INTENT_VALIDATION_FAILED",
      error: "Intent agent.enforcement must be hard-block",
      trace,
      intentCard,
      truthContract,
    });
  }

  if (stepIndex > intentCard.agent.max_steps) {
    pushTrace(
      trace,
      "block",
      "step-limit-exceeded",
      "BLOCK",
      { stepIndex, max_steps: intentCard.agent.max_steps },
      "Step limit exceeded",
      "STEP_LIMIT_EXCEEDED",
    );
    return blockResult({
      reason: "STEP_LIMIT_EXCEEDED",
      error: `Step ${stepIndex} exceeds max_steps ${intentCard.agent.max_steps}`,
      trace,
      intentCard,
      truthContract,
    });
  }

  if (!intentCard.agent.allowed_tools.includes(options.action.tool)) {
    pushTrace(
      trace,
      "block",
      "tool-not-allowed",
      "BLOCK",
      { tool: options.action.tool },
      "Tool is not allowed by intent",
      "TOOL_NOT_ALLOWED",
    );
    return blockResult({
      reason: "TOOL_NOT_ALLOWED",
      error: `Tool not allowed: ${options.action.tool}`,
      trace,
      intentCard,
      truthContract,
    });
  }

  if (!intentCard.agent.allowed_actions.includes(options.action.action)) {
    pushTrace(
      trace,
      "block",
      "action-not-allowed",
      "BLOCK",
      { action: options.action.action },
      "Action is not allowed by intent",
      "ACTION_NOT_ALLOWED",
    );
    return blockResult({
      reason: "ACTION_NOT_ALLOWED",
      error: `Action not allowed: ${options.action.action}`,
      trace,
      intentCard,
      truthContract,
    });
  }

  if (!areTargetPathsInScope(intentCard.system.scope_files, options.action.targetPaths)) {
    pushTrace(
      trace,
      "block",
      "scope-violation",
      "BLOCK",
      {
        targetPaths: options.action.targetPaths ?? [],
        scope_files: intentCard.system.scope_files,
      },
      "Target paths are outside allowed scope",
      "SCOPE_VIOLATION",
    );
    return blockResult({
      reason: "SCOPE_VIOLATION",
      error: "Action target paths are outside scope_files",
      trace,
      intentCard,
      truthContract,
    });
  }

  const matchedStopConditions = resolveMatchedConditions(intentCard.system.stop_conditions, options.action);
  if (matchedStopConditions.length > 0) {
    pushTrace(
      trace,
      "block",
      "stop-condition-triggered",
      "BLOCK",
      { matched: matchedStopConditions },
      "A stop condition was triggered",
      "STOP_CONDITION_TRIGGERED",
    );
    return blockResult({
      reason: "STOP_CONDITION_TRIGGERED",
      error: `Triggered stop_conditions: ${matchedStopConditions.join(", ")}`,
      trace,
      intentCard,
      truthContract,
    });
  }

  const matchedTerminationConditions = resolveMatchedConditions(
    intentCard.agent.termination_conditions,
    options.action,
  );
  if (matchedTerminationConditions.length > 0) {
    pushTrace(
      trace,
      "block",
      "termination-condition-triggered",
      "BLOCK",
      { matched: matchedTerminationConditions },
      "A termination condition was triggered",
      "TERMINATION_CONDITION_TRIGGERED",
    );
    return blockResult({
      reason: "TERMINATION_CONDITION_TRIGGERED",
      error: `Triggered termination_conditions: ${matchedTerminationConditions.join(", ")}`,
      trace,
      intentCard,
      truthContract,
    });
  }

  pushTrace(trace, "decision", "allow-execution", "ALLOW", {
    action: options.action.action,
    tool: options.action.tool,
    stepIndex,
    agentContext: options.agentContext,
  });

  const executionContext = {
    workspaceDir: options.workspaceDir,
    context: options.context,
    action: options.action,
    intentCard,
    truthContract,
    agentContext: options.agentContext,
  };

  try {
    const maybePromise = options.handler(executionContext);

    const data = options.maxRuntimeMs && options.maxRuntimeMs > 0
      ? await Promise.race<TResult>([
          Promise.resolve(maybePromise),
          new Promise<TResult>((_, reject) => {
            setTimeout(() => reject(new Error("runWithIntent handler timed out")), options.maxRuntimeMs);
          }),
        ])
      : await Promise.resolve(maybePromise);

    pushTrace(trace, "execute", "handler-executed", "ALLOW", {
      hasResult: data !== undefined,
    });

    return {
      success: true,
      blocked: false,
      exitCode: 0,
      decision: "ALLOW",
      data,
      trace,
      intentSummary: {
        schema_version: intentCard.schema_version,
        max_steps: intentCard.agent.max_steps,
        enforcement: intentCard.agent.enforcement,
      },
      truthSummary: {
        verdict: truthContract.verdict,
        generated_at: truthContract.generated_at,
      },
    };
  } catch (error) {
    pushTrace(
      trace,
      "block",
      "handler-error",
      "BLOCK",
      undefined,
      "Handler execution failed",
      "UNKNOWN_ERROR",
    );
    return blockResult({
      reason: "UNKNOWN_ERROR",
      error: error instanceof Error ? error.message : String(error),
      trace,
      intentCard,
      truthContract,
    });
  }
}
