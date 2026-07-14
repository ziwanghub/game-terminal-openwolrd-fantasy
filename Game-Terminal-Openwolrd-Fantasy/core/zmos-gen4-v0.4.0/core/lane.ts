import {
  CONTEXT_LANES,
  TaskContextError,
  type TaskArtifactLock,
  type TaskContext,
  type TaskPathLock,
} from "./task-context.js";

export class LaneError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(`[${code}] ${message}`);
    this.code = code;
  }
}

export type LaneName = (typeof CONTEXT_LANES)[number];

export function ensureLane(value: string): LaneName {
  if (CONTEXT_LANES.includes(value as LaneName)) {
    return value as LaneName;
  }
  throw new LaneError("LANE_VALIDATION_FAIL", `Unsupported lane: ${value}`);
}

function nowIso(): string {
  return new Date().toISOString();
}

function isExpired(iso: string): boolean {
  if (!iso) return true;
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) return true;
  return ms <= Date.now();
}

export function isActiveClaim(context: TaskContext): boolean {
  if (!context.ownership.claimed_by) {
    return false;
  }
  const expires = context.ownership.claim_expires_at || "";
  return !isExpired(expires);
}

export function ensureOwnershipMutable(
  context: TaskContext,
  actor: string,
  overrideReason: string,
  overrideApprover: string,
): void {
  if (!isActiveClaim(context)) {
    return;
  }
  if (context.ownership.claimed_by === actor) {
    return;
  }
  if (overrideReason.trim() && overrideApprover.trim()) {
    return;
  }
  throw new LaneError(
    "LANE_OVERRIDE_REQUIRED",
    "Active ownership belongs to another actor and override metadata is missing.",
  );
}

export function ensureNoPendingHandoff(context: TaskContext): void {
  if (context.ownership.handoff_pending) {
    throw new LaneError(
      "LANE_HANDOFF_PENDING",
      "Handoff is pending acknowledgement; mutation lock operation is blocked.",
    );
  }
}

export function applyLaneClaim(
  context: TaskContext,
  lane: LaneName,
  actor: string,
  timeoutMinutes = 30,
): { staleReclaimed: boolean } {
  const active = isActiveClaim(context);
  const claimedBy = context.ownership.claimed_by || "";
  const staleReclaimed = Boolean(claimedBy) && !active;

  if (active && claimedBy && claimedBy !== actor) {
    throw new LaneError(
      "LANE_CLAIM_CONFLICT",
      `Task is already claimed by actor=${claimedBy} lane=${context.ownership.lane}.`,
    );
  }

  const claimedAt = nowIso();
  const expiresAt = new Date(Date.now() + timeoutMinutes * 60_000).toISOString();
  context.ownership.lane = lane;
  context.ownership.claimed_by = actor;
  context.ownership.claimed_at = claimedAt;
  context.ownership.claim_expires_at = expiresAt;
  context.ownership.handoff_pending = false;
  context.ownership.handoff_to_lane = "unassigned";
  context.ownership.handoff_ack_at = "";
  if (!context.locks) {
    context.locks = { paths: [], artifacts: [] };
  }
  return { staleReclaimed };
}

export function applyLaneRelease(context: TaskContext, actor: string): void {
  if (context.ownership.claimed_by && context.ownership.claimed_by !== actor) {
    throw new LaneError(
      "LANE_OVERRIDE_REQUIRED",
      `Release denied. Current owner is ${context.ownership.claimed_by}.`,
    );
  }
  context.ownership.lane = "unassigned";
  context.ownership.claimed_by = "";
  context.ownership.claimed_at = "";
  context.ownership.claim_expires_at = "";
  context.ownership.handoff_pending = false;
  context.ownership.handoff_to_lane = "unassigned";
  context.ownership.handoff_ack_at = "";
}

function pathOverlap(a: string, b: string): boolean {
  return a === b || a.startsWith(`${b}/`) || b.startsWith(`${a}/`);
}

function ensureLocksContainer(context: TaskContext): void {
  if (!context.locks) {
    context.locks = { paths: [], artifacts: [] };
  }
}

export function applyPathLock(
  context: TaskContext,
  actor: string,
  lane: LaneName,
  lockPath: string,
): void {
  ensureLocksContainer(context);
  ensureNoPendingHandoff(context);

  // artifact lock precedence over path lock
  const blockingArtifact = context.locks!.artifacts.find((entry) => entry.actor !== actor);
  if (blockingArtifact) {
    throw new LaneError(
      "LANE_LOCK_CONFLICT",
      `Artifact lock held by ${blockingArtifact.actor}; path lock denied by precedence.`,
    );
  }

  const conflict = context.locks!.paths.find(
    (entry) => entry.actor !== actor && pathOverlap(entry.path, lockPath),
  );
  if (conflict) {
    throw new LaneError(
      "LANE_LOCK_CONFLICT",
      `Path lock conflict with ${conflict.path} owned by ${conflict.actor}.`,
    );
  }

  const existing = context.locks!.paths.find(
    (entry) => entry.actor === actor && entry.path === lockPath,
  );
  if (existing) {
    return;
  }
  const lock: TaskPathLock = {
    path: lockPath,
    lane,
    actor,
    created_at: nowIso(),
  };
  context.locks!.paths.push(lock);
}

export function applyArtifactLock(
  context: TaskContext,
  actor: string,
  lane: LaneName,
  artifact: string,
): void {
  ensureLocksContainer(context);
  ensureNoPendingHandoff(context);

  const conflict = context.locks!.artifacts.find(
    (entry) => entry.actor !== actor && entry.artifact === artifact,
  );
  if (conflict) {
    throw new LaneError(
      "LANE_LOCK_CONFLICT",
      `Artifact lock conflict with ${artifact} owned by ${conflict.actor}.`,
    );
  }
  const existing = context.locks!.artifacts.find(
    (entry) => entry.actor === actor && entry.artifact === artifact,
  );
  if (existing) {
    return;
  }
  const lock: TaskArtifactLock = {
    artifact,
    lane,
    actor,
    created_at: nowIso(),
  };
  context.locks!.artifacts.push(lock);
}

export function applyHandoff(
  context: TaskContext,
  actor: string,
  toLane: LaneName,
): void {
  if (!isActiveClaim(context) || context.ownership.claimed_by !== actor) {
    throw new LaneError(
      "LANE_OVERRIDE_REQUIRED",
      "Handoff allowed only for active owner.",
    );
  }
  context.ownership.handoff_pending = true;
  context.ownership.handoff_to_lane = toLane;
  context.ownership.handoff_ack_at = "";
}

export function applyHandoffAck(context: TaskContext, actor: string): void {
  if (!context.ownership.handoff_pending) {
    throw new LaneError("LANE_HANDOFF_PENDING", "No pending handoff to acknowledge.");
  }
  const toLane = context.ownership.handoff_to_lane || "unassigned";
  const lane = ensureLane(toLane);
  context.ownership.lane = lane;
  context.ownership.claimed_by = actor;
  context.ownership.claimed_at = nowIso();
  context.ownership.claim_expires_at = new Date(Date.now() + 30 * 60_000).toISOString();
  context.ownership.handoff_pending = false;
  context.ownership.handoff_ack_at = nowIso();
}

export function mapLaneError(error: unknown): TaskContextError {
  if (error instanceof LaneError) {
    return new TaskContextError(error.code, error.message);
  }
  if (error instanceof TaskContextError) {
    return error;
  }
  const message = error instanceof Error ? error.message : "Unknown lane error";
  return new TaskContextError("LANE_VALIDATION_FAIL", message);
}
