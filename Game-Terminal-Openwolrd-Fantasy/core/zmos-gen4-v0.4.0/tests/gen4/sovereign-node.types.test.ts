import test from "node:test";
import assert from "node:assert/strict";
import type {
  AuthorityOwnerRef,
  FederationScopeRef,
  NodeIdentity,
  NodeLifecycleState,
  NodeVerificationStatus,
  SovereignNode,
  TrustBoundaryMetadata,
} from "../../core/gen4/sovereign-node/index.ts";

const exampleAuthorityOwner: AuthorityOwnerRef = {
  authority_owner_id: "auth-001",
  authority_namespace: "sovereignty-root",
  authority_type: "root-authority",
  explicit_ownership: true,
  authorized_at: "2026-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-123",
};

const exampleScope: FederationScopeRef = {
  federation_id: "federation-001",
  permitted_actions: ["read", "update"],
  permitted_resources: ["truth", "membership"],
  escalation_policy: "authority-approved",
  scope_description: "Core governance trust scope for Phase 1.",
};

const exampleTrustBoundary: TrustBoundaryMetadata = {
  trust_boundary_id: "trust-boundary-001",
  trust_envelope_id: "envelope-001",
  trust_scope: exampleScope,
  valid_from: "2026-05-28T00:00:00Z",
  valid_until: "2027-05-28T00:00:00Z",
  enforcement_mode: "fail-closed",
  issued_by: exampleAuthorityOwner,
  reviewed_at: "2026-05-28T00:00:00Z",
};

const exampleIdentity: NodeIdentity = {
  node_id: "node-001",
  node_name: "sovereign-node-1",
  node_role: "sovereign",
  canonical_identity: "sovereign-node-1@zmos",
  created_at: "2026-05-28T00:00:00Z",
  authority_owner: exampleAuthorityOwner,
};

const exampleNode: SovereignNode = {
  node_identity: exampleIdentity,
  lifecycle_state: "active",
  verification_status: "verified",
  authority_owner_ref: exampleAuthorityOwner,
  trust_boundary: exampleTrustBoundary,
  federation_scope_ref: exampleScope,
  last_human_authorized_at: "2026-05-28T00:00:00Z",
  explicit_human_authorization_ref: "human-auth-123",
};

// @ts-expect-error: invalid lifecycle state should be rejected by type system
const invalidLifecycle: NodeLifecycleState = "unknown";

// @ts-expect-error: invalid authority type should be rejected by type system
const invalidAuthority: AuthorityOwnerRef = {
  authority_owner_id: "auth-002",
  authority_namespace: "sovereignty-root",
  authority_type: "hidden-authority",
  explicit_ownership: true,
  authorized_at: "2026-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-456",
};

test("SovereignNode type shape is valid", () => {
  assert.equal(exampleNode.node_identity.node_id, "node-001");
  assert.equal(exampleNode.lifecycle_state, "active");
  assert.equal(exampleNode.verification_status, "verified");
  assert.equal(exampleNode.trust_boundary.enforcement_mode, "fail-closed");
  assert.equal(exampleNode.federation_scope_ref.escalation_policy, "authority-approved");
  assert.equal(exampleNode.authority_owner_ref.explicit_ownership, true);
});

test("TrustBoundaryMetadata requires fail-closed enforcement", () => {
  assert.equal(exampleTrustBoundary.enforcement_mode, "fail-closed");
  assert.equal(exampleTrustBoundary.issued_by.authority_type, "root-authority");
});
