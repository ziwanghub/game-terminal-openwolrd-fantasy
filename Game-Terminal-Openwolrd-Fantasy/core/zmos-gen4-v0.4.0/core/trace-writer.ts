import { promises as fs } from "node:fs";
import * as fsSync from "node:fs";
import * as path from "node:path";
import * as readline from "node:readline";

import { getCanonicalPayload, computeTraceHash } from "./trace-crypto.js";
import { createHash } from "node:crypto";

import { readManifest } from "./manifest.js";
import { loadNodeIdentity } from "./node.js";
import type {
  TraceActor,
  TraceEnvironment,
  TraceExecutionStatus,
  TraceExpectation,
  TraceGateStatus,
  TracePolicyStatus,
  TraceRecordContract,
  TraceResult,
  TraceResultClass,
} from "../contracts/trace.js";

const ROOT_DIR = process.cwd();
const DEFAULT_TRACE_DIR = path.join(ROOT_DIR, ".z-mos", "trace");
const TRACE_FILE_NAME = "runtime-trace.jsonl";

export type TraceRecord = TraceRecordContract;

export type LegacyTraceStatus = "success" | "failed";

export type TraceWriteInput = {
  command: string;
  status: LegacyTraceStatus;
  actor: TraceActor;
  details: Record<string, unknown>;
};

export type CanonicalTraceWriteInput = {
  command: string;
  actor: TraceActor;
  execution_status: TraceExecutionStatus;
  result_class: TraceResultClass;
  preflight_status: TraceGateStatus;
  canonical_status: TraceGateStatus;
  policy_status: TracePolicyStatus;
  trace_expectation: TraceExpectation;
  trace_result: TraceResult;
  details?: Record<string, unknown>;
};

export type TraceWriteResult = {
  ok: boolean;
  tracePath: string;
  record?: TraceRecord;
  error?: string;
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asNonEmptyString(value: unknown): string | null {
  if (typeof value === "string" && value.trim().length > 0) {
    return value;
  }
  return null;
}

function assertNonEmptyString(value: unknown, fieldPath: string): asserts value is string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Invalid trace record: ${fieldPath} must be a non-empty string`);
  }
}

function assertInSet<T extends string>(
  value: unknown,
  fieldPath: string,
  allowed: readonly T[],
): asserts value is T {
  if (typeof value !== "string" || !allowed.includes(value as T)) {
    throw new Error(`Invalid trace record: ${fieldPath} has unsupported value`);
  }
}

function assertTraceEnvironment(value: unknown): asserts value is TraceEnvironment {
  if (!isObject(value)) {
    throw new Error("Invalid trace record: environment must be an object");
  }

  assertNonEmptyString(value.platform, "environment.platform");
  assertNonEmptyString(value.arch, "environment.arch");
}

function assertTraceDetails(value: unknown): asserts value is Record<string, unknown> {
  if (!isObject(value)) {
    throw new Error("Invalid trace record: details must be an object");
  }
}

const TRACE_EXECUTION_STATUSES = ["success", "warning", "blocked", "failed"] as const;
const TRACE_RESULT_CLASSES = [
  "success",
  "warning-execution",
  "blocked-preflight",
  "blocked-canonical-integrity",
  "blocked-policy",
  "failed-runtime",
] as const;
const TRACE_GATE_STATUSES = ["healthy", "warning", "blocking", "not-evaluated"] as const;
const TRACE_POLICY_STATUSES = ["healthy", "warning", "blocking", "not-applicable"] as const;
const TRACE_EXPECTATIONS = ["required-if-business-logic", "optional-by-design"] as const;
const TRACE_RESULTS = [
  "emitted",
  "not-emitted-by-design",
  "not-emitted-blocked-before-logic",
  "not-emitted-due-failure",
  "not-enough-evidence",
] as const;
const TRACE_ACTORS = ["human", "system", "ollama", "codex"] as const;

export function validateTraceRecord(record: TraceRecord): TraceRecord {
  assertNonEmptyString(record.timestamp, "timestamp");
  assertNonEmptyString(record.command, "command");
  assertInSet(record.execution_status, "execution_status", TRACE_EXECUTION_STATUSES);
  assertInSet(record.result_class, "result_class", TRACE_RESULT_CLASSES);
  assertInSet(record.preflight_status, "preflight_status", TRACE_GATE_STATUSES);
  assertInSet(record.canonical_status, "canonical_status", TRACE_GATE_STATUSES);
  assertInSet(record.policy_status, "policy_status", TRACE_POLICY_STATUSES);
  assertInSet(record.trace_expectation, "trace_expectation", TRACE_EXPECTATIONS);
  assertInSet(record.trace_result, "trace_result", TRACE_RESULTS);
  assertTraceEnvironment(record.environment);
  assertInSet(record.actor, "actor", TRACE_ACTORS);
  assertNonEmptyString(record.repository, "repository");
  assertNonEmptyString(record.framework, "framework");
  if (record.node_id !== undefined) {
    assertNonEmptyString(record.node_id, "node_id");
  }
  if (record.node_role !== undefined) {
    assertNonEmptyString(record.node_role, "node_role");
  }
  assertTraceDetails(record.details);
  return record;
}

function inferExecutionStatus(input: TraceWriteInput): TraceExecutionStatus {
  const mapped = asNonEmptyString(input.details.execution_status);
  if (mapped && TRACE_EXECUTION_STATUSES.includes(mapped as TraceExecutionStatus)) {
    return mapped as TraceExecutionStatus;
  }
  return input.status === "success" ? "success" : "failed";
}

function inferResultClass(
  executionStatus: TraceExecutionStatus,
  details: Record<string, unknown>,
): TraceResultClass {
  const mapped = asNonEmptyString(details.result_class);
  if (mapped && TRACE_RESULT_CLASSES.includes(mapped as TraceResultClass)) {
    return mapped as TraceResultClass;
  }
  if (executionStatus === "warning") {
    return "warning-execution";
  }
  if (executionStatus === "blocked") {
    return "blocked-policy";
  }
  if (executionStatus === "failed") {
    return "failed-runtime";
  }
  return "success";
}

function inferGateStatus(
  details: Record<string, unknown>,
  key: "preflight_status" | "canonical_status",
): TraceGateStatus {
  const mapped = asNonEmptyString(details[key]);
  if (mapped && TRACE_GATE_STATUSES.includes(mapped as TraceGateStatus)) {
    return mapped as TraceGateStatus;
  }
  return "not-evaluated";
}

function inferPolicyStatus(details: Record<string, unknown>): TracePolicyStatus {
  const mapped = asNonEmptyString(details.policy_status);
  if (mapped && TRACE_POLICY_STATUSES.includes(mapped as TracePolicyStatus)) {
    return mapped as TracePolicyStatus;
  }
  return "not-applicable";
}

function inferTraceExpectation(details: Record<string, unknown>): TraceExpectation {
  const mapped = asNonEmptyString(details.trace_expectation);
  if (mapped && TRACE_EXPECTATIONS.includes(mapped as TraceExpectation)) {
    return mapped as TraceExpectation;
  }
  return "required-if-business-logic";
}

function inferTraceResult(
  executionStatus: TraceExecutionStatus,
  details: Record<string, unknown>,
): TraceResult {
  const mapped = asNonEmptyString(details.trace_result);
  if (mapped && TRACE_RESULTS.includes(mapped as TraceResult)) {
    return mapped as TraceResult;
  }
  if (executionStatus === "blocked") {
    return "not-emitted-blocked-before-logic";
  }
  if (executionStatus === "failed") {
    return "not-emitted-due-failure";
  }
  return "emitted";
}

async function resolveTracePath(): Promise<string> {
  try {
    const manifest = await readManifest();
    const traceDir = path.resolve(ROOT_DIR, manifest.workspace.traceDir);
    const canonicalTraceDir = path.join(ROOT_DIR, ".z-mos", "trace");
    if (traceDir !== canonicalTraceDir) {
      throw new Error(
        `Canonical trace path mismatch: expected ${canonicalTraceDir}, received ${traceDir}`,
      );
    }
    return path.join(traceDir, TRACE_FILE_NAME);
  } catch {
    return path.join(DEFAULT_TRACE_DIR, TRACE_FILE_NAME);
  }
}

export async function getTraceFilePath(): Promise<string> {
  return resolveTracePath();
}

async function buildCanonicalTraceRecord(input: CanonicalTraceWriteInput): Promise<TraceRecord> {
  const [manifest, node] = await Promise.all([readManifest(), loadNodeIdentity()]);
  const details = isObject(input.details) ? input.details : {};

  const record: TraceRecord = {
    timestamp: new Date().toISOString(),
    command: input.command,
    execution_status: input.execution_status,
    result_class: input.result_class,
    preflight_status: input.preflight_status,
    canonical_status: input.canonical_status,
    policy_status: input.policy_status,
    trace_expectation: input.trace_expectation,
    trace_result: input.trace_result,
    environment: {
      platform: process.platform,
      arch: process.arch,
    },
    actor: input.actor,
    repository: manifest.repository.name,
    framework: manifest.repository.framework,
    node_id: node.node_id,
    node_role: node.node_role,
    details,
  };

  return validateTraceRecord(record);
}

async function buildLegacyTraceRecord(input: TraceWriteInput): Promise<TraceRecord> {
  const [manifest, node] = await Promise.all([readManifest(), loadNodeIdentity()]);
  const details = isObject(input.details) ? input.details : {};
  const executionStatus = inferExecutionStatus(input);
  const resultClass = inferResultClass(executionStatus, details);
  const preflightStatus = inferGateStatus(details, "preflight_status");
  const canonicalStatus = inferGateStatus(details, "canonical_status");
  const policyStatus = inferPolicyStatus(details);
  const traceExpectation = inferTraceExpectation(details);
  const traceResult = inferTraceResult(executionStatus, details);

  const record: TraceRecord = {
    timestamp: new Date().toISOString(),
    command: input.command,
    execution_status: executionStatus,
    result_class: resultClass,
    preflight_status: preflightStatus,
    canonical_status: canonicalStatus,
    policy_status: policyStatus,
    trace_expectation: traceExpectation,
    trace_result: traceResult,
    environment: {
      platform: process.platform,
      arch: process.arch,
    },
    actor: input.actor,
    repository: manifest.repository.name,
    framework: manifest.repository.framework,
    node_id: node.node_id,
    node_role: node.node_role,
    details,
  };

  return validateTraceRecord(record);
}

export async function getLastHashedTrace(tracePath: string): Promise<TraceRecord | null> {
  try {
    const fileStream = fsSync.createReadStream(tracePath);
    const rl = readline.createInterface({
      input: fileStream,
      crlfDelay: Infinity
    });
    let lastValid: TraceRecord | null = null;
    for await (const line of rl) {
      if (!line.trim()) continue;
      try {
        const record = JSON.parse(line) as TraceRecord;
        if (record.current_hash) {
          lastValid = record;
        }
      } catch (e) {
        // ignore malformed
      }
    }
    if (lastValid) return lastValid;
  } catch {}

  // If active trace is empty/missing, look at the archive
  const archiveDir = path.join(path.dirname(tracePath), "archive");
  try {
    const files = await fs.readdir(archiveDir);
    const metaFiles = files.filter(f => f.endsWith(".meta.json")).sort();
    if (metaFiles.length > 0) {
      const lastMetaFile = metaFiles[metaFiles.length - 1];
      const content = await fs.readFile(path.join(archiveDir, lastMetaFile), "utf8");
      const meta = JSON.parse(content);
      return {
        sequence: meta.end_sequence,
        current_hash: meta.end_hash,
      } as TraceRecord;
    }
  } catch {}

  return null;
}

async function computeSegmentHash(filePath: string): Promise<string> {
  const fileBuffer = await fs.readFile(filePath);
  return createHash("sha256").update(fileBuffer).digest("hex");
}

async function getLastArchiveMeta(archiveDir: string): Promise<{ segment_hash: string } | null> {
  try {
    const files = await fs.readdir(archiveDir);
    const metaFiles = files.filter(f => f.endsWith(".meta.json")).sort();
    if (metaFiles.length === 0) return null;
    const lastFile = metaFiles[metaFiles.length - 1];
    const content = await fs.readFile(path.join(archiveDir, lastFile), "utf8");
    return JSON.parse(content);
  } catch {
    return null;
  }
}

async function getFirstHashedTrace(tracePath: string): Promise<TraceRecord | null> {
  try {
    const fileStream = fsSync.createReadStream(tracePath);
    const rl = readline.createInterface({ input: fileStream, crlfDelay: Infinity });
    for await (const line of rl) {
      if (!line.trim()) continue;
      try {
        const record = JSON.parse(line) as TraceRecord;
        if (record.current_hash) {
          rl.close();
          return record;
        }
      } catch (e) {}
    }
  } catch {}
  return null;
}

async function rotateTraceIfNecessary(tracePath: string, lastHashed: TraceRecord | null): Promise<void> {
  if (!lastHashed || !lastHashed.sequence) return;

  const ROTATION_LIMIT = parseInt(process.env.ZMOS_TRACE_ROTATION_LIMIT || "10000", 10);
  const SIZE_LIMIT_MB = parseInt(process.env.ZMOS_TRACE_ROTATION_SIZE_MB || "50", 10);

  let shouldRotate = false;
  
  if (lastHashed.sequence > 0 && lastHashed.sequence % ROTATION_LIMIT === 0) {
    shouldRotate = true;
  } else {
    try {
      const stats = await fs.stat(tracePath);
      if (stats.size >= SIZE_LIMIT_MB * 1024 * 1024) {
        shouldRotate = true;
      }
    } catch {}
  }

  if (!shouldRotate) return;

  const archiveDir = path.join(path.dirname(tracePath), "archive");
  await fs.mkdir(archiveDir, { recursive: true });

  const rotatingPath = `${tracePath}.rotating`;
  try {
    await fs.rename(tracePath, rotatingPath);
  } catch {
    return; // File might not exist or be locked
  }

  const firstRecord = await getFirstHashedTrace(rotatingPath);
  if (!firstRecord) {
    return;
  }

  const startSeq = String(firstRecord.sequence).padStart(6, "0");
  const endSeq = String(lastHashed.sequence).padStart(6, "0");
  
  const archiveFilename = `trace-${startSeq}-${endSeq}.jsonl`;
  const metaFilename = `trace-${startSeq}-${endSeq}.meta.json`;

  const segmentHash = await computeSegmentHash(rotatingPath);
  const lastMeta = await getLastArchiveMeta(archiveDir);
  const previousSegmentHash = lastMeta?.segment_hash || "GENESIS";

  const meta = {
    start_sequence: firstRecord.sequence,
    end_sequence: lastHashed.sequence,
    start_hash: firstRecord.current_hash,
    end_hash: lastHashed.current_hash,
    segment_hash: segmentHash,
    previous_segment_hash: previousSegmentHash,
    archived_at: new Date().toISOString(),
  };

  await fs.writeFile(path.join(archiveDir, metaFilename), JSON.stringify(meta, null, 2), "utf8");
  await fs.rename(rotatingPath, path.join(archiveDir, archiveFilename));
}

async function appendJsonlLine(tracePath: string, record: TraceRecord): Promise<void> {
  const lastHashed = await getLastHashedTrace(tracePath);
  
  await rotateTraceIfNecessary(tracePath, lastHashed);
  
  const sequence = lastHashed?.sequence ? lastHashed.sequence + 1 : 1;
  const previous_hash = lastHashed?.current_hash ? lastHashed.current_hash : "GENESIS";
  
  record.sequence = sequence;
  record.previous_hash = previous_hash;
  
  const canonicalPayload = getCanonicalPayload(record);
  record.current_hash = computeTraceHash(sequence, record.timestamp, canonicalPayload, previous_hash);

  const line = `${JSON.stringify(record)}\n`;
  await fs.mkdir(path.dirname(tracePath), { recursive: true });
  await fs.appendFile(tracePath, line, { encoding: "utf8", flag: "a" });
}

export async function writeCanonicalTraceRecord(
  input: CanonicalTraceWriteInput,
): Promise<TraceWriteResult> {
  const tracePath = await resolveTracePath();
  try {
    const record = await buildCanonicalTraceRecord(input);
    await appendJsonlLine(tracePath, record);
    return {
      ok: true,
      tracePath,
      record,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown trace write error";
    return {
      ok: false,
      tracePath,
      error: message,
    };
  }
}

export async function writeTraceRecord(input: TraceWriteInput): Promise<TraceWriteResult> {
  const tracePath = await resolveTracePath();
  try {
    const record = await buildLegacyTraceRecord(input);
    await appendJsonlLine(tracePath, record);
    return {
      ok: true,
      tracePath,
      record,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown trace write error";
    return {
      ok: false,
      tracePath,
      error: message,
    };
  }
}

export async function appendTraceRecord(input: TraceWriteInput): Promise<TraceRecord> {
  const result = await writeTraceRecord(input);
  if (!result.ok || !result.record) {
    throw new Error(
      `Trace write failed: ${result.error || "Unknown error"} (path: ${result.tracePath})`,
    );
  }
  return result.record;
}
