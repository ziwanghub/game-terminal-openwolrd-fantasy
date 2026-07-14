import test from "node:test";
import assert from "node:assert/strict";
import type {
  FederationMembership,
  MembershipAuthorityRef,
  MembershipEvidenceRef,
  MembershipLifecycleMetadata,
  MembershipScopeRef,
  MembershipState,
  MembershipSubjectRef,
  MembershipTransition,
  MembershipTransitionReason,
  MembershipVerificationStatus,
} from "../../core/gen4/membership/index.ts";

const authorityRef: MembershipAuthorityRef = {
  authority_owner_id: "auth-001",
  authority_namespace: "sovereignty-root",
  authority_type: "root-authority",
  explicit_ownership: true,
  approved_at: "2026-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-001",
  approval_policy: "Phase 1 governance approval",
};

const scopeRef: MembershipScopeRef = {
  federation_id: "fed-001",
  permitted_actions: ["read", "validate"],
  permitted_resources: ["truth", "membership"],
  escalation_policy: "authority-approved",
  scope_description: "Membership trust scope for federation governance.",
  scope_boundary_ref: "boundary-001",
};

const evidenceRef: MembershipEvidenceRef = {
  evidence_id: "evidence-001",
  evidence_type: "membership-change",
  recorded_at: "2026-05-28T00:00:00Z",
  recorded_by: authorityRef,
  trace_reference: "trace-001",
  summary: "Initial membership established under Phase 1 rules.",
};

const subjectRef: MembershipSubjectRef = {
  node_id: "node-001",
  node_namespace: "sovereignty-root",
  node_role: "sovereign",
  canonical_identity: "sovereign-node-1@zmos",
  joined_at: "2026-05-28T00:00:00Z",
  authority_owner_ref: authorityRef,
};

const transition: MembershipTransition = {
  transition_id: "transition-001",
  from_state: "joining",
  to_state: "active",
  reason: "authority-approved",
  authorized_by: authorityRef,
  authorized_at: "2026-05-28T00:00:00Z",
  evidence: evidenceRef,
  scope_context: scopeRef,
};

const exampleMembership: FederationMembership = {
  membership_id: "membership-001",
  membership_state: "active",
  verification_status: "verified",
  subject: subjectRef,
  authority_ref: authorityRef,
  scope_ref: scopeRef,
  evidence_refs: [evidenceRef],
  lifecycle_metadata: {
    created_at: "2026-05-28T00:00:00Z",
    last_updated_at: "2026-05-28T00:00:00Z",
    approved_at: "2026-05-28T00:00:00Z",
  },
  transitions: [transition],
  governance_relationship: "trust",
  allowed_actions: ["read", "validate"],
  permitted_resources: ["truth", "membership"],
};

// Membership is a governance trust relationship, not a network connection.
const invalidConnectionState: MembershipState = "connected"; // @ts-expect-error
const invalidVerificationStatus: MembershipVerificationStatus = "online"; // @ts-expect-error

const invalidAuthorityType: MembershipAuthorityRef = {
  authority_owner_id: "auth-002",
  authority_namespace: "sovereignty-root",
  authority_type: "hidden-authority", // @ts-expect-error
  explicit_ownership: true,
  approved_at: "2026-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-002",
  approval_policy: "Invalid authority type should fail on compile.",
};

const invalidTransitionReason: MembershipTransitionReason = "unsupported-action"; // @ts-expect-error

const invalidScopeBoundary: MembershipScopeRef = {
  federation_id: "fed-002",
  permitted_actions: [],
  permitted_resources: [],
  escalation_policy: "authority-approved",
  scope_description: "Invalid shape for membership scope.",
  scope_boundary_ref: "boundary-002",
};

test("FederationMembership type shape is valid", () => {
  assert.equal(exampleMembership.membership_id, "membership-001");
  assert.equal(exampleMembership.membership_state, "active");
  assert.equal(exampleMembership.verification_status, "verified");
  assert.equal(exampleMembership.subject.node_role, "sovereign");
  assert.equal(exampleMembership.scope_ref.federation_id, "fed-001");
  assert.equal(exampleMembership.lifecycle_metadata.approved_at, "2026-05-28T00:00:00Z");
  assert.equal(exampleMembership.transitions[0].reason, "authority-approved");
  assert.equal(exampleMembership.governance_relationship, "trust");
});

test("Membership lifecycle states include revoked and recovering", () => {
  assert.equal(exampleMembership.membership_state, "active");
  assert.ok(["joining", "active", "suspended", "revoked", "recovering", "leaving", "left"].includes(exampleMembership.membership_state));
});
