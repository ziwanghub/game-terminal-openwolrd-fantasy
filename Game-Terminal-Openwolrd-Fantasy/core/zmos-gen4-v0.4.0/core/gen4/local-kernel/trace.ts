import type {
  LocalDecisionResult,
  LocalIntent,
  LocalTraceRecord,
  LocalTraceWriter,
} from "./types.js";
import { LocalKernelValidationError, LOCAL_KERNEL_ERROR_CODES } from "./errors.js";
import { deepFreeze } from "./immutability.js";

function toTraceRecord(input: {
  sequence: number;
  timestamp: string;
  intent: LocalIntent;
  decision: LocalDecisionResult;
}): LocalTraceRecord {
  const { sequence, timestamp, intent, decision } = input;

  if (sequence <= 0) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.TRACE_APPEND_FAILURE,
      "Trace sequence must be positive and monotonic.",
    );
  }

  return deepFreeze({
    trace_id: `trace-${String(sequence).padStart(6, "0")}`,
    sequence,
    timestamp,
    intent_id: intent.intent_id,
    decision_id: decision.decision_id,
    decision_status: decision.status,
    subject_ref: intent.subject_ref,
    issuer_ref: intent.issuer_ref,
    trust_envelope_ref: decision.trust_envelope_ref ?? intent.trust_envelope_ref,
    error_codes: [...decision.error_codes],
    invariant_violations: [...decision.invariant_violations],
    metadata: {
      deterministic_key: [
        sequence,
        timestamp,
        intent.intent_id,
        decision.decision_id,
        decision.status,
      ].join("|"),
      trace_correlation_id: intent.metadata.trace_correlation_id,
      replay_nonce: intent.metadata.replay_nonce,
    },
  });
}

export function createLocalTraceWriter(): LocalTraceWriter {
  const records: LocalTraceRecord[] = [];
  let sequence = 0;

  return {
    appendTraceRecord(input) {
      sequence += 1;
      const record = toTraceRecord({
        sequence,
        timestamp: input.timestamp,
        intent: input.intent,
        decision: input.decision,
      });
      records.push(record);
      return deepFreeze({
        ...record,
        error_codes: [...record.error_codes],
        invariant_violations: [...record.invariant_violations],
        metadata: { ...record.metadata },
      });
    },
    listTraceRecords() {
      return deepFreeze(
        records.map((record) =>
          deepFreeze({
            ...record,
            error_codes: [...record.error_codes],
            invariant_violations: [...record.invariant_violations],
            metadata: { ...record.metadata },
          }),
        ),
      );
    },
  };
}
