import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import {
  appendLocalTraceRecordToFile,
  loadLocalTraceRecordsFromFile,
} from "../../core/gen4/local-kernel/trace-persistence.ts";
import { createLocalTraceWriter } from "../../core/gen4/local-kernel/trace.ts";
import { runLocalIntent } from "../../core/gen4/local-kernel/harness.ts";
import { replayLocalTraceRecords } from "../../core/gen4/local-kernel/replay.ts";
import { buildValidTrustEnvelope } from "./fixtures/trust-envelope.fixtures.ts";

const now = () => "2026-05-28T00:00:00Z";

const baseIntent = {
  intent_id: "intent-persist-001",
  subject_ref: "subject-persist-001",
  issuer_ref: "issuer-persist-001",
  requested_action: "read",
  requested_resource: "truth",
  human_authorization_ref: "human-auth-persist-001",
  trust_envelope_ref: "envelope-001",
  metadata: {
    submitted_at: "2026-05-28T00:00:00Z",
    trace_correlation_id: "trace-corr-persist-001",
    replay_nonce: "replay-persist-001",
  },
};

async function newFilePath(name: string): Promise<string> {
  const dir = await mkdtemp(path.join(tmpdir(), "zmos-local-kernel-"));
  return path.join(dir, name);
}

function buildTraceRecords() {
  const writer = createLocalTraceWriter();

  runLocalIntent(baseIntent, {
    trust_envelope: buildValidTrustEnvelope(),
    trace_writer: writer,
    now,
  });

  runLocalIntent(
    { ...baseIntent, intent_id: "intent-persist-002", requested_action: "delete" },
    {
      trust_envelope: buildValidTrustEnvelope(),
      trace_writer: writer,
      now,
    },
  );

  return writer.listTraceRecords();
}

test("append one trace record to local file", async () => {
  const filePath = await newFilePath("trace.jsonl");
  const [record] = buildTraceRecords();

  const result = await appendLocalTraceRecordToFile({ file_path: filePath, record });
  assert.equal(result.status, "written");
  assert.equal(result.record_count, 1);

  const data = await readFile(filePath, "utf8");
  assert.equal(data.trim().length > 0, true);
});

test("append multiple records preserves file order", async () => {
  const filePath = await newFilePath("trace.jsonl");
  const records = buildTraceRecords();

  await appendLocalTraceRecordToFile({ file_path: filePath, record: records[0] });
  await appendLocalTraceRecordToFile({ file_path: filePath, record: records[1] });

  const loaded = await loadLocalTraceRecordsFromFile({ file_path: filePath });
  assert.equal(loaded.status, "loaded");
  assert.equal(loaded.records.length, 2);
  assert.equal(loaded.records[0].sequence, 1);
  assert.equal(loaded.records[1].sequence, 2);
});

test("load trace records from file and replay deterministically", async () => {
  const filePath = await newFilePath("trace.jsonl");
  const records = buildTraceRecords();

  for (const record of records) {
    await appendLocalTraceRecordToFile({ file_path: filePath, record });
  }

  const loaded = await loadLocalTraceRecordsFromFile({ file_path: filePath });
  assert.equal(loaded.status, "loaded");

  const a = replayLocalTraceRecords(loaded.records);
  const b = replayLocalTraceRecords(loaded.records);

  assert.deepEqual(a, b);
  assert.equal(a.status, "completed");
});

test("loaded records cannot be externally mutated", async () => {
  const filePath = await newFilePath("trace.jsonl");
  const [record] = buildTraceRecords();

  await appendLocalTraceRecordToFile({ file_path: filePath, record });
  const loaded = await loadLocalTraceRecordsFromFile({ file_path: filePath });
  assert.equal(loaded.status, "loaded");

  assert.throws(() => {
    (loaded.records as unknown as Array<unknown>).push({});
  });
  assert.throws(() => {
    (loaded.records[0].error_codes as string[]).push("INJECTED");
  });
});

test("append does not overwrite existing content", async () => {
  const filePath = await newFilePath("trace.jsonl");
  const records = buildTraceRecords();

  await appendLocalTraceRecordToFile({ file_path: filePath, record: records[0] });
  const firstSize = (await readFile(filePath, "utf8")).length;

  await appendLocalTraceRecordToFile({ file_path: filePath, record: records[1] });
  const secondData = await readFile(filePath, "utf8");
  const secondSize = secondData.length;

  assert.equal(secondSize > firstSize, true);
  assert.equal(secondData.trim().split("\n").length, 2);
});

test("malformed JSON fails closed", async () => {
  const filePath = await newFilePath("trace.jsonl");
  await writeFile(filePath, "{bad-json}\n", "utf8");

  const loaded = await loadLocalTraceRecordsFromFile({ file_path: filePath });
  assert.equal(loaded.status, "failed");
  assert.equal(loaded.error_codes[0], "TRACE_PERSISTENCE_MALFORMED_JSON");
});

test("malformed trace record fails closed", async () => {
  const filePath = await newFilePath("trace.jsonl");
  await writeFile(filePath, `${JSON.stringify({ trace_id: "x", sequence: 1 })}\n`, "utf8");

  const loaded = await loadLocalTraceRecordsFromFile({ file_path: filePath });
  assert.equal(loaded.status, "failed");
  assert.equal(loaded.error_codes[0], "TRACE_PERSISTENCE_MALFORMED_RECORD");
});

test("corrupted sequence can load but replay fails closed", async () => {
  const filePath = await newFilePath("trace.jsonl");
  const records = buildTraceRecords();
  const record1 = records[0];
  const record2 = {
    ...records[1],
    sequence: 3,
    trace_id: "trace-000003",
    metadata: {
      ...records[1].metadata,
      deterministic_key: "3|2026-05-28T00:00:00Z|intent-persist-002|decision-intent-persist-002|rejected",
    },
  };

  await appendLocalTraceRecordToFile({ file_path: filePath, record: record1 });
  await appendLocalTraceRecordToFile({ file_path: filePath, record: record2 });

  const loaded = await loadLocalTraceRecordsFromFile({ file_path: filePath });
  assert.equal(loaded.status, "loaded");

  const replay = replayLocalTraceRecords(loaded.records);
  assert.equal(replay.status, "failed");
  assert.equal(replay.error_codes[0], "REPLAY_SEQUENCE_GAP");
});

test("invalid path fails closed", async () => {
  const [record] = buildTraceRecords();
  const writeResult = await appendLocalTraceRecordToFile({ file_path: "", record });
  assert.equal(writeResult.status, "failed");
  assert.equal(writeResult.error_codes[0], "TRACE_PERSISTENCE_INVALID_PATH");

  const loadResult = await loadLocalTraceRecordsFromFile({ file_path: "" });
  assert.equal(loadResult.status, "failed");
  assert.equal(loadResult.error_codes[0], "TRACE_PERSISTENCE_INVALID_PATH");
});

test("no forbidden imports beyond local fs/path usage in trace-persistence", async () => {
  const sourcePath = path.resolve("core/gen4/local-kernel/trace-persistence.ts");
  const content = await readFile(sourcePath, "utf8");

  const forbidden = ["http", "https", "net", "tls", "dgram", "ws", "child_process"];
  for (const item of forbidden) {
    assert.equal(content.includes(item), false, `Found forbidden import pattern: ${item}`);
  }
});
