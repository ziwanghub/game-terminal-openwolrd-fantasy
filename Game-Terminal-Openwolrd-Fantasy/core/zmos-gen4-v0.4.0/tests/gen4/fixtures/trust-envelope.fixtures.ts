import type {
  TrustEnvelope,
  TrustVerificationPolicy,
  FederationScope,
  IssuerAuthorityRef,
  DelegatedAuthorityRef,
  TrustEnvelopeSignatureMetadata,
  TrustRevocationRef,
} from "../../core/gen4/trust-envelope/index.ts";

const issuerAuthority: IssuerAuthorityRef = {
  authority_owner_id: "auth-001",
  authority_namespace: "sovereignty-root",
  authority_type: "root-authority",
  explicit_ownership: true,
  authorized_at: "2026-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-001",
};

const federationScope: FederationScope = {
  federation_id: "fed-001",
  permitted_actions: ["read", "validate"],
  permitted_resources: ["truth", "membership"],
  escalation_policy: "authority-approved",
  scope_description: "Core governance trust scope.",
};

const verificationPolicy: TrustVerificationPolicy = {
  verification_mode: "fail-closed",
  required_authority_types: ["root-authority", "delegated-authority"],
  require_human_authorization: true,
  allow_delegated_authority: true,
  accepted_scope: federationScope,
  accepted_truth_lineage_reference: "lineage-001",
};

const signatureMetadata: TrustEnvelopeSignatureMetadata = {
  signature_id: "sig-001",
  signed_at: "2026-05-28T00:00:00Z",
  signer_authority: issuerAuthority,
  signature_scheme: "placeholder",
  signature_reference: "sig-ref-001",
  verification_policy: verificationPolicy,
};

const revocationRef: TrustRevocationRef = {
  revocation_id: "rev-001",
  revoked_at: "2026-05-28T00:00:00Z",
  revoked_by: issuerAuthority,
  revocation_reason: "Revoked by governance policy.",
  trace_reference: "trace-rev-001",
};

const delegatedAuthorityBase: DelegatedAuthorityRef = {
  delegate_id: "delegate-001",
  delegate_namespace: "sovereignty-root",
  delegate_type: "delegated-authority",
  explicit_ownership: true,
  delegated_by: issuerAuthority,
  delegated_at: "2026-05-28T00:00:00Z",
  expires_at: "2027-05-28T00:00:00Z",
  delegation_policy: "restricted",
  authorized_scopes: [federationScope],
  human_authorization_ref: "human-auth-002",
};

export function buildValidTrustEnvelope(): TrustEnvelope {
  return {
    trust_envelope_id: "envelope-001",
    version: "1.0",
    lifecycle_state: "active",
    issuer: issuerAuthority,
    delegated_authority: delegatedAuthorityBase,
    federation_scope: federationScope,
    verification_policy: verificationPolicy,
    signature: signatureMetadata,
    issued_at: "2026-05-28T00:00:00Z",
    valid_from: "2026-05-28T00:00:00Z",
    valid_until: "2027-05-28T00:00:00Z",
    human_authorization_ref: "human-auth-003",
  };
}

export function buildMissingIssuerAuthorityEnvelope(): TrustEnvelope {
  const envelope = buildValidTrustEnvelope();
  // @ts-expect-error intentionally remove issuer for fixture
  delete envelope.issuer;
  return envelope;
}

export function buildMissingSubjectNodeEnvelope(): TrustEnvelope {
  const envelope = buildValidTrustEnvelope();
  // @ts-expect-error intentionally remove delegate_id to simulate missing subject node
  delete envelope.delegated_authority?.delegate_id;
  return envelope;
}

export function buildExpiredTrustEnvelope(): TrustEnvelope {
  const envelope = buildValidTrustEnvelope();
  envelope.valid_from = "2020-01-01T00:00:00Z";
  envelope.valid_until = "2021-01-01T00:00:00Z";
  return envelope;
}

export function buildRevokedEnvelopeWithoutRevocationRef(): TrustEnvelope {
  const envelope = buildValidTrustEnvelope();
  envelope.lifecycle_state = "revoked";
  // @ts-expect-error intentionally remove revocation_ref
  delete envelope.revocation_ref;
  return envelope;
}

export function buildInvalidDelegatedScopeEnvelope(): TrustEnvelope {
  const envelope = buildValidTrustEnvelope();
  envelope.delegated_authority = {
    ...delegatedAuthorityBase,
    authorized_scopes: [
      {
        federation_id: "fed-001",
        permitted_actions: ["read"],
        permitted_resources: ["truth"],
        escalation_policy: "authority-approved",
        scope_description: "Restricted read-only scope.",
      },
    ],
  };
  return envelope;
}

export function buildMissingVerificationPolicyEnvelope(): TrustEnvelope {
  const envelope = buildValidTrustEnvelope();
  // @ts-expect-error intentionally remove verification_policy
  delete envelope.verification_policy;
  return envelope;
}

export function buildInvalidAcceptedTruthLineageEnvelope(): TrustEnvelope {
  const envelope = buildValidTrustEnvelope();
  envelope.verification_policy = {
    ...envelope.verification_policy,
    accepted_truth_lineage_reference: "",
  };
  return envelope;
}

export function buildSelfAuthorizedEscalationEnvelope(): TrustEnvelope {
  const envelope = buildValidTrustEnvelope();
  envelope.delegated_authority = {
    ...delegatedAuthorityBase,
    delegate_id: issuerAuthority.authority_owner_id,
    delegate_namespace: issuerAuthority.authority_namespace,
    delegated_by: issuerAuthority,
  };
  return envelope;
}
