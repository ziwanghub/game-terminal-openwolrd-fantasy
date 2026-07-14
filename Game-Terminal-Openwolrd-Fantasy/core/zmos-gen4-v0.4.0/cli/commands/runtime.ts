import { ensureValidLockOrCleanup, listPortLockFiles, readLock } from "../../core/port-lock.js";

export async function runRuntimeLockStatusCommand(): Promise<void> {
  const files = await listPortLockFiles();
  if (files.length === 0) {
    console.log("RUNTIME_LOCK_STATUS: no lock files found");
    return;
  }

  const lines = ["RUNTIME_LOCK_STATUS"];
  for (const filePath of files) {
    const lock = await readLock(filePath);
    const pid = lock?.pid ?? "unknown";
    const port = lock?.port ?? "unknown";
    const project = lock?.project ?? "unknown";
    const runtimeType = lock?.runtime_type ?? "unknown";
    lines.push(`- ${filePath} | pid=${String(pid)} | port=${String(port)} | project=${project} | runtime=${runtimeType}`);
  }

  console.log(lines.join("\n"));
}

export async function runRuntimeClearStaleLocksCommand(): Promise<void> {
  const results = await ensureValidLockOrCleanup();
  const stale = results.filter((entry) => entry.stale);
  const active = results.filter((entry) => !entry.stale);

  const lines = [
    "RUNTIME_CLEAR_STALE_LOCKS",
    `- total: ${results.length}`,
    `- stale_cleared: ${stale.length}`,
    `- active_preserved: ${active.length}`,
  ];
  for (const entry of stale) {
    lines.push(`- cleared: ${entry.filePath} (${entry.reason})`);
  }
  for (const entry of active) {
    lines.push(`- kept: ${entry.filePath} (${entry.reason})`);
  }
  console.log(lines.join("\n"));
}
