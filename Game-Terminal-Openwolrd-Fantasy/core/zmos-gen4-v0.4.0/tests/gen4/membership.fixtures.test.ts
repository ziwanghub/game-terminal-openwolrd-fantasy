import test from "node:test";
import assert from "node:assert/strict";
import { validateMembershipTransition } from "../../core/gen4/membership/validator.ts";
import { MembershipTransitionValidationError } from "../../core/gen4/membership/errors.ts";
import {
  buildValidMembershipJoining,
  buildValidTransitionJoiningToActive,
  buildValidTransitionActiveToSuspended,
  buildValidTransitionSuspendedToRecovering,
  buildValidTransitionRecoveringToActive,
  buildValidTransitionActiveToLeaving,
  buildValidTransitionLeavingToLeft,
  buildInvalidTransitionRevokedToActive,
  buildInvalidTransitionLeftToActive,
  buildInvalidTransitionSuspendedToActive,
  buildInvalidTransitionMissingAuthorityApproval,
  buildInvalidTransitionMissingEvidenceReference,
  buildStaleRevokedMembership,
  buildStaleLeftMembership,
} from "./fixtures/membership.fixtures.ts";

test("fixture: joining->active transition is allowed", () => {
  const membership = buildValidMembershipJoining();
  const transition = buildValidTransitionJoiningToActive();
  const validated = validateMembershipTransition(membership, transition);
  assert.equal(validated.to_state, "active");
});

test("fixture: active->suspended transition is allowed", () => {
  const membership = buildValidMembershipJoining();
  membership.membership_state = "active";
  const transition = buildValidTransitionActiveToSuspended();
  const validated = validateMembershipTransition(membership, transition);
  assert.equal(validated.to_state, "suspended");
});

test("fixture: suspended->recovering transition is allowed", () => {
  const membership = buildValidMembershipJoining();
  membership.membership_state = "suspended";
  const transition = buildValidTransitionSuspendedToRecovering();
  const validated = validateMembershipTransition(membership, transition);
  assert.equal(validated.to_state, "recovering");
});

test("fixture: recovering->active transition is allowed", () => {
  const membership = buildValidMembershipJoining();
  membership.membership_state = "recovering";
  const transition = buildValidTransitionRecoveringToActive();
  const validated = validateMembershipTransition(membership, transition);
  assert.equal(validated.to_state, "active");
});

test("fixture: active->leaving transition is allowed", () => {
  const membership = buildValidMembershipJoining();
  membership.membership_state = "active";
  const transition = buildValidTransitionActiveToLeaving();
  const validated = validateMembershipTransition(membership, transition);
  assert.equal(validated.to_state, "leaving");
});

test("fixture: leaving->left transition is allowed", () => {
  const membership = buildValidMembershipJoining();
  membership.membership_state = "leaving";
  const transition = buildValidTransitionLeavingToLeft();
  const validated = validateMembershipTransition(membership, transition);
  assert.equal(validated.to_state, "left");
});

test("fixture: revoked->active transition fails", () => {
  const membership = buildStaleRevokedMembership();
  const transition = buildInvalidTransitionRevokedToActive();
  assert.throws(
    () => validateMembershipTransition(membership, transition),
    (error) => error instanceof MembershipTransitionValidationError,
  );
});

test("fixture: left->active transition fails", () => {
  const membership = buildStaleLeftMembership();
  const transition = buildInvalidTransitionLeftToActive();
  assert.throws(
    () => validateMembershipTransition(membership, transition),
    (error) => error instanceof MembershipTransitionValidationError,
  );
});

test("fixture: suspended->active transition without recovery fails", () => {
  const membership = buildValidMembershipJoining();
  membership.membership_state = "suspended";
  const transition = buildInvalidTransitionSuspendedToActive();
  assert.throws(
    () => validateMembershipTransition(membership, transition),
    (error) => error instanceof MembershipTransitionValidationError,
  );
});

test("fixture: missing authority approval fails", () => {
  const membership = buildValidMembershipJoining();
  const transition = buildInvalidTransitionMissingAuthorityApproval();
  assert.throws(
    () => validateMembershipTransition(membership, transition),
    (error) => error instanceof MembershipTransitionValidationError,
  );
});

test("fixture: missing evidence reference fails", () => {
  const membership = buildValidMembershipJoining();
  const transition = buildInvalidTransitionMissingEvidenceReference();
  assert.throws(
    () => validateMembershipTransition(membership, transition),
    (error) => error instanceof MembershipTransitionValidationError,
  );
});
