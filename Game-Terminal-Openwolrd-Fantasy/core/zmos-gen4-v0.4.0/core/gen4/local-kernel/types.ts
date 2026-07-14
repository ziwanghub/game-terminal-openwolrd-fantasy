export type LocalIntent = {
  intent_id: string;
  subject_ref: string;
  issuer_ref: string;
  requested_action: string;
  requested_resource: string;
  human_authorization_ref: string;
  trust_envelope_ref: string;
  metadata: Readonly<{
    submitted_at: string;
    trace_correlation_id: string;
    replay_nonce: string;
    ambiguous_verification?: boolean;
  }>;
};

export type LocalDecisionStatus = "accepted" | "rejected" | "quarantined";

export type LocalInvariantViolation =
  | "MALFORMED_INTENT"
  | "MISSING_SUBJECT_REF"
  | "MISSING_ISSUER_REF"
  | "MISSING_HUMAN_AUTHORIZATION"
  | "MISSING_TRUST_ENVELOPE_REF"
  | "TRUST_ENVELOPE_MISSING"
  | "TRUST_ENVELOPE_INVALID"
  | "TRUST_ENVELOPE_REF_MISMATCH"
  | "TRUST_SCOPE_VIOLATION"
  | "INVALID_ACTION_SCOPE"
  | "AMBIGUOUS_VERIFICATION"
  | "TRACE_APPEND_FAILURE";

export type LocalDecisionResult = {
  decision_id: string;
  intent_id: string;
  status: LocalDecisionStatus;
  error_codes: readonly string[];
  invariant_violations: readonly LocalInvariantViolation[];
  trust_envelope_ref?: string;
  metadata: Readonly<{
    decided_at: string;
    execution_mode: "mock-only";
    deterministic_key: string;
  }>;
};

export type LocalHarnessOptions = {
  trust_envelope?: unknown;
  trace_writer?: LocalTraceWriter;
  allow_actions?: readonly string[];
  allow_resources?: readonly string[];
  now?: () => string;
};

export type LocalTraceRecord = {
  trace_id: string;
  sequence: number;
  timestamp: string;
  intent_id: string;
  decision_id: string;
  decision_status: LocalDecisionStatus;
  subject_ref: string;
  issuer_ref: string;
  trust_envelope_ref: string;
  error_codes: readonly string[];
  invariant_violations: readonly LocalInvariantViolation[];
  metadata: Readonly<{
    deterministic_key: string;
    trace_correlation_id: string;
    replay_nonce: string;
  }>;
};

export type LocalTraceWriter = {
  appendTraceRecord(input: {
    timestamp: string;
    intent: LocalIntent;
    decision: LocalDecisionResult;
  }): LocalTraceRecord;
  listTraceRecords(): readonly LocalTraceRecord[];
};

export type LocalReplayStatus = "completed" | "failed";

export type LocalReplayResult = {
  replay_id: string;
  status: LocalReplayStatus;
  record_count: number;
  accepted_count: number;
  rejected_count: number;
  quarantined_count: number;
  last_sequence: number;
  decision_ids: readonly string[];
  intent_ids: readonly string[];
  error_codes: readonly string[];
  invariant_violation_refs: readonly LocalInvariantViolation[];
  metadata: Readonly<{
    deterministic_key: string;
    failure_reason?: string;
  }>;
};

export type LocalEvidencePackageStatus = "complete" | "incomplete" | "failed";

export type LocalEvidencePackage = {
  evidence_package_id: string;
  status: LocalEvidencePackageStatus;
  decision_ids: readonly string[];
  intent_ids: readonly string[];
  trace_ids: readonly string[];
  replay_id: string;
  accepted_count: number;
  rejected_count: number;
  quarantined_count: number;
  error_codes: readonly string[];
  invariant_violation_refs: readonly LocalInvariantViolation[];
  metadata: Readonly<{
    deterministic_key: string;
    reason?: string;
  }>;
};

export type LocalRecoveryStatus = "recoverable" | "blocked" | "failed";

export type LocalRecoveryDiagnostic = {
  recovery_id: string;
  status: LocalRecoveryStatus;
  record_count: number;
  last_sequence: number;
  replay_status: LocalReplayStatus;
  evidence_status: LocalEvidencePackageStatus;
  diagnostic_codes: readonly string[];
  error_codes: readonly string[];
  invariant_violation_refs: readonly LocalInvariantViolation[];
  metadata: Readonly<{
    deterministic_key: string;
    reason?: string;
  }>;
};
