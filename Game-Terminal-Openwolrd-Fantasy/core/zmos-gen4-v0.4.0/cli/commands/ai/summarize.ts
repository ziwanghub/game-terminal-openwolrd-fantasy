// Restored in Z-MOS v1.4.0 (Phase 2D)
// Context is now built via `zcl ai context build` before summarization.
// The command reads .z-mos/context/workspace.md and invokes the AI client
// through the governed execution gate (_governed-run.ts).

import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import * as path from "node:path";
import { runGovernedAiTask } from "./_governed-run.js";

const ROOT_DIR = process.cwd();
const CONTEXT_FILE = path.join(ROOT_DIR, ".z-mos", "context", "workspace.md");

export async function runSummarizeCommand(): Promise<void> {
  if (!existsSync(CONTEXT_FILE)) {
    console.error(
      [
        "zcl ai summarize: context not found",
        "",
        "Run context build first to generate workspace context:",
        "  zcl ai context build",
        "",
        "Then re-run:",
        "  zcl ai summarize",
      ].join("\n"),
    );
    process.exitCode = 1;
    return;
  }

  const contextContent = await readFile(CONTEXT_FILE, "utf8");
  const relativePath = path.relative(ROOT_DIR, CONTEXT_FILE);

  const payload = {
    task: "system-check",
    goal: "Produce a concise advisory summary of the current Z-MOS workspace state",
    input: contextContent,
    constraints: [
      "base your response strictly on the provided context",
      "identify what is implemented vs scaffold only",
      "highlight any governance gaps or risks visible from the context",
      "keep the response under 300 words",
      "output plain text only, no markdown headers",
    ],
  };

  console.log(`SUMMARIZE: reading context from ${relativePath}`);
  await runGovernedAiTask("zcl ai summarize", payload, relativePath, "execute");
}
