import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { runLocalIntent } from "../../core/gen4/local-kernel/harness.ts";
import { createLocalTraceWriter } from "../../core/gen4/local-kernel/trace.ts";
import { replayLocalTraceRecords } from "../../core/gen4/local-kernel/replay.ts";
import {
  buildExpiredTrustEnvelope,
  buildRevokedEnvelopeWithoutRevocationRef,
  buildSelfAuthorizedEscalationEnvelope,
  buildValidTrustEnvelope,
} from "./fixtures/trust-envelope.fixtures.ts";

const now = () => "2026-05-28T00:00:00Z";

const baseIntent = {
  intent_id: "intent-invariant-001",
  subject_ref: "subject-invariant-001",
  issuer_ref: "issuer-invariant-001",
  requested_action: "read",
  requested_resource: "truth",
  human_authorization_ref: "human-auth-invariant-001",
  trust_envelope_ref: "envelope-001",
  metadata: {
    submitted_at: "2026-05-28T00:00:00Z",
    trace_correlation_id: "trace-corr-invariant-001",
    replay_nonce: "replay-invariant-001",
  },
};

test("invariant: no hidden authority (missing trust context is rejected)", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(baseIntent, { trace_writer: writer, now });

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes.includes("TRUST_ENVELOPE_MISSING"), true);
  assert.equal(result.invariant_violations.includes("TRUST_ENVELOPE_MISSING"), true);
  assert.equal(writer.listTraceRecords().length, 1);
  assert.notEqual(result.status, "accepted");
});

test("invariant: no hidden authority (trust envelope ref mismatch is rejected)", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(
    {
      ...baseIntent,
      trust_envelope_ref: "different-envelope-ref",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRUST_ENVELOPE_REF_MISMATCH");
  assert.equal(result.invariant_violations[0], "TRUST_ENVELOPE_REF_MISMATCH");
  assert.equal(writer.listTraceRecords().length, 1);
  assert.notEqual(result.status, "accepted");
});

test("invariant: no self-delegation/self-authorized escalation", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(baseIntent, {
    trust_envelope: buildSelfAuthorizedEscalationEnvelope(),
    trace_writer: writer,
    now,
  });

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRUST_ENVELOPE_INVALID");
  assert.equal(result.invariant_violations[0], "TRUST_ENVELOPE_INVALID");
  assert.equal(writer.listTraceRecords().length, 1);
  assert.notEqual(result.status, "accepted");
});

test("invariant: intent scope must stay within envelope scope", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(
    {
      ...baseIntent,
      requested_action: "delete",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRUST_SCOPE_VIOLATION");
  assert.equal(result.invariant_violations[0], "TRUST_SCOPE_VIOLATION");
  assert.equal(writer.listTraceRecords().length, 1);
  assert.notEqual(result.status, "accepted");
});

test("invariant: missing human authorization fails closed", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(
    {
      ...baseIntent,
      human_authorization_ref: "",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "MISSING_HUMAN_AUTHORIZATION");
  assert.equal(result.invariant_violations[0], "MISSING_HUMAN_AUTHORIZATION");
  assert.equal(writer.listTraceRecords().length, 1);
  assert.notEqual(result.status, "accepted");
});

test("invariant: invalid trust envelope fails closed", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(baseIntent, {
    trust_envelope: buildExpiredTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRUST_ENVELOPE_INVALID");
  assert.equal(result.invariant_violations[0], "TRUST_ENVELOPE_INVALID");
  assert.equal(writer.listTraceRecords().length, 1);
  assert.notEqual(result.status, "accepted");
});

test("invariant: stale/revoked trust fails closed when represented by fixture", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(baseIntent, {
    trust_envelope: buildRevokedEnvelopeWithoutRevocationRef(),
    trace_writer: writer,
    now,
  });

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRUST_ENVELOPE_INVALID");
  assert.equal(writer.listTraceRecords().length, 1);
  assert.notEqual(result.status, "accepted");
});

test("invariant: trace is append-only and deterministic sequence", () => {
  const writer = createLocalTraceWriter();

  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-invariant-002",
      requested_resource: "membership",
    },
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

test("invariant: rejected decisions emit trace evidence", () => {
  const writer = createLocalTraceWriter();
  runLocalIntent(
    {
      ...baseIntent,
      requested_resource: "unknown-resource",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  const records = writer.listTraceRecords();
  assert.equal(records.length, 1);
  assert.equal(records[0].decision_status, "rejected");
  assert.equal(records[0].error_codes.length > 0, true);
});

test("invariant: quarantined decisions emit trace evidence", () => {
  const writer = createLocalTraceWriter();
  runLocalIntent(
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

  const records = writer.listTraceRecords();
  assert.equal(records.length, 1);
  assert.equal(records[0].decision_status, "quarantined");
  assert.equal(records[0].error_codes.includes("AMBIGUOUS_VERIFICATION"), true);
});

test("invariant: deterministic replay summary for same trace", () => {
  const writer = createLocalTraceWriter();

  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-invariant-003",
      requested_action: "delete",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  const trace = writer.listTraceRecords();
  const a = replayLocalTraceRecords(trace);
  const b = replayLocalTraceRecords(trace);
  assert.deepEqual(a, b);
  assert.equal(a.status, "completed");
});

test("invariant: replay fails closed on malformed/gapped/duplicated trace", () => {
  const writer = createLocalTraceWriter();
  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });
  runLocalIntent(
    { ...baseIntent, intent_id: "intent-invariant-004" },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  const trace = writer.listTraceRecords();

  const duplicated = [...trace, { ...trace[1], sequence: trace[0].sequence }];
  const duplicateResult = replayLocalTraceRecords(duplicated as any);
  assert.equal(duplicateResult.status, "failed");

  const gapped = trace.map((r) => ({ ...r }));
  gapped[1].sequence = 3;
  const gapResult = replayLocalTraceRecords(gapped);
  assert.equal(gapResult.status, "failed");

  const malformed = trace.map((r) => ({ ...r })) as any[];
  delete malformed[0].intent_id;
  const malformedResult = replayLocalTraceRecords(malformed as any);
  assert.equal(malformedResult.status, "failed");
});

test("invariant: no network surface imports in local-kernel", () => {
  const root = path.resolve("core/gen4/local-kernel");
  const disallowed = [
    "http",
    "https",
    "net",
    "tls",
    "dgram",
    "ws",
    "child_process",
  ];

  const entries = fs.readdirSync(root).filter((name) => name.endsWith(".ts"));
  for (const entry of entries) {
    const content = fs.readFileSync(path.join(root, entry), "utf8");
    for (const pattern of disallowed) {
      assert.equal(
        content.includes(pattern),
        false,
        `Found disallowed pattern \"${pattern}\" in ${entry}`,
      );
    }
  }
});
