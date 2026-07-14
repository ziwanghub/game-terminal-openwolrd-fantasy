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
  intent_id: "intent-evidence-001",
  subject_ref: "subject-evidence-001",
  issuer_ref: "issuer-evidence-001",
  requested_action: "read",
  requested_resource: "truth",
  human_authorization_ref: "human-auth-evidence-001",
  trust_envelope_ref: "envelope-001",
  metadata: {
    submitted_at: "2026-05-28T00:00:00Z",
    trace_correlation_id: "trace-corr-evidence-001",
    replay_nonce: "replay-evidence-001",
  },
};

function buildTraceAndReplay() {
  const writer = createLocalTraceWriter();

  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  runLocalIntent(
    { ...baseIntent, intent_id: "intent-evidence-002", requested_action: "delete" },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  runLocalIntent(
    {
      ...baseIntent,
      intent_id: "intent-evidence-003",
      metadata: { ...baseIntent.metadata, ambiguous_verification: true },
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  const trace = writer.listTraceRecords();
  const replay = replayLocalTraceRecords(trace);
  return { trace, replay };
}

test("complete package from valid trace + completed replay", () => {
  const { trace, replay } = buildTraceAndReplay();
  const pkg = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });

  assert.equal(pkg.status, "complete");
  assert.equal(pkg.replay_id, replay.replay_id);
  assert.equal(pkg.trace_ids.length, trace.length);
  assert.equal(pkg.decision_ids.length, trace.length);
  assert.equal(pkg.intent_ids.length, trace.length);
});

test("failed package from failed replay", () => {
  const { trace, replay } = buildTraceAndReplay();
  const failedReplay = {
    ...replay,
    status: "failed" as const,
    metadata: { ...replay.metadata, failure_reason: "forced failure" },
  };

  const pkg = buildLocalEvidencePackage({ trace_records: trace, replay_result: failedReplay });
  assert.equal(pkg.status, "failed");
  assert.equal(pkg.error_codes.includes("EVIDENCE_REPLAY_FAILED"), true);
});

test("trace/replay count mismatch is incomplete fail-closed posture", () => {
  const { trace, replay } = buildTraceAndReplay();
  const mismatchReplay = { ...replay, record_count: replay.record_count + 1 };

  const pkg = buildLocalEvidencePackage({ trace_records: trace, replay_result: mismatchReplay });
  assert.equal(pkg.status, "incomplete");
  assert.equal(pkg.error_codes.includes("EVIDENCE_COUNT_MISMATCH"), true);
});

test("decision ID mismatch is incomplete fail-closed posture", () => {
  const { trace, replay } = buildTraceAndReplay();
  const mismatchReplay = {
    ...replay,
    decision_ids: [...replay.decision_ids.slice(0, 2), "decision-mismatch"],
  };

  const pkg = buildLocalEvidencePackage({ trace_records: trace, replay_result: mismatchReplay });
  assert.equal(pkg.status, "incomplete");
  assert.equal(pkg.error_codes.includes("EVIDENCE_DECISION_ID_MISMATCH"), true);
});

test("intent ID mismatch is incomplete fail-closed posture", () => {
  const { trace, replay } = buildTraceAndReplay();
  const mismatchReplay = {
    ...replay,
    intent_ids: [...replay.intent_ids.slice(0, 2), "intent-mismatch"],
  };

  const pkg = buildLocalEvidencePackage({ trace_records: trace, replay_result: mismatchReplay });
  assert.equal(pkg.status, "incomplete");
  assert.equal(pkg.error_codes.includes("EVIDENCE_INTENT_ID_MISMATCH"), true);
});

test("identical input produces deterministic package", () => {
  const { trace, replay } = buildTraceAndReplay();
  const a = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });
  const b = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });
  assert.deepEqual(a, b);
});

test("package result is immutable and does not mutate source inputs", () => {
  const { trace, replay } = buildTraceAndReplay();
  const traceSnapshot = structuredClone(trace);
  const replaySnapshot = structuredClone(replay);
  const pkg = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });

  assert.throws(() => {
    (pkg.decision_ids as string[]).push("inject");
  });

  assert.deepEqual(trace, traceSnapshot);
  assert.deepEqual(replay, replaySnapshot);
});

test("aggregates error codes and invariant refs deterministically", () => {
  const { trace, replay } = buildTraceAndReplay();
  const pkg = buildLocalEvidencePackage({ trace_records: trace, replay_result: replay });

  assert.deepEqual(pkg.error_codes, ["AMBIGUOUS_VERIFICATION", "TRUST_SCOPE_VIOLATION"]);
  assert.deepEqual(pkg.invariant_violation_refs, ["AMBIGUOUS_VERIFICATION", "TRUST_SCOPE_VIOLATION"]);
});

test("no networking imports introduced in local-kernel", () => {
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
