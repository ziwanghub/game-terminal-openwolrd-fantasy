import { deepFreeze } from "./immutability.js";
import { LOCAL_KERNEL_ERROR_CODES } from "./errors.js";
import type {
  LocalEvidencePackage,
  LocalInvariantViolation,
  LocalRecoveryDiagnostic,
  LocalReplayResult,
  LocalTraceRecord,
} from "./types.js";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function uniqueSorted(values: string[]): string[] {
  return [...new Set(values)].sort();
}

function uniqueSortedInvariant(values: LocalInvariantViolation[]): LocalInvariantViolation[] {
  return [...new Set(values)].sort();
}

function cloneTraceRecord(record: LocalTraceRecord): LocalTraceRecord {
  return {
    ...record,
    error_codes: [...record.error_codes],
    invariant_violations: [...record.invariant_violations],
    metadata: { ...record.metadata },
  };
}

function cloneReplayResult(replay: LocalReplayResult): LocalReplayResult {
  return {
    ...replay,
    decision_ids: [...replay.decision_ids],
    intent_ids: [...replay.intent_ids],
    error_codes: [...replay.error_codes],
    invariant_violation_refs: [...replay.invariant_violation_refs],
    metadata: { ...replay.metadata },
  };
}

function cloneEvidencePackage(evidence: LocalEvidencePackage): LocalEvidencePackage {
  return {
    ...evidence,
    decision_ids: [...evidence.decision_ids],
    intent_ids: [...evidence.intent_ids],
    trace_ids: [...evidence.trace_ids],
    error_codes: [...evidence.error_codes],
    invariant_violation_refs: [...evidence.invariant_violation_refs],
    metadata: { ...evidence.metadata },
  };
}

function isTraceRecordLike(record: unknown): record is LocalTraceRecord {
  if (!isRecord(record)) return false;
  if (
    !isNonEmptyString(record.trace_id) ||
    typeof record.sequence !== "number" ||
    !isNonEmptyString(record.intent_id) ||
    !isNonEmptyString(record.decision_id) ||
    !isNonEmptyString(record.decision_status) ||
    !Array.isArray(record.error_codes) ||
    !Array.isArray(record.invariant_violations)
  ) {
    return false;
  }
  return true;
}

function failedDiagnostic(input: {
  replayStatus: LocalReplayResult["status"];
  evidenceStatus: LocalEvidencePackage["status"];
  recordCount: number;
  code: string;
  reason: string;
}): LocalRecoveryDiagnostic {
  return deepFreeze({
    recovery_id: "recovery-local-kernel-v1",
    status: "failed",
    record_count: input.recordCount,
    last_sequence: 0,
    replay_status: input.replayStatus,
    evidence_status: input.evidenceStatus,
    diagnostic_codes: [input.code],
    error_codes: [input.code],
    invariant_violation_refs: [],
    metadata: {
      deterministic_key: [
        "recovery-local-kernel-v1",
        "failed",
        input.code,
        input.replayStatus,
        input.evidenceStatus,
        input.recordCount,
      ].join("|"),
      reason: input.reason,
    },
  });
}

function analyzeSequence(records: readonly LocalTraceRecord[]): {
  lastSequence: number;
  malformed: boolean;
  invalidSequence: boolean;
} {
  if (records.some((r) => !isTraceRecordLike(r))) {
    return { lastSequence: 0, malformed: true, invalidSequence: false };
  }

  const sorted = [...records].sort((a, b) => a.sequence - b.sequence);
  let previous = 0;
  const seen = new Set<number>();

  for (const record of sorted) {
    if (!Number.isInteger(record.sequence) || record.sequence <= 0) {
      return { lastSequence: 0, malformed: false, invalidSequence: true };
    }
    if (seen.has(record.sequence)) {
      return { lastSequence: 0, malformed: false, invalidSequence: true };
    }
    if (previous !== 0 && record.sequence !== previous + 1) {
      return { lastSequence: 0, malformed: false, invalidSequence: true };
    }
    seen.add(record.sequence);
    previous = record.sequence;
  }

  return { lastSequence: sorted.length > 0 ? sorted[sorted.length - 1].sequence : 0, malformed: false, invalidSequence: false };
}

export function diagnoseLocalTraceRecovery(input: {
  trace_records: ReadonlyArray<LocalTraceRecord>;
  replay_result: LocalReplayResult;
  evidence_package: LocalEvidencePackage;
}): LocalRecoveryDiagnostic {
  if (!input || !Array.isArray(input.trace_records) || !input.replay_result || !input.evidence_package) {
    return failedDiagnostic({
      replayStatus: "failed",
      evidenceStatus: "failed",
      recordCount: 0,
      code: LOCAL_KERNEL_ERROR_CODES.RECOVERY_INPUT_MISSING,
      reason: "Required diagnostic input is missing.",
    });
  }

  let records: LocalTraceRecord[];
  let replay: LocalReplayResult;
  let evidence: LocalEvidencePackage;
  try {
    records = input.trace_records.map(cloneTraceRecord);
    replay = cloneReplayResult(input.replay_result);
    evidence = cloneEvidencePackage(input.evidence_package);
  } catch {
    return failedDiagnostic({
      replayStatus: "failed",
      evidenceStatus: "failed",
      recordCount: Array.isArray(input.trace_records) ? input.trace_records.length : 0,
      code: LOCAL_KERNEL_ERROR_CODES.RECOVERY_INPUT_MISSING,
      reason: "Required diagnostic input is malformed.",
    });
  }

  if (!isNonEmptyString(replay.replay_id) || !isNonEmptyString(evidence.evidence_package_id)) {
    return failedDiagnostic({
      replayStatus: replay.status ?? "failed",
      evidenceStatus: evidence.status ?? "failed",
      recordCount: records.length,
      code: LOCAL_KERNEL_ERROR_CODES.RECOVERY_INPUT_MISSING,
      reason: "Replay or evidence identifiers are missing.",
    });
  }

  try {
    const diagnostics: string[] = [LOCAL_KERNEL_ERROR_CODES.RECOVERY_REPAIR_PROHIBITED];
    const errors = uniqueSorted([...replay.error_codes, ...evidence.error_codes]);
    const invariantRefs = uniqueSortedInvariant([
      ...replay.invariant_violation_refs,
      ...evidence.invariant_violation_refs,
      ...records.flatMap((r) => r.invariant_violations),
    ]);

    const sequence = analyzeSequence(records);

    if (sequence.malformed) {
      diagnostics.push(LOCAL_KERNEL_ERROR_CODES.RECOVERY_TRACE_MALFORMED);
    }
    if (sequence.invalidSequence) {
      diagnostics.push(LOCAL_KERNEL_ERROR_CODES.RECOVERY_TRACE_SEQUENCE_INVALID);
    }
    if (replay.status === "failed") {
      diagnostics.push(LOCAL_KERNEL_ERROR_CODES.RECOVERY_REPLAY_FAILED);
    }
    if (evidence.status === "incomplete") {
      diagnostics.push(LOCAL_KERNEL_ERROR_CODES.RECOVERY_EVIDENCE_INCOMPLETE);
    }
    if (evidence.status === "failed") {
      diagnostics.push(LOCAL_KERNEL_ERROR_CODES.RECOVERY_EVIDENCE_FAILED);
    }

    const traceDecisionIds = records
      .slice()
      .sort((a, b) => a.sequence - b.sequence)
      .map((r) => r.decision_id)
      .join("|");
    const traceIntentIds = records
      .slice()
      .sort((a, b) => a.sequence - b.sequence)
      .map((r) => r.intent_id)
      .join("|");

    if (traceDecisionIds !== replay.decision_ids.join("|") || traceIntentIds !== replay.intent_ids.join("|")) {
      diagnostics.push(LOCAL_KERNEL_ERROR_CODES.RECOVERY_TRACE_SEQUENCE_INVALID);
    }

    if (records.length !== replay.record_count || records.length !== evidence.trace_ids.length) {
      diagnostics.push(LOCAL_KERNEL_ERROR_CODES.RECOVERY_TRACE_SEQUENCE_INVALID);
    }

    const status =
      diagnostics.includes(LOCAL_KERNEL_ERROR_CODES.RECOVERY_TRACE_MALFORMED) ||
      diagnostics.includes(LOCAL_KERNEL_ERROR_CODES.RECOVERY_INPUT_MISSING)
        ? "failed"
        : diagnostics.some((code) => code !== LOCAL_KERNEL_ERROR_CODES.RECOVERY_REPAIR_PROHIBITED)
          ? "blocked"
          : "recoverable";

    return deepFreeze({
      recovery_id: "recovery-local-kernel-v1",
      status,
      record_count: records.length,
      last_sequence: sequence.lastSequence,
      replay_status: replay.status,
      evidence_status: evidence.status,
      diagnostic_codes: uniqueSorted(diagnostics),
      error_codes: errors,
      invariant_violation_refs: invariantRefs,
      metadata: {
        deterministic_key: [
          "recovery-local-kernel-v1",
          status,
          records.length,
          sequence.lastSequence,
          replay.status,
          evidence.status,
          uniqueSorted(diagnostics).join(","),
          errors.join(","),
          invariantRefs.join(","),
        ].join("|"),
      },
    });
  } catch {
    return failedDiagnostic({
      replayStatus: replay.status,
      evidenceStatus: evidence.status,
      recordCount: records.length,
      code: LOCAL_KERNEL_ERROR_CODES.RECOVERY_SUMMARY_FAILURE,
      reason: "Unable to produce deterministic recovery diagnostic summary.",
    });
  }
}
