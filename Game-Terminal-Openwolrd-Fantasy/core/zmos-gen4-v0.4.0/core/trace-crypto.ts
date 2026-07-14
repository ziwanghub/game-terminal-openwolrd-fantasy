import * as crypto from "node:crypto";
import type { TraceRecordContract } from "../contracts/trace.js";

export function getCanonicalPayload(record: Partial<TraceRecordContract>): string {
  // Create a copy of the record for hashing payload
  const clone = { ...record };
  
  // Exclude integrity fields
  delete clone.sequence;
  delete clone.previous_hash;
  delete clone.current_hash;

  // Canonical JSON stringification (sorted keys, no extra whitespace)
  return stringifyCanonical(clone);
}

function stringifyCanonical(obj: unknown): string {
  if (obj === null || typeof obj !== "object") {
    return JSON.stringify(obj);
  }

  if (Array.isArray(obj)) {
    const arr = obj.map((item) => (item === undefined ? null : item));
    return `[${arr.map(stringifyCanonical).join(",")}]`;
  }

  const keys = Object.keys(obj as Record<string, unknown>).sort();
  const parts: string[] = [];

  for (const key of keys) {
    const val = (obj as Record<string, unknown>)[key];
    if (val !== undefined) {
      parts.push(`${JSON.stringify(key)}:${stringifyCanonical(val)}`);
    }
  }

  return `{${parts.join(",")}}`;
}

export function computeTraceHash(
  sequence: number,
  timestamp: string,
  canonicalPayload: string,
  previousHash: string,
): string {
  const input = `${sequence}|${timestamp}|${canonicalPayload}|${previousHash}`;
  return crypto.createHash("sha256").update(input).digest("hex");
}
