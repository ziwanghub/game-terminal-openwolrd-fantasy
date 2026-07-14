import test from "node:test";
import assert from "node:assert/strict";
import { createLocalTraceWriter } from "../../core/gen4/local-kernel/trace.ts";
import { runLocalIntent } from "../../core/gen4/local-kernel/harness.ts";
import { buildValidTrustEnvelope } from "./fixtures/trust-envelope.fixtures.ts";

const now = () => "2026-05-28T00:00:00Z";

const baseIntent = {
  intent_id: "intent-trace-001",
  subject_ref: "subject-trace-001",
  issuer_ref: "issuer-trace-001",
  requested_action: "read",
  requested_resource: "truth",
  human_authorization_ref: "human-auth-trace-001",
  trust_envelope_ref: "envelope-001",
  metadata: {
    submitted_at: "2026-05-28T00:00:00Z",
    trace_correlation_id: "trace-corr-001",
    replay_nonce: "replay-001",
  },
};

test("accepted decision emits trace", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });
  assert.equal(result.status, "accepted");
  assert.equal(writer.listTraceRecords().length, 1);
});

test("rejected decision emits trace with error codes", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(
    { ...baseIntent, requested_action: "delete" },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  assert.equal(result.status, "rejected");
  const records = writer.listTraceRecords();
  assert.equal(records.length, 1);
  assert.equal(records[0].error_codes[0], "TRUST_SCOPE_VIOLATION");
});

test("quarantined decision emits trace with error codes", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(
    {
      ...baseIntent,
      metadata: {
        ...baseIntent.metadata,
        ambiguous_verification: true,
      },
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  assert.equal(result.status, "quarantined");
  const records = writer.listTraceRecords();
  assert.equal(records.length, 1);
  assert.equal(records[0].error_codes[0], "AMBIGUOUS_VERIFICATION");
});

test("trace sequence increments deterministically", () => {
  const writer = createLocalTraceWriter();

  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  runLocalIntent(
    { ...baseIntent, intent_id: "intent-trace-002" },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  const records = writer.listTraceRecords();
  assert.equal(records.length, 2);
  assert.equal(records[0].sequence, 1);
  assert.equal(records[1].sequence, 2);
});

test("listTraceRecords is copy-safe and external mutation cannot affect internal state", () => {
  const writer = createLocalTraceWriter();
  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  const records = writer.listTraceRecords();
  assert.throws(() => {
    (records[0].error_codes as string[]).push("INJECTED");
  });
  assert.throws(() => {
    (records[0].metadata as { deterministic_key: string }).deterministic_key = "mutated";
  });

  const fresh = writer.listTraceRecords();
  assert.equal(fresh[0].error_codes.includes("INJECTED"), false);
  assert.notEqual(fresh[0].metadata.deterministic_key, "mutated");
});

test("trace links intent_id and decision_id", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  const [record] = writer.listTraceRecords();
  assert.equal(record.intent_id, baseIntent.intent_id);
  assert.equal(record.decision_id, result.decision_id);
});
