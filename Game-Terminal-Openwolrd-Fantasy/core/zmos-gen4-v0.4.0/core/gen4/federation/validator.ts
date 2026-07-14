import type { TrustEnvelope } from "../trust-envelope/index.js";
import type {
  FederationMembership,
  MembershipAuthorityRef,
  MembershipScopeRef,
  MembershipState,
  MembershipVerificationStatus,
} from "../membership/types.js";
import type { FederationNodeRef, FederationSimulationEvent } from "./types.js";
import {
  FederationSimulationValidationError,
  FEDERATION_SIMULATION_ERROR_CODES,
} from "./errors.js";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertNonEmptyString(value: unknown, label: string): asserts value is string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${label} must be a non-empty string.`,
    );
  }
}

function assertBoolean(value: unknown, label: string): asserts value is boolean {
  if (typeof value !== "boolean") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${label} must be a boolean.`,
    );
  }
}

function assertMembershipState(value: unknown, label: string): asserts value is MembershipState {
  if (typeof value !== "string") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${label} must be a string representing a membership state.`,
    );
  }

  const allowed: readonly MembershipState[] = [
    "joining",
    "active",
    "suspended",
    "revoked",
    "recovering",
    "leaving",
    "left",
  ];

  if (!allowed.includes(value as MembershipState)) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${label} must be one of: ${allowed.join(", ")}.`,
    );
  }
}

function assertVerificationStatus(value: unknown, label: string): asserts value is MembershipVerificationStatus {
  if (typeof value !== "string") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${label} must be a string representing a verification status.`,
    );
  }

  const allowed: readonly MembershipVerificationStatus[] = [
    "pending",
    "verified",
    "failed",
    "quarantined",
    "revoked",
  ];

  if (!allowed.includes(value as MembershipVerificationStatus)) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${label} must be one of: ${allowed.join(", ")}.`,
    );
  }
}

function validateScopeRef(value: unknown, path: string): MembershipScopeRef {
  if (!isRecord(value)) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${path} must be an object.`,
    );
  }

  assertNonEmptyString(value.federation_id, `${path}.federation_id`);

  if (!Array.isArray(value.permitted_actions)) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${path}.permitted_actions must be an array.`,
    );
  }

  if (!Array.isArray(value.permitted_resources)) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${path}.permitted_resources must be an array.`,
    );
  }

  if (value.escalation_policy !== "authority-approved" && value.escalation_policy !== "none") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${path}.escalation_policy must be authority-approved or none.`,
    );
  }

  assertNonEmptyString(value.scope_description, `${path}.scope_description`);

  if (typeof value.scope_boundary_ref !== "undefined") {
    assertNonEmptyString(value.scope_boundary_ref, `${path}.scope_boundary_ref`);
  }

  return value as MembershipScopeRef;
}

function validateAuthorityRef(value: unknown, path: string): MembershipAuthorityRef {
  if (!isRecord(value)) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${path} must be an object.`,
    );
  }

  assertNonEmptyString(value.authority_owner_id, `${path}.authority_owner_id`);
  assertNonEmptyString(value.authority_namespace, `${path}.authority_namespace`);
  assertNonEmptyString(value.authority_type, `${path}.authority_type`);
  if (value.explicit_ownership !== true) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      `${path}.explicit_ownership must be true.`,
    );
  }
  assertNonEmptyString(value.approved_at, `${path}.approved_at`);
  assertNonEmptyString(value.human_authorization_ref, `${path}.human_authorization_ref`);
  assertNonEmptyString(value.approval_policy, `${path}.approval_policy`);

  return value as MembershipAuthorityRef;
}

export function validateFederationNodeRef(node: unknown): FederationNodeRef {
  if (!isRecord(node)) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      "Federation node reference must be an object.",
    );
  }

  const candidate = node as Record<string, unknown>;

  assertNonEmptyString(candidate.node_id, "node_ref.node_id");
  assertNonEmptyString(candidate.node_namespace, "node_ref.node_namespace");

  if (
    candidate.node_role !== "sovereign" &&
    candidate.node_role !== "observer" &&
    candidate.node_role !== "auditor" &&
    candidate.node_role !== "validator" &&
    candidate.node_role !== "participant"
  ) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      "node_ref.node_role must be one of sovereign, observer, auditor, validator, or participant.",
    );
  }

  assertNonEmptyString(candidate.federation_membership_id, "node_ref.federation_membership_id");
  assertMembershipState(candidate.membership_state, "node_ref.membership_state");
  assertVerificationStatus(candidate.verification_status, "node_ref.verification_status");

  const authorityOwnerRef = validateAuthorityRef(candidate.authority_owner_ref, "node_ref.authority_owner_ref");
  assertNonEmptyString(candidate.trust_envelope_id, "node_ref.trust_envelope_id");
  assertNonEmptyString(candidate.lineage_reference, "node_ref.lineage_reference");

  const scopeRef = validateScopeRef(candidate.scope_ref, "node_ref.scope_ref");
  assertBoolean(candidate.active, "node_ref.active");

  if (scopeRef.escalation_policy === "authority-approved" && authorityOwnerRef.authority_type !== "root-authority") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.INVALID_NODE_PARTICIPATION,
      "Escalation scope requires root authority approval for federation node participation.",
    );
  }

  return candidate as FederationNodeRef;
}

export function validateFederationNodeParticipation(node: FederationNodeRef): FederationNodeRef {
  if (!node.active) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.INVALID_NODE_PARTICIPATION,
      "Federation node participation is disabled.",
    );
  }

  if (node.membership_state === "revoked" || node.membership_state === "left") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.STALE_MEMBERSHIP_STATE,
      `Federation node with membership state ${node.membership_state} may not participate in simulation.`,
    );
  }

  return node;
}

export function validateTrustEnvelopeCompatibility(
  node: FederationNodeRef,
  envelope: TrustEnvelope,
): TrustEnvelope {
  if (envelope.federation_scope.federation_id !== node.scope_ref.federation_id) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.TRUST_ENVELOPE_INCOMPATIBLE,
      "Trust envelope federation identifier does not match node federation scope.",
    );
  }

  const missingAction = node.scope_ref.permitted_actions.find(
    (action) => !envelope.federation_scope.permitted_actions.includes(action),
  );
  if (typeof missingAction !== "undefined") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.TRUST_ENVELOPE_INCOMPATIBLE,
      `Trust envelope does not allow required action: ${missingAction}.`,
    );
  }

  const missingResource = node.scope_ref.permitted_resources.find(
    (resource) => !envelope.federation_scope.permitted_resources.includes(resource),
  );
  if (typeof missingResource !== "undefined") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.TRUST_ENVELOPE_INCOMPATIBLE,
      `Trust envelope does not authorize required resource: ${missingResource}.`,
    );
  }

  return envelope;
}

export function validateMembershipCompatibility(
  node: FederationNodeRef,
  membership: FederationMembership,
): FederationMembership {
  if (membership.membership_id !== node.federation_membership_id) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MEMBERSHIP_INCOMPATIBLE,
      "Federation membership identifier does not match node reference.",
    );
  }

  if (membership.scope_ref.federation_id !== node.scope_ref.federation_id) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MEMBERSHIP_INCOMPATIBLE,
      "Federation membership scope does not match node federation scope.",
    );
  }

  if (membership.verification_status === "failed") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MEMBERSHIP_INCOMPATIBLE,
      "Federation membership verification has failed and cannot participate.",
    );
  }

  if (membership.membership_state === "revoked" || membership.membership_state === "left") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.STALE_MEMBERSHIP_STATE,
      `Federation membership state ${membership.membership_state} is stale and cannot participate.`,
    );
  }

  return membership;
}

export function validateLineageCompatibility(
  node: FederationNodeRef,
  expectedLineageReference: string,
): string {
  if (node.lineage_reference !== expectedLineageReference) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.LINEAGE_MISMATCH,
      "Federation node lineage does not match the expected federation lineage reference.",
    );
  }

  return node.lineage_reference;
}

export function validateFederationScopeCompatibility(
  node: FederationNodeRef,
  requiredScope: MembershipScopeRef,
): MembershipScopeRef {
  if (requiredScope.federation_id !== node.scope_ref.federation_id) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.SCOPE_INCOMPATIBLE,
      "Required federation scope does not match node federation scope.",
    );
  }

  const missingAction = requiredScope.permitted_actions.find(
    (action) => !node.scope_ref.permitted_actions.includes(action),
  );
  if (typeof missingAction !== "undefined") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.SCOPE_INCOMPATIBLE,
      `Federation node scope does not permit required action: ${missingAction}.`,
    );
  }

  const missingResource = requiredScope.permitted_resources.find(
    (resource) => !node.scope_ref.permitted_resources.includes(resource),
  );
  if (typeof missingResource !== "undefined") {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.SCOPE_INCOMPATIBLE,
      `Federation node scope does not permit required resource: ${missingResource}.`,
    );
  }

  return requiredScope;
}

export function validateFederationSimulationEvent(event: unknown): FederationSimulationEvent {
  if (!isRecord(event)) {
    throw new FederationSimulationValidationError(
      FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
      "Federation simulation event must be an object.",
    );
  }

  assertNonEmptyString(event.event_id, "event.event_id");
  assertNonEmptyString(event.event_type, "event.event_type");
  assertNonEmptyString(event.initiated_at, "event.initiated_at");
  validateFederationNodeRef(event.node_ref);

  return event as FederationSimulationEvent;
}
