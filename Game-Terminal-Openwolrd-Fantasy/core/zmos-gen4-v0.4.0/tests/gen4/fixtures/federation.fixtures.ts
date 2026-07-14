import type {
  FederationNodeRef,
  FederationSimulationState,
  FederationSimulationEvent,
} from "../../core/gen4/federation/index.ts";
import type { TrustEnvelope } from "../../core/gen4/trust-envelope/index.ts";
import { buildValidTrustEnvelope } from "./trust-envelope.fixtures.ts";

const baseAuthority = {
  authority_owner_id: "auth-001",
  authority_namespace: "sovereignty-root",
  authority_type: "root-authority",
  explicit_ownership: true,
  approved_at: "2026-05-28T00:00:00Z",
  human_authorization_ref: "human-auth-001",
  approval_policy: "Federation participation approval.",
};

const baseScope = {
  federation_id: "fed-001",
  permitted_actions: ["read", "validate"],
  permitted_resources: ["truth", "membership"],
  escalation_policy: "authority-approved",
  scope_description: "Controlled federation scope.",
  scope_boundary_ref: "boundary-001",
};

export function buildValidFederationNodeRef(): FederationNodeRef {
  return {
    node_id: "node-001",
    node_namespace: "sovereignty-root",
    node_role: "sovereign",
    federation_membership_id: "membership-001",
    membership_state: "active",
    verification_status: "verified",
    authority_owner_ref: baseAuthority,
    trust_envelope_id: "envelope-001",
    lineage_reference: "lineage-001",
    scope_ref: baseScope,
    active: true,
  };
}

export function buildJoiningFederationNodeRef(): FederationNodeRef {
  return {
    ...buildValidFederationNodeRef(),
    membership_state: "joining",
    verification_status: "pending",
    trust_envelope_id: "envelope-001",
    active: true,
  };
}

export function buildValidFederationSimulationState(): FederationSimulationState {
  return {
    federation_id: "fed-001",
    nodes: [buildValidFederationNodeRef()],
  };
}

export function buildValidJoinRequestEvent(): FederationSimulationEvent {
  return {
    event_id: "event-001",
    event_type: "join-request",
    node_ref: buildJoiningFederationNodeRef(),
    initiated_at: "2026-05-28T00:00:00Z",
  };
}

export function buildValidTrustValidationEvent(): FederationSimulationEvent {
  return {
    event_id: "event-002",
    event_type: "trust-validation",
    node_ref: buildValidFederationNodeRef(),
    trust_envelope: buildValidTrustEnvelope(),
    initiated_at: "2026-05-28T00:00:00Z",
  };
}

export function buildInvalidTrustValidationEvent(): FederationSimulationEvent {
  const envelope = buildValidTrustEnvelope();
  envelope.federation_scope = {
    ...envelope.federation_scope,
    federation_id: "other-federation",
    permitted_actions: ["read"],
  };

  return {
    event_id: "event-003",
    event_type: "trust-validation",
    node_ref: buildValidFederationNodeRef(),
    trust_envelope: envelope,
    initiated_at: "2026-05-28T00:00:00Z",
  };
}

export function buildLineageMismatchEvent(): FederationSimulationEvent {
  return {
    event_id: "event-004",
    event_type: "lineage-validation",
    node_ref: buildValidFederationNodeRef(),
    expected_lineage_reference: "lineage-expected-001",
    actual_lineage_reference: "lineage-actual-002",
    initiated_at: "2026-05-28T00:00:00Z",
  };
}

export function buildRevokedMembershipEvent(): FederationSimulationEvent {
  return {
    event_id: "event-005",
    event_type: "membership-update",
    node_ref: buildValidFederationNodeRef(),
    membership_state: "revoked",
    initiated_at: "2026-05-28T00:00:00Z",
  };
}

export function buildStaleStateAuditEvent(): FederationSimulationEvent {
  const node = buildValidFederationNodeRef();
  return {
    event_id: "event-006",
    event_type: "audit",
    node_ref: {
      ...node,
      membership_state: "left",
      active: false,
    },
    initiated_at: "2026-05-28T00:00:00Z",
  };
}

export function buildUnsortedEvents(): readonly FederationSimulationEvent[] {
  return [
    {
      event_id: "event-003",
      event_type: "trust-validation",
      node_ref: buildValidFederationNodeRef(),
      trust_envelope: buildValidTrustEnvelope(),
      initiated_at: "2026-05-28T00:00:00Z",
    },
    {
      event_id: "event-001",
      event_type: "join-request",
      node_ref: buildJoiningFederationNodeRef(),
      initiated_at: "2026-05-28T00:00:00Z",
    },
    {
      event_id: "event-002",
      event_type: "lineage-validation",
      node_ref: buildValidFederationNodeRef(),
      expected_lineage_reference: "lineage-001",
      actual_lineage_reference: "lineage-001",
      initiated_at: "2026-05-28T00:00:00Z",
    },
  ];
}
