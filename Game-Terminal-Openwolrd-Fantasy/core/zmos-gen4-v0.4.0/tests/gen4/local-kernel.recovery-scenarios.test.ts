import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import {
  createAmbiguousVerificationIntentFixture,
  createIntentWithoutHumanAuthorizationFixture,
  createOutOfScopeIntentFixture,
  createValidLocalIntentFixture,
  createValidTrustEnvelopeForIntentFixture,
  runLocalKernelScenarioFixture,
} from "./fixtures/local-kernel.fixtures.ts";
import { buildLocalEvidencePackage } from "../../core/gen4/local-kernel/evidence.ts";
import { diagnoseLocalTraceRecovery } from "../../core/gen4/local-kernel/recovery.ts";
import { replayLocalTraceRecords } from "../../core/gen4/local-kernel/replay.ts";
import { scanLocalKernelBoundary } from "./helpers/no-network-boundary.ts";

function toScenarioSummary(input: {
  scenario_id: string;
  decision_status: string;
  replay_status: string;
  evidence_status: string;
  recovery_status: string;
  diagnostic_codes: readonly string[];
  error_codes: readonly string[];
  invariant_violation_refs: readonly string[];
}) {
  return {
    ...input,
    diagnostic_codes: [...input.diagnostic_codes],
    error_codes: [...input.error_codes],
    invariant_violation_refs: [...input.invariant_violation_refs],
  };
}

test("Scenario 1: rejected intent investigation is visible and deterministic", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createIntentWithoutHumanAuthorizationFixture({ intent_id: "intent-rec-s1" }),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  assert.equal(scenario.decision.status, "rejected");
  assert.equal(scenario.trace_records.length, 1);
  assert.equal(scenario.replay_result.status, "completed");
  assert.equal(scenario.evidence_package.status, "complete");
  assert.equal(scenario.recovery_diagnostic.status, "recoverable");
  assert.equal(scenario.recovery_diagnostic.error_codes.includes("MISSING_HUMAN_AUTHORIZATION"), true);
  assert.equal(
    scenario.recovery_diagnostic.invariant_violation_refs.includes("MISSING_HUMAN_AUTHORIZATION"),
    true,
  );

  const summaryA = toScenarioSummary({
    scenario_id: "S1",
    decision_status: scenario.decision.status,
    replay_status: scenario.replay_result.status,
    evidence_status: scenario.evidence_package.status,
    recovery_status: scenario.recovery_diagnostic.status,
    diagnostic_codes: scenario.recovery_diagnostic.diagnostic_codes,
    error_codes: scenario.recovery_diagnostic.error_codes,
    invariant_violation_refs: scenario.recovery_diagnostic.invariant_violation_refs,
  });

  const scenarioRepeat = runLocalKernelScenarioFixture({
    intent: createIntentWithoutHumanAuthorizationFixture({ intent_id: "intent-rec-s1" }),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  const summaryB = toScenarioSummary({
    scenario_id: "S1",
    decision_status: scenarioRepeat.decision.status,
    replay_status: scenarioRepeat.replay_result.status,
    evidence_status: scenarioRepeat.evidence_package.status,
    recovery_status: scenarioRepeat.recovery_diagnostic.status,
    diagnostic_codes: scenarioRepeat.recovery_diagnostic.diagnostic_codes,
    error_codes: scenarioRepeat.recovery_diagnostic.error_codes,
    invariant_violation_refs: scenarioRepeat.recovery_diagnostic.invariant_violation_refs,
  });

  assert.deepEqual(summaryA, summaryB);
});

test("Scenario 2: quarantine inspection remains deterministic without auto-release", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createAmbiguousVerificationIntentFixture({ intent_id: "intent-rec-s2" }),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  assert.equal(scenario.decision.status, "quarantined");
  assert.equal(scenario.trace_records.length, 1);
  assert.equal(scenario.replay_result.status, "completed");
  assert.equal(scenario.evidence_package.status, "complete");
  assert.equal(["recoverable", "blocked"].includes(scenario.recovery_diagnostic.status), true);
  assert.equal(scenario.recovery_diagnostic.error_codes.includes("AMBIGUOUS_VERIFICATION"), true);
  assert.equal(scenario.recovery_diagnostic.diagnostic_codes.includes("RECOVERY_REPAIR_PROHIBITED"), true);

  const snapshot = structuredClone(scenario.trace_records);
  const replayAgain = replayLocalTraceRecords(scenario.trace_records);
  assert.deepEqual(scenario.trace_records, snapshot);
  assert.equal(replayAgain.status, "completed");
});

test("Scenario 3: replay/evidence mismatch investigation is blocked or failed with visible reason", () => {
  const base = runLocalKernelScenarioFixture({
    intent: createOutOfScopeIntentFixture({ intent_id: "intent-rec-s3" }),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  const mismatchReplay = {
    ...base.replay_result,
    decision_ids: ["decision-mismatch"],
  };

  const mismatchEvidence = buildLocalEvidencePackage({
    trace_records: base.trace_records,
    replay_result: mismatchReplay,
  });

  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: base.trace_records,
    replay_result: mismatchReplay,
    evidence_package: mismatchEvidence,
  });

  assert.equal(["blocked", "failed"].includes(diagnostic.status), true);
  assert.equal(
    diagnostic.error_codes.includes("EVIDENCE_DECISION_ID_MISMATCH") ||
      diagnostic.diagnostic_codes.includes("RECOVERY_TRACE_SEQUENCE_INVALID"),
    true,
  );
});

test("Scenario 4: corrupted trace leads replay failure and non-recoverable diagnostic", () => {
  const base = runLocalKernelScenarioFixture({
    intent: createValidLocalIntentFixture({ intent_id: "intent-rec-s4" }),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  const corrupted = base.trace_records.map((record) => ({
    ...record,
    metadata: { ...record.metadata },
  }));
  corrupted[0].sequence = -1;

  const replay = replayLocalTraceRecords(corrupted as any);
  const evidence = buildLocalEvidencePackage({
    trace_records: corrupted as any,
    replay_result: replay,
  });
  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: corrupted as any,
    replay_result: replay,
    evidence_package: evidence,
  });

  assert.equal(replay.status, "failed");
  assert.notEqual(evidence.status, "complete");
  assert.equal(["blocked", "failed"].includes(diagnostic.status), true);
  assert.equal(
    diagnostic.diagnostic_codes.includes("RECOVERY_REPLAY_FAILED") ||
      diagnostic.diagnostic_codes.includes("RECOVERY_TRACE_SEQUENCE_INVALID"),
    true,
  );
});

test("Scenario 5: incomplete evidence review remains blocked and deterministic", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createValidLocalIntentFixture({ intent_id: "intent-rec-s5" }),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  const replayMismatch = {
    ...scenario.replay_result,
    record_count: scenario.replay_result.record_count + 1,
  };

  const evidenceIncomplete = buildLocalEvidencePackage({
    trace_records: scenario.trace_records,
    replay_result: replayMismatch,
  });

  const diagnosticA = diagnoseLocalTraceRecovery({
    trace_records: scenario.trace_records,
    replay_result: replayMismatch,
    evidence_package: evidenceIncomplete,
  });

  const diagnosticB = diagnoseLocalTraceRecovery({
    trace_records: scenario.trace_records,
    replay_result: replayMismatch,
    evidence_package: evidenceIncomplete,
  });

  assert.equal(evidenceIncomplete.status, "incomplete");
  assert.equal(diagnosticA.status, "blocked");
  assert.equal(diagnosticA.diagnostic_codes.includes("RECOVERY_EVIDENCE_INCOMPLETE"), true);
  assert.deepEqual(diagnosticA, diagnosticB);
  assert.equal(diagnosticA.diagnostic_codes.includes("RECOVERY_REPAIR_PROHIBITED"), true);
});

test("recovery scenarios do not mutate inputs and no auto-repair behavior exists", () => {
  const scenario = runLocalKernelScenarioFixture({
    intent: createOutOfScopeIntentFixture({ intent_id: "intent-rec-sx" }),
    trust_envelope: createValidTrustEnvelopeForIntentFixture(),
  });

  const traceSnapshot = structuredClone(scenario.trace_records);
  const replaySnapshot = structuredClone(scenario.replay_result);
  const evidenceSnapshot = structuredClone(scenario.evidence_package);

  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: scenario.trace_records,
    replay_result: scenario.replay_result,
    evidence_package: scenario.evidence_package,
  });

  assert.deepEqual(scenario.trace_records, traceSnapshot);
  assert.deepEqual(scenario.replay_result, replaySnapshot);
  assert.deepEqual(scenario.evidence_package, evidenceSnapshot);
  assert.equal(diagnostic.diagnostic_codes.includes("RECOVERY_REPAIR_PROHIBITED"), true);
});

test("no-network boundary guard still passes", () => {
  const findings = scanLocalKernelBoundary({
    localKernelRoot: path.resolve("core/gen4/local-kernel"),
    fsAllowedFiles: [path.resolve("core/gen4/local-kernel/trace-persistence.ts")],
  });

  assert.equal(findings.length, 0);
});
