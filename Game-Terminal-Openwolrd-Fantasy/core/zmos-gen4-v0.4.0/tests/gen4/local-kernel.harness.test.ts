import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { runLocalIntent } from "../../core/gen4/local-kernel/harness.ts";
import { createLocalTraceWriter } from "../../core/gen4/local-kernel/trace.ts";
import {
  buildExpiredTrustEnvelope,
  buildValidTrustEnvelope,
} from "./fixtures/trust-envelope.fixtures.ts";

const now = () => "2026-05-28T00:00:00Z";

const validIntent = {
  intent_id: "intent-100",
  subject_ref: "subject-100",
  issuer_ref: "issuer-100",
  requested_action: "read",
  requested_resource: "truth",
  human_authorization_ref: "human-auth-100",
  trust_envelope_ref: "envelope-001",
  metadata: {
    submitted_at: "2026-05-28T00:00:00Z",
    trace_correlation_id: "trace-100",
    replay_nonce: "nonce-100",
  },
};

test("runLocalIntent accepts valid intent + valid trust envelope with mock-only execution", () => {
  const result = runLocalIntent(validIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    now,
  });

  assert.equal(result.status, "accepted");
  assert.equal(result.metadata.execution_mode, "mock-only");
});

test("runLocalIntent still works without trace writer", () => {
  const result = runLocalIntent(validIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    now,
  });
  assert.equal(result.status, "accepted");
});

test("runLocalIntent rejects missing trust envelope fail-closed", () => {
  const result = runLocalIntent(validIntent, { now });
  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRUST_ENVELOPE_MISSING");
});

test("runLocalIntent rejects invalid trust envelope fail-closed", () => {
  const result = runLocalIntent(validIntent, {
    trust_envelope: buildExpiredTrustEnvelope(),
    now,
  });
  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRUST_ENVELOPE_INVALID");
});

test("runLocalIntent rejects trust envelope ref mismatch", () => {
  const result = runLocalIntent(
    {
      ...validIntent,
      trust_envelope_ref: "envelope-mismatch",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      now,
    },
  );

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRUST_ENVELOPE_REF_MISMATCH");
});

test("runLocalIntent rejects action scope mismatch", () => {
  const result = runLocalIntent(
    {
      ...validIntent,
      requested_action: "delete",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      now,
    },
  );

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRUST_SCOPE_VIOLATION");
});

test("runLocalIntent rejects resource scope mismatch", () => {
  const result = runLocalIntent(
    {
      ...validIntent,
      requested_resource: "secrets",
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      now,
    },
  );

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRUST_SCOPE_VIOLATION");
});

test("runLocalIntent rejects missing human authorization fail-closed", () => {
  const invalid = {
    ...validIntent,
    human_authorization_ref: "",
  };

  const result = runLocalIntent(invalid, {
    trust_envelope: buildValidTrustEnvelope(),
    now,
  });
  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "MISSING_HUMAN_AUTHORIZATION");
});

test("runLocalIntent rejects malformed intent fail-closed", () => {
  const result = runLocalIntent(null, {
    trust_envelope: buildValidTrustEnvelope(),
    now,
  });
  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "MALFORMED_INTENT");
});

test("runLocalIntent quarantines ambiguous verification", () => {
  const result = runLocalIntent(
    {
      ...validIntent,
      metadata: {
        ...validIntent.metadata,
        ambiguous_verification: true,
      },
    },
    {
      trust_envelope: buildValidTrustEnvelope(),
      now,
    },
  );

  assert.equal(result.status, "quarantined");
  assert.equal(result.error_codes[0], "AMBIGUOUS_VERIFICATION");
});

test("accepted result is impossible when trust validation fails", () => {
  const result = runLocalIntent(validIntent, {
    trust_envelope: buildExpiredTrustEnvelope(),
    now,
  });

  assert.notEqual(result.status, "accepted");
  assert.equal(result.status, "rejected");
});

test("trace append failure prevents accepted result", () => {
  const failingTraceWriter = {
    appendTraceRecord() {
      throw new Error("append failure");
    },
    listTraceRecords() {
      return [];
    },
  };

  const result = runLocalIntent(validIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: failingTraceWriter,
    now,
  });

  assert.equal(result.status, "rejected");
  assert.equal(result.error_codes[0], "TRACE_APPEND_FAILURE");
});

test("runLocalIntent emits trace when writer is provided", () => {
  const writer = createLocalTraceWriter();
  const result = runLocalIntent(validIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  assert.equal(result.status, "accepted");
  const traces = writer.listTraceRecords();
  assert.equal(traces.length, 1);
  assert.equal(traces[0].intent_id, validIntent.intent_id);
  assert.equal(traces[0].decision_id, result.decision_id);
});

test("local-kernel module introduces no networking imports", () => {
  const root = path.resolve("core/gen4/local-kernel");
  const disallowed = [
    "http",
    "https",
    "net",
    "tls",
    "dgram",
    "ws",
    "child_process",
    "fetch(",
    "XMLHttpRequest",
    "socket",
    "rpc",
  ];

  const entries = fs.readdirSync(root).filter((name) => name.endsWith(".ts"));
  for (const entry of entries) {
    const content = fs.readFileSync(path.join(root, entry), "utf8");
    for (const pattern of disallowed) {
      assert.equal(
        content.includes(pattern),
        false,
        `Found disallowed network pattern \"${pattern}\" in ${entry}`,
      );
    }
  }
});
