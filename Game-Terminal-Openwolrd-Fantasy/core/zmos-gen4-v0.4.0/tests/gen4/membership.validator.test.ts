import test from "node:test";
import assert from "node:assert/strict";
import { validateMembershipTransition } from "../../core/gen4/membership/validator.ts";
import { MembershipTransitionValidationError } from "../../core/gen4/membership/errors.ts";
import type {
  FederationMembership,
  MembershipTransition,
} from "../../core/gen4/membership/types.ts";

const baseMembership: FederationMembership = {
  membership_id: "membership-001",
  membership_state: "joining",
  verification_status: "pending",
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
      summary: "Initial membership created.",
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

const validTransition: MembershipTransition = {
  transition_id: "transition-001",
  from_state: "joining",
  to_state: "active",
  reason: "authority-approved",
  authorized_by: {
    authority_owner_id: "auth-001",
    authority_namespace: "sovereignty-root",
    authority_type: "root-authority",
    explicit_ownership: true,
    approved_at: "2026-05-28T00:00:00Z",
    human_authorization_ref: "human-auth-001",
    approval_policy: "Initial membership activation.",
  },
  authorized_at: "2026-05-28T00:00:00Z",
  evidence: {
    evidence_id: "evidence-002",
    evidence_type: "membership-change",
    recorded_at: "2026-05-28T00:00:00Z",
    recorded_by: {
      authority_owner_id: "auth-001",
      authority_namespace: "sovereignty-root",
      authority_type: "root-authority",
      explicit_ownership: true,
      approved_at: "2026-05-28T00:00:00Z",
      human_authorization_ref: "human-auth-001",
      approval_policy: "Activation evidence.",
    },
    trace_reference: "trace-002",
    summary: "Transition from joining to active.",
  },
  scope_context: {
    federation_id: "fed-001",
    permitted_actions: ["read", "validate"],
    permitted_resources: ["truth", "membership"],
    escalation_policy: "authority-approved",
    scope_description: "Activation scope.",
    scope_boundary_ref: "boundary-001",
  },
};

test("validateMembershipTransition accepts an allowed joining->active transition", () => {
  const result = validateMembershipTransition(baseMembership, validTransition);
  assert.equal(result.transition_id, "transition-001");
});

test("validateMembershipTransition rejects unknown current state", () => {
  const invalidMembership = structuredClone(baseMembership);
  // @ts-expect-error: force an invalid state for runtime validation
  invalidMembership.membership_state = "unknown";

  assert.throws(
    () => validateMembershipTransition(invalidMembership, validTransition),
    (error) => {
      return (
        error instanceof MembershipTransitionValidationError &&
        error.code === "UNKNOWN_CURRENT_STATE"
      );
    },
  );
});

test("validateMembershipTransition rejects unknown target state", () => {
  const invalidTransition = structuredClone(validTransition);
  // @ts-expect-error: force invalid target state for runtime validation
  invalidTransition.to_state = "unknown";

  assert.throws(
    () => validateMembershipTransition(baseMembership, invalidTransition),
    (error) => {
      return (
        error instanceof MembershipTransitionValidationError &&
        error.code === "UNKNOWN_TARGET_STATE"
      );
    },
  );
});

test("validateMembershipTransition rejects an unsupported transition graph", () => {
  const invalidTransition = structuredClone(validTransition);
  invalidTransition.from_state = "active";
  invalidTransition.to_state = "joining";

  assert.throws(
    () => validateMembershipTransition(baseMembership, invalidTransition),
    (error) => {
      return (
        error instanceof MembershipTransitionValidationError &&
        error.code === "INVALID_TRANSITION"
      );
    },
  );
});

test("validateMembershipTransition rejects missing authority approval", () => {
  const invalidTransition = structuredClone(validTransition);
  // @ts-expect-error: intentionally remove authorized_by
  delete invalidTransition.authorized_by;

  assert.throws(
    () => validateMembershipTransition(baseMembership, invalidTransition),
    (error) => {
      return (
        error instanceof MembershipTransitionValidationError &&
        error.code === "MISSING_AUTHORITY_APPROVAL"
      );
    },
  );
});

test("validateMembershipTransition rejects missing evidence reference", () => {
  const invalidTransition = structuredClone(validTransition);
  // @ts-expect-error: intentionally remove evidence
  delete invalidTransition.evidence;

  assert.throws(
    () => validateMembershipTransition(baseMembership, invalidTransition),
    (error) => {
      return (
        error instanceof MembershipTransitionValidationError &&
        error.code === "MISSING_EVIDENCE_REFERENCE"
      );
    },
  );
});

test("validateMembershipTransition rejects revoked->active direct transition", () => {
  const invalidMembership = structuredClone(baseMembership);
  invalidMembership.membership_state = "revoked";

  const invalidTransition = structuredClone(validTransition);
  invalidTransition.from_state = "revoked";
  invalidTransition.to_state = "active";

  assert.throws(
    () => validateMembershipTransition(invalidMembership, invalidTransition),
    (error) => {
      return (
        error instanceof MembershipTransitionValidationError &&
        error.code === "STALE_MEMBERSHIP_STATE"
      );
    },
  );
});

test("validateMembershipTransition rejects left->active direct transition", () => {
  const invalidMembership = structuredClone(baseMembership);
  invalidMembership.membership_state = "left";

  const invalidTransition = structuredClone(validTransition);
  invalidTransition.from_state = "left";
  invalidTransition.to_state = "active";

  assert.throws(
    () => validateMembershipTransition(invalidMembership, invalidTransition),
    (error) => {
      return (
        error instanceof MembershipTransitionValidationError &&
        error.code === "STALE_MEMBERSHIP_STATE"
      );
    },
  );
});

test("validateMembershipTransition rejects suspended->active without recovery", () => {
  const invalidMembership = structuredClone(baseMembership);
  invalidMembership.membership_state = "suspended";

  const invalidTransition = structuredClone(validTransition);
  invalidTransition.from_state = "suspended";
  invalidTransition.to_state = "active";

  assert.throws(
    () => validateMembershipTransition(invalidMembership, invalidTransition),
    (error) => {
      return (
        error instanceof MembershipTransitionValidationError &&
        error.code === "INVALID_RECOVERY_PATH"
      );
    },
  );
});

test("validateMembershipTransition rejects escalation scope without explicit approval", () => {
  const invalidTransition = structuredClone(validTransition);
  invalidTransition.authorized_by = {
    ...invalidTransition.authorized_by,
    authority_type: "delegated-authority",
  } as any;

  assert.throws(
    () => validateMembershipTransition(baseMembership, invalidTransition),
    (error) => {
      return (
        error instanceof MembershipTransitionValidationError &&
        error.code === "SCOPE_ESCALATION_WITHOUT_APPROVAL"
      );
    },
  );
});

test("validateMembershipTransition rejects transition from stale revoked membership", () => {
  const invalidMembership = structuredClone(baseMembership);
  invalidMembership.membership_state = "revoked";

  assert.throws(
    () => validateMembershipTransition(invalidMembership, validTransition),
    (error) => {
      return (
        error instanceof MembershipTransitionValidationError &&
        error.code === "STALE_MEMBERSHIP_STATE"
      );
    },
  );
});
