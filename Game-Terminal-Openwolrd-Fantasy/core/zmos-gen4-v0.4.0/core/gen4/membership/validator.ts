import type {
  FederationMembership,
  MembershipAuthorityRef,
  MembershipEvidenceRef,
  MembershipScopeRef,
  MembershipState,
  MembershipTransition,
} from "./types.js";
import {
  MembershipTransitionValidationError,
  MEMBERSHIP_TRANSITION_ERROR_CODES,
} from "./errors.js";

const ALLOWED_MEMBERSHIP_STATES: readonly MembershipState[] = [
  "joining",
  "active",
  "suspended",
  "revoked",
  "recovering",
  "leaving",
  "left",
];

const ALLOWED_TRANSITIONS: Record<MembershipState, readonly MembershipState[]> = {
  joining: ["active", "revoked"],
  active: ["suspended", "revoked", "leaving"],
  suspended: ["recovering", "revoked"],
  recovering: ["active", "revoked"],
  leaving: ["left", "revoked"],
  revoked: [],
  left: [],
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertMembershipState(value: unknown, label: string): asserts value is MembershipState {
  if (typeof value !== "string" || !ALLOWED_MEMBERSHIP_STATES.includes(value as MembershipState)) {
    throw new MembershipTransitionValidationError(
      label === "current state"
        ? MEMBERSHIP_TRANSITION_ERROR_CODES.UNKNOWN_CURRENT_STATE
        : MEMBERSHIP_TRANSITION_ERROR_CODES.UNKNOWN_TARGET_STATE,
      `${label} must be one of: ${ALLOWED_MEMBERSHIP_STATES.join(", ")}.`,
    );
  }
}

function assertNonEmptyString(value: unknown, label: string): asserts value is string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MALFORMED_MEMBERSHIP_REFERENCE,
      `${label} must be a non-empty string.`,
    );
  }
}

function assertIsoDate(value: unknown, label: string): asserts value is string {
  assertNonEmptyString(value, label);
  if (Number.isNaN(Date.parse(value))) {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MALFORMED_MEMBERSHIP_REFERENCE,
      `${label} must be a valid ISO 8601 date string.`,
    );
  }
}

function validateAuthorityRef(value: unknown, path: string): MembershipAuthorityRef {
  if (!isRecord(value)) {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MISSING_AUTHORITY_APPROVAL,
      `${path} must be an object.`,
    );
  }

  assertNonEmptyString(value.authority_owner_id, `${path}.authority_owner_id`);
  assertNonEmptyString(value.authority_namespace, `${path}.authority_namespace`);
  assertNonEmptyString(value.authority_type, `${path}.authority_type`);

  if (value.explicit_ownership !== true) {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MISSING_AUTHORITY_APPROVAL,
      `${path}.explicit_ownership must be true.`,
    );
  }

  assertIsoDate(value.approved_at, `${path}.approved_at`);
  assertNonEmptyString(value.human_authorization_ref, `${path}.human_authorization_ref`);
  assertNonEmptyString(value.approval_policy, `${path}.approval_policy`);

  return value as MembershipAuthorityRef;
}

function validateEvidenceRef(value: unknown, path: string): MembershipEvidenceRef {
  if (!isRecord(value)) {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MISSING_EVIDENCE_REFERENCE,
      `${path} must be an object.`,
    );
  }

  assertNonEmptyString(value.evidence_id, `${path}.evidence_id`);
  assertNonEmptyString(value.evidence_type, `${path}.evidence_type`);
  assertIsoDate(value.recorded_at, `${path}.recorded_at`);
  assertNonEmptyString(value.trace_reference, `${path}.trace_reference`);

  validateAuthorityRef(value.recorded_by, `${path}.recorded_by`);

  if (typeof value.summary !== "undefined" && typeof value.summary !== "string") {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MALFORMED_MEMBERSHIP_REFERENCE,
      `${path}.summary must be a string when present.`,
    );
  }

  return value as MembershipEvidenceRef;
}

function validateScopeRef(value: unknown, path: string): MembershipScopeRef {
  if (!isRecord(value)) {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MALFORMED_MEMBERSHIP_REFERENCE,
      `${path} must be an object.`,
    );
  }

  assertNonEmptyString(value.federation_id, `${path}.federation_id`);

  if (!Array.isArray(value.permitted_actions)) {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MALFORMED_MEMBERSHIP_REFERENCE,
      `${path}.permitted_actions must be an array.`,
    );
  }

  if (!Array.isArray(value.permitted_resources)) {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MALFORMED_MEMBERSHIP_REFERENCE,
      `${path}.permitted_resources must be an array.`,
    );
  }

  if (value.escalation_policy !== "authority-approved" && value.escalation_policy !== "none") {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MALFORMED_MEMBERSHIP_REFERENCE,
      `${path}.escalation_policy must be authority-approved or none.`,
    );
  }

  assertNonEmptyString(value.scope_description, `${path}.scope_description`);

  if (typeof value.scope_boundary_ref !== "undefined") {
    assertNonEmptyString(value.scope_boundary_ref, `${path}.scope_boundary_ref`);
  }

  return value as MembershipScopeRef;
}

function assertTransitionAllowed(
  currentState: MembershipState,
  nextState: MembershipState,
): void {
  if (currentState === "suspended" && nextState === "active") {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.INVALID_RECOVERY_PATH,
      "Suspended membership must enter recovering before becoming active.",
    );
  }

  if (!ALLOWED_TRANSITIONS[currentState].includes(nextState)) {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.INVALID_TRANSITION,
      `Transition from ${currentState} to ${nextState} is not allowed.`,
    );
  }
}

function assertStateRules(
  currentState: MembershipState,
  nextState: MembershipState,
): void {
  if (currentState === "revoked" && nextState === "active") {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.INVALID_TRANSITION,
      "revoked membership cannot transition directly to active.",
    );
  }

  if (currentState === "left" && nextState === "active") {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.INVALID_TRANSITION,
      "left membership cannot transition directly to active.",
    );
  }
}

function assertScopeEscalation(
  scope: MembershipScopeRef,
  authorizedBy: MembershipAuthorityRef,
): void {
  if (scope.escalation_policy === "authority-approved") {
    if (authorizedBy.authority_type !== "root-authority") {
      throw new MembershipTransitionValidationError(
        MEMBERSHIP_TRANSITION_ERROR_CODES.SCOPE_ESCALATION_WITHOUT_APPROVAL,
        "Escalation scope requires root authority approval.",
      );
    }

    if (authorizedBy.explicit_ownership !== true || typeof authorizedBy.human_authorization_ref !== "string" || authorizedBy.human_authorization_ref.trim().length === 0) {
      throw new MembershipTransitionValidationError(
        MEMBERSHIP_TRANSITION_ERROR_CODES.SCOPE_ESCALATION_WITHOUT_APPROVAL,
        "Escalation scope requires explicit human approved authority.",
      );
    }
  }
}

function assertStaleMembershipState(
  membership: FederationMembership,
  transition: MembershipTransition,
): void {
  if (membership.membership_state === "revoked" || membership.membership_state === "left") {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.STALE_MEMBERSHIP_STATE,
      `Membership in state ${membership.membership_state} may not transition.`,
    );
  }

  if (membership.lifecycle_metadata.last_updated_at && Number.isNaN(Date.parse(membership.lifecycle_metadata.last_updated_at))) {
    throw new MembershipTransitionValidationError(
      MEMBERSHIP_TRANSITION_ERROR_CODES.MALFORMED_MEMBERSHIP_REFERENCE,
      "membership.lifecycle_metadata.last_updated_at must be a valid ISO 8601 date string.",
    );
  }
}

export function validateMembershipTransition(
  membership: FederationMembership,
  transition: MembershipTransition,
): MembershipTransition {
  assertMembershipState(membership.membership_state, "current state");
  assertMembershipState(transition.from_state, "current state");
  assertMembershipState(transition.to_state, "target state");

  assertNonEmptyString(transition.transition_id, "transition.transition_id");
  assertIsoDate(transition.authorized_at, "transition.authorized_at");

  validateAuthorityRef(transition.authorized_by, "transition.authorized_by");
  validateEvidenceRef(transition.evidence, "transition.evidence");
  validateScopeRef(transition.scope_context, "transition.scope_context");

  assertStaleMembershipState(membership, transition);
  assertTransitionAllowed(membership.membership_state, transition.to_state);
  assertStateRules(membership.membership_state, transition.to_state);
  assertScopeEscalation(transition.scope_context, transition.authorized_by);

  return transition;
}
