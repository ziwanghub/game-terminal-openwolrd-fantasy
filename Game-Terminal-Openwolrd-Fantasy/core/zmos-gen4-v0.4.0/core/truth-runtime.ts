import { promises as fs } from "node:fs";
import * as path from "node:path";
import { validateTruthContractPayload } from "./truth-store.js";

export type TruthRuntimeSnapshot = {
  truthAvailable: boolean;
  sessionState: string;
  workspace: string;
  framework: string;
};

export async function readTruthRuntimeSnapshot(): Promise<TruthRuntimeSnapshot> {
  const truthPath = path.join(process.cwd(), ".z-mos", "truth.contract.json");
  try {
    const raw = await fs.readFile(truthPath, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    await validateTruthContractPayload(parsed);
    const obj = parsed as Record<string, unknown>;
    const verdict =
      typeof obj.verdict === "string" && obj.verdict.trim().length > 0
        ? obj.verdict
        : "UNKNOWN";
    const phase =
      typeof obj.phase === "string" && obj.phase.trim().length > 0
        ? obj.phase
        : "truth-contract";
    return {
      truthAvailable: true,
      sessionState: verdict === "SAFE_TO_CONTINUE" ? "active" : "warning",
      workspace: "zmos-core",
      framework: "Z-MOS",
    };
  } catch {
    return {
      truthAvailable: false,
      sessionState: "fallback",
      workspace: "zmos-core",
      framework: "Z-MOS",
    };
  }
}

