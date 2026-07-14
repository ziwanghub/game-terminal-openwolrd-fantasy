import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { runLocalIntent } from "../../core/gen4/local-kernel/harness.ts";
import { createLocalTraceWriter } from "../../core/gen4/local-kernel/trace.ts";
import { replayLocalTraceRecords } from "../../core/gen4/local-kernel/replay.ts";
import { buildLocalEvidencePackage } from "../../core/gen4/local-kernel/evidence.ts";
import { buildValidTrustEnvelope } from "./fixtures/trust-envelope.fixtures.ts";

const now = () => "2026-05-28T00:00:00Z";

const baseIntent = {
  intent_id: "intent-e2e-001",
  subject_ref: "subject-e2e-001",
  issuer_ref: "issuer-e2e-001",
  requested_action: "read",
  requested_resource: "truth",
  human_authorization_ref: "human-auth-e2e-001",
  trust_envelope_ref: "envelope-001",
  metadata: {
    submitted_at: "2026-05-28T00:00:00Z",
    trace_correlation_id: "trace-corr-e2e-001",
    replay_nonce: "replay-e2e-001",
  },
};

test("Scenario 1: valid intent accepted flow end-to-end", () => {
  const writer = createLocalTraceWriter();
  const decision = runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  assert.equal(decision.status, "accepted");

  const trace = writer.listTraceRecords();
  assert.equal(trace.length, 1);
  assert.equal(trace[0].decision_status, "accepted");
  assert.equal(trace[0].intent_id, baseIntent.intent_id);
  assert.equal(trace[0].decision_id, decision.decision_id);

  const replay = replayLocalTraceRecords(trace);
  assert.equal(replay.status, "completed");
  assert.equal(replay.accepted_count, 1);

  const evidence = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });
  assert.equal(evidence.status, "complete");
  assert.equal(evidence.accepted_count, 1);
});

test("Scenario 2: missing human authorization rejected flow end-to-end", () => {
  const writer = createLocalTraceWriter();
  const decision = runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-e2e-002",
      human_authorization_ref: "",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  assert.equal(decision.status, "rejected");
  assert.equal(decision.error_codes.includes("MISSING_HUMAN_AUTHORIZATION"), true);
  assert.notEqual(decision.status, "accepted");

  const trace = writer.listTraceRecords();
  assert.equal(trace.length, 1);
  assert.equal(trace[0].decision_status, "rejected");
  assert.equal(trace[0].error_codes.includes("MISSING_HUMAN_AUTHORIZATION"), true);

  const replay = replayLocalTraceRecords(trace);
  assert.equal(replay.status, "completed");

  const evidence = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });
  assert.equal(evidence.status, "complete");
  assert.equal(evidence.rejected_count, 1);
  assert.equal(evidence.error_codes.includes("MISSING_HUMAN_AUTHORIZATION"), true);
  assert.equal(evidence.invariant_violation_refs.includes("MISSING_HUMAN_AUTHORIZATION"), true);
});

test("Scenario 3: trust scope violation rejected flow end-to-end", () => {
  const writer = createLocalTraceWriter();
  const decision = runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-e2e-003",
      requested_action: "delete",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  assert.equal(decision.status, "rejected");
  assert.equal(decision.error_codes[0], "TRUST_SCOPE_VIOLATION");

  const trace = writer.listTraceRecords();
  assert.equal(trace.length, 1);
  assert.equal(trace[0].error_codes[0], "TRUST_SCOPE_VIOLATION");

  const replay = replayLocalTraceRecords(trace);
  assert.equal(replay.status, "completed");

  const evidence = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });
  assert.equal(evidence.status, "complete");
  assert.equal(evidence.rejected_count, 1);
  assert.equal(evidence.invariant_violation_refs.includes("TRUST_SCOPE_VIOLATION"), true);
});

test("Scenario 4: ambiguous verification quarantine flow end-to-end", () => {
  const writer = createLocalTraceWriter();
  const decision = runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-e2e-004",
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

  assert.equal(decision.status, "quarantined");
  assert.notEqual(decision.status, "accepted");

  const trace = writer.listTraceRecords();
  assert.equal(trace.length, 1);
  assert.equal(trace[0].decision_status, "quarantined");

  const replay = replayLocalTraceRecords(trace);
  assert.equal(replay.status, "completed");
  assert.equal(replay.quarantined_count, 1);

  const evidence = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });
  assert.equal(evidence.status, "complete");
  assert.equal(evidence.quarantined_count, 1);
  assert.equal(evidence.error_codes.includes("AMBIGUOUS_VERIFICATION"), true);
});

test("Scenario 5: mixed trace replay flow deterministic and complete", () => {
  const writer = createLocalTraceWriter();

  runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-e2e-005-a",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-e2e-005-r",
      requested_resource: "restricted-resource",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-e2e-005-q",
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

  const trace = writer.listTraceRecords();
  assert.equal(trace.length, 3);

  const replayA = replayLocalTraceRecords(trace);
  const replayB = replayLocalTraceRecords(trace);
  assert.deepEqual(replayA, replayB);
  assert.equal(replayA.accepted_count, 1);
  assert.equal(replayA.rejected_count, 1);
  assert.equal(replayA.quarantined_count, 1);

  const evidence = buildLocalEvidencePackage({ trace_records: trace, replay_result: replayA });
  assert.equal(evidence.status, "complete");
  assert.equal(evidence.accepted_count, 1);
  assert.equal(evidence.rejected_count, 1);
  assert.equal(evidence.quarantined_count, 1);
});

test("Scenario 6: failed replay blocks complete evidence", () => {
  const writer = createLocalTraceWriter();

  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });
  runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-e2e-006-b",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  const trace = writer.listTraceRecords();
  const broken = trace.map((record) => ({ ...record }));
  broken[1].sequence = broken[0].sequence;

  const replay = replayLocalTraceRecords(broken as any);
  assert.equal(replay.status, "failed");

  const evidence = buildLocalEvidencePackage({ trace_records: broken as any, replay_result: replay });
  assert.notEqual(evidence.status, "complete");
  assert.equal(evidence.status, "failed");
  assert.equal(evidence.error_codes.includes("EVIDENCE_REPLAY_FAILED"), true);
});

test("no network surface imports in local-kernel", () => {
  const root = path.resolve("core/gen4/local-kernel");
  const disallowed = ["http", "https", "net", "tls", "dgram", "ws", "child_process"];

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
