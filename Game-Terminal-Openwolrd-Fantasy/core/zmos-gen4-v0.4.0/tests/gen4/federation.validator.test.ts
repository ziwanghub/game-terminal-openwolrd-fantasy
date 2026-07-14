import test from "node:test";
import assert from "node:assert/strict";
import {
  validateFederationNodeRef,
  validateTrustEnvelopeCompatibility,
  validateMembershipCompatibility,
  validateLineageCompatibility,
  validateFederationScopeCompatibility,
} from "../../core/gen4/federation/validator.ts";
import { FederationSimulationValidationError } from "../../core/gen4/federation/errors.ts";
import type { FederationNodeRef } from "../../core/gen4/federation/types.ts";
import type { FederationMembership, MembershipScopeRef } from "../../core/gen4/membership/types.ts";
import {
  buildValidFederationNodeRef,
  buildValidTrustValidationEvent,
  buildValidFederationNodeRef as buildValidNode,
} from "./fixtures/federation.fixtures.ts";
import { buildValidTrustEnvelope } from "./fixtures/trust-envelope.fixtures.ts";

const baseMembership: FederationMembership = {
  membership_id: "membership-001",
  membership_state: "active",
  verification_status: "verified",
  subject: {
    node_id: "node-001",
    node_namespace: "sovereignty-root",
    node_role: "sovereign",
    canonical_identity: "sovereign-node-1@zmos",
    joined_at: "2026-05-28T00:00:00Z",
    authority_owner_ref: {
      authority_owner_id: "auth-001",
      authority_namespace: "sovereignty-root",
      authority_type: "root-authority",
      explicit_ownership: true,
      approved_at: "2026-05-28T00:00:00Z",
      human_authorization_ref: "human-auth-001",
      approval_policy: "Initial membership approval.",
    },
  },
  authority_ref: {
    authority_owner_id: "auth-001",
    authority_namespace: "sovereignty-root",
    authority_type: "root-authority",
    explicit_ownership: true,
    approved_at: "2026-05-28T00:00:00Z",
    human_authorization_ref: "human-auth-001",
    approval_policy: "Initial membership approval.",
  },
  scope_ref: {
    federation_id: "fed-001",
    permitted_actions: ["read", "validate"],
    permitted_resources: ["truth", "membership"],
    escalation_policy: "authority-approved",
    scope_description: "Core governance trust scope.",
    scope_boundary_ref: "boundary-001",
  },
  evidence_refs: [
    {
      evidence_id: "evidence-001",
      evidence_type: "membership-change",
      recorded_at: "2026-05-28T00:00:00Z",
      recorded_by: {
        authority_owner_id: "auth-001",
        authority_namespace: "sovereignty-root",
        authority_type: "root-authority",
        explicit_ownership: true,
        approved_at: "2026-05-28T00:00:00Z",
        human_authorization_ref: "human-auth-001",
        approval_policy: "Initial membership approval.",
      },
      trace_reference: "trace-001",
      summary: "Initial membership evidence.",
    },
  ],
  lifecycle_metadata: {
    created_at: "2026-05-28T00:00:00Z",
    last_updated_at: "2026-05-28T00:00:00Z",
    approved_at: "2026-05-28T00:00:00Z",
  },
  transitions: [],
  governance_relationship: "trust",
  allowed_actions: ["read", "validate"],
  permitted_resources: ["truth", "membership"],
};

test("validateFederationNodeRef accepts a valid node reference", () => {
  const node = buildValidFederationNodeRef();
  const validated = validateFederationNodeRef(node);
  assert.equal(validated.node_id, node.node_id);
});

test("validateTrustEnvelopeCompatibility rejects incompatible federation id", () => {
  const node = buildValidFederationNodeRef();
  const envelope = buildValidTrustEnvelope();
  envelope.federation_scope = {
    ...envelope.federation_scope,
    federation_id: "other-federation",
  };

  assert.throws(
    () => validateTrustEnvelopeCompatibility(node, envelope),
    (error) => error instanceof FederationSimulationValidationError && error.code === "TRUST_ENVELOPE_INCOMPATIBLE",
  );
});

test("validateMembershipCompatibility rejects mismatched membership id", () => {
  const node = buildValidFederationNodeRef();
  const invalidMembership = {
    ...baseMembership,
    membership_id: "membership-999",
  };

  assert.throws(
    () => validateMembershipCompatibility(node, invalidMembership),
    (error) => error instanceof FederationSimulationValidationError && error.code === "MEMBERSHIP_INCOMPATIBLE",
  );
});

test("validateLineageCompatibility rejects lineage mismatch", () => {
  const node = buildValidFederationNodeRef();

  assert.throws(
    () => validateLineageCompatibility(node, "lineage-different-001"),
    (error) => error instanceof FederationSimulationValidationError && error.code === "LINEAGE_MISMATCH",
  );
});

test("validateFederationScopeCompatibility rejects missing required resources", () => {
  const node = buildValidFederationNodeRef();
  const requiredScope: MembershipScopeRef = {
    federation_id: "fed-001",
    permitted_actions: ["read"],
    permitted_resources: ["truth", "membership", "secret"],
    escalation_policy: "authority-approved",
    scope_description: "Expanded required scope.",
    scope_boundary_ref: "boundary-001",
  };

  assert.throws(
    () => validateFederationScopeCompatibility(node, requiredScope),
    (error) => error instanceof FederationSimulationValidationError && error.code === "SCOPE_INCOMPATIBLE",
  );
});
