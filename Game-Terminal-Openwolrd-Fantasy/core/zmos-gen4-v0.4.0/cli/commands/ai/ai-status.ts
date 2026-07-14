import { evaluateCanonicalStateIntegrity } from "../../../core/state-integrity.js";
import { getTraceFilePath } from "../../../trace/writer.js";
import { promises as fs } from "node:fs";
import { resolveAiProvider } from "../../../core/ai-provider.js";
import { readTruthRuntimeSnapshot } from "../../../core/truth-runtime.js";

export async function runAiStatusCommand(): Promise<void> {
  const [truthRuntime, canonical, tracePath] = await Promise.all([
    readTruthRuntimeSnapshot(),
    evaluateCanonicalStateIntegrity(),
    getTraceFilePath(),
  ]);

  let lastAiTrace: string = "(none)";
  try {
    const raw = await fs.readFile(tracePath, "utf8");
    const lines = raw.trim().split("\n").filter(Boolean);
    for (let i = lines.length - 1; i >= 0; i--) {
      try {
        const record = JSON.parse(lines[i]) as Record<string, unknown>;
        const cmd = record.command;
        if (typeof cmd === "string" && (cmd === "zcl ai test" || cmd === "zcl ai run")) {
          const details = record.details as Record<string, unknown> | undefined;
          lastAiTrace = [
            `command: ${cmd}`,
            `status: ${record.execution_status}`,
            `task: ${details?.task ?? "unknown"}`,
            `summary: ${details?.summary ?? "(none)"}`,
            `timestamp: ${record.timestamp}`,
          ].join(" | ");
          break;
        }
      } catch {
        // skip malformed lines
      }
    }
  } catch {
    // trace file may not exist yet
  }

  const provider = resolveAiProvider();
  const maxTokens = process.env.ZMOS_AI_MAX_TOKENS ?? "512 (default)";

  const lines = [
    "Z-MOS AI Readiness Status",
    "",
    `truth_state:      ${truthRuntime.sessionState}`,
    `canonical_status: ${canonical.status}`,
    `ai_provider:      ${provider}`,
    `max_tokens:       ${maxTokens}`,
    "",
    `last_ai_trace:    ${lastAiTrace}`,
  ];

  console.log(lines.join("\n"));
}
