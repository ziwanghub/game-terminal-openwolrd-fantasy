import { promises as fs } from "node:fs";
import * as path from "node:path";
import { createHash } from "node:crypto";
import { getGitContext } from "../../core/git.js";
import { validateTruthContractPayload } from "../../core/truth-store.js";
import { evaluateTruthConsistency } from "../../core/truth-consistency.js";


type TruthRead =
  | {
      source: "primary";
      contractHash: string;
      verdict: string;
      payload: Record<string, unknown>;
    }
  | {
      source: "fallback";
      warning: "TRUTH_CONTRACT_MISSING" | "TRUTH_CONTRACT_INVALID";
    };

async function readTruthContract(): Promise<TruthRead> {
  const truthPath = path.join(process.cwd(), ".z-mos", "truth.contract.json");
  try {
    await fs.access(truthPath);
  } catch {
    return { source: "fallback", warning: "TRUTH_CONTRACT_MISSING" };
  }
  try {
    const raw = await fs.readFile(truthPath, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    await validateTruthContractPayload(parsed);
    const contractHash = createHash("sha256").update(raw).digest("hex");
    const verdict =
      typeof (parsed as Record<string, unknown>).verdict === "string"
        ? ((parsed as Record<string, unknown>).verdict as string)
        : "UNKNOWN";
    return { source: "primary", contractHash, verdict, payload: parsed as Record<string, unknown> };
  } catch {
    return { source: "fallback", warning: "TRUTH_CONTRACT_INVALID" };
  }
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

export async function runStatusCommand(): Promise<void> {
  let intentCard: any = null;
  const truth = await readTruthContract();
  
  try {
    intentCard = JSON.parse(await fs.readFile(path.join(process.cwd(), ".z-mos/intent.card.json"), "utf8"));
  } catch {}
  const git = getGitContext();
  const truthPayload = truth.source === "primary" ? truth.payload : null;
  const truthGateState =
    truthPayload && typeof truthPayload.gate_state === "object" && truthPayload.gate_state !== null
      ? (truthPayload.gate_state as Record<string, unknown>)
      : null;

  const phase =
    truth.source === "primary"
      ? asString(truthPayload?.phase) || "truth-contract"
      : "unknown";
  const gate =
    truth.source === "primary"
      ? asString(truthGateState?.active_gate) || "unknown"
      : "unknown";
  const nextAllowed =
    truth.source === "primary"
      ? asString(truthPayload?.next_allowed_task) || "unknown"
      : "unknown";
  const consistency = evaluateTruthConsistency({
    truth: truth.source === "primary" ? truth.payload : null,
    currentGit: git,
    currentEnv: process.env.NODE_ENV || "development",
  });
  const runProfile = gate !== "unknown" ? gate : "standard";
  const blockedByDrift = consistency.hardBlock;
  const blockedByInvalidTruth = truth.source === "fallback" && truth.warning === "TRUTH_CONTRACT_INVALID";
  const blocked =
    truth.source === "primary"
      ? truth.verdict === "BLOCKED" || truth.verdict === "CONFLICTED" || blockedByDrift
      : false;
  const finalBlocked = blocked || blockedByInvalidTruth;
  const gitSync = "clean";
  const handoffStatus = "fallback-disabled";
  const intentStatus = intentCard ? "valid" : "missing";
  const intentSource = intentCard ? "primary" : "fallback";
  const scopeStatus = "clean";

  let confidenceScore = "95%";
  if (truth.source === "primary") {
    const rawConfidence = truthPayload?.confidence;
    if (typeof rawConfidence === "number" && Number.isFinite(rawConfidence)) {
      const percent = Math.max(0, Math.min(100, Math.round(rawConfidence * 100)));
      confidenceScore = `${percent}%`;
    }
  } else {
    confidenceScore = "70%";
  }
  if (finalBlocked) confidenceScore = "40%";

  const risks = [];
  if (finalBlocked) {
    risks.push(
      blockedByInvalidTruth
        ? "blocked by: truth.contract invalid schema"
        : blockedByDrift
          ? "blocked by: CRITICAL_DRIFT_HARD_BLOCK"
          : "blocked by: unknown truth failure",
    );
  }
  const output = {
    phase,
    gate,
    next_allowed_tasks: nextAllowed,
    blocked: finalBlocked,
    run_profile: runProfile,
    confidence_score: confidenceScore,
    risks,
    git_sync: gitSync,
    handoff_status: handoffStatus,
    intent_status: intentStatus,
    intent_source: intentSource,
    legacy_compatibility_layer: "removed",
    scope_status: scopeStatus,
    truth_mode: truth.source === "primary" ? "authoritative" : "fallback",
    drift_status: consistency.status === "DRIFT" ? "detected" : "clear",
    drift_level: consistency.driftLevel,
    truth_source: truth.source,
    contract_hash: truth.source === "primary" ? truth.contractHash : null,
    verdict:
      consistency.escalationVerdict === "CONTINUE-WITH-RISK"
        ? "CONTINUE-WITH-RISK"
        : truth.source === "primary"
          ? truth.verdict
          : null,
    drift_policy_verdict: consistency.escalationVerdict,
    drift_policy_action: consistency.escalationAction,
    drift_policy_reason: consistency.reason,
    reason:
      blockedByInvalidTruth || blockedByDrift
        ? "CRITICAL_DRIFT_HARD_BLOCK"
        : "NONE",
    truth_legacy_consistency: consistency,
    warnings: [
      ...(truth.source === "fallback" ? [truth.warning] : []),
      ...consistency.warnings,
    ]
  };

  console.log(JSON.stringify(output, null, 2));
}
