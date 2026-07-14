import * as fs from "node:fs";
import * as readline from "node:readline";
import { getTraceFilePath } from "../../core/trace-writer.js";

type TraceEntry = {
  timestamp?: string;
  command?: string;
  execution_status?: string;
  result_class?: string;
  actor?: string;
  details?: Record<string, unknown>;
  sequence?: number;
};

type QueryFilters = {
  status?: string;
  command?: string;
  resultClass?: string;
  last?: number;
  since?: string;
  json: boolean;
};

function parseFilters(args: string[]): QueryFilters {
  const get = (flag: string): string | undefined => {
    const idx = args.indexOf(flag);
    if (idx === -1) return undefined;
    const val = args[idx + 1];
    return val && !val.startsWith("--") ? val : undefined;
  };

  const lastStr = get("--last");
  const last = lastStr ? parseInt(lastStr, 10) : undefined;
  if (lastStr && (isNaN(last!) || last! <= 0)) {
    throw new Error("--last must be a positive integer");
  }

  return {
    status: get("--status"),
    command: get("--command"),
    resultClass: get("--result-class"),
    last,
    since: get("--since"),
    json: args.includes("--json"),
  };
}

async function readAllEntries(): Promise<TraceEntry[]> {
  const tracePath = await getTraceFilePath();
  if (!fs.existsSync(tracePath)) return [];

  const entries: TraceEntry[] = [];
  const stream = fs.createReadStream(tracePath, { encoding: "utf8" });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });

  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      entries.push(JSON.parse(trimmed) as TraceEntry);
    } catch {
      // skip malformed lines
    }
  }

  return entries;
}

function applyFilters(entries: TraceEntry[], filters: QueryFilters): TraceEntry[] {
  let result = entries;

  if (filters.status) {
    const s = filters.status.toLowerCase();
    result = result.filter((e) => e.execution_status?.toLowerCase() === s);
  }

  if (filters.command) {
    const c = filters.command.toLowerCase();
    result = result.filter((e) => e.command?.toLowerCase().includes(c));
  }

  if (filters.resultClass) {
    const rc = filters.resultClass.toLowerCase();
    result = result.filter((e) => e.result_class?.toLowerCase() === rc);
  }

  if (filters.since) {
    const sinceMs = Date.parse(filters.since);
    if (isNaN(sinceMs)) throw new Error(`--since: invalid date "${filters.since}"`);
    result = result.filter((e) => {
      if (!e.timestamp) return false;
      return Date.parse(e.timestamp) >= sinceMs;
    });
  }

  if (filters.last !== undefined) {
    result = result.slice(-filters.last);
  }

  return result;
}

function formatEntry(e: TraceEntry, index: number): string {
  const seq = e.sequence !== undefined ? `#${e.sequence}` : `[${index}]`;
  const ts = e.timestamp ? e.timestamp.slice(0, 19) : "unknown";
  const cmd = e.command ?? "unknown";
  const status = e.execution_status ?? "unknown";
  const cls = e.result_class ?? "unknown";
  const actor = e.actor ?? "unknown";
  return `${seq}  ${ts}  ${status.padEnd(9)}  ${cls.padEnd(32)}  actor=${actor}  cmd=${cmd}`;
}

export async function runTraceQueryCommand(args: string[]): Promise<void> {
  const filters = parseFilters(args);
  const allEntries = await readAllEntries();
  const matched = applyFilters(allEntries, filters);

  if (filters.json) {
    console.log(JSON.stringify(matched, null, 2));
    return;
  }

  const totalEntries = allEntries.length;
  const appliedFilters: string[] = [];
  if (filters.status) appliedFilters.push(`status=${filters.status}`);
  if (filters.command) appliedFilters.push(`command~${filters.command}`);
  if (filters.resultClass) appliedFilters.push(`result-class=${filters.resultClass}`);
  if (filters.since) appliedFilters.push(`since=${filters.since}`);
  if (filters.last !== undefined) appliedFilters.push(`last=${filters.last}`);

  console.log(`Trace Query`);
  console.log(`  Total entries: ${totalEntries}`);
  console.log(`  Matched: ${matched.length}`);
  if (appliedFilters.length > 0) {
    console.log(`  Filters: ${appliedFilters.join(", ")}`);
  }
  console.log("");

  if (matched.length === 0) {
    console.log("  (no matching entries)");
    return;
  }

  for (let i = 0; i < matched.length; i++) {
    console.log(formatEntry(matched[i], i));
  }
}
