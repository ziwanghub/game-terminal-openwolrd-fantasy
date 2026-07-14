import test from "node:test";
import assert from "node:assert/strict";
import { validateLocalIntent } from "../../core/gen4/local-kernel/harness.ts";

const validIntent = {
  intent_id: "intent-001",
  subject_ref: "subject-001",
  issuer_ref: "issuer-001",
  requested_action: "read",
  requested_resource: "truth",
  human_authorization_ref: "human-auth-001",
  trust_envelope_ref: "te-001",
  metadata: {
    submitted_at: "2026-05-28T00:00:00Z",
    trace_correlation_id: "trace-001",
    replay_nonce: "nonce-001",
  },
};

test("validateLocalIntent accepts a valid local intent", () => {
  const result = validateLocalIntent(validIntent);
  assert.equal(result.intent_id, "intent-001");
});

test("validateLocalIntent rejects missing human_authorization_ref", () => {
  const invalid = {
    ...validIntent,
    human_authorization_ref: "",
  };

  assert.throws(() => validateLocalIntent(invalid));
});

test("validateLocalIntent rejects malformed intent", () => {
  assert.throws(() => validateLocalIntent("not-an-object"));
});

test("validateLocalIntent rejects missing subject_ref", () => {
  const invalid = {
    ...validIntent,
    subject_ref: "",
  };

  assert.throws(() => validateLocalIntent(invalid));
});

test("validateLocalIntent rejects missing issuer_ref", () => {
  const invalid = {
    ...validIntent,
    issuer_ref: "",
  };

  assert.throws(() => validateLocalIntent(invalid));
});
