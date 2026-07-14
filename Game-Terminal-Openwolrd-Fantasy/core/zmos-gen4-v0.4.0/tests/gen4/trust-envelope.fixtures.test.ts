import test from "node:test";
import assert from "node:assert/strict";
import { validateTrustEnvelope } from "../../core/gen4/trust-envelope/validator.ts";
import { TrustEnvelopeValidationError } from "../../core/gen4/trust-envelope/errors.ts";
import {
  buildValidTrustEnvelope,
  buildMissingIssuerAuthorityEnvelope,
  buildMissingSubjectNodeEnvelope,
  buildExpiredTrustEnvelope,
  buildRevokedEnvelopeWithoutRevocationRef,
  buildInvalidDelegatedScopeEnvelope,
  buildMissingVerificationPolicyEnvelope,
  buildInvalidAcceptedTruthLineageEnvelope,
  buildSelfAuthorizedEscalationEnvelope,
} from "./fixtures/trust-envelope.fixtures.ts";

test("fixture: valid trust envelope passes validation", () => {
  const envelope = buildValidTrustEnvelope();
  const validated = validateTrustEnvelope(envelope);
  assert.equal(validated.trust_envelope_id, envelope.trust_envelope_id);
});

test("fixture: missing issuer authority fails validation", () => {
  assert.throws(
    () => validateTrustEnvelope(buildMissingIssuerAuthorityEnvelope()),
    (error) => error instanceof TrustEnvelopeValidationError,
  );
});

test("fixture: missing subject node fails validation", () => {
  assert.throws(
    () => validateTrustEnvelope(buildMissingSubjectNodeEnvelope()),
    (error) => error instanceof TrustEnvelopeValidationError,
  );
});

test("fixture: expired trust envelope fails validation", () => {
  assert.throws(
    () => validateTrustEnvelope(buildExpiredTrustEnvelope()),
    (error) => error instanceof TrustEnvelopeValidationError,
  );
});

test("fixture: revoked envelope without revocation ref fails validation", () => {
  assert.throws(
    () => validateTrustEnvelope(buildRevokedEnvelopeWithoutRevocationRef()),
    (error) => error instanceof TrustEnvelopeValidationError,
  );
});

test("fixture: invalid delegated scope fails validation", () => {
  assert.throws(
    () => validateTrustEnvelope(buildInvalidDelegatedScopeEnvelope()),
    (error) => error instanceof TrustEnvelopeValidationError,
  );
});

test("fixture: missing verification policy fails validation", () => {
  assert.throws(
    () => validateTrustEnvelope(buildMissingVerificationPolicyEnvelope()),
    (error) => error instanceof TrustEnvelopeValidationError,
  );
});

test("fixture: invalid accepted truth lineage fails validation", () => {
  assert.throws(
    () => validateTrustEnvelope(buildInvalidAcceptedTruthLineageEnvelope()),
    (error) => error instanceof TrustEnvelopeValidationError,
  );
});

test("fixture: self-authorized escalation fails validation", () => {
  assert.throws(
    () => validateTrustEnvelope(buildSelfAuthorizedEscalationEnvelope()),
    (error) => error instanceof TrustEnvelopeValidationError,
  );
});
