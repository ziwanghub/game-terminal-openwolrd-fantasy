export type TrustEnvelopeId = string;
export type TrustEnvelopeVersion = string;

export type TrustEnvelopeLifecycleState =
  | "draft"
  | "issued"
  | "active"
  | "suspended"
  | "revoked"
  | "expired";

export type IssuerAuthorityRef = {
  authority_owner_id: string;
  authority_namespace: string;
  authority_type: "root-authority" | "delegated-authority";
  explicit_ownership: true;
  authorized_at: string;
  human_authorization_ref: string;
};

export type DelegatedAuthorityRef = {
  delegate_id: string;
  delegate_namespace: string;
  delegate_type: "delegated-authority";
  explicit_ownership: true;
  delegated_by: IssuerAuthorityRef;
  delegated_at: string;
  expires_at: string;
  delegation_policy: "restricted" | "scoped" | "none";
  authorized_scopes: FederationScope[];
  human_authorization_ref: string;
};

export type FederationScope = {
  federation_id: string;
  permitted_actions: readonly string[];
  permitted_resources: readonly string[];
  escalation_policy: "authority-approved" | "none";
  scope_description: string;
};

export type TrustVerificationPolicy = {
  verification_mode: "fail-closed";
  required_authority_types: ReadonlyArray<"root-authority" | "delegated-authority">;
  require_human_authorization: true;
  allow_delegated_authority: boolean;
  accepted_scope: FederationScope;
  accepted_truth_lineage_reference?: string;
};

export type TrustRevocationRef = {
  revocation_id: string;
  revoked_at: string;
  revoked_by: IssuerAuthorityRef | DelegatedAuthorityRef;
  revocation_reason: string;
  trace_reference: string;
};

export type TrustEnvelopeSignatureMetadata = {
  signature_id: string;
  signed_at: string;
  signer_authority: IssuerAuthorityRef | DelegatedAuthorityRef;
  signature_scheme: "placeholder";
  signature_reference: string;
  verification_policy: TrustVerificationPolicy;
};

export type TrustEnvelope = {
  trust_envelope_id: TrustEnvelopeId;
  version: TrustEnvelopeVersion;
  lifecycle_state: TrustEnvelopeLifecycleState;
  issuer: IssuerAuthorityRef;
  delegated_authority?: DelegatedAuthorityRef;
  federation_scope: FederationScope;
  verification_policy: TrustVerificationPolicy;
  revocation_ref?: TrustRevocationRef;
  signature: TrustEnvelopeSignatureMetadata;
  issued_at: string;
  valid_from: string;
  valid_until: string;
  human_authorization_ref: string;
};
