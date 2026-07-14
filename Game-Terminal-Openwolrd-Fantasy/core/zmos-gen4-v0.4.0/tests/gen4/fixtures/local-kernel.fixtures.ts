import { runLocalIntent } from "../../../core/gen4/local-kernel/harness.ts";
import { createLocalTraceWriter } from "../../../core/gen4/local-kernel/trace.ts";
import { replayLocalTraceRecords } from "../../../core/gen4/local-kernel/replay.ts";
import { buildLocalEvidencePackage } from "../../../core/gen4/local-kernel/evidence.ts";
import { diagnoseLocalTraceRecovery } from "../../../core/gen4/local-kernel/recovery.ts";
import type {
  LocalDecisionResult,
  LocalEvidencePackage,
  LocalIntent,
  LocalRecoveryDiagnostic,
  LocalReplayResult,
  LocalTraceRecord,
} from "../../../core/gen4/local-kernel/types.ts";
import {
  buildExpiredTrustEnvelope,
  buildValidTrustEnvelope,
} from "./trust-envelope.fixtures.ts";

type LocalIntentOverride = Partial<LocalIntent> & {
  metadata?: Partial<LocalIntent["metadata"]>;
};

function mergeIntent(overrides: LocalIntentOverride = {}): LocalIntent {
  const base = createValidLocalIntentFixture();
  return {
    ...base,
    ...overrides,
    metadata: {
      ...base.metadata,
      ...(overrides.metadata ?? {}),
    },
  };
}

export function createValidLocalIntentFixture(overrides: LocalIntentOverride = {}): LocalIntent {
  return {
    intent_id: "intent-fixture-001",
    subject_ref: "subject-fixture-001",
    issuer_ref: "issuer-fixture-001",
    requested_action: "read",
    requested_resource: "truth",
    human_authorization_ref: "human-auth-fixture-001",
    trust_envelope_ref: "envelope-001",
    metadata: {
      submitted_at: "2026-05-28T00:00:00Z",
      trace_correlation_id: "trace-corr-fixture-001",
      replay_nonce: "replay-fixture-001",
    },
    ...overrides,
    metadata: {
      submitted_at: "2026-05-28T00:00:00Z",
      trace_correlation_id: "trace-corr-fixture-001",
      replay_nonce: "replay-fixture-001",
      ...(overrides.metadata ?? {}),
    },
  };
}

export function createInvalidLocalIntentFixture(overrides: LocalIntentOverride = {}): unknown {
  return {
    ...mergeIntent(overrides),
    intent_id: "",
  };
}

export function createIntentWithoutHumanAuthorizationFixture(
  overrides: LocalIntentOverride = {},
): LocalIntent {
  return mergeIntent({
    ...overrides,
    human_authorization_ref: "",
  });
}

export function createOutOfScopeIntentFixture(overrides: LocalIntentOverride = {}): LocalIntent {
  return mergeIntent({
    ...overrides,
    requested_action: "delete",
  });
}

export function createAmbiguousVerificationIntentFixture(
  overrides: LocalIntentOverride = {},
): LocalIntent {
  return mergeIntent({
    ...overrides,
    metadata: {
      ...overrides.metadata,
      ambiguous_verification: true,
    },
  });
}

export function createValidTrustEnvelopeForIntentFixture(): ReturnType<typeof buildValidTrustEnvelope> {
  return buildValidTrustEnvelope();
}

export function createTrustEnvelopeWithLimitedScopeFixture() {
  const envelope = buildValidTrustEnvelope();
  envelope.federation_scope = {
    ...envelope.federation_scope,
    permitted_actions: ["read"],
    permitted_resources: ["truth"],
  };
  return envelope;
}

export function createMismatchedTrustEnvelopeFixture() {
  const envelope = buildValidTrustEnvelope();
  envelope.trust_envelope_id = "envelope-mismatch-001";
  return envelope;
}

export function createInvalidTrustEnvelopeFixture() {
  return buildExpiredTrustEnvelope();
}

export function runLocalKernelScenarioFixture(input?: {
  intent?: unknown;
  trust_envelope?: unknown;
  now?: () => string;
}): {
  decision: LocalDecisionResult;
  trace_records: readonly LocalTraceRecord[];
  replay_result: LocalReplayResult;
  evidence_package: LocalEvidencePackage;
  recovery_diagnostic: LocalRecoveryDiagnostic;
} {
  const now = input?.now ?? (() => "2026-05-28T00:00:00Z");
  const traceWriter = createLocalTraceWriter();
  const intent = input?.intent ?? createValidLocalIntentFixture();
  const trustEnvelope = input?.trust_envelope ?? createValidTrustEnvelopeForIntentFixture();

  const decision = runLocalIntent(intent, {
    trust_envelope: trustEnvelope,
    trace_writer: traceWriter,
    now,
  });

  const traceRecords = traceWriter.listTraceRecords();
  const replayResult = replayLocalTraceRecords(traceRecords);
  const evidencePackage = buildLocalEvidencePackage({
    trace_records: traceRecords,
    replay_result: replayResult,
  });
  const recoveryDiagnostic = diagnoseLocalTraceRecovery({
    trace_records: traceRecords,
    replay_result: replayResult,
    evidence_package: evidencePackage,
  });

  return {
    decision,
    trace_records: traceRecords,
    replay_result: replayResult,
    evidence_package: evidencePackage,
    recovery_diagnostic: recoveryDiagnostic,
  };
}

export function extractDecisionSummary(decision: LocalDecisionResult) {
  return {
    status: decision.status,
    error_codes: [...decision.error_codes],
    invariant_violations: [...decision.invariant_violations],
  };
}

export function extractTraceSummary(traceRecords: readonly LocalTraceRecord[]) {
  return {
    count: traceRecords.length,
    statuses: traceRecords.map((record) => record.decision_status),
    sequences: traceRecords.map((record) => record.sequence),
  };
}

export function extractReplaySummary(replay: LocalReplayResult) {
  return {
    status: replay.status,
    record_count: replay.record_count,
    accepted_count: replay.accepted_count,
    rejected_count: replay.rejected_count,
    quarantined_count: replay.quarantined_count,
    error_codes: [...replay.error_codes],
  };
}

export function extractEvidenceSummary(evidence: LocalEvidencePackage) {
  return {
    status: evidence.status,
    accepted_count: evidence.accepted_count,
    rejected_count: evidence.rejected_count,
    quarantined_count: evidence.quarantined_count,
    error_codes: [...evidence.error_codes],
  };
}

export function extractRecoverySummary(recovery: LocalRecoveryDiagnostic) {
  return {
    status: recovery.status,
    diagnostic_codes: [...recovery.diagnostic_codes],
    error_codes: [...recovery.error_codes],
    invariant_violation_refs: [...recovery.invariant_violation_refs],
  };
}
