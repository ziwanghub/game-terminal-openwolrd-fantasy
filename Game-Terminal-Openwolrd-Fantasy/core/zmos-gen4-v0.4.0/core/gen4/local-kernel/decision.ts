import type {
  LocalDecisionResult,
  LocalDecisionStatus,
  LocalInvariantViolation,
  LocalIntent,
} from "./types.js";
import { deepFreeze } from "./immutability.js";

export function createLocalDecisionResult(input: {
  intent: Pick<LocalIntent, "intent_id" | "trust_envelope_ref">;
  status: LocalDecisionStatus;
  error_codes?: string[];
  invariant_violations?: LocalInvariantViolation[];
  decided_at: string;
}): LocalDecisionResult {
  const errorCodes = input.error_codes ?? [];
  const violations = input.invariant_violations ?? [];

  if (input.status === "accepted" && (errorCodes.length > 0 || violations.length > 0)) {
    throw new Error("Accepted decisions cannot contain error codes or invariant violations.");
  }

  const deterministicKey = [
    input.intent.intent_id,
    input.status,
    input.decided_at,
    input.intent.trust_envelope_ref,
  ].join("|");

  return deepFreeze({
    decision_id: `decision-${input.intent.intent_id}`,
    intent_id: input.intent.intent_id,
    status: input.status,
    error_codes: [...errorCodes],
    invariant_violations: [...violations],
    trust_envelope_ref: input.intent.trust_envelope_ref,
    metadata: {
      decided_at: input.decided_at,
      execution_mode: "mock-only",
      deterministic_key: deterministicKey,
    },
  });
}
