import { LOCAL_KERNEL_ERROR_CODES } from "./errors.js";
import type {
  LocalEvidencePackage,
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

function stableUnique(values: string[]): string[] {
  return [...new Set(values)].sort();
}

function stableUniqueInvariant(values: LocalInvariantViolation[]): LocalInvariantViolation[] {
  return [...new Set(values)].sort();
}

function buildPackageId(replayId: string, recordCount: number): string {
  return `evidence-${replayId}-${recordCount}`;
}

function failedPackage(input: {
  replayId: string;
  records: LocalTraceRecord[];
  code: string;
  reason: string;
}): LocalEvidencePackage {
  const errorCodes = stableUnique([
    input.code,
    ...input.records.flatMap((record) => record.error_codes),
  ]);

  const invariantRefs = stableUniqueInvariant(
    input.records.flatMap((record) => record.invariant_violations),
  );

  return deepFreeze({
    evidence_package_id: buildPackageId(input.replayId, input.records.length),
    status: "failed",
    decision_ids: stableUnique(input.records.map((record) => record.decision_id)),
    intent_ids: stableUnique(input.records.map((record) => record.intent_id)),
    trace_ids: stableUnique(input.records.map((record) => record.trace_id)),
    replay_id: input.replayId,
    accepted_count: 0,
    rejected_count: 0,
    quarantined_count: 0,
    error_codes: errorCodes,
    invariant_violation_refs: invariantRefs,
    metadata: {
      deterministic_key: [input.replayId, "failed", input.code, input.records.length].join("|"),
      reason: input.reason,
    },
  });
}

function incompletePackage(input: {
  replayId: string;
  records: LocalTraceRecord[];
  code: string;
  reason: string;
}): LocalEvidencePackage {
  const errorCodes = stableUnique([
    input.code,
    ...input.records.flatMap((record) => record.error_codes),
  ]);

  const invariantRefs = stableUniqueInvariant(
    input.records.flatMap((record) => record.invariant_violations),
  );

  const accepted = input.records.filter((record) => record.decision_status === "accepted").length;
  const rejected = input.records.filter((record) => record.decision_status === "rejected").length;
  const quarantined = input.records.filter((record) => record.decision_status === "quarantined").length;

  return deepFreeze({
    evidence_package_id: buildPackageId(input.replayId, input.records.length),
    status: "incomplete",
    decision_ids: stableUnique(input.records.map((record) => record.decision_id)),
    intent_ids: stableUnique(input.records.map((record) => record.intent_id)),
    trace_ids: stableUnique(input.records.map((record) => record.trace_id)),
    replay_id: input.replayId,
    accepted_count: accepted,
    rejected_count: rejected,
    quarantined_count: quarantined,
    error_codes: errorCodes,
    invariant_violation_refs: invariantRefs,
    metadata: {
      deterministic_key: [input.replayId, "incomplete", input.code, input.records.length].join("|"),
      reason: input.reason,
    },
  });
}

function validateTraceShape(record: unknown): record is LocalTraceRecord {
  if (!isRecord(record)) {
    return false;
  }

  if (
    !isNonEmptyString(record.trace_id) ||
    typeof record.sequence !== "number" ||
    !isNonEmptyString(record.intent_id) ||
    !isNonEmptyString(record.decision_id) ||
    !Array.isArray(record.error_codes) ||
    !Array.isArray(record.invariant_violations)
  ) {
    return false;
  }

  return true;
}

export function buildLocalEvidencePackage(input: {
  trace_records: ReadonlyArray<LocalTraceRecord>;
  replay_result: LocalReplayResult;
}): LocalEvidencePackage {
  const records = input.trace_records.map((record) => ({
    ...record,
    error_codes: [...record.error_codes],
    invariant_violations: [...record.invariant_violations],
    metadata: { ...record.metadata },
  }));
  const replay = {
    ...input.replay_result,
    decision_ids: [...input.replay_result.decision_ids],
    intent_ids: [...input.replay_result.intent_ids],
    error_codes: [...input.replay_result.error_codes],
    invariant_violation_refs: [...input.replay_result.invariant_violation_refs],
    metadata: { ...input.replay_result.metadata },
  };

  if (!isNonEmptyString(replay.replay_id) || replay.status === undefined) {
    return failedPackage({
      replayId: replay.replay_id || "unknown-replay",
      records,
      code: LOCAL_KERNEL_ERROR_CODES.EVIDENCE_MALFORMED_INPUT,
      reason: "Replay result is malformed.",
    });
  }

  if (records.some((record) => !validateTraceShape(record))) {
    return failedPackage({
      replayId: replay.replay_id,
      records,
      code: LOCAL_KERNEL_ERROR_CODES.EVIDENCE_MALFORMED_INPUT,
      reason: "Trace records are malformed.",
    });
  }

  if (replay.status === "failed") {
    return failedPackage({
      replayId: replay.replay_id,
      records,
      code: LOCAL_KERNEL_ERROR_CODES.EVIDENCE_REPLAY_FAILED,
      reason: replay.metadata.failure_reason ?? "Replay failed.",
    });
  }

  if (replay.record_count !== records.length) {
    return incompletePackage({
      replayId: replay.replay_id,
      records,
      code: LOCAL_KERNEL_ERROR_CODES.EVIDENCE_COUNT_MISMATCH,
      reason: "Replay record_count does not match trace record count.",
    });
  }

  const sorted = [...records].sort((a, b) => a.sequence - b.sequence);
  const decisionIds = sorted.map((record) => record.decision_id);
  const intentIds = sorted.map((record) => record.intent_id);

  if (decisionIds.join("|") !== replay.decision_ids.join("|")) {
    return incompletePackage({
      replayId: replay.replay_id,
      records,
      code: LOCAL_KERNEL_ERROR_CODES.EVIDENCE_DECISION_ID_MISMATCH,
      reason: "Replay decision IDs do not match trace decision IDs.",
    });
  }

  if (intentIds.join("|") !== replay.intent_ids.join("|")) {
    return incompletePackage({
      replayId: replay.replay_id,
      records,
      code: LOCAL_KERNEL_ERROR_CODES.EVIDENCE_INTENT_ID_MISMATCH,
      reason: "Replay intent IDs do not match trace intent IDs.",
    });
  }

  try {
    const traceIds = sorted.map((record) => record.trace_id);
    const errorCodes = stableUnique([...replay.error_codes, ...sorted.flatMap((record) => record.error_codes)]);
    const invariantRefs = stableUniqueInvariant([
      ...replay.invariant_violation_refs,
      ...sorted.flatMap((record) => record.invariant_violations),
    ]);

    return deepFreeze({
      evidence_package_id: buildPackageId(replay.replay_id, records.length),
      status: "complete",
      decision_ids: decisionIds,
      intent_ids: intentIds,
      trace_ids: traceIds,
      replay_id: replay.replay_id,
      accepted_count: replay.accepted_count,
      rejected_count: replay.rejected_count,
      quarantined_count: replay.quarantined_count,
      error_codes: errorCodes,
      invariant_violation_refs: invariantRefs,
      metadata: {
        deterministic_key: [
          replay.replay_id,
          records.length,
          replay.accepted_count,
          replay.rejected_count,
          replay.quarantined_count,
          decisionIds.join(","),
          intentIds.join(","),
          traceIds.join(","),
          errorCodes.join(","),
          invariantRefs.join(","),
        ].join("|"),
      },
    });
  } catch {
    return failedPackage({
      replayId: replay.replay_id,
      records,
      code: LOCAL_KERNEL_ERROR_CODES.EVIDENCE_SUMMARY_FAILURE,
      reason: "Unable to produce deterministic evidence package.",
    });
  }
}
