import { LOCAL_KERNEL_ERROR_CODES } from "./errors.js";
import type {
  LocalDecisionStatus,
  LocalInvariantViolation,
  LocalReplayResult,
  LocalTraceRecord,
} from "./types.js";
import { deepFreeze } from "./immutability.js";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function asDeterministicUnique(values: string[]): string[] {
  return [...new Set(values)].sort();
}

function asDeterministicUniqueInvariant(values: LocalInvariantViolation[]): LocalInvariantViolation[] {
  return [...new Set(values)].sort();
}

function failedReplay(input: {
  replayId: string;
  recordCount: number;
  reason: string;
  code: string;
}): LocalReplayResult {
  return deepFreeze({
    replay_id: input.replayId,
    status: "failed",
    record_count: input.recordCount,
    accepted_count: 0,
    rejected_count: 0,
    quarantined_count: 0,
    last_sequence: 0,
    decision_ids: [],
    intent_ids: [],
    error_codes: [input.code],
    invariant_violation_refs: [],
    metadata: {
      deterministic_key: [input.replayId, "failed", input.code, input.recordCount].join("|"),
      failure_reason: input.reason,
    },
  });
}

function validateRecordShape(record: unknown): record is LocalTraceRecord {
  if (!isRecord(record)) {
    return false;
  }

  if (
    !isNonEmptyString(record.trace_id) ||
    typeof record.sequence !== "number" ||
    !isNonEmptyString(record.timestamp) ||
    !isNonEmptyString(record.intent_id) ||
    !isNonEmptyString(record.decision_id) ||
    !isNonEmptyString(record.subject_ref) ||
    !isNonEmptyString(record.issuer_ref) ||
    !isNonEmptyString(record.trust_envelope_ref)
  ) {
    return false;
  }

  if (!isNonEmptyString(record.decision_status)) {
    return false;
  }

  if (!Array.isArray(record.error_codes) || !Array.isArray(record.invariant_violations)) {
    return false;
  }

  if (!isRecord(record.metadata) || !isNonEmptyString(record.metadata.deterministic_key)) {
    return false;
  }

  return true;
}

export function replayLocalTraceRecords(records: ReadonlyArray<LocalTraceRecord>): LocalReplayResult {
  const replayId = "replay-local-kernel-v1";
  const snapshot = records.map((record) => ({
    ...record,
    error_codes: [...record.error_codes],
    invariant_violations: [...record.invariant_violations],
    metadata: { ...record.metadata },
  }));

  if (snapshot.some((record) => !validateRecordShape(record))) {
    return failedReplay({
      replayId,
      recordCount: snapshot.length,
      code: LOCAL_KERNEL_ERROR_CODES.REPLAY_MALFORMED_RECORD,
      reason: "Trace contains malformed record.",
    });
  }

  const sorted = [...snapshot].sort((a, b) => a.sequence - b.sequence);

  const seen = new Set<number>();
  let previous = 0;
  for (const record of sorted) {
    if (!Number.isInteger(record.sequence) || record.sequence <= 0) {
      return failedReplay({
        replayId,
        recordCount: sorted.length,
        code: LOCAL_KERNEL_ERROR_CODES.REPLAY_INVALID_SEQUENCE,
        reason: "Trace sequence must be positive integer.",
      });
    }

    if (seen.has(record.sequence)) {
      return failedReplay({
        replayId,
        recordCount: sorted.length,
        code: LOCAL_KERNEL_ERROR_CODES.REPLAY_DUPLICATE_SEQUENCE,
        reason: "Trace contains duplicate sequence value.",
      });
    }

    if (previous !== 0 && record.sequence !== previous + 1) {
      return failedReplay({
        replayId,
        recordCount: sorted.length,
        code: LOCAL_KERNEL_ERROR_CODES.REPLAY_SEQUENCE_GAP,
        reason: "Trace sequence gap detected.",
      });
    }

    if (
      record.decision_status !== "accepted" &&
      record.decision_status !== "rejected" &&
      record.decision_status !== "quarantined"
    ) {
      return failedReplay({
        replayId,
        recordCount: sorted.length,
        code: LOCAL_KERNEL_ERROR_CODES.REPLAY_UNKNOWN_DECISION_STATUS,
        reason: `Unknown decision status: ${String(record.decision_status)}.`,
      });
    }

    seen.add(record.sequence);
    previous = record.sequence;
  }

  try {
    const accepted = sorted.filter((record) => record.decision_status === "accepted").length;
    const rejected = sorted.filter((record) => record.decision_status === "rejected").length;
    const quarantined = sorted.filter((record) => record.decision_status === "quarantined").length;

    const decisionIds = sorted.map((record) => record.decision_id);
    const intentIds = sorted.map((record) => record.intent_id);
    const errorCodes = asDeterministicUnique(sorted.flatMap((record) => record.error_codes));
    const invariantRefs = asDeterministicUniqueInvariant(
      sorted.flatMap((record) => record.invariant_violations),
    );
    const lastSequence = sorted.length > 0 ? sorted[sorted.length - 1].sequence : 0;

    return deepFreeze({
      replay_id: replayId,
      status: "completed",
      record_count: sorted.length,
      accepted_count: accepted,
      rejected_count: rejected,
      quarantined_count: quarantined,
      last_sequence: lastSequence,
      decision_ids: decisionIds,
      intent_ids: intentIds,
      error_codes: errorCodes,
      invariant_violation_refs: invariantRefs,
      metadata: {
        deterministic_key: [
          replayId,
          sorted.length,
          accepted,
          rejected,
          quarantined,
          lastSequence,
          decisionIds.join(","),
          intentIds.join(","),
          errorCodes.join(","),
          invariantRefs.join(","),
        ].join("|"),
      },
    });
  } catch {
    return failedReplay({
      replayId,
      recordCount: sorted.length,
      code: LOCAL_KERNEL_ERROR_CODES.REPLAY_SUMMARY_FAILURE,
      reason: "Unable to produce deterministic replay summary.",
    });
  }
}
