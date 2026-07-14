import test from "node:test";
import assert from "node:assert/strict";
import { replayLocalTraceRecords } from "../../core/gen4/local-kernel/replay.ts";
import { createLocalTraceWriter } from "../../core/gen4/local-kernel/trace.ts";
import { runLocalIntent } from "../../core/gen4/local-kernel/harness.ts";
import { buildValidTrustEnvelope } from "./fixtures/trust-envelope.fixtures.ts";

const now = () => "2026-05-28T00:00:00Z";

const baseIntent = {
  intent_id: "intent-replay-001",
  subject_ref: "subject-replay-001",
  issuer_ref: "issuer-replay-001",
  requested_action: "read",
  requested_resource: "truth",
  human_authorization_ref: "human-auth-replay-001",
  trust_envelope_ref: "envelope-001",
  metadata: {
    submitted_at: "2026-05-28T00:00:00Z",
    trace_correlation_id: "trace-corr-replay-001",
    replay_nonce: "replay-001",
  },
};

function mixedTrace() {
  const writer = createLocalTraceWriter();

  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  runLocalIntent(
    { ...baseIntent, intent_id: "intent-replay-002", requested_action: "delete" },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-replay-003",
      metadata: { ...baseIntent.metadata, ambiguous_verification: true },
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  return writer.listTraceRecords();
}

test("replay accepted/rejected/quarantined mixed trace", () => {
  const result = replayLocalTraceRecords(mixedTrace());
  assert.equal(result.status, "completed");
  assert.equal(result.record_count, 3);
  assert.equal(result.accepted_count, 1);
  assert.equal(result.rejected_count, 1);
  assert.equal(result.quarantined_count, 1);
});

test("identical trace input produces identical replay result", () => {
  const trace = mixedTrace();
  const a = replayLocalTraceRecords(trace);
  const b = replayLocalTraceRecords(trace);
  assert.deepEqual(a, b);
});

test("replay deterministically sorts records by sequence", () => {
  const trace = mixedTrace();
  const shuffled = [trace[2], trace[0], trace[1]];
  const result = replayLocalTraceRecords(shuffled);
  assert.equal(result.status, "completed");
  assert.deepEqual(result.intent_ids, ["intent-replay-001", "intent-replay-002", "intent-replay-003"]);
});

test("duplicate sequence fails closed", () => {
  const trace = mixedTrace();
  const duplicated = [...trace, { ...trace[2], sequence: trace[1].sequence }];
  const result = replayLocalTraceRecords(duplicated as any);
  assert.equal(result.status, "failed");
  assert.equal(result.error_codes[0], "REPLAY_DUPLICATE_SEQUENCE");
});

test("sequence gap fails closed", () => {
  const trace = mixedTrace();
  const gapped = trace.map((record) => ({ ...record }));
  gapped[2].sequence = 4;
  const result = replayLocalTraceRecords(gapped);
  assert.equal(result.status, "failed");
  assert.equal(result.error_codes[0], "REPLAY_SEQUENCE_GAP");
});

test("malformed trace record fails closed", () => {
  const trace = mixedTrace().map((record) => ({
    ...record,
    error_codes: [...record.error_codes],
    invariant_violations: [...record.invariant_violations],
    metadata: { ...record.metadata },
  })) as any[];
  delete trace[1].decision_id;
  const result = replayLocalTraceRecords(trace as any);
  assert.equal(result.status, "failed");
  assert.equal(result.error_codes[0], "REPLAY_MALFORMED_RECORD");
});

test("unknown decision status fails closed", () => {
  const trace = mixedTrace().map((record) => ({ ...record }));
  (trace[1] as any).decision_status = "unknown";
  const result = replayLocalTraceRecords(trace as any);
  assert.equal(result.status, "failed");
  assert.equal(result.error_codes[0], "REPLAY_UNKNOWN_DECISION_STATUS");
});

test("replay does not mutate input trace records", () => {
  const trace = mixedTrace();
  const snapshot = structuredClone(trace);
  replayLocalTraceRecords(trace);
  assert.deepEqual(trace, snapshot);
});

test("error codes and invariant refs aggregate deterministically", () => {
  const result = replayLocalTraceRecords(mixedTrace());
  assert.equal(result.status, "completed");
  assert.deepEqual(result.error_codes, ["AMBIGUOUS_VERIFICATION", "TRUST_SCOPE_VIOLATION"]);
  assert.deepEqual(result.invariant_violation_refs, ["AMBIGUOUS_VERIFICATION", "TRUST_SCOPE_VIOLATION"]);
});
