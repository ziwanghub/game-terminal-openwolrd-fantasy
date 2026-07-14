export type MembershipState =
  | "joining"
  | "active"
  | "suspended"
  | "revoked"
  | "recovering"
  | "leaving"
  | "left";

export type MembershipVerificationStatus =
  | "pending"
  | "verified"
  | "failed"
  | "quarantined"
  | "revoked";

export type MembershipTransitionReason =
  | "authority-approved"
  | "policy-violation"
  | "voluntary-leave"
  | "recovery"
  | "suspension"
  | "revocation"
  | "disciplinary-action";

export type MembershipAuthorityRef = {
  authority_owner_id: string;
  authority_namespace: string;
  authority_type: "root-authority" | "delegated-authority" | "service-authority";
  explicit_ownership: true;
  approved_at: string;
  human_authorization_ref: string;
  approval_policy: string;
};

export type MembershipScopeRef = {
  federation_id: string;
  permitted_actions: readonly string[];
  permitted_resources: readonly string[];
  escalation_policy: "authority-approved" | "none";
  scope_description: string;
  scope_boundary_ref?: string;
};

export type MembershipEvidenceRef = {
  evidence_id: string;
  evidence_type:
    | "audit"
    | "review"
    | "suspension-notice"
    | "revocation-notice"
    | "membership-change";
  recorded_at: string;
  recorded_by: MembershipAuthorityRef;
  trace_reference: string;
  summary?: string;
};

export type MembershipSubjectRef = {
  node_id: string;
  node_namespace: string;
  node_role: "sovereign" | "observer" | "auditor" | "validator" | "participant";
  canonical_identity: string;
  joined_at: string;
  authority_owner_ref: MembershipAuthorityRef;
};

export type MembershipLifecycleMetadata = {
  created_at: string;
  last_updated_at: string;
  approved_at?: string;
  suspended_at?: string;
  revoked_at?: string;
  leaving_at?: string;
  left_at?: string;
  review_notes?: string;
};

export type MembershipTransition = {
  transition_id: string;
  from_state: MembershipState;
  to_state: MembershipState;
  reason: MembershipTransitionReason;
  authorized_by: MembershipAuthorityRef;
  authorized_at: string;
  evidence: MembershipEvidenceRef;
  scope_context: MembershipScopeRef;
};

export type FederationMembership = {
  membership_id: string;
  membership_state: MembershipState;
  verification_status: MembershipVerificationStatus;
  subject: MembershipSubjectRef;
  authority_ref: MembershipAuthorityRef;
  scope_ref: MembershipScopeRef;
  evidence_refs: readonly MembershipEvidenceRef[];
  lifecycle_metadata: MembershipLifecycleMetadata;
  transitions: readonly MembershipTransition[];
  governance_relationship: "trust" | "delegation";
  allowed_actions: readonly string[];
  permitted_resources: readonly string[];
};
