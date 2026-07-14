import { appendFile, readFile } from "node:fs/promises";
import type { LocalTraceRecord } from "./types.js";
import { deepFreeze } from "./immutability.js";
import { LOCAL_KERNEL_ERROR_CODES } from "./errors.js";

type TracePersistenceStatus = "written" | "loaded" | "failed";

type TracePersistenceMeta = Readonly<{
  file_path: string;
  deterministic_key: string;
  reason?: string;
}>;

export type LocalTracePersistenceWriteResult = Readonly<{
  status: TracePersistenceStatus;
  record_count: number;
  error_codes: readonly string[];
  metadata: TracePersistenceMeta;
}>;

export type LocalTracePersistenceLoadResult = Readonly<{
  status: TracePersistenceStatus;
  record_count: number;
  error_codes: readonly string[];
  records: readonly LocalTraceRecord[];
  metadata: TracePersistenceMeta;
}>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isText(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function cloneRecord(record: LocalTraceRecord): LocalTraceRecord {
  return {
    ...record,
    error_codes: [...record.error_codes],
    invariant_violations: [...record.invariant_violations],
    metadata: { ...record.metadata },
  };
}

function validateTraceRecord(record: unknown): record is LocalTraceRecord {
  if (!isRecord(record)) return false;

  if (
    !isText(record.trace_id) ||
    typeof record.sequence !== "number" ||
    !isText(record.timestamp) ||
    !isText(record.intent_id) ||
    !isText(record.decision_id) ||
    !isText(record.decision_status) ||
    !isText(record.subject_ref) ||
    !isText(record.issuer_ref) ||
    !isText(record.trust_envelope_ref)
  ) {
    return false;
  }

  if (!Array.isArray(record.error_codes) || !Array.isArray(record.invariant_violations)) {
    return false;
  }

  if (!isRecord(record.metadata)) return false;
  if (!isText(record.metadata.deterministic_key)) return false;
  if (!isText(record.metadata.trace_correlation_id)) return false;
  if (!isText(record.metadata.replay_nonce)) return false;

  return true;
}

function toFailureMeta(filePath: string, code: string, reason: string): TracePersistenceMeta {
  return {
    file_path: filePath,
    deterministic_key: ["trace-persistence", "failed", code, filePath].join("|"),
    reason,
  };
}

function toFailureWrite(filePath: string, code: string, reason: string): LocalTracePersistenceWriteResult {
  return deepFreeze({
    status: "failed",
    record_count: 0,
    error_codes: [code],
    metadata: toFailureMeta(filePath, code, reason),
  });
}

function toFailureLoad(filePath: string, code: string, reason: string): LocalTracePersistenceLoadResult {
  return deepFreeze({
    status: "failed",
    record_count: 0,
    error_codes: [code],
    records: [],
    metadata: toFailureMeta(filePath, code, reason),
  });
}

function normalizePath(filePath: string): string | null {
  if (!isText(filePath)) return null;
  if (filePath.includes("\0")) return null;
  return filePath;
}

function serializeRecord(record: LocalTraceRecord): string {
  const stable = {
    trace_id: record.trace_id,
    sequence: record.sequence,
    timestamp: record.timestamp,
    intent_id: record.intent_id,
    decision_id: record.decision_id,
    decision_status: record.decision_status,
    subject_ref: record.subject_ref,
    issuer_ref: record.issuer_ref,
    trust_envelope_ref: record.trust_envelope_ref,
    error_codes: [...record.error_codes],
    invariant_violations: [...record.invariant_violations],
    metadata: {
      deterministic_key: record.metadata.deterministic_key,
      trace_correlation_id: record.metadata.trace_correlation_id,
      replay_nonce: record.metadata.replay_nonce,
    },
  };

  return `${JSON.stringify(stable)}\n`;
}

export async function appendLocalTraceRecordToFile(input: {
  file_path: string;
  record: LocalTraceRecord;
}): Promise<LocalTracePersistenceWriteResult> {
  const pathValue = normalizePath(input.file_path);
  if (!pathValue) {
    return toFailureWrite(
      input.file_path,
      LOCAL_TRACE_PERSISTENCE_ERROR_CODES.TRACE_PERSISTENCE_INVALID_PATH,
      "Trace file path is invalid.",
    );
  }

  if (!validateTraceRecord(input.record)) {
    return toFailureWrite(
      pathValue,
      LOCAL_TRACE_PERSISTENCE_ERROR_CODES.TRACE_PERSISTENCE_MALFORMED_RECORD,
      "Trace record is malformed.",
    );
  }

  try {
    const line = serializeRecord(cloneRecord(input.record));
    await appendFile(pathValue, line, "utf8");
    return deepFreeze({
      status: "written",
      record_count: 1,
      error_codes: [],
      metadata: {
        file_path: pathValue,
        deterministic_key: ["trace-persistence", "written", input.record.trace_id, pathValue].join("|"),
      },
    });
  } catch {
    return toFailureWrite(
      pathValue,
      LOCAL_TRACE_PERSISTENCE_ERROR_CODES.TRACE_PERSISTENCE_WRITE_FAILED,
      "Append write failed.",
    );
  }
}

export async function loadLocalTraceRecordsFromFile(input: {
  file_path: string;
}): Promise<LocalTracePersistenceLoadResult> {
  const pathValue = normalizePath(input.file_path);
  if (!pathValue) {
    return toFailureLoad(
      input.file_path,
      LOCAL_TRACE_PERSISTENCE_ERROR_CODES.TRACE_PERSISTENCE_INVALID_PATH,
      "Trace file path is invalid.",
    );
  }

  let data = "";
  try {
    data = await readFile(pathValue, "utf8");
  } catch {
    return toFailureLoad(
      pathValue,
      LOCAL_TRACE_PERSISTENCE_ERROR_CODES.TRACE_PERSISTENCE_READ_FAILED,
      "Trace file read failed.",
    );
  }

  const lines = data.split("\n").filter((line) => line.trim().length > 0);
  const parsed: LocalTraceRecord[] = [];

  for (const line of lines) {
    let raw: unknown;
    try {
      raw = JSON.parse(line);
    } catch {
      return toFailureLoad(
        pathValue,
        LOCAL_TRACE_PERSISTENCE_ERROR_CODES.TRACE_PERSISTENCE_MALFORMED_JSON,
        "Trace file has malformed JSON line.",
      );
    }

    if (!validateTraceRecord(raw)) {
      return toFailureLoad(
        pathValue,
        LOCAL_TRACE_PERSISTENCE_ERROR_CODES.TRACE_PERSISTENCE_MALFORMED_RECORD,
        "Trace file has malformed trace record.",
      );
    }

    parsed.push(deepFreeze(cloneRecord(raw)));
  }

  return deepFreeze({
    status: "loaded",
    record_count: parsed.length,
    error_codes: [],
    records: deepFreeze(parsed),
    metadata: {
      file_path: pathValue,
      deterministic_key: ["trace-persistence", "loaded", parsed.length, pathValue].join("|"),
    },
  });
}

export function isLocalTracePersistenceFailure(
  result: LocalTracePersistenceWriteResult | LocalTracePersistenceLoadResult,
): boolean {
  return result.status === "failed";
}

export const LOCAL_TRACE_PERSISTENCE_ERROR_CODES = {
  TRACE_PERSISTENCE_WRITE_FAILED: LOCAL_KERNEL_ERROR_CODES.TRACE_PERSISTENCE_WRITE_FAILED,
  TRACE_PERSISTENCE_READ_FAILED: LOCAL_KERNEL_ERROR_CODES.TRACE_PERSISTENCE_READ_FAILED,
  TRACE_PERSISTENCE_MALFORMED_RECORD: LOCAL_KERNEL_ERROR_CODES.TRACE_PERSISTENCE_MALFORMED_RECORD,
  TRACE_PERSISTENCE_MALFORMED_JSON: LOCAL_KERNEL_ERROR_CODES.TRACE_PERSISTENCE_MALFORMED_JSON,
  TRACE_PERSISTENCE_INVALID_PATH: LOCAL_KERNEL_ERROR_CODES.TRACE_PERSISTENCE_INVALID_PATH,
} as const;
