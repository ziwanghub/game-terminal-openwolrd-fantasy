import { evaluateMutationGuard } from "../../core/mutation-guard.js";
import {
  applyArtifactLock,
  applyHandoff,
  applyHandoffAck,
  applyLaneClaim,
  applyLaneRelease,
  applyPathLock,
  ensureLane,
  ensureOwnershipMutable,
  mapLaneError,
} from "../../core/lane.js";
import {
  TaskContextError,
  getTaskContextPath,
  normalizeTaskId,
  readTaskContext,
  writeTaskContextAtomic,
} from "../../core/task-context.js";
import { appendTraceRecord } from "../../trace/writer.js";

type LaneSubcommand =
  | "claim"
  | "release"
  | "lock-path"
  | "lock-artifact"
  | "handoff"
  | "ack";

type LaneArgs = {
  taskId: string;
  lane: string;
  actor: string;
  path: string;
  artifact: string;
  toLane: string;
  summary: string;
  timeoutMinutes: number;
  overrideReason: string;
  overrideApprover: string;
};

function parseLaneArgs(argv: string[]): LaneArgs {
  const args: LaneArgs = {
    taskId: "",
    lane: "",
    actor: process.env.USER || "unknown",
    path: "",
    artifact: "",
    toLane: "",
    summary: "",
    timeoutMinutes: 30,
    overrideReason: "",
    overrideApprover: "",
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const [rawKey, inlineValue] = arg.includes("=") ? arg.split("=", 2) : [arg, ""];
    const key = rawKey.replace("--", "");
    const hasNext = i + 1 < argv.length && !argv[i + 1]?.startsWith("--");
    const value = inlineValue || (hasNext ? argv[++i] || "" : "");
    if (key === "task-id") args.taskId = value;
    if (key === "lane") args.lane = value;
    if (key === "actor") args.actor = value;
    if (key === "path") args.path = value;
    if (key === "artifact") args.artifact = value;
    if (key === "to-lane") args.toLane = value;
    if (key === "summary") args.summary = value;
    if (key === "timeout-minutes") {
      const parsed = Number(value);
      if (Number.isFinite(parsed) && parsed > 0) {
        args.timeoutMinutes = parsed;
      }
    }
    if (key === "override-reason") args.overrideReason = value;
    if (key === "override-approver") args.overrideApprover = value;
  }
  return args;
}

function printLaneUsage(): void {
  console.error(
    [
      "Usage:",
      "  zcl lane claim --task-id <id> --lane <lane> --actor <id> [--timeout-minutes <n>]",
      "  zcl lane release --task-id <id> --actor <id>",
      "  zcl lane lock-path --task-id <id> --lane <lane> --actor <id> --path <glob> [--override-reason <text> --override-approver <text>]",
      "  zcl lane lock-artifact --task-id <id> --lane <lane> --actor <id> --artifact <id> [--override-reason <text> --override-approver <text>]",
      "  zcl lane handoff --task-id <id> --to-lane <lane> --actor <id> --summary <text>",
      "  zcl lane ack --task-id <id> --actor <id>",
      "",
      "Lanes: unassigned|docs|backend|frontend|ops",
    ].join("\n"),
  );
}

async function ensureLaneMutationAllowed(taskId: string): Promise<void> {
  const guard = await evaluateMutationGuard({
    command: "zcl lane mutate",
    targetPaths: [getTaskContextPath(taskId)],
    allowProtectedPrefixes: [".z-mos"],
  });
  if (!guard.allowed) {
    throw new TaskContextError("LANE_OVERRIDE_REQUIRED", `Mutation blocked by policy: ${guard.reason}`);
  }
}

async function writeLaneTrace(
  subcommand: LaneSubcommand,
  status: "success" | "failed",
  details: Record<string, unknown>,
): Promise<void> {
  await appendTraceRecord({
    command: `zcl lane ${subcommand}`,
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

function requireTaskId(raw: string): string {
  if (!raw) {
    throw new TaskContextError("LANE_VALIDATION_FAIL", "--task-id is required.");
  }
  return normalizeTaskId(raw);
}

export async function runLaneCommand(subcommand: LaneSubcommand, argv: string[]): Promise<void> {
  const args = parseLaneArgs(argv);
  const taskId = args.taskId || "unknown";
  try {
    if (subcommand === "claim") {
      const normalizedTaskId = requireTaskId(args.taskId);
      await ensureLaneMutationAllowed(normalizedTaskId);
      const lane = ensureLane(args.lane || "unassigned");
      if (!args.actor.trim()) {
        throw new TaskContextError("LANE_VALIDATION_FAIL", "--actor is required.");
      }
      const context = await readTaskContext(normalizedTaskId);
      const claimResult = applyLaneClaim(context, lane, args.actor.trim(), args.timeoutMinutes);
      const filePath = await writeTaskContextAtomic(normalizedTaskId, context);
      await writeLaneTrace("claim", "success", {
        task_id: normalizedTaskId,
        lane,
        actor: args.actor,
        stale_reclaimed: claimResult.staleReclaimed,
        warning_code: claimResult.staleReclaimed ? "LANE_STALE_CLAIM_RECLAIMED" : undefined,
        context_path: filePath,
      });
      console.log(
        `Lane claimed: ${filePath}${claimResult.staleReclaimed ? " (stale claim reclaimed)" : ""}`,
      );
      return;
    }

    if (subcommand === "release") {
      const normalizedTaskId = requireTaskId(args.taskId);
      await ensureLaneMutationAllowed(normalizedTaskId);
      if (!args.actor.trim()) {
        throw new TaskContextError("LANE_VALIDATION_FAIL", "--actor is required.");
      }
      const context = await readTaskContext(normalizedTaskId);
      applyLaneRelease(context, args.actor.trim());
      const filePath = await writeTaskContextAtomic(normalizedTaskId, context);
      await writeLaneTrace("release", "success", {
        task_id: normalizedTaskId,
        actor: args.actor,
        context_path: filePath,
      });
      console.log(`Lane released: ${filePath}`);
      return;
    }

    if (subcommand === "lock-path") {
      const normalizedTaskId = requireTaskId(args.taskId);
      await ensureLaneMutationAllowed(normalizedTaskId);
      const lane = ensureLane(args.lane || "unassigned");
      if (!args.actor.trim() || !args.path.trim()) {
        throw new TaskContextError("LANE_VALIDATION_FAIL", "--actor and --path are required.");
      }
      const context = await readTaskContext(normalizedTaskId);
      ensureOwnershipMutable(context, args.actor, args.overrideReason, args.overrideApprover);
      applyPathLock(context, args.actor.trim(), lane, args.path.trim());
      const filePath = await writeTaskContextAtomic(normalizedTaskId, context);
      await writeLaneTrace("lock-path", "success", {
        task_id: normalizedTaskId,
        lane,
        actor: args.actor,
        path: args.path,
        override_used: Boolean(args.overrideReason || args.overrideApprover),
        context_path: filePath,
      });
      console.log(`Path lock added: ${filePath}`);
      return;
    }

    if (subcommand === "lock-artifact") {
      const normalizedTaskId = requireTaskId(args.taskId);
      await ensureLaneMutationAllowed(normalizedTaskId);
      const lane = ensureLane(args.lane || "unassigned");
      if (!args.actor.trim() || !args.artifact.trim()) {
        throw new TaskContextError(
          "LANE_VALIDATION_FAIL",
          "--actor and --artifact are required.",
        );
      }
      const context = await readTaskContext(normalizedTaskId);
      ensureOwnershipMutable(context, args.actor, args.overrideReason, args.overrideApprover);
      applyArtifactLock(context, args.actor.trim(), lane, args.artifact.trim());
      const filePath = await writeTaskContextAtomic(normalizedTaskId, context);
      await writeLaneTrace("lock-artifact", "success", {
        task_id: normalizedTaskId,
        lane,
        actor: args.actor,
        artifact: args.artifact,
        override_used: Boolean(args.overrideReason || args.overrideApprover),
        context_path: filePath,
      });
      console.log(`Artifact lock added: ${filePath}`);
      return;
    }

    if (subcommand === "handoff") {
      const normalizedTaskId = requireTaskId(args.taskId);
      await ensureLaneMutationAllowed(normalizedTaskId);
      if (!args.actor.trim() || !args.toLane.trim() || !args.summary.trim()) {
        throw new TaskContextError(
          "LANE_VALIDATION_FAIL",
          "--actor, --to-lane, and --summary are required.",
        );
      }
      const toLane = ensureLane(args.toLane);
      const context = await readTaskContext(normalizedTaskId);
      applyHandoff(context, args.actor.trim(), toLane);
      const filePath = await writeTaskContextAtomic(normalizedTaskId, context);
      await writeLaneTrace("handoff", "success", {
        task_id: normalizedTaskId,
        actor: args.actor,
        to_lane: toLane,
        summary: args.summary,
        context_path: filePath,
      });
      console.log(`Handoff created: ${filePath}`);
      return;
    }

    if (subcommand === "ack") {
      const normalizedTaskId = requireTaskId(args.taskId);
      await ensureLaneMutationAllowed(normalizedTaskId);
      if (!args.actor.trim()) {
        throw new TaskContextError("LANE_VALIDATION_FAIL", "--actor is required.");
      }
      const context = await readTaskContext(normalizedTaskId);
      applyHandoffAck(context, args.actor.trim());
      const filePath = await writeTaskContextAtomic(normalizedTaskId, context);
      await writeLaneTrace("ack", "success", {
        task_id: normalizedTaskId,
        actor: args.actor,
        context_path: filePath,
      });
      console.log(`Handoff acknowledged: ${filePath}`);
      return;
    }
  } catch (error) {
    const normalized = mapLaneError(error);
    try {
      await writeLaneTrace(subcommand, "failed", {
        task_id: taskId,
        error_code: normalized.code,
        error: normalized.message,
      });
    } catch {
      // keep original error
    }
    throw normalized;
  }

  printLaneUsage();
  process.exitCode = 1;
}

export function isLaneSubcommand(value: string): value is LaneSubcommand {
  return (
    value === "claim" ||
    value === "release" ||
    value === "lock-path" ||
    value === "lock-artifact" ||
    value === "handoff" ||
    value === "ack"
  );
}
