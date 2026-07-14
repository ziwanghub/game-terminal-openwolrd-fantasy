import { promises as fs } from "node:fs";

import { evaluateMutationGuard } from "../../core/mutation-guard.js";
import {
  CONTEXT_INVALID_REASONS,
  CONTEXT_MODES,
  TaskContextError,
  applyPatch,
  computeFreshnessWarning,
  createDefaultTaskContext,
  getTaskContextPath,
  normalizeTaskId,
  readTaskContext,
  validatePatch,
  writeTaskContextAtomic,
} from "../../core/task-context.js";
import { appendTraceRecord } from "../../trace/writer.js";

type ContextSubcommand = "init" | "show" | "update" | "invalidate";

type ContextArgs = {
  taskId: string;
  force: boolean;
  reason: string;
  patchRaw: string;
  mode: string;
  inputTokens: number | null;
  outputTokens: number | null;
  turnaroundMs: number | null;
  actor: string;
  overrideReason: string;
  overrideApprover: string;
};

function parseNumber(value: string): number | null {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}

function parseContextArgs(argv: string[]): ContextArgs {
  const args: ContextArgs = {
    taskId: "",
    force: false,
    reason: "",
    patchRaw: "",
    mode: "",
    inputTokens: null,
    outputTokens: null,
    turnaroundMs: null,
    actor: process.env.ZMOS_CONTEXT_ACTOR || process.env.USER || "unknown",
    overrideReason: "",
    overrideApprover: "",
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--force") {
      args.force = true;
      continue;
    }
    if (!arg.startsWith("--")) {
      continue;
    }

    const [rawKey, inlineValue] = arg.includes("=") ? arg.split("=", 2) : [arg, ""];
    const key = rawKey.replace("--", "");
    const hasNext = i + 1 < argv.length && !argv[i + 1]?.startsWith("--");
    const value = inlineValue || (hasNext ? argv[++i] || "" : "");

    if (key === "task-id") args.taskId = value;
    if (key === "reason") args.reason = value;
    if (key === "patch") args.patchRaw = value;
    if (key === "mode") args.mode = value;
    if (key === "input-tokens") args.inputTokens = parseNumber(value);
    if (key === "output-tokens") args.outputTokens = parseNumber(value);
    if (key === "turnaround-ms") args.turnaroundMs = parseNumber(value);
    if (key === "actor") args.actor = value;
    if (key === "override-reason") args.overrideReason = value;
    if (key === "override-approver") args.overrideApprover = value;
  }

  return args;
}

function printUsage(): void {
  console.error(
    [
      "Usage:",
      "  zcl context init --task-id <id> [--force]",
      "  zcl context show --task-id <id>",
      "  zcl context update --task-id <id> --patch <json> [--actor <id>] [--mode full|compact|unknown] [--input-tokens <n>] [--output-tokens <n>] [--turnaround-ms <n>] [--override-reason <text> --override-approver <text>]",
      "  zcl context invalidate --task-id <id> --reason <taxonomy>",
      "",
      "Invalidation taxonomy:",
      `  ${CONTEXT_INVALID_REASONS.filter((entry) => entry !== "none").join(", ")}`,
    ].join("\n"),
  );
}

function ensureContextMode(value: string): "full" | "compact" | "unknown" {
  if (!value) {
    return "unknown";
  }
  if (CONTEXT_MODES.includes(value as "full" | "compact" | "unknown")) {
    return value as "full" | "compact" | "unknown";
  }
  throw new TaskContextError(
    "CONTEXT_VALIDATION_FAIL",
    `Unsupported mode: ${value}. Expected full|compact|unknown.`,
  );
}

async function ensureMutationAllowed(taskId: string): Promise<void> {
  const guard = await evaluateMutationGuard({
    command: "zcl context mutate",
    targetPaths: [getTaskContextPath(taskId)],
    allowProtectedPrefixes: [".z-mos"],
  });
  if (!guard.allowed) {
    throw new TaskContextError(
      "CONTEXT_PATCH_FORBIDDEN",
      `Mutation blocked by policy: ${guard.reason}`,
    );
  }
}

async function appendContextTrace(
  subcommand: ContextSubcommand,
  status: "success" | "failed",
  details: Record<string, unknown>,
): Promise<void> {
  await appendTraceRecord({
    command: `zcl context ${subcommand}`,
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

function requireTaskId(args: ContextArgs): string {
  if (!args.taskId) {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", "--task-id is required.");
  }
  return normalizeTaskId(args.taskId);
}

async function runInit(args: ContextArgs): Promise<void> {
  const taskId = requireTaskId(args);
  await ensureMutationAllowed(taskId);
  const contextPath = getTaskContextPath(taskId);
  const context = createDefaultTaskContext(taskId);

  if (!args.force) {
    try {
      await fs.access(contextPath);
      throw new TaskContextError(
        "CONTEXT_ALREADY_EXISTS",
        `Context already exists for task_id=${taskId}. Use --force to overwrite.`,
      );
    } catch (error) {
      const code = (error as NodeJS.ErrnoException).code;
      if (!(error instanceof TaskContextError) && code !== "ENOENT") {
        throw new TaskContextError("CONTEXT_READ_FAIL", `Cannot access context path: ${contextPath}`);
      }
      if (error instanceof TaskContextError) {
        throw error;
      }
    }
  }

  const filePath = await writeTaskContextAtomic(taskId, context);
  await appendContextTrace("init", "success", {
    task_id: taskId,
    forced: args.force,
    context_path: filePath,
  });
  console.log(`Context initialized: ${filePath}`);
}

async function runShow(args: ContextArgs): Promise<void> {
  const taskId = requireTaskId(args);
  const context = await readTaskContext(taskId);
  const freshnessWarning = computeFreshnessWarning(context);
  await appendContextTrace("show", "success", {
    task_id: taskId,
    stale: Boolean(freshnessWarning),
  });
  const payload = freshnessWarning
    ? { ...context, freshness_warning: freshnessWarning }
    : context;
  console.log(JSON.stringify(payload, null, 2));
}

function parsePatch(args: ContextArgs): Record<string, unknown> {
  if (!args.patchRaw) {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", "--patch is required.");
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(args.patchRaw);
  } catch {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", "Patch must be valid JSON.");
  }
  return validatePatch(parsed);
}

function validateOwnershipPatch(
  beforeClaimedBy: string,
  patch: Record<string, unknown>,
  actor: string,
  overrideReason: string,
  overrideApprover: string,
): void {
  const ownershipPatch = patch.ownership;
  if (!ownershipPatch || typeof ownershipPatch !== "object" || Array.isArray(ownershipPatch)) {
    return;
  }
  if (!beforeClaimedBy) {
    return;
  }
  if (beforeClaimedBy === actor) {
    return;
  }
  if (overrideReason.trim() && overrideApprover.trim()) {
    return;
  }
  throw new TaskContextError(
    "CONTEXT_PATCH_FORBIDDEN",
    "Ownership update requires unclaimed context, same actor, or --override-reason with --override-approver.",
  );
}

async function runUpdate(args: ContextArgs): Promise<void> {
  const taskId = requireTaskId(args);
  await ensureMutationAllowed(taskId);
  const patch = parsePatch(args);
  const context = await readTaskContext(taskId);
  validateOwnershipPatch(
    context.ownership.claimed_by,
    patch,
    args.actor,
    args.overrideReason,
    args.overrideApprover,
  );
  const next = applyPatch(context, patch);
  next.telemetry.update_count += 1;
  if (args.mode) {
    next.telemetry.last_mode = ensureContextMode(args.mode);
  }
  if (args.inputTokens !== null) {
    next.telemetry.last_input_tokens = args.inputTokens;
  }
  if (args.outputTokens !== null) {
    next.telemetry.last_output_tokens = args.outputTokens;
  }
  if (args.turnaroundMs !== null) {
    next.telemetry.last_turnaround_ms = args.turnaroundMs;
  }

  const filePath = await writeTaskContextAtomic(taskId, next);
  await appendContextTrace("update", "success", {
    task_id: taskId,
    actor: args.actor,
    override_used: Boolean(args.overrideReason || args.overrideApprover),
    context_path: filePath,
  });
  console.log(`Context updated: ${filePath}`);
}

async function runInvalidate(args: ContextArgs): Promise<void> {
  const taskId = requireTaskId(args);
  await ensureMutationAllowed(taskId);
  if (!args.reason) {
    throw new TaskContextError("CONTEXT_INVALID_REASON", "--reason is required.");
  }
  const reason = args.reason.trim();
  if (!CONTEXT_INVALID_REASONS.includes(reason as (typeof CONTEXT_INVALID_REASONS)[number])) {
    throw new TaskContextError(
      "CONTEXT_INVALID_REASON",
      `Unsupported invalidation reason: ${reason}`,
    );
  }

  const context = await readTaskContext(taskId);
  context.freshness.invalidated = true;
  context.freshness.reason = reason as (typeof CONTEXT_INVALID_REASONS)[number];
  context.freshness.invalidated_at = new Date().toISOString();
  context.telemetry.invalidation_count += 1;

  const filePath = await writeTaskContextAtomic(taskId, context);
  await appendContextTrace("invalidate", "success", {
    task_id: taskId,
    reason,
    context_path: filePath,
  });
  console.log(`Context invalidated: ${filePath}`);
}

export async function runContextCommand(
  subcommand: ContextSubcommand,
  argv: string[],
): Promise<void> {
  const args = parseContextArgs(argv);
  try {
    if (subcommand === "init") {
      await runInit(args);
      return;
    }
    if (subcommand === "show") {
      await runShow(args);
      return;
    }
    if (subcommand === "update") {
      await runUpdate(args);
      return;
    }
    if (subcommand === "invalidate") {
      await runInvalidate(args);
      return;
    }
    printUsage();
    process.exitCode = 1;
  } catch (error) {
    const taskId = args.taskId || "unknown";
    const message = error instanceof Error ? error.message : "Unknown context command error.";
    try {
      await appendContextTrace(subcommand, "failed", {
        task_id: taskId,
        error: message,
      });
    } catch {
      // do not overwrite original command error
    }
    throw error;
  }
}

export function isContextSubcommand(value: string): value is ContextSubcommand {
  return value === "init" || value === "show" || value === "update" || value === "invalidate";
}

export { printUsage as printContextUsage };
