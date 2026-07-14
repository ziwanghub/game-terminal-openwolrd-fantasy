import { runMacroSequence } from "./macros/runner.js";

export async function runRecoverCommand(): Promise<void> {
  await runMacroSequence("recover", [
    { label: "Clear Stale Locks", command: ["runtime", "clear-stale-locks"] },
    { label: "Validate Integrity", command: ["schema", "validate"] },
    { label: "Rebuild Truth", command: ["truth", "build"] },
    { label: "Verify State", command: ["doctor"] },
  ]);
}
