import test from "node:test";
import assert from "node:assert/strict";
import { createLocalDecisionResult } from "../../core/gen4/local-kernel/decision.ts";

test("createLocalDecisionResult builds accepted decision for valid input", () => {
  const result = createLocalDecisionResult({
    intent: {
      intent_id: "intent-001",
      trust_envelope_ref: "te-001",
    },
    status: "accepted",
    decided_at: "2026-05-28T00:00:00Z",
  });

  assert.equal(result.status, "accepted");
  assert.equal(result.error_codes.length, 0);
  assert.equal(result.metadata.execution_mode, "mock-only");
});

test("createLocalDecisionResult prevents accepted status with errors", () => {
  assert.throws(() =>
    createLocalDecisionResult({
      intent: {
        intent_id: "intent-001",
        trust_envelope_ref: "te-001",
      },
      status: "accepted",
      error_codes: ["MALFORMED_INTENT"],
      invariant_violations: ["MALFORMED_INTENT"],
      decided_at: "2026-05-28T00:00:00Z",
    }),
  );
});
