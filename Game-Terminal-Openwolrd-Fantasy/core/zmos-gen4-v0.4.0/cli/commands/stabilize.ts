import { runMacroSequence } from "./macros/runner.js";

export async function runStabilizeCommand(): Promise<void> {
  await runMacroSequence("stabilize", [
    { label: "Build Truth Contract", command: ["truth", "build"] },
    { label: "Validate Schema", command: ["schema", "validate"] },
    { label: "Cleanup Stale Locks", command: ["runtime", "clear-stale-locks"] },
    { label: "Project Diagnostics", command: ["doctor"] },
  ]);
}
