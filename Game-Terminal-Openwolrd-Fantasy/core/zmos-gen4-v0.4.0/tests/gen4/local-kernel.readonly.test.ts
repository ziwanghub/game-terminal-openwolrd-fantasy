import test from "node:test";
import assert from "node:assert/strict";
import { runLocalIntent } from "../../core/gen4/local-kernel/harness.ts";
import { createLocalTraceWriter } from "../../core/gen4/local-kernel/trace.ts";
import { replayLocalTraceRecords } from "../../core/gen4/local-kernel/replay.ts";
import { buildLocalEvidencePackage } from "../../core/gen4/local-kernel/evidence.ts";
import { buildValidTrustEnvelope } from "./fixtures/trust-envelope.fixtures.ts";

const now = () => "2026-05-28T00:00:00Z";

const baseIntent = {
  intent_id: "intent-readonly-001",
  subject_ref: "subject-readonly-001",
  issuer_ref: "issuer-readonly-001",
  requested_action: "read",
  requested_resource: "truth",
  human_authorization_ref: "human-auth-readonly-001",
  trust_envelope_ref: "envelope-001",
  metadata: {
    submitted_at: "2026-05-28T00:00:00Z",
    trace_correlation_id: "trace-corr-readonly-001",
    replay_nonce: "replay-readonly-001",
  },
};

function prepareArtifacts() {
  const writer = createLocalTraceWriter();
  const decision = runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });
  const trace = writer.listTraceRecords();
  const replay = replayLocalTraceRecords(trace);
  const evidence = buildLocalEvidencePackage({
    trace_records: trace,
    replay_result: replay,
  });
  return { writer, decision, trace, replay, evidence };
}

test("decision result is immutable externally", () => {
  const { decision } = prepareArtifacts();
  assert.throws(() => {
    (decision as { status: string }).status = "rejected";
  });
  assert.throws(() => {
    (decision.error_codes as string[]).push("INJECTED");
  });
});

test("trace list/records are immutable and copy-safe", () => {
  const { writer } = prepareArtifacts();
  const first = writer.listTraceRecords();
  assert.throws(() => {
    (first as unknown as Array<unknown>).push({});
  });
  assert.throws(() => {
    (first[0].error_codes as string[]).push("INJECTED");
  });

  const second = writer.listTraceRecords();
  assert.equal(second.length, 1);
  assert.equal(second[0].error_codes.includes("INJECTED"), false);
});

test("replay result is immutable externally", () => {
  const { replay } = prepareArtifacts();
  assert.throws(() => {
    (replay.error_codes as string[]).push("INJECTED");
  });
  assert.throws(() => {
    (replay.metadata as { deterministic_key: string }).deterministic_key = "mutated";
  });
});

test("evidence package remains immutable/deep-frozen", () => {
  const { evidence } = prepareArtifacts();
  assert.throws(() => {
    (evidence.intent_ids as string[]).push("intent-injected");
  });
  assert.throws(() => {
    (evidence.metadata as { deterministic_key: string }).deterministic_key = "mutated";
  });
});

test("repeated reads produce deterministic results", () => {
  const { writer } = prepareArtifacts();
  const a = writer.listTraceRecords();
  const b = writer.listTraceRecords();
  assert.deepEqual(a, b);
  assert.notEqual(a, b);
});
