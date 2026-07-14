export type NodeLifecycleState =
  | "initializing"
  | "standby"
  | "active"
  | "suspended"
  | "revoked"
  | "decommissioned";

export type NodeVerificationStatus =
  | "unverified"
  | "verified"
  | "failed"
  | "quarantined"
  | "revoked";

export type AuthorityOwnerRef = {
  authority_owner_id: string;
  authority_namespace: string;
  authority_type: "root-authority" | "delegated-authority" | "service-authority";
  explicit_ownership: true;
  authorized_at: string;
  human_authorization_ref: string;
};

export type FederationScopeRef = {
  federation_id: string;
  permitted_actions: readonly string[];
  permitted_resources: readonly string[];
  escalation_policy: "authority-approved" | "none";
  scope_description: string;
};

export type TrustBoundaryMetadata = {
  trust_boundary_id: string;
  trust_envelope_id: string;
  trust_scope: FederationScopeRef;
  valid_from: string;
  valid_until: string;
  enforcement_mode: "fail-closed";
  issued_by: AuthorityOwnerRef;
  reviewed_at: string;
};

export type NodeIdentity = {
  node_id: string;
  node_name: string;
  node_role: "sovereign" | "observer" | "auditor" | "validator";
  canonical_identity: string;
  created_at: string;
  authority_owner: AuthorityOwnerRef;
};

export type SovereignNode = {
  node_identity: NodeIdentity;
  lifecycle_state: NodeLifecycleState;
  verification_status: NodeVerificationStatus;
  authority_owner_ref: AuthorityOwnerRef;
  trust_boundary: TrustBoundaryMetadata;
  federation_scope_ref: FederationScopeRef;
  last_human_authorized_at: string;
  explicit_human_authorization_ref: string;
};
