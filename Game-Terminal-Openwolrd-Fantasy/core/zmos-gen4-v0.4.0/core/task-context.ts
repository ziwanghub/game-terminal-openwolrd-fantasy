import { promises as fs } from "node:fs";
import * as path from "node:path";

export const CONTEXT_INVALID_REASONS = [
  "none",
  "status_completed",
  "status_failed",
  "scope_changed",
  "artifact_version_changed",
  "dependency_changed",
  "quality_gate_failed",
  "manual_purge",
  "lane_change",
] as const;

export const CONTEXT_LANES = ["unassigned", "docs", "backend", "frontend", "ops"] as const;
export const CONTEXT_STATUSES = [
  "planned",
  "in_progress",
  "blocked",
  "completed",
  "failed",
] as const;
export const CONTEXT_MODES = ["full", "compact", "unknown"] as const;

type ContextInvalidReason = (typeof CONTEXT_INVALID_REASONS)[number];
type ContextLane = (typeof CONTEXT_LANES)[number];
type ContextStatus = (typeof CONTEXT_STATUSES)[number];
type ContextMode = (typeof CONTEXT_MODES)[number];

export type TaskPathLock = {
  path: string;
  lane: ContextLane;
  actor: string;
  created_at: string;
};

export type TaskArtifactLock = {
  artifact: string;
  lane: ContextLane;
  actor: string;
  created_at: string;
};

export type TaskContext = {
  task_id: string;
  version: 1;
  scope: {
    allowed_paths: string[];
    objectives: string[];
    constraints: string[];
  };
  context_pack: {
    summary: string;
    artifacts: string[];
    validated_outputs: string[];
  };
  progress: {
    status: ContextStatus;
    percent: number;
    last_action: string;
  };
  freshness: {
    validated_at: string;
    last_access_at: string;
    ttl_seconds: number;
    warn_after_seconds: number;
    invalidated: boolean;
    reason: ContextInvalidReason;
    invalidated_at: string;
  };
  ownership: {
    lane: ContextLane;
    claimed_by: string;
    claimed_at: string;
    claim_expires_at?: string;
    handoff_pending?: boolean;
    handoff_to_lane?: ContextLane;
    handoff_ack_at?: string;
  };
  locks?: {
    paths: TaskPathLock[];
    artifacts: TaskArtifactLock[];
  };
  telemetry: {
    update_count: number;
    invalidation_count: number;
    last_mode: ContextMode;
    last_input_tokens: number;
    last_output_tokens: number;
    last_turnaround_ms: number;
  };
};

export class TaskContextError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(`[${code}] ${message}`);
    this.code = code;
  }
}

const ROOT_DIR = process.cwd();

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isIsoOrEmpty(value: unknown): boolean {
  if (value === "") {
    return true;
  }
  if (typeof value !== "string") {
    return false;
  }
  return !Number.isNaN(Date.parse(value));
}

function assertObject(value: unknown, label: string): asserts value is Record<string, unknown> {
  if (!isRecord(value)) {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", `${label} must be an object.`);
  }
}

function assertString(value: unknown, label: string, allowEmpty = false): asserts value is string {
  if (typeof value !== "string") {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", `${label} must be a string.`);
  }
  if (!allowEmpty && value.trim() === "") {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", `${label} must be non-empty.`);
  }
}

function assertFiniteNumber(value: unknown, label: string): asserts value is number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", `${label} must be a finite number.`);
  }
}

function assertBoolean(value: unknown, label: string): asserts value is boolean {
  if (typeof value !== "boolean") {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", `${label} must be a boolean.`);
  }
}

function assertStringArray(value: unknown, label: string): asserts value is string[] {
  if (!Array.isArray(value) || value.some((entry) => typeof entry !== "string")) {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", `${label} must be string array.`);
  }
}

function assertEnum<T extends string>(
  value: unknown,
  label: string,
  allowed: readonly T[],
): asserts value is T {
  if (typeof value !== "string" || !allowed.includes(value as T)) {
    throw new TaskContextError(
      "CONTEXT_VALIDATION_FAIL",
      `${label} has unsupported value.`,
    );
  }
}

function assertIsoOrEmpty(value: unknown, label: string): asserts value is string {
  if (!isIsoOrEmpty(value)) {
    throw new TaskContextError(
      "CONTEXT_VALIDATION_FAIL",
      `${label} must be ISO-8601 timestamp or empty string.`,
    );
  }
}

function assertNoUnknownKeys(
  value: Record<string, unknown>,
  allowed: readonly string[],
  label: string,
): void {
  const unknown = Object.keys(value).filter((key) => !allowed.includes(key));
  if (unknown.length > 0) {
    throw new TaskContextError(
      "CONTEXT_VALIDATION_FAIL",
      `${label} contains unknown fields: ${unknown.join(", ")}`,
    );
  }
}

export function normalizeTaskId(taskId: string): string {
  if (typeof taskId !== "string" || taskId.trim() === "") {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", "task_id is required.");
  }
  const normalized = taskId.trim();
  if (!/^[A-Za-z0-9._-]+$/u.test(normalized)) {
    throw new TaskContextError(
      "CONTEXT_VALIDATION_FAIL",
      "task_id must match [A-Za-z0-9._-].",
    );
  }
  return normalized;
}

export function getTaskContextDir(rootDir = ROOT_DIR): string {
  return path.join(rootDir, ".z-mos", "state", "task-context");
}

export function getTaskContextPath(taskId: string, rootDir = ROOT_DIR): string {
  return path.join(getTaskContextDir(rootDir), `${normalizeTaskId(taskId)}.json`);
}

export function createDefaultTaskContext(taskId: string): TaskContext {
  const normalizedTaskId = normalizeTaskId(taskId);
  return {
    task_id: normalizedTaskId,
    version: 1,
    scope: {
      allowed_paths: [],
      objectives: [],
      constraints: [],
    },
    context_pack: {
      summary: "",
      artifacts: [],
      validated_outputs: [],
    },
    progress: {
      status: "planned",
      percent: 0,
      last_action: "context_initialized",
    },
    freshness: {
      validated_at: "",
      last_access_at: "",
      ttl_seconds: 86400,
      warn_after_seconds: 14400,
      invalidated: false,
      reason: "none",
      invalidated_at: "",
    },
    ownership: {
      lane: "unassigned",
      claimed_by: "",
      claimed_at: "",
      claim_expires_at: "",
      handoff_pending: false,
      handoff_to_lane: "unassigned",
      handoff_ack_at: "",
    },
    locks: {
      paths: [],
      artifacts: [],
    },
    telemetry: {
      update_count: 0,
      invalidation_count: 0,
      last_mode: "unknown",
      last_input_tokens: 0,
      last_output_tokens: 0,
      last_turnaround_ms: 0,
    },
  };
}

export function validateTaskContext(value: unknown): TaskContext {
  assertObject(value, "context");
  assertNoUnknownKeys(
    value,
    [
      "task_id",
      "version",
      "scope",
      "context_pack",
      "progress",
      "freshness",
      "ownership",
      "locks",
      "telemetry",
    ],
    "context",
  );

  assertString(value.task_id, "task_id");
  normalizeTaskId(value.task_id);
  if (value.version !== 1) {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", "version must equal 1.");
  }

  assertObject(value.scope, "scope");
  assertNoUnknownKeys(value.scope, ["allowed_paths", "objectives", "constraints"], "scope");
  assertStringArray(value.scope.allowed_paths, "scope.allowed_paths");
  assertStringArray(value.scope.objectives, "scope.objectives");
  assertStringArray(value.scope.constraints, "scope.constraints");

  assertObject(value.context_pack, "context_pack");
  assertNoUnknownKeys(value.context_pack, ["summary", "artifacts", "validated_outputs"], "context_pack");
  assertString(value.context_pack.summary, "context_pack.summary", true);
  assertStringArray(value.context_pack.artifacts, "context_pack.artifacts");
  assertStringArray(value.context_pack.validated_outputs, "context_pack.validated_outputs");

  assertObject(value.progress, "progress");
  assertNoUnknownKeys(value.progress, ["status", "percent", "last_action"], "progress");
  assertEnum(value.progress.status, "progress.status", CONTEXT_STATUSES);
  assertFiniteNumber(value.progress.percent, "progress.percent");
  if (value.progress.percent < 0 || value.progress.percent > 100) {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", "progress.percent must be 0..100.");
  }
  assertString(value.progress.last_action, "progress.last_action", true);

  assertObject(value.freshness, "freshness");
  assertNoUnknownKeys(
    value.freshness,
    [
      "validated_at",
      "last_access_at",
      "ttl_seconds",
      "warn_after_seconds",
      "invalidated",
      "reason",
      "invalidated_at",
    ],
    "freshness",
  );
  assertIsoOrEmpty(value.freshness.validated_at, "freshness.validated_at");
  assertIsoOrEmpty(value.freshness.last_access_at, "freshness.last_access_at");
  assertFiniteNumber(value.freshness.ttl_seconds, "freshness.ttl_seconds");
  assertFiniteNumber(value.freshness.warn_after_seconds, "freshness.warn_after_seconds");
  assertBoolean(value.freshness.invalidated, "freshness.invalidated");
  assertEnum(value.freshness.reason, "freshness.reason", CONTEXT_INVALID_REASONS);
  assertIsoOrEmpty(value.freshness.invalidated_at, "freshness.invalidated_at");

  assertObject(value.ownership, "ownership");
  assertNoUnknownKeys(
    value.ownership,
    [
      "lane",
      "claimed_by",
      "claimed_at",
      "claim_expires_at",
      "handoff_pending",
      "handoff_to_lane",
      "handoff_ack_at",
    ],
    "ownership",
  );
  assertEnum(value.ownership.lane, "ownership.lane", CONTEXT_LANES);
  assertString(value.ownership.claimed_by, "ownership.claimed_by", true);
  assertIsoOrEmpty(value.ownership.claimed_at, "ownership.claimed_at");
  if (value.ownership.claim_expires_at !== undefined) {
    assertIsoOrEmpty(value.ownership.claim_expires_at, "ownership.claim_expires_at");
  }
  if (value.ownership.handoff_pending !== undefined) {
    assertBoolean(value.ownership.handoff_pending, "ownership.handoff_pending");
  }
  if (value.ownership.handoff_to_lane !== undefined) {
    assertEnum(value.ownership.handoff_to_lane, "ownership.handoff_to_lane", CONTEXT_LANES);
  }
  if (value.ownership.handoff_ack_at !== undefined) {
    assertIsoOrEmpty(value.ownership.handoff_ack_at, "ownership.handoff_ack_at");
  }

  if (value.locks !== undefined) {
    assertObject(value.locks, "locks");
    assertNoUnknownKeys(value.locks, ["paths", "artifacts"], "locks");
    if (!Array.isArray(value.locks.paths)) {
      throw new TaskContextError("CONTEXT_VALIDATION_FAIL", "locks.paths must be array.");
    }
    if (!Array.isArray(value.locks.artifacts)) {
      throw new TaskContextError("CONTEXT_VALIDATION_FAIL", "locks.artifacts must be array.");
    }
    for (const [index, lock] of value.locks.paths.entries()) {
      assertObject(lock, `locks.paths[${index}]`);
      assertNoUnknownKeys(lock, ["path", "lane", "actor", "created_at"], `locks.paths[${index}]`);
      assertString(lock.path, `locks.paths[${index}].path`);
      assertEnum(lock.lane, `locks.paths[${index}].lane`, CONTEXT_LANES);
      assertString(lock.actor, `locks.paths[${index}].actor`);
      assertIsoOrEmpty(lock.created_at, `locks.paths[${index}].created_at`);
    }
    for (const [index, lock] of value.locks.artifacts.entries()) {
      assertObject(lock, `locks.artifacts[${index}]`);
      assertNoUnknownKeys(
        lock,
        ["artifact", "lane", "actor", "created_at"],
        `locks.artifacts[${index}]`,
      );
      assertString(lock.artifact, `locks.artifacts[${index}].artifact`);
      assertEnum(lock.lane, `locks.artifacts[${index}].lane`, CONTEXT_LANES);
      assertString(lock.actor, `locks.artifacts[${index}].actor`);
      assertIsoOrEmpty(lock.created_at, `locks.artifacts[${index}].created_at`);
    }
  } else {
    (value as Record<string, unknown>).locks = { paths: [], artifacts: [] };
  }

  assertObject(value.telemetry, "telemetry");
  assertNoUnknownKeys(
    value.telemetry,
    [
      "update_count",
      "invalidation_count",
      "last_mode",
      "last_input_tokens",
      "last_output_tokens",
      "last_turnaround_ms",
    ],
    "telemetry",
  );
  assertFiniteNumber(value.telemetry.update_count, "telemetry.update_count");
  assertFiniteNumber(value.telemetry.invalidation_count, "telemetry.invalidation_count");
  assertEnum(value.telemetry.last_mode, "telemetry.last_mode", CONTEXT_MODES);
  assertFiniteNumber(value.telemetry.last_input_tokens, "telemetry.last_input_tokens");
  assertFiniteNumber(value.telemetry.last_output_tokens, "telemetry.last_output_tokens");
  assertFiniteNumber(value.telemetry.last_turnaround_ms, "telemetry.last_turnaround_ms");

  return value as TaskContext;
}

export async function readTaskContext(taskId: string): Promise<TaskContext> {
  const filePath = getTaskContextPath(taskId);
  let raw: string;
  try {
    raw = await fs.readFile(filePath, "utf8");
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    if (code === "ENOENT") {
      throw new TaskContextError("CONTEXT_NOT_FOUND", `Context not found for task_id=${taskId}.`);
    }
    throw new TaskContextError("CONTEXT_READ_FAIL", `Cannot read context: ${filePath}`);
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new TaskContextError("CONTEXT_VALIDATION_FAIL", `Context JSON is malformed: ${filePath}`);
  }
  return validateTaskContext(parsed);
}

export async function writeTaskContextAtomic(taskId: string, context: TaskContext): Promise<string> {
  const filePath = getTaskContextPath(taskId);
  const dirPath = path.dirname(filePath);
  await fs.mkdir(dirPath, { recursive: true });
  const tmpPath = path.join(
    dirPath,
    `.${path.basename(filePath)}.${Date.now()}.${Math.random().toString(16).slice(2)}.tmp`,
  );
  const content = `${JSON.stringify(context, null, 2)}\n`;
  try {
    await fs.writeFile(tmpPath, content, "utf8");
    await fs.rename(tmpPath, filePath);
  } catch {
    try {
      await fs.unlink(tmpPath);
    } catch {
      // no-op cleanup
    }
    throw new TaskContextError("CONTEXT_WRITE_FAIL", `Atomic write failed: ${filePath}`);
  }
  return filePath;
}

function mergePatch(target: unknown, patch: unknown): unknown {
  if (patch === null) {
    return null;
  }
  if (Array.isArray(patch)) {
    return patch;
  }
  if (!isRecord(patch)) {
    return patch;
  }
  const base = isRecord(target) ? { ...target } : {};
  for (const [key, value] of Object.entries(patch)) {
    base[key] = mergePatch(base[key], value);
  }
  return base;
}

const ALLOWED_PATCH_PATHS = new Set([
  "scope.objectives",
  "scope.constraints",
  "context_pack.summary",
  "context_pack.artifacts",
  "context_pack.validated_outputs",
  "progress.status",
  "progress.percent",
  "progress.last_action",
  "freshness.last_access_at",
  "ownership.lane",
  "ownership.claimed_by",
  "ownership.claimed_at",
  "telemetry.update_count",
  "telemetry.invalidation_count",
  "telemetry.last_mode",
  "telemetry.last_input_tokens",
  "telemetry.last_output_tokens",
  "telemetry.last_turnaround_ms",
]);

const FORBIDDEN_PATCH_PREFIXES = ["task_id", "version", "freshness.reason", "freshness.invalidated_at"];
const REQUIRED_FIELD_PREFIXES = [
  "task_id",
  "version",
  "scope",
  "context_pack",
  "progress",
  "freshness",
  "ownership",
  "telemetry",
];

function collectPatchPaths(
  value: unknown,
  prefix = "",
  output: string[] = [],
): string[] {
  if (!isRecord(value)) {
    if (prefix) {
      output.push(prefix);
    }
    return output;
  }
  for (const [key, child] of Object.entries(value)) {
    const nextPrefix = prefix ? `${prefix}.${key}` : key;
    if (isRecord(child)) {
      collectPatchPaths(child, nextPrefix, output);
      continue;
    }
    output.push(nextPrefix);
  }
  return output;
}

function isPrefix(pathValue: string, prefix: string): boolean {
  return pathValue === prefix || pathValue.startsWith(`${prefix}.`);
}

export function validatePatch(patch: unknown): Record<string, unknown> {
  if (!isRecord(patch)) {
    throw new TaskContextError("CONTEXT_PATCH_FORBIDDEN", "Patch must be a JSON object.");
  }

  const patchPaths = collectPatchPaths(patch);
  if (patchPaths.length === 0) {
    throw new TaskContextError("CONTEXT_PATCH_FORBIDDEN", "Patch cannot be empty.");
  }

  for (const patchPath of patchPaths) {
    if (FORBIDDEN_PATCH_PREFIXES.some((prefix) => isPrefix(patchPath, prefix))) {
      throw new TaskContextError(
        "CONTEXT_PATCH_FORBIDDEN",
        `Patch path is forbidden: ${patchPath}`,
      );
    }
    if (!ALLOWED_PATCH_PATHS.has(patchPath)) {
      throw new TaskContextError(
        "CONTEXT_PATCH_FORBIDDEN",
        `Patch path is not allowed: ${patchPath}`,
      );
    }
  }

  for (const requiredPrefix of REQUIRED_FIELD_PREFIXES) {
    const targeted = patchPaths.some((patchPath) => isPrefix(patchPath, requiredPrefix));
    if (!targeted) {
      continue;
    }
    const segments = requiredPrefix.split(".");
    let pointer: unknown = patch;
    for (const segment of segments) {
      if (!isRecord(pointer) || !(segment in pointer)) {
        pointer = undefined;
        break;
      }
      pointer = pointer[segment];
    }
    if (pointer === null) {
      throw new TaskContextError(
        "CONTEXT_PATCH_FORBIDDEN",
        `Null is not allowed for required field: ${requiredPrefix}`,
      );
    }
  }

  return patch;
}

export function applyPatch(context: TaskContext, patch: Record<string, unknown>): TaskContext {
  const merged = mergePatch(context, patch);
  return validateTaskContext(merged);
}

export function computeFreshnessWarning(context: TaskContext): string | null {
  if (!context.freshness.last_access_at) {
    return null;
  }
  const lastAccessMs = Date.parse(context.freshness.last_access_at);
  if (Number.isNaN(lastAccessMs)) {
    return null;
  }
  const ageSeconds = Math.floor((Date.now() - lastAccessMs) / 1000);
  if (ageSeconds > context.freshness.warn_after_seconds) {
    return `Context stale: last_access_at=${context.freshness.last_access_at}, age_seconds=${ageSeconds}, warn_after_seconds=${context.freshness.warn_after_seconds}`;
  }
  return null;
}
