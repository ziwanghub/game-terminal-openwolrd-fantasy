import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createLocalTraceWriter } from "../../core/gen4/local-kernel/trace.ts";
import { runLocalIntent } from "../../core/gen4/local-kernel/harness.ts";
import { replayLocalTraceRecords } from "../../core/gen4/local-kernel/replay.ts";
import { buildLocalEvidencePackage } from "../../core/gen4/local-kernel/evidence.ts";
import { diagnoseLocalTraceRecovery } from "../../core/gen4/local-kernel/recovery.ts";
import { buildValidTrustEnvelope } from "./fixtures/trust-envelope.fixtures.ts";

const now = () => "2026-05-28T00:00:00Z";

const baseIntent = {
  intent_id: "intent-recovery-001",
  subject_ref: "subject-recovery-001",
  issuer_ref: "issuer-recovery-001",
  requested_action: "read",
  requested_resource: "truth",
  human_authorization_ref: "human-auth-recovery-001",
  trust_envelope_ref: "envelope-001",
  metadata: {
    submitted_at: "2026-05-28T00:00:00Z",
    trace_correlation_id: "trace-corr-recovery-001",
    replay_nonce: "replay-recovery-001",
  },
};

function buildArtifacts() {
  const writer = createLocalTraceWriter();

  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  runLocalIntent(
    { ...baseIntent, intent_id: "intent-recovery-002", requested_action: "delete" },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  const trace = writer.listTraceRecords();
  const replay = replayLocalTraceRecords(trace);
  const evidence = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });

  return { trace, replay, evidence };
}

test("recoverable diagnostic from valid trace + completed replay + complete evidence", () => {
  const writer = createLocalTraceWriter();
  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });
  const trace = writer.listTraceRecords();
  const replay = replayLocalTraceRecords(trace);
  const evidence = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });

  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: trace,
    replay_result: replay,
    evidence_package: evidence,
  });

  assert.equal(diagnostic.status, "recoverable");
  assert.equal(diagnostic.replay_status, "completed");
  assert.equal(diagnostic.evidence_status, "complete");
  assert.equal(diagnostic.diagnostic_codes.includes("RECOVERY_REPAIR_PROHIBITED"), true);
});

test("blocked diagnostic when replay failed", () => {
  const { trace, replay } = buildArtifacts();
  const failedReplay = {
    ...replay,
    status: "failed" as const,
    metadata: { ...replay.metadata, failure_reason: "forced" },
  };
  const evidence = buildLocalEvidencePackage({ trace_records: trace, replay_result: failedReplay });

  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: trace,
    replay_result: failedReplay,
    evidence_package: evidence,
  });

  assert.equal(diagnostic.status, "blocked");
  assert.equal(diagnostic.diagnostic_codes.includes("RECOVERY_REPLAY_FAILED"), true);
});

test("blocked diagnostic when evidence incomplete", () => {
  const { trace, replay, evidence } = buildArtifacts();
  const incomplete = {
    ...evidence,
    status: "incomplete" as const,
    metadata: { ...evidence.metadata, reason: "forced incomplete" },
  };

  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: trace,
    replay_result: replay,
    evidence_package: incomplete,
  });

  assert.equal(diagnostic.status, "blocked");
  assert.equal(diagnostic.diagnostic_codes.includes("RECOVERY_EVIDENCE_INCOMPLETE"), true);
});

test("blocked diagnostic when evidence failed", () => {
  const { trace, replay, evidence } = buildArtifacts();
  const failed = {
    ...evidence,
    status: "failed" as const,
    metadata: { ...evidence.metadata, reason: "forced failed" },
  };

  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: trace,
    replay_result: replay,
    evidence_package: failed,
  });

  assert.equal(diagnostic.status, "blocked");
  assert.equal(diagnostic.diagnostic_codes.includes("RECOVERY_EVIDENCE_FAILED"), true);
});

test("failed diagnostic when required input is missing", () => {
  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: [] as any,
    replay_result: {} as any,
    evidence_package: {} as any,
  });

  assert.equal(diagnostic.status, "failed");
  assert.equal(diagnostic.diagnostic_codes.includes("RECOVERY_INPUT_MISSING"), true);
});

test("deterministic identical output on repeated diagnostics", () => {
  const { trace, replay, evidence } = buildArtifacts();
  const a = diagnoseLocalTraceRecovery({ trace_records: trace, replay_result: replay, evidence_package: evidence });
  const b = diagnoseLocalTraceRecovery({ trace_records: trace, replay_result: replay, evidence_package: evidence });

  assert.deepEqual(a, b);
});

test("diagnostic does not mutate trace/replay/evidence inputs", () => {
  const { trace, replay, evidence } = buildArtifacts();
  const traceSnapshot = structuredClone(trace);
  const replaySnapshot = structuredClone(replay);
  const evidenceSnapshot = structuredClone(evidence);

  diagnoseLocalTraceRecovery({
    trace_records: trace,
    replay_result: replay,
    evidence_package: evidence,
  });

  assert.deepEqual(trace, traceSnapshot);
  assert.deepEqual(replay, replaySnapshot);
  assert.deepEqual(evidence, evidenceSnapshot);
});

test("corrupted trace sequence leads blocked diagnostic", () => {
  const { trace, replay, evidence } = buildArtifacts();
  const corrupted = trace.map((record) => ({ ...record, metadata: { ...record.metadata } }));
  corrupted[1].sequence = 4;

  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: corrupted as any,
    replay_result: replay,
    evidence_package: evidence,
  });

  assert.equal(diagnostic.status, "blocked");
  assert.equal(diagnostic.diagnostic_codes.includes("RECOVERY_TRACE_SEQUENCE_INVALID"), true);
});

test("diagnostic includes replay/evidence error codes and invariant refs", () => {
  const { trace, replay } = buildArtifacts();
  const failedReplay = {
    ...replay,
    status: "failed" as const,
    error_codes: ["REPLAY_SEQUENCE_GAP"],
    invariant_violation_refs: ["TRUST_SCOPE_VIOLATION"] as const,
    metadata: { ...replay.metadata, failure_reason: "forced" },
  };
  const evidence = buildLocalEvidencePackage({ trace_records: trace, replay_result: failedReplay });

  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: trace,
    replay_result: failedReplay,
    evidence_package: evidence,
  });

  assert.equal(diagnostic.error_codes.includes("REPLAY_SEQUENCE_GAP"), true);
  assert.equal(diagnostic.invariant_violation_refs.includes("TRUST_SCOPE_VIOLATION"), true);
});

test("automatic repair is not exposed or performed", () => {
  const { trace, replay, evidence } = buildArtifacts();
  const diagnostic = diagnoseLocalTraceRecovery({
    trace_records: trace,
    replay_result: replay,
    evidence_package: evidence,
  });

  assert.equal(diagnostic.diagnostic_codes.includes("RECOVERY_REPAIR_PROHIBITED"), true);
});

test("no networking imports introduced in local-kernel", () => {
  const root = path.resolve("core/gen4/local-kernel");
  const disallowed = ["http", "https", "net", "tls", "dgram", "ws", "child_process"];

  const entries = fs.readdirSync(root).filter((name) => name.endsWith(".ts"));
  for (const entry of entries) {
    const content = fs.readFileSync(path.join(root, entry), "utf8");
    for (const pattern of disallowed) {
      assert.equal(content.includes(pattern), false, `Found disallowed pattern \"${pattern}\" in ${entry}`);
    }
  }
});
