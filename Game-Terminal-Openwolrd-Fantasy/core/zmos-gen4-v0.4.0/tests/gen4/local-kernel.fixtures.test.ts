import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {
  createAmbiguousVerificationIntentFixture,
  createIntentWithoutHumanAuthorizationFixture,
  createOutOfScopeIntentFixture,
  createValidLocalIntentFixture,
  createValidTrustEnvelopeForIntentFixture,
  runLocalKernelScenarioFixture,
} from "./fixtures/local-kernel.fixtures.ts";

test("valid intent fixture produces accepted local scenario", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createValidLocalIntentFixture(),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  assert.equal(scenario.decision.status, "accepted");
  assert.equal(scenario.trace_records.length, 1);
  assert.equal(scenario.replay_result.status, "completed");
  assert.equal(scenario.evidence_package.status, "complete");
  assert.equal(scenario.recovery_diagnostic.status, "recoverable");
});

test("missing human authorization fixture produces rejected scenario", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createIntentWithoutHumanAuthorizationFixture(),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  assert.equal(scenario.decision.status, "rejected");
  assert.equal(scenario.decision.error_codes.includes("MISSING_HUMAN_AUTHORIZATION"), true);
  assert.equal(scenario.evidence_package.error_codes.includes("MISSING_HUMAN_AUTHORIZATION"), true);
  assert.notEqual(scenario.decision.status, "accepted");
});

test("out-of-scope fixture produces rejected scenario", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createOutOfScopeIntentFixture(),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  assert.equal(scenario.decision.status, "rejected");
  assert.equal(scenario.decision.error_codes.includes("TRUST_SCOPE_VIOLATION"), true);
});

test("ambiguous verification fixture produces quarantined scenario", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createAmbiguousVerificationIntentFixture(),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  assert.equal(scenario.decision.status, "quarantined");
  assert.equal(scenario.trace_records[0].decision_status, "quarantined");
});

test("scenario runner returns decision + trace + replay + evidence + recovery", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createValidLocalIntentFixture(),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  assert.ok(scenario.decision.decision_id.length > 0);
  assert.ok(scenario.trace_records.length > 0);
  assert.ok(scenario.replay_result.replay_id.length > 0);
  assert.ok(scenario.evidence_package.evidence_package_id.length > 0);
  assert.ok(scenario.recovery_diagnostic.recovery_id.length > 0);
});

test("fixture outputs are deterministic", () => {
  const a = runLocalKernelScenarioFixture({
    intent: createValidLocalIntentFixture(),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });
  const b = runLocalKernelScenarioFixture({
    intent: createValidLocalIntentFixture(),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  assert.deepEqual(a.decision, b.decision);
  assert.deepEqual(a.trace_records, b.trace_records);
  assert.deepEqual(a.replay_result, b.replay_result);
  assert.deepEqual(a.evidence_package, b.evidence_package);
  assert.deepEqual(a.recovery_diagnostic, b.recovery_diagnostic);
});

test("override options are deterministic and respected", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createValidLocalIntentFixture({
      intent_id: "intent-fixture-override-001",
      requested_resource: "membership",
      metadata: { replay_nonce: "replay-override-001" },
    }),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  assert.equal(scenario.trace_records[0].intent_id, "intent-fixture-override-001");
  assert.equal(scenario.trace_records[0].metadata.replay_nonce, "replay-override-001");
});

test("helper usage does not weaken fail-closed behavior", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createIntentWithoutHumanAuthorizationFixture({ intent_id: "intent-fixture-fail-closed-001" }),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  assert.equal(scenario.decision.status, "rejected");
  assert.equal(scenario.replay_result.accepted_count, 0);
});

test("no test helper imports forbidden network modules", () => {
  const helperPath = path.resolve("tests/gen4/fixtures/local-kernel.fixtures.ts");
  const content = fs.readFileSync(helperPath, "utf8");
  const disallowed = ["http", "https", "net", "tls", "dgram", "ws", "child_process"];

  for (const pattern of disallowed) {
    assert.equal(content.includes(pattern), false, `Found disallowed pattern \"${pattern}\"`);
  }
});
