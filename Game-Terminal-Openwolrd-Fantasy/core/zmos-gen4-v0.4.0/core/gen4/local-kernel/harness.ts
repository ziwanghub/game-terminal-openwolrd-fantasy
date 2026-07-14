import {
  LOCAL_KERNEL_ERROR_CODES,
  LocalKernelValidationError,
} from "./errors.js";
import { createLocalDecisionResult } from "./decision.js";
import {
  TrustEnvelopeValidationError,
  validateTrustEnvelope,
} from "../trust-envelope/index.js";
import type {
  LocalDecisionResult,
  LocalHarnessOptions,
  LocalIntent,
  LocalInvariantViolation,
} from "./types.js";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function toIsoNow(now?: () => string): string {
  const current = now ? now() : new Date().toISOString();
  return current;
}

function emitTraceOrFailClosed(params: {
  intent: LocalIntent;
  decision: LocalDecisionResult;
  options: LocalHarnessOptions;
}): LocalDecisionResult {
  const { intent, decision, options } = params;
  if (!options.trace_writer) {
    return decision;
  }

  try {
    options.trace_writer.appendTraceRecord({
      timestamp: decision.metadata.decided_at,
      intent,
      decision,
    });
    return decision;
  } catch {
    return createLocalDecisionResult({
      intent,
      status: "rejected",
      error_codes: [LOCAL_KERNEL_ERROR_CODES.TRACE_APPEND_FAILURE],
      invariant_violations: ["TRACE_APPEND_FAILURE"],
      decided_at: toIsoNow(options.now),
    });
  }
}

export function validateLocalIntent(input: unknown): LocalIntent {
  if (!isRecord(input)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.MALFORMED_INTENT,
      "Local intent must be an object.",
    );
  }

  if (!nonEmptyString(input.intent_id)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.MALFORMED_INTENT,
      "intent_id must be a non-empty string.",
    );
  }

  if (!nonEmptyString(input.subject_ref)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.MISSING_SUBJECT_REF,
      "subject_ref must be a non-empty string.",
    );
  }

  if (!nonEmptyString(input.issuer_ref)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.MISSING_ISSUER_REF,
      "issuer_ref must be a non-empty string.",
    );
  }

  if (!nonEmptyString(input.requested_action) || !nonEmptyString(input.requested_resource)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.MALFORMED_INTENT,
      "requested_action and requested_resource must be non-empty strings.",
    );
  }

  if (!nonEmptyString(input.human_authorization_ref)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.MISSING_HUMAN_AUTHORIZATION,
      "human_authorization_ref is required under fail-closed policy.",
    );
  }

  if (!nonEmptyString(input.trust_envelope_ref)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.MISSING_TRUST_ENVELOPE_REF,
      "trust_envelope_ref must be a non-empty string.",
    );
  }

  if (!isRecord(input.metadata)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.MALFORMED_INTENT,
      "metadata must be an object.",
    );
  }

  if (
    !nonEmptyString(input.metadata.submitted_at) ||
    !nonEmptyString(input.metadata.trace_correlation_id) ||
    !nonEmptyString(input.metadata.replay_nonce)
  ) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.MALFORMED_INTENT,
      "metadata.submitted_at, metadata.trace_correlation_id, and metadata.replay_nonce are required.",
    );
  }

  return input as LocalIntent;
}

function buildRejection(
  intent: Pick<LocalIntent, "intent_id" | "trust_envelope_ref">,
  code: string,
  violation: LocalInvariantViolation,
  now?: () => string,
): LocalDecisionResult {
  return createLocalDecisionResult({
    intent,
    status: "rejected",
    error_codes: [code],
    invariant_violations: [violation],
    decided_at: toIsoNow(now),
  });
}

function enforceTrustEnvelope(intent: LocalIntent, envelopeInput: unknown): void {
  if (!isRecord(envelopeInput)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.TRUST_ENVELOPE_MISSING,
      "Trust envelope context is required for local execution.",
    );
  }

  let envelope;
  try {
    envelope = validateTrustEnvelope(envelopeInput);
  } catch (error) {
    if (error instanceof TrustEnvelopeValidationError) {
      throw new LocalKernelValidationError(
        LOCAL_KERNEL_ERROR_CODES.TRUST_ENVELOPE_INVALID,
        `Trust envelope validation failed: ${error.code}`,
      );
    }
    throw error;
  }

  if (intent.trust_envelope_ref !== envelope.trust_envelope_id) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.TRUST_ENVELOPE_REF_MISMATCH,
      "Intent trust_envelope_ref does not match provided trust envelope.",
    );
  }

  if (!envelope.federation_scope.permitted_actions.includes(intent.requested_action)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.TRUST_SCOPE_VIOLATION,
      "Requested action is outside trust envelope scope.",
    );
  }

  if (!envelope.federation_scope.permitted_resources.includes(intent.requested_resource)) {
    throw new LocalKernelValidationError(
      LOCAL_KERNEL_ERROR_CODES.TRUST_SCOPE_VIOLATION,
      "Requested resource is outside trust envelope scope.",
    );
  }
}

export function runLocalIntent(
  input: unknown,
  options: LocalHarnessOptions = {},
): LocalDecisionResult {
  const now = options.now;
  let validatedIntent: LocalIntent | null = null;

  try {
    const intent = validateLocalIntent(input);
    validatedIntent = intent;

    if (intent.metadata.ambiguous_verification === true) {
      const decision = createLocalDecisionResult({
        intent,
        status: "quarantined",
        error_codes: [LOCAL_KERNEL_ERROR_CODES.AMBIGUOUS_VERIFICATION],
        invariant_violations: ["AMBIGUOUS_VERIFICATION"],
        decided_at: toIsoNow(now),
      });
      return emitTraceOrFailClosed({ intent, decision, options });
    }

    enforceTrustEnvelope(intent, options.trust_envelope);

    if (
      options.allow_actions &&
      options.allow_actions.length > 0 &&
      !options.allow_actions.includes(intent.requested_action)
    ) {
      const decision = buildRejection(
        intent,
        LOCAL_KERNEL_ERROR_CODES.INVALID_ACTION_SCOPE,
        "INVALID_ACTION_SCOPE",
        now,
      );
      return emitTraceOrFailClosed({ intent, decision, options });
    }

    if (
      options.allow_resources &&
      options.allow_resources.length > 0 &&
      !options.allow_resources.includes(intent.requested_resource)
    ) {
      const decision = buildRejection(
        intent,
        LOCAL_KERNEL_ERROR_CODES.INVALID_ACTION_SCOPE,
        "INVALID_ACTION_SCOPE",
        now,
      );
      return emitTraceOrFailClosed({ intent, decision, options });
    }

    const decision = createLocalDecisionResult({
      intent,
      status: "accepted",
      decided_at: toIsoNow(now),
    });
    return emitTraceOrFailClosed({ intent, decision, options });
  } catch (error) {
    if (error instanceof LocalKernelValidationError) {
      const fallbackIntentId =
        isRecord(input) && nonEmptyString(input.intent_id) ? input.intent_id : "unknown-intent";
      const fallbackTrustRef =
        isRecord(input) && nonEmptyString(input.trust_envelope_ref)
          ? input.trust_envelope_ref
          : "unknown-trust-envelope";

      const codeToViolation: Record<string, LocalInvariantViolation> = {
        [LOCAL_KERNEL_ERROR_CODES.MALFORMED_INTENT]: "MALFORMED_INTENT",
        [LOCAL_KERNEL_ERROR_CODES.MISSING_SUBJECT_REF]: "MISSING_SUBJECT_REF",
        [LOCAL_KERNEL_ERROR_CODES.MISSING_ISSUER_REF]: "MISSING_ISSUER_REF",
        [LOCAL_KERNEL_ERROR_CODES.MISSING_HUMAN_AUTHORIZATION]: "MISSING_HUMAN_AUTHORIZATION",
        [LOCAL_KERNEL_ERROR_CODES.MISSING_TRUST_ENVELOPE_REF]: "MISSING_TRUST_ENVELOPE_REF",
        [LOCAL_KERNEL_ERROR_CODES.TRUST_ENVELOPE_MISSING]: "TRUST_ENVELOPE_MISSING",
        [LOCAL_KERNEL_ERROR_CODES.TRUST_ENVELOPE_INVALID]: "TRUST_ENVELOPE_INVALID",
        [LOCAL_KERNEL_ERROR_CODES.TRUST_ENVELOPE_REF_MISMATCH]: "TRUST_ENVELOPE_REF_MISMATCH",
        [LOCAL_KERNEL_ERROR_CODES.TRUST_SCOPE_VIOLATION]: "TRUST_SCOPE_VIOLATION",
        [LOCAL_KERNEL_ERROR_CODES.INVALID_ACTION_SCOPE]: "INVALID_ACTION_SCOPE",
        [LOCAL_KERNEL_ERROR_CODES.AMBIGUOUS_VERIFICATION]: "AMBIGUOUS_VERIFICATION",
      };

      const intentForDecision: LocalIntent = validatedIntent ?? {
        intent_id: fallbackIntentId,
        subject_ref: "unknown-subject",
        issuer_ref: "unknown-issuer",
        requested_action: "unknown-action",
        requested_resource: "unknown-resource",
        human_authorization_ref: "unknown-human-auth",
        trust_envelope_ref: fallbackTrustRef,
        metadata: {
          submitted_at: toIsoNow(now),
          trace_correlation_id: "unknown-trace-correlation",
          replay_nonce: "unknown-replay-nonce",
        },
      };

      const decision = createLocalDecisionResult({
        intent: {
          intent_id: intentForDecision.intent_id,
          trust_envelope_ref: intentForDecision.trust_envelope_ref,
        },
        status: "rejected",
        error_codes: [error.code],
        invariant_violations: [codeToViolation[error.code] ?? "MALFORMED_INTENT"],
        decided_at: toIsoNow(now),
      });
      return emitTraceOrFailClosed({ intent: intentForDecision, decision, options });
    }

    throw error;
  }
}
