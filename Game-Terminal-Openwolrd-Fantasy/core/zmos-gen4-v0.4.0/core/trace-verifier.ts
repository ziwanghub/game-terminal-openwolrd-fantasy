import * as fsSync from "node:fs";
import { promises as fs } from "node:fs";
import * as path from "node:path";
import * as readline from "node:readline";

import { getCanonicalPayload, computeTraceHash } from "./trace-crypto.js";
import { createHash } from "node:crypto";
import type { TraceRecord } from "./trace-writer.js";

const STATE_FILE_PATH = path.join(process.cwd(), ".z-mos", "state", "trace-integrity.json");

export type IntegrityStatus = "valid" | "tampered" | "error";

export interface IntegrityState {
  last_verified_sequence: number;
  status: IntegrityStatus;
  last_verified_at: string;
  tampered_at_sequence: number | null;
  enforcement_start_sequence: number | null;
}

export interface VerifyResult {
  status: IntegrityStatus;
  checked_entries: number;
  tampered_at_sequence: number | null;
  verified_at: string;
  enforcement_start_sequence: number | null;
}

async function writeIntegrityState(state: IntegrityState): Promise<void> {
  const dir = path.dirname(STATE_FILE_PATH);
  const tempPath = path.join(dir, ".trace-integrity.tmp");
  await fs.mkdir(dir, { recursive: true });
  await fs.writeFile(tempPath, JSON.stringify(state, null, 2), "utf8");
  await fs.rename(tempPath, STATE_FILE_PATH);
}

async function computeSegmentHashStream(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const hash = createHash("sha256");
    const stream = fsSync.createReadStream(filePath);
    stream.on("data", (chunk) => hash.update(chunk));
    stream.on("end", () => resolve(hash.digest("hex")));
    stream.on("error", reject);
  });
}

async function getFirstLine(filePath: string): Promise<string | null> {
  const fileStream = fsSync.createReadStream(filePath);
  const rl = readline.createInterface({ input: fileStream, crlfDelay: Infinity });
  for await (const line of rl) {
    if (line.trim()) {
      rl.close();
      return line;
    }
  }
  return null;
}

export async function verifyTraceIntegrity(tracePath: string): Promise<VerifyResult> {
  let checkedEntries = 0;
  let expectedSequence = 1;
  let expectedPreviousHash = "GENESIS";
  let expectedPreviousSegmentHash = "GENESIS";

  const result: VerifyResult = {
    status: "valid",
    checked_entries: 0,
    tampered_at_sequence: null,
    verified_at: new Date().toISOString(),
    enforcement_start_sequence: null
  };

  try {
    if (!fsSync.existsSync(tracePath)) {
      // Distinguish: fresh project (no session yet) vs initialized project with missing trace
      const sessionPath = path.join(process.cwd(), ".z-mos", "state", "runtime-state.json");
      if (fsSync.existsSync(sessionPath)) {
        // Project is initialized but trace file is absent — treat as integrity error
        result.status = "error";
        await updateStateFile(result, 0);
        return result;
      }
      // Fresh project with no session yet — trace absence is expected
      await updateStateFile(result, 0);
      return result;
    }

    const archiveDir = path.join(path.dirname(tracePath), "archive");
    if (fsSync.existsSync(archiveDir)) {
      const files = await fs.readdir(archiveDir);
      const metaFiles = files.filter(f => f.endsWith(".meta.json")).sort();

      for (const metaFile of metaFiles) {
        const metaContent = await fs.readFile(path.join(archiveDir, metaFile), "utf8");
        const meta = JSON.parse(metaContent);

        const archiveFilename = metaFile.replace(".meta.json", ".jsonl");
        const archivePath = path.join(archiveDir, archiveFilename);

        if (!fsSync.existsSync(archivePath)) {
          result.status = "error";
          result.tampered_at_sequence = expectedSequence;
          return result;
        }

        if (meta.previous_segment_hash !== expectedPreviousSegmentHash) {
          result.status = "tampered";
          result.tampered_at_sequence = expectedSequence;
          return result;
        }

        const actualSegmentHash = await computeSegmentHashStream(archivePath);
        if (actualSegmentHash !== meta.segment_hash) {
          result.status = "tampered";
          result.tampered_at_sequence = expectedSequence;
          return result;
        }

        const firstLine = await getFirstLine(archivePath);
        if (firstLine) {
          const firstRecord = JSON.parse(firstLine) as TraceRecord;
          if (firstRecord.sequence !== expectedSequence || firstRecord.previous_hash !== expectedPreviousHash) {
            result.status = "tampered";
            result.tampered_at_sequence = expectedSequence;
            return result;
          }
          if (result.enforcement_start_sequence === null && firstRecord.sequence !== undefined) {
            result.enforcement_start_sequence = firstRecord.sequence;
          }
        }

        checkedEntries += (meta.end_sequence - meta.start_sequence + 1);
        expectedSequence = meta.end_sequence + 1;
        expectedPreviousHash = meta.end_hash;
        expectedPreviousSegmentHash = meta.segment_hash;
      }
    }

    const fileStream = fsSync.createReadStream(tracePath);
    const rl = readline.createInterface({
      input: fileStream,
      crlfDelay: Infinity
    });

    for await (const line of rl) {
      if (!line.trim()) continue;

      let record: TraceRecord;
      try {
        record = JSON.parse(line) as TraceRecord;
      } catch (e) {
        result.status = "error";
        result.tampered_at_sequence = expectedSequence;
        break;
      }

      // Skip legacy entries
      if (!record.current_hash) {
        continue;
      }

      if (result.enforcement_start_sequence === null && record.sequence !== undefined) {
        result.enforcement_start_sequence = record.sequence;
      }

      checkedEntries++;

      const { sequence, previous_hash, current_hash, timestamp } = record;

      if (sequence !== expectedSequence || previous_hash !== expectedPreviousHash) {
        result.status = "tampered";
        result.tampered_at_sequence = sequence !== undefined ? sequence : expectedSequence;
        break;
      }

      const canonicalPayload = getCanonicalPayload(record);
      const computedHash = computeTraceHash(sequence, timestamp, canonicalPayload, previous_hash);

      if (computedHash !== current_hash) {
        result.status = "tampered";
        result.tampered_at_sequence = sequence;
        break;
      }

      expectedSequence = sequence + 1;
      expectedPreviousHash = current_hash;
    }

    result.checked_entries = checkedEntries;
    await updateStateFile(result, expectedSequence > 1 ? expectedSequence - 1 : 0);

    return result;
  } catch (error) {
    result.status = "error";
    result.checked_entries = checkedEntries;
    await updateStateFile(result, expectedSequence > 1 ? expectedSequence - 1 : 0);
    return result;
  }
}

async function updateStateFile(result: VerifyResult, lastVerifiedSequence: number): Promise<void> {
  const state: IntegrityState = {
    last_verified_sequence: lastVerifiedSequence,
    status: result.status,
    last_verified_at: result.verified_at,
    tampered_at_sequence: result.tampered_at_sequence,
    enforcement_start_sequence: result.enforcement_start_sequence
  };
  await writeIntegrityState(state);
}
