import type {
  FederationMembership,
  MembershipTransition,
} from "../../core/gen4/membership/index.ts";

const authorityRef = {
  authority_owner_id: "auth-001",
  authority_namespace: "sovereignty-root",
  authority_type: "root-authority",
  explicit_ownership: true,
  approved_at: "2026-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-001",
  approval_policy: "Phase 1 governance approval.",
};

const baseScope = {
  federation_id: "fed-001",
  permitted_actions: ["read", "validate"],
  permitted_resources: ["truth", "membership"],
  escalation_policy: "authority-approved",
  scope_description: "Core governance trust scope.",
  scope_boundary_ref: "boundary-001",
};

const baseEvidence = {
  evidence_id: "evidence-001",
  evidence_type: "membership-change",
  recorded_at: "2026-05-28T00:00:00Z",
  recorded_by: authorityRef,
  trace_reference: "trace-001",
  summary: "Initial membership evidence.",
};

function buildBaseMembership(): FederationMembership {
  return {
    membership_id: "membership-001",
    membership_state: "joining",
    verification_status: "pending",
    subject: {
      node_id: "node-001",
      node_namespace: "sovereignty-root",
      node_role: "sovereign",
      canonical_identity: "sovereign-node-1@zmos",
      joined_at: "2026-05-28T00:00:00Z",
      authority_owner_ref: authorityRef,
    },
    authority_ref: authorityRef,
    scope_ref: baseScope,
    evidence_refs: [baseEvidence],
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
}

function buildTransition(overrides: Partial<MembershipTransition>): MembershipTransition {
  return {
    transition_id: "transition-001",
    from_state: "joining",
    to_state: "active",
    reason: "authority-approved",
    authorized_by: authorityRef,
    authorized_at: "2026-05-28T00:00:00Z",
    evidence: {
      evidence_id: "evidence-002",
      evidence_type: "membership-change",
      recorded_at: "2026-05-28T00:00:00Z",
      recorded_by: authorityRef,
      trace_reference: "trace-002",
      summary: "Transition evidence.",
    },
    scope_context: baseScope,
    ...overrides,
  };
}

export function buildValidMembershipJoining(): FederationMembership {
  return buildBaseMembership();
}

export function buildValidTransitionJoiningToActive(): MembershipTransition {
  return buildTransition({ from_state: "joining", to_state: "active" });
}

export function buildValidTransitionActiveToSuspended(): MembershipTransition {
  return buildTransition({ from_state: "active", to_state: "suspended" });
}

export function buildValidTransitionSuspendedToRecovering(): MembershipTransition {
  return buildTransition({ from_state: "suspended", to_state: "recovering" });
}

export function buildValidTransitionRecoveringToActive(): MembershipTransition {
  return buildTransition({ from_state: "recovering", to_state: "active" });
}

export function buildValidTransitionActiveToLeaving(): MembershipTransition {
  return buildTransition({ from_state: "active", to_state: "leaving" });
}

export function buildValidTransitionLeavingToLeft(): MembershipTransition {
  return buildTransition({ from_state: "leaving", to_state: "left" });
}

export function buildInvalidTransitionRevokedToActive(): MembershipTransition {
  return buildTransition({ from_state: "revoked", to_state: "active" });
}

export function buildInvalidTransitionLeftToActive(): MembershipTransition {
  return buildTransition({ from_state: "left", to_state: "active" });
}

export function buildInvalidTransitionSuspendedToActive(): MembershipTransition {
  return buildTransition({ from_state: "suspended", to_state: "active" });
}

export function buildInvalidTransitionMissingAuthorityApproval(): MembershipTransition {
  const transition = buildTransition({});
  // @ts-expect-error intentionally remove authorized_by for fixture
  delete transition.authorized_by;
  return transition;
}

export function buildInvalidTransitionMissingEvidenceReference(): MembershipTransition {
  const transition = buildTransition({});
  // @ts-expect-error intentionally remove evidence for fixture
  delete transition.evidence;
  return transition;
}

export function buildStaleRevokedMembership(): FederationMembership {
  const membership = buildBaseMembership();
  membership.membership_state = "revoked";
  membership.lifecycle_metadata.last_updated_at = "2026-05-28T00:00:00Z";
  return membership;
}

export function buildStaleLeftMembership(): FederationMembership {
  const membership = buildBaseMembership();
  membership.membership_state = "left";
  membership.lifecycle_metadata.last_updated_at = "2026-05-28T00:00:00Z";
  return membership;
}
