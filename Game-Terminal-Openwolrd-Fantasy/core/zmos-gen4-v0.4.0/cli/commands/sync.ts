import { runMacroSequence } from "./macros/runner.js";

export async function runSyncCommand(): Promise<void> {
  await runMacroSequence("sync", [
    { label: "Build Truth Contract", command: ["truth", "build"] },
    { label: "Validate Schema", command: ["schema", "validate"] },
    { label: "Clear Stale Locks", command: ["runtime", "clear-stale-locks"] },
    { label: "Preflight Check", command: ["preflight"] },
  ]);
}
