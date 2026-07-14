import { evaluateMutationGuard } from "../../core/mutation-guard.js";
import {
  buildDefaultBudgetState,
  ensureProfile,
  ensureRisk,
  evaluateBudgetPolicy,
  getBudgetStatePath,
  getBudgetStatus,
  loadBudgetPolicy,
  readBudgetState,
  writeBudgetStateAtomic,
} from "../../core/budget.js";
import { TaskContextError, normalizeTaskId } from "../../core/task-context.js";
import { appendTraceRecord } from "../../trace/writer.js";

type BudgetSubcommand = "evaluate" | "profile" | "status";

type BudgetArgs = {
  taskId: string;
  risk: string;
  mode: string;
  estimatedInput: number | null;
  profile: string;
  overrideReason: string;
  overrideApprover: string;
  policyFile: string;
};

function parseBudgetArgs(argv: string[]): BudgetArgs {
  const args: BudgetArgs = {
    taskId: "",
    risk: "medium",
    mode: "unknown",
    estimatedInput: null,
    profile: "",
    overrideReason: "",
    overrideApprover: "",
    policyFile: "",
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const [rawKey, inlineValue] = arg.includes("=") ? arg.split("=", 2) : [arg, ""];
    const key = rawKey.replace("--", "");
    const hasNext = i + 1 < argv.length && !argv[i + 1]?.startsWith("--");
    const value = inlineValue || (hasNext ? argv[++i] || "" : "");
    if (key === "task-id") args.taskId = value;
    if (key === "risk") args.risk = value;
    if (key === "mode") args.mode = value;
    if (key === "estimated-input") {
      const parsed = Number(value);
      args.estimatedInput = Number.isFinite(parsed) ? parsed : null;
    }
    if (key === "profile") args.profile = value;
    if (key === "override-reason") args.overrideReason = value;
    if (key === "override-approver") args.overrideApprover = value;
    if (key === "policy-file") args.policyFile = value;
  }
  return args;
}

function printBudgetUsage(): void {
  console.error(
    [
      "Usage:",
      "  zcl budget evaluate --task-id <id> --risk <low|medium|high> --mode <full|compact|unknown> --estimated-input <n> [--override-reason <text> --override-approver <text>] [--policy-file <path>]",
      "  zcl budget profile --task-id <id> --profile <compact|balanced|full>",
      "  zcl budget status --task-id <id>",
    ].join("\n"),
  );
}

async function ensureBudgetMutationAllowed(taskId: string): Promise<void> {
  const guard = await evaluateMutationGuard({
    command: "zcl budget mutate",
    targetPaths: [getBudgetStatePath(taskId)],
    allowProtectedPrefixes: [".z-mos"],
  });
  if (!guard.allowed) {
    throw new TaskContextError(
      "BUDGET_POLICY_BLOCKED",
      `Budget mutation blocked by policy: ${guard.reason}`,
    );
  }
}

async function writeBudgetTrace(
  subcommand: BudgetSubcommand,
  status: "success" | "failed",
  details: Record<string, unknown>,
): Promise<void> {
  await appendTraceRecord({
    command: `zcl budget ${subcommand}`,
    status,
    actor: "system",
    details: {
      execution_status: status === "success" ? "success" : "failed",
      result_class: status === "success" ? "success" : "failed-runtime",
      trace_expectation: "required-if-business-logic",
      trace_result: "emitted",
      ...details,
    },
  });
}

function normalizeTask(raw: string): string {
  if (!raw) {
    throw new TaskContextError("BUDGET_VALIDATION_FAIL", "--task-id is required.");
  }
  return normalizeTaskId(raw);
}

export async function runBudgetCommand(
  subcommand: BudgetSubcommand,
  argv: string[],
): Promise<void> {
  const args = parseBudgetArgs(argv);
  const taskId = args.taskId || "unknown";
  try {
    if (subcommand === "evaluate") {
      const normalizedTaskId = normalizeTask(args.taskId);
      await ensureBudgetMutationAllowed(normalizedTaskId);
      const risk = ensureRisk(args.risk);
      if (args.mode !== "full" && args.mode !== "compact" && args.mode !== "unknown") {
        throw new TaskContextError("BUDGET_VALIDATION_FAIL", "Unsupported mode.");
      }
      const runtime = await getBudgetStatus(normalizedTaskId);
      const effectiveMode =
        args.mode === "unknown"
          ? (runtime.telemetry.last_mode as "full" | "compact" | "unknown")
          : args.mode;
      const effectiveEstimatedInput =
        args.estimatedInput !== null
          ? args.estimatedInput
          : runtime.telemetry.last_input_tokens;
      if (effectiveEstimatedInput < 0) {
        throw new TaskContextError("BUDGET_VALIDATION_FAIL", "--estimated-input must be >= 0.");
      }
      const policy = await loadBudgetPolicy(args.policyFile || undefined);
      const state = await readBudgetState(normalizedTaskId);
      const evaluation = evaluateBudgetPolicy(
        {
          taskId: normalizedTaskId,
          risk,
          estimatedInputTokens: effectiveEstimatedInput,
          mode: effectiveMode,
          overrideReason: args.overrideReason,
          overrideApprover: args.overrideApprover,
        },
        policy,
      );
      const next = state || buildDefaultBudgetState(normalizedTaskId);
      next.current_profile = evaluation.recommendedProfile;
      next.updated_at = new Date().toISOString();
      next.last_evaluation = {
        decision: evaluation.decision,
        recommended_profile: evaluation.recommendedProfile,
        risk,
        estimated_input_tokens: evaluation.estimatedInputTokens,
        warning_limit: evaluation.warningLimit,
        budget_limit: evaluation.budgetLimit,
        rule_id: evaluation.ruleId,
        explanation: evaluation.explanation,
        override_used: Boolean(args.overrideReason.trim() && args.overrideApprover.trim()),
      };
      const statePath = await writeBudgetStateAtomic(normalizedTaskId, next);
      await writeBudgetTrace("evaluate", "success", {
        task_id: normalizedTaskId,
        risk,
        estimated_input_tokens: evaluation.estimatedInputTokens,
        mode: effectiveMode,
        decision: evaluation.decision,
        profile_before: state.current_profile,
        profile_after: next.current_profile,
        policy_rule_id: evaluation.ruleId,
        override_used: Boolean(args.overrideReason.trim() && args.overrideApprover.trim()),
        budget_limit: evaluation.budgetLimit,
        context_path: statePath,
      });
      console.log(
        JSON.stringify(
          {
            task_id: normalizedTaskId,
            decision: evaluation.decision,
            recommended_profile: evaluation.recommendedProfile,
            rule_id: evaluation.ruleId,
            explanation: evaluation.explanation,
            warning_limit: evaluation.warningLimit,
            budget_limit: evaluation.budgetLimit,
          },
          null,
          2,
        ),
      );
      return;
    }

    if (subcommand === "profile") {
      const normalizedTaskId = normalizeTask(args.taskId);
      await ensureBudgetMutationAllowed(normalizedTaskId);
      const profile = ensureProfile(args.profile);
      const state = await readBudgetState(normalizedTaskId);
      const before = state.current_profile;
      state.current_profile = profile;
      state.updated_at = new Date().toISOString();
      const statePath = await writeBudgetStateAtomic(normalizedTaskId, state);
      await writeBudgetTrace("profile", "success", {
        task_id: normalizedTaskId,
        profile_before: before,
        profile_after: profile,
        policy_rule_id: "BUDGET-RULE-MANUAL-PROFILE",
        decision: "allow",
        reason: "Manual profile update.",
        context_path: statePath,
      });
      console.log(`Budget profile updated: ${statePath}`);
      return;
    }

    if (subcommand === "status") {
      const normalizedTaskId = normalizeTask(args.taskId);
      const status = await getBudgetStatus(normalizedTaskId);
      console.log(JSON.stringify(status, null, 2));
      return;
    }
  } catch (error) {
    const normalized =
      error instanceof TaskContextError
        ? error
        : new TaskContextError(
            "BUDGET_VALIDATION_FAIL",
            error instanceof Error ? error.message : "Unknown budget error",
          );
    try {
      await writeBudgetTrace(subcommand, "failed", {
        task_id: taskId,
        error_code: normalized.code,
        error: normalized.message,
      });
    } catch {
      // keep original error
    }
    throw normalized;
  }

  printBudgetUsage();
  process.exitCode = 1;
}

export function isBudgetSubcommand(value: string): value is BudgetSubcommand {
  return value === "evaluate" || value === "profile" || value === "status";
}
