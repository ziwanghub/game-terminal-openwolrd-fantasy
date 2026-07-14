import test from "node:test";
import assert from "node:assert/strict";
import { validateTrustEnvelope } from "../../core/gen4/trust-envelope/validator.ts";
import { TrustEnvelopeValidationError } from "../../core/gen4/trust-envelope/errors.ts";

const baseEnvelope = {
  trust_envelope_id: "env-001",
  version: "1.0",
  lifecycle_state: "active",
  issuer: {
    authority_owner_id: "auth-001",
    authority_namespace: "sovereignty-root",
    authority_type: "root-authority",
    explicit_ownership: true,
    authorized_at: "2026-05-28T00:00:00Z",
    human_authorization_ref: "human-auth-001",
  },
  federation_scope: {
    federation_id: "fed-001",
    permitted_actions: ["read", "validate"],
    permitted_resources: ["truth", "membership"],
    escalation_policy: "authority-approved",
    scope_description: "Core governance trust scope.",
  },
  verification_policy: {
    verification_mode: "fail-closed",
    required_authority_types: ["root-authority", "delegated-authority"],
    require_human_authorization: true,
    allow_delegated_authority: true,
    accepted_scope: {
      federation_id: "fed-001",
      permitted_actions: ["read", "validate"],
      permitted_resources: ["truth", "membership"],
      escalation_policy: "authority-approved",
      scope_description: "Core governance trust scope.",
    },
  },
  signature: {
    signature_id: "sig-001",
    signed_at: "2026-05-28T00:00:00Z",
    signer_authority: {
      authority_owner_id: "auth-001",
      authority_namespace: "sovereignty-root",
      authority_type: "root-authority",
      explicit_ownership: true,
      authorized_at: "2026-05-28T00:00:00Z",
      human_authorization_ref: "human-auth-001",
    },
    signature_scheme: "placeholder",
    signature_reference: "sig-ref-001",
    verification_policy: {
      verification_mode: "fail-closed",
      required_authority_types: ["root-authority", "delegated-authority"],
      require_human_authorization: true,
      allow_delegated_authority: true,
      accepted_scope: {
        federation_id: "fed-001",
        permitted_actions: ["read", "validate"],
        permitted_resources: ["truth", "membership"],
        escalation_policy: "authority-approved",
        scope_description: "Core governance trust scope.",
      },
    },
  },
  issued_at: "2026-05-28T00:00:00Z",
  valid_from: "2026-05-28T00:00:00Z",
  valid_until: "2027-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-002",
};

test("validateTrustEnvelope accepts a valid trust envelope", () => {
  const validated = validateTrustEnvelope(baseEnvelope);
  assert.equal(validated.trust_envelope_id, "env-001");
  assert.equal(validated.issuer.authority_type, "root-authority");
});

test("validateTrustEnvelope rejects hidden authority", () => {
  const invalid = structuredClone(baseEnvelope);
  invalid.issuer.authority_type = "hidden-authority";

  assert.throws(
    () => validateTrustEnvelope(invalid),
    (error) => {
      return (
        error instanceof TrustEnvelopeValidationError &&
        error.code === "HIDDEN_AUTHORITY"
      );
    },
  );
});

test("validateTrustEnvelope rejects invalid lifecycle state", () => {
  const invalid = structuredClone(baseEnvelope);
  invalid.lifecycle_state = "unknown";

  assert.throws(
    () => validateTrustEnvelope(invalid),
    (error) => {
      return (
        error instanceof TrustEnvelopeValidationError &&
        error.code === "INVALID_LIFECYCLE_STATE"
      );
    },
  );
});

test("validateTrustEnvelope rejects stale expired envelope", () => {
  const invalid = structuredClone(baseEnvelope);
  invalid.valid_from = "2019-01-01T00:00:00Z";
  invalid.valid_until = "2020-01-01T00:00:00Z";

  assert.throws(
    () => validateTrustEnvelope(invalid),
    (error) => {
      return (
        error instanceof TrustEnvelopeValidationError &&
        error.code === "STALE_ENVELOPE"
      );
    },
  );
});

test("validateTrustEnvelope rejects missing verification policy", () => {
  const invalid = structuredClone(baseEnvelope);
  // @ts-expect-error intentionally remove the verification policy
  delete invalid.verification_policy;

  assert.throws(
    () => validateTrustEnvelope(invalid),
    (error) => {
      return (
        error instanceof TrustEnvelopeValidationError &&
        error.code === "MISSING_VERIFICATION_POLICY"
      );
    },
  );
});

test("validateTrustEnvelope rejects self-authorized delegation", () => {
  const invalid = structuredClone(baseEnvelope);
  invalid.delegated_authority = {
    delegate_id: "auth-001",
    delegate_namespace: "sovereignty-root",
    delegate_type: "delegated-authority",
    explicit_ownership: true,
    delegated_by: invalid.issuer,
    delegated_at: "2026-05-28T00:00:00Z",
    expires_at: "2026-11-28T00:00:00Z",
    delegation_policy: "restricted",
    authorized_scopes: [invalid.federation_scope],
    human_authorization_ref: "human-auth-003",
  };

  assert.throws(
    () => validateTrustEnvelope(invalid),
    (error) => {
      return (
        error instanceof TrustEnvelopeValidationError &&
        error.code === "SELF_AUTHORIZED_ESCALATION"
      );
    },
  );
});

test("validateTrustEnvelope rejects invalid federation scope", () => {
  const invalid = structuredClone(baseEnvelope);
  invalid.federation_scope.permitted_actions = [];

  assert.throws(
    () => validateTrustEnvelope(invalid),
    (error) => {
      return (
        error instanceof TrustEnvelopeValidationError &&
        error.code === "INVALID_FEDERATION_SCOPE"
      );
    },
  );
});

test("validateTrustEnvelope rejects missing issuer authority", () => {
  const invalid = structuredClone(baseEnvelope);
  // @ts-expect-error intentionally remove issuer
  delete invalid.issuer;

  assert.throws(
    () => validateTrustEnvelope(invalid),
    (error) => {
      return (
        error instanceof TrustEnvelopeValidationError &&
        error.code === "MISSING_ISSUER_AUTHORITY"
      );
    },
  );
});

test("validateTrustEnvelope rejects revoked envelope without revocation_ref", () => {
  const invalid = structuredClone(baseEnvelope);
  invalid.lifecycle_state = "revoked";

  assert.throws(
    () => validateTrustEnvelope(invalid),
    (error) => {
      return (
        error instanceof TrustEnvelopeValidationError &&
        error.code === "MALFORMED_TRUST_REFERENCE"
      );
    },
  );
});

test("validateTrustEnvelope rejects invalid accepted truth lineage reference", () => {
  const invalid = structuredClone(baseEnvelope);
  invalid.verification_policy.accepted_truth_lineage_reference = "";

  assert.throws(
    () => validateTrustEnvelope(invalid),
    (error) => {
      return (
        error instanceof TrustEnvelopeValidationError &&
        error.code === "INVALID_ACCEPTED_TRUTH_LINEAGE_REFERENCE"
      );
    },
  );
});

test("validateTrustEnvelope rejects delegated authority scope that does not contain envelope scope", () => {
  const invalid = structuredClone(baseEnvelope);
  invalid.delegated_authority = {
    delegate_id: "delegate-001",
    delegate_namespace: "sovereignty-root",
    delegate_type: "delegated-authority",
    explicit_ownership: true,
    delegated_by: invalid.issuer,
    delegated_at: "2026-05-28T00:00:00Z",
    expires_at: "2026-11-28T00:00:00Z",
    delegation_policy: "restricted",
    authorized_scopes: [
      {
        federation_id: "fed-001",
        permitted_actions: ["read"],
        permitted_resources: ["truth"],
        escalation_policy: "authority-approved",
        scope_description: "Restricted read-only scope.",
      },
    ],
    human_authorization_ref: "human-auth-003",
  };

  assert.throws(
    () => validateTrustEnvelope(invalid),
    (error) => {
      return (
        error instanceof TrustEnvelopeValidationError &&
        error.code === "INVALID_DELEGATION_CHAIN"
      );
    },
  );
});
