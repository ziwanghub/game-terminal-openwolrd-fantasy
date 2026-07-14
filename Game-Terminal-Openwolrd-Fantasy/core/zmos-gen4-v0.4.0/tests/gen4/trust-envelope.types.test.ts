import test from "node:test";
import assert from "node:assert/strict";
import type {
  DelegatedAuthorityRef,
  FederationScope,
  IssuerAuthorityRef,
  TrustEnvelope,
  TrustEnvelopeId,
  TrustEnvelopeLifecycleState,
  TrustEnvelopeSignatureMetadata,
  TrustEnvelopeVersion,
  TrustRevocationRef,
  TrustVerificationPolicy,
} from "../../core/gen4/trust-envelope/index.ts";

const exampleIssuer: IssuerAuthorityRef = {
  authority_owner_id: "issuer-001",
  authority_namespace: "sovereignty-root",
  authority_type: "root-authority",
  explicit_ownership: true,
  authorized_at: "2026-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-001",
};

const exampleScope: FederationScope = {
  federation_id: "federation-001",
  permitted_actions: ["read", "validate"],
  permitted_resources: ["truth", "membership"],
  escalation_policy: "authority-approved",
  scope_description: "Core governance trust scope for Phase 1.",
};

const exampleVerificationPolicy: TrustVerificationPolicy = {
  verification_mode: "fail-closed",
  required_authority_types: ["root-authority", "delegated-authority"],
  require_human_authorization: true,
  allow_delegated_authority: true,
  accepted_scope: exampleScope,
};

const exampleDelegatedAuthority: DelegatedAuthorityRef = {
  delegate_id: "delegate-001",
  delegate_namespace: "sovereignty-delegation",
  delegate_type: "delegated-authority",
  explicit_ownership: true,
  delegated_by: exampleIssuer,
  delegated_at: "2026-05-28T00:00:00Z",
  expires_at: "2026-11-28T00:00:00Z",
  delegation_policy: "restricted",
  authorized_scopes: [exampleScope],
  human_authorization_ref: "human-auth-002",
};

const exampleSignature: TrustEnvelopeSignatureMetadata = {
  signature_id: "sig-001",
  signed_at: "2026-05-28T00:00:00Z",
  signer_authority: exampleIssuer,
  signature_scheme: "placeholder",
  signature_reference: "sig-ref-001",
  verification_policy: exampleVerificationPolicy,
};

const exampleRevocation: TrustRevocationRef = {
  revocation_id: "rev-001",
  revoked_at: "2026-06-01T00:00:00Z",
  revoked_by: exampleIssuer,
  revocation_reason: "authority withdrawal",
  trace_reference: "trace-001",
};

const exampleEnvelope: TrustEnvelope = {
  trust_envelope_id: "envelope-001" as TrustEnvelopeId,
  version: "1.0" as TrustEnvelopeVersion,
  lifecycle_state: "active" as TrustEnvelopeLifecycleState,
  issuer: exampleIssuer,
  delegated_authority: exampleDelegatedAuthority,
  federation_scope: exampleScope,
  verification_policy: exampleVerificationPolicy,
  revocation_ref: exampleRevocation,
  signature: exampleSignature,
  issued_at: "2026-05-28T00:00:00Z",
  valid_from: "2026-05-28T00:00:00Z",
  valid_until: "2027-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-003",
};

// @ts-expect-error: invalid lifecycle state should be rejected by type system
const invalidLifecycle: TrustEnvelopeLifecycleState = "unknown";

// @ts-expect-error: hidden authority type is not allowed
const invalidAuthorityType: IssuerAuthorityRef = {
  authority_owner_id: "issuer-002",
  authority_namespace: "sovereignty-root",
  authority_type: "hidden-authority",
  explicit_ownership: true,
  authorized_at: "2026-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-004",
};

// @ts-expect-error: invalid delegation_policy must be rejected
const invalidDelegationPolicy: DelegatedAuthorityRef = {
  delegate_id: "delegate-002",
  delegate_namespace: "sovereignty-delegation",
  delegate_type: "delegated-authority",
  explicit_ownership: true,
  delegated_by: exampleIssuer,
  delegated_at: "2026-05-28T00:00:00Z",
  expires_at: "2026-11-28T00:00:00Z",
  delegation_policy: "self-authorized",
  authorized_scopes: [exampleScope],
  human_authorization_ref: "human-auth-005",
};

// @ts-expect-error: trust verification policy must be fail-closed
const invalidVerificationPolicy: TrustVerificationPolicy = {
  verification_mode: "soft-fail",
  required_authority_types: ["root-authority"],
  require_human_authorization: true,
  allow_delegated_authority: true,
  accepted_scope: exampleScope,
};

const assertEnvelope = (envelope: TrustEnvelope): void => {
  assert.equal(envelope.lifecycle_state, "active");
  assert.equal(envelope.issuer.authority_type, "root-authority");
  assert.equal(envelope.verification_policy.verification_mode, "fail-closed");
  assert.equal(envelope.federation_scope.escalation_policy, "authority-approved");
};

test("TrustEnvelope type shape is valid", () => {
  assertEnvelope(exampleEnvelope);
  assert.equal(exampleEnvelope.revocation_ref?.revocation_reason, "authority withdrawal");
  assert.equal(exampleEnvelope.signature.signature_scheme, "placeholder");
});

test("Explicit authority ownership is required", () => {
  assert.equal(exampleIssuer.explicit_ownership, true);
  assert.equal(exampleDelegatedAuthority.explicit_ownership, true);
});
