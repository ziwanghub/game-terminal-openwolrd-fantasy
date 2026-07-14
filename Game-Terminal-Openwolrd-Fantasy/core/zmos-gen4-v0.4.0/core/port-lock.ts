import { existsSync, promises as fs } from "node:fs";
import os from "node:os";
import * as path from "node:path";

export type PortLockRecord = {
  project?: string;
  pid?: string | number;
  port?: number;
  runtime_type?: string;
  started_at?: string;
};

export type PortLockStatus = {
  filePath: string;
  stale: boolean;
  cleanupSucceeded: boolean;
  reason: string;
  skipped: boolean;
  lock: PortLockRecord | null;
};

const LOCK_DIR = path.join(os.homedir(), ".config", "zmos", "port-locks");

function normalizePid(value: string | number | undefined): number | null {
  if (typeof value === "number" && Number.isInteger(value) && value > 0) return value;
  if (typeof value === "string") {
    const parsed = Number.parseInt(value, 10);
    if (Number.isInteger(parsed) && parsed > 0) return parsed;
  }
  return null;
}

export function isProcessAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

export async function readLock(filePath: string): Promise<PortLockRecord | null> {
  try {
    const raw = await fs.readFile(filePath, "utf8");
    const parsed = JSON.parse(raw) as PortLockRecord;
    return parsed;
  } catch {
    return null;
  }
}

export function isLockStale(
  lock: PortLockRecord | null,
  expected?: { project?: string; runtimeType?: string },
): { stale: boolean; reason: string } {
  if (lock === null) {
    return { stale: true, reason: "lock file malformed or unreadable" };
  }

  const pid = normalizePid(lock.pid);
  if (pid === null) {
    return { stale: true, reason: "missing/invalid pid" };
  }

  if (!isProcessAlive(pid)) {
    return { stale: true, reason: `dead pid: ${pid}` };
  }

  if (expected?.project && lock.project && expected.project !== lock.project) {
    return {
      stale: true,
      reason: `project mismatch (${lock.project} != ${expected.project})`,
    };
  }

  if (expected?.runtimeType && lock.runtime_type && expected.runtimeType !== lock.runtime_type) {
    return {
      stale: true,
      reason: `runtime mismatch (${lock.runtime_type} != ${expected.runtimeType})`,
    };
  }

  return { stale: false, reason: "active lock" };
}

export async function clearStaleLock(filePath: string): Promise<boolean> {
  try {
    await fs.unlink(filePath);
    return true;
  } catch {
    return false;
  }
}

export async function listPortLockFiles(): Promise<string[]> {
  if (!existsSync(LOCK_DIR)) {
    return [];
  }
  try {
    const files = await fs.readdir(LOCK_DIR);
    return files
      .filter((file) => file.endsWith(".lock.json"))
      .map((file) => path.join(LOCK_DIR, file))
      .sort();
  } catch {
    return [];
  }
}

export async function ensureValidLockOrCleanup(expected?: {
  project?: string;
  runtimeType?: string;
  scopeProjectOnly?: boolean;
}): Promise<PortLockStatus[]> {
  const files = await listPortLockFiles();
  const results: PortLockStatus[] = [];

  for (const filePath of files) {
    const lock = await readLock(filePath);
    const scopeProjectOnly = expected?.scopeProjectOnly === true;
    if (scopeProjectOnly && expected?.project && lock?.project && lock.project !== expected.project) {
      results.push({
        filePath,
        stale: false,
        cleanupSucceeded: true,
        reason: `ignored lock from other project (${lock.project})`,
        skipped: true,
        lock,
      });
      continue;
    }
    const decision = isLockStale(lock, expected);
    let cleanupSucceeded = true;
    if (decision.stale) {
      cleanupSucceeded = await clearStaleLock(filePath);
    }
    results.push({
      filePath,
      stale: decision.stale,
      cleanupSucceeded,
      reason: decision.reason,
      skipped: false,
      lock,
    });
  }

  return results;
}
