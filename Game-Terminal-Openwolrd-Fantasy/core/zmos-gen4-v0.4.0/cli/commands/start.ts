import { buildDocumentIndex } from "../../core/document-index.js";
import { renderCommandExecutionResult } from "../../core/execution-contract.js";
import { createHash } from "node:crypto";
import { readManifest } from "../../core/manifest.js";
import { evaluateLifecycleReadiness } from "../../core/mutation-guard.js";
import { runPreflightChecks } from "../../core/preflight.js";
import { evaluateCanonicalStateIntegrity } from "../../core/state-integrity.js";
import { validateTruthContractPayload } from "../../core/truth-store.js";
import { evaluateTruthConsistency } from "../../core/truth-consistency.js";
import { evaluateDoctorDiagnostics } from "./doctor.js";
import { ensureValidLockOrCleanup } from "../../core/port-lock.js";
import { promises as fs } from "node:fs";
import * as path from "node:path";
import { getGitContext } from "../../core/git.js";
import { readTruthRuntimeSnapshot } from "../../core/truth-runtime.js";
import { FULL_VERSION } from "../../sdk/version.js";


async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

type EntryVerdict =
  | "SAFE-TO-CONTINUE"
  | "CONTINUE-WITH-CAUTION"
  | "STOP-AND-REPAIR";

type EntryStatus = "healthy" | "warning" | "blocking";

type TruthRead =
  | { source: "primary"; contractHash: string; verdict: string; payload: Record<string, unknown> }
  | { source: "fallback"; warning: "TRUTH_CONTRACT_MISSING" | "TRUTH_CONTRACT_INVALID" };

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

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

function toUpperStatus(status: EntryStatus): string {
  if (status === "healthy") {
    return "HEALTHY";
  }
  if (status === "warning") {
    return "WARNING";
  }
  return "BLOCKING";
}

function summarizeCanonical(integrity: Awaited<ReturnType<typeof evaluateCanonicalStateIntegrity>>): string {
  const topFinding = integrity.findings[0];
  if (!topFinding) {
    return `${integrity.status} (${integrity.recoveryClass})`;
  }
  return `${integrity.status} (${integrity.recoveryClass}) — ${topFinding.reason}`;
}

function inferConfidence(args: {
  preflight: EntryStatus;
  canonical: EntryStatus;
  doctor: EntryStatus;
  docs: EntryStatus;
  lifecycle: EntryStatus;
}): "core-verified" | "verification-warning" | "core-unverified" {
  const statuses = [args.preflight, args.canonical, args.doctor, args.docs, args.lifecycle];
  if (statuses.includes("blocking")) {
    return "core-unverified";
  }
  if (statuses.includes("warning")) {
    return "verification-warning";
  }
  return "core-verified";
}

function resolveEntryVerdict(args: {
  preflight: EntryStatus;
  canonical: EntryStatus;
  doctor: EntryStatus;
  docs: EntryStatus;
  lifecycle: EntryStatus;
}): EntryVerdict {
  const statuses = [args.preflight, args.canonical, args.doctor, args.docs, args.lifecycle];
  if (statuses.includes("blocking")) {
    return "STOP-AND-REPAIR";
  }
  if (statuses.includes("warning")) {
    return "CONTINUE-WITH-CAUTION";
  }
  return "SAFE-TO-CONTINUE";
}

function recommendedActions(verdict: EntryVerdict, confidence: string): string[] {
  if (verdict === "STOP-AND-REPAIR") {
    return [
      "Fix blocking issue first.",
      "Run npm run ops:preflight after repair.",
      "Run npm run verify:all before continuing development.",
      "Update runlog/case document with root cause and repair evidence.",
    ];
  }

  if (verdict === "CONTINUE-WITH-CAUTION") {
    return [
      "Continue development with warning awareness.",
      "Review warning sections in preflight/doctor/doc summary.",
      "Run npm run verify:all before merge or milestone close.",
      "Update docs/playbook if warning pattern is repeatable.",
    ];
  }

  return [
    "Continue development.",
    "Run npm run verify:all at milestone boundaries.",
    "Keep workflow inside Preflight -> Execute -> Validate -> Verify -> Document.",
    confidence === "core-verified"
      ? "Baseline is verified; keep evidence fresh as work changes."
      : "Keep confidence evidence current.",
  ];
}

export async function runStartCommand(): Promise<void> {
  const truth = await readTruthContract();
  const manifestForLock = await readManifest().catch(() => null);
  const staleLockScan = await ensureValidLockOrCleanup({
    project: manifestForLock?.repository.name,
    scopeProjectOnly: true,
  });
  const staleCleared = staleLockScan.filter((entry) => entry.stale && !entry.skipped).length;

  const preflight = await runPreflightChecks({
    executionMode: "ops-dist",
    allowMissingCanonical: false,
  });

  const canonicalIntegrity = await evaluateCanonicalStateIntegrity();
  const docIndex = await buildDocumentIndex();
  const topCanonicalFinding = canonicalIntegrity.findings[0];

  let manifest: Awaited<ReturnType<typeof readManifest>> | null = null;
  let manifestError: string | null = null;

  try {
    manifest = await readManifest();
  } catch (error) {
    manifestError = error instanceof Error ? error.message : "manifest read failure";
  }

  let intentCardForBoot: any = null;
  try {
    intentCardForBoot = JSON.parse(await fs.readFile(path.join(process.cwd(), ".z-mos/intent.card.json"), "utf8"));
  } catch {}
  const truthRuntime = await readTruthRuntimeSnapshot();
  const currentPhase = truthRuntime.sessionState || "not enough evidence";
  const lifecycleReadiness = await evaluateLifecycleReadiness();
  const lifecycleStatus: EntryStatus =
    lifecycleReadiness.status === "active" ||
    lifecycleReadiness.status === "stabilized"
      ? "healthy"
      : lifecycleReadiness.status === "freeze"
        ? "blocking"
        : lifecycleReadiness.status === "unknown" || lifecycleReadiness.status === "archived"
        ? "warning"
        : "warning";

  let doctorStatus: EntryStatus = "healthy";
  let doctorError: string | null = null;
  let doctorSummary = {
    healthy: 0,
    warning: 0,
    blocking: 0,
    recommendedAction: "not enough evidence",
    traceHealth: "not enough evidence",
    traceValidation: "not enough evidence",
  };

  if (canonicalIntegrity.status !== "blocking") {
    try {
      const doctor = await evaluateDoctorDiagnostics();
      doctorStatus = doctor.overallStatus;

      const traceHealth = doctor.checks.find((check) => check.label === "trace health");
      const traceValidation = doctor.checks.find(
        (check) => check.label === "trace validation status",
      );

      doctorSummary = {
        healthy: doctor.diagnosticsSummary.healthy,
        warning: doctor.diagnosticsSummary.warning,
        blocking: doctor.diagnosticsSummary.blocking,
        recommendedAction: doctor.recommendedAction,
        traceHealth: traceHealth?.detail || "not enough evidence",
        traceValidation: traceValidation?.detail || "not enough evidence",
      };
    } catch (error) {
      doctorError =
        error instanceof Error ? error.message : "doctor diagnostics evaluation failed";
      doctorStatus = "blocking";
      doctorSummary = {
        healthy: 0,
        warning: 0,
        blocking: 1,
        recommendedAction: "Repair runtime diagnostics prerequisites and rerun zcl start.",
        traceHealth: "not enough evidence",
        traceValidation: "not enough evidence",
      };
    }
  } else {
    doctorStatus = "blocking";
    doctorSummary = {
      healthy: 0,
      warning: 0,
      blocking: 1,
      recommendedAction:
        topCanonicalFinding?.action ||
        "Repair canonical blockers before diagnostics.",
      traceHealth: "not evaluated due to canonical blocking state",
      traceValidation: "not evaluated due to canonical blocking state",
    };
  }


  const confidence = inferConfidence({
    preflight: preflight.status,
    canonical: canonicalIntegrity.status,
    doctor: doctorStatus,
    docs: docIndex.status,
    lifecycle: lifecycleStatus,
  });

  const verdict = resolveEntryVerdict({
    preflight: preflight.status,
    canonical: canonicalIntegrity.status,
    doctor: doctorStatus,
    docs: docIndex.status,
    lifecycle: lifecycleStatus,
  });

  const git = getGitContext();
  let driftWarningBlock: string[] = [];
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
  const nextCommand = `zcl run-gate ${runProfile}`;
  const blockedFromTruth =
    truth.source === "primary" &&
    (truth.verdict === "BLOCKED" || truth.verdict === "CONFLICTED");
  const blockedByDrift = consistency.hardBlock;
  const blockedByInvalidTruth = truth.source === "fallback" && truth.warning === "TRUTH_CONTRACT_INVALID";
  const blocked = blockedFromTruth || blockedByDrift || blockedByInvalidTruth || verdict === "STOP-AND-REPAIR";
  const gitSync = driftWarningBlock.length > 0 ? "drift-detected" : "clean";
  const handoffStatus = "fallback-disabled";
  const intentStatus = intentCardForBoot ? "valid" : "missing";
  const intentSource = intentCardForBoot ? "primary" : "fallback";
  const scopeStatus = "clean";

  let confidenceScore = "80%";
  if (truth.source === "primary") {
    const rawConfidence = truthPayload?.confidence;
    if (typeof rawConfidence === "number" && Number.isFinite(rawConfidence)) {
      const percent = Math.max(0, Math.min(100, Math.round(rawConfidence * 100)));
      confidenceScore = `${percent}%`;
    } else {
      confidenceScore = "70%";
    }
  } else {
    if (confidence === "core-verified") confidenceScore = "95%";
    if (confidence === "verification-warning") confidenceScore = "70%";
    if (confidence === "core-unverified") confidenceScore = "40%";
  }
  if (blocked) {
    confidenceScore = "40%";
  }

  const topRisks = [];
  if (doctorSummary.blocking > 0) topRisks.push(`${doctorSummary.blocking} blocking issues`);
  if (doctorSummary.warning > 0) topRisks.push(`${doctorSummary.warning} warnings`);
  if (driftWarningBlock.length > 0) topRisks.push("git sync drift detected");
  if (topRisks.length === 0) topRisks.push("none");
  if (consistency.warnings.length > 0) {
    topRisks.push("TRUTH_LEGACY_DRIFT");
  }
  const driftVerdict = blockedByDrift || blockedByInvalidTruth ? "STOP-AND-REPAIR" : consistency.escalationVerdict;
  const hardBlockReason = blockedByDrift || blockedByInvalidTruth ? "CRITICAL_DRIFT_HARD_BLOCK" : consistency.reason;

  const lines = [
    "===================================================",
    `Z-MOS ${FULL_VERSION}`,
    "===================================================",
    "",
    "[SINGLE TRUTH CONTEXT]",
    `phase: ${phase}`,
    `gate: ${gate}`,
    `next_allowed_task: ${nextAllowed}`,
    `next_command: ${nextCommand}`,
    `blocked: ${blocked}`,
    `run_profile: ${runProfile}`,
    "",
    "[SYSTEM]",
    `git_sync: ${gitSync}`,
    `handoff: ${handoffStatus}`,
    `intent: ${intentStatus}`,
    `intent_source: ${intentSource}`,
    `legacy_compatibility_layer: removed`,
    `scope: ${scopeStatus}`,
    `confidence_score: ${confidenceScore}`,
    "",
    "[RUNTIME ADVISORY]",
    `truth_mode: ${truth.source === "primary" ? "authoritative" : "fallback"}`,
    `drift_status: ${consistency.status === "DRIFT" ? "detected" : "clear"}`,
    `drift_level: ${consistency.driftLevel}`,
    `truth_source: ${truth.source}`,
    `contract_hash: ${truth.source === "primary" ? truth.contractHash : "not enough evidence"}`,
    `verdict: ${driftVerdict === "STOP-AND-REPAIR" ? driftVerdict : (driftVerdict === "CONTINUE-WITH-RISK" ? driftVerdict : (truth.source === "primary" ? truth.verdict : "not enough evidence"))}`,
    `drift_policy_action: ${consistency.escalationAction}`,
    `drift_policy_reason: ${hardBlockReason}`,
    ...(truth.source === "fallback" ? [`warning: ${truth.warning}`] : []),
    `truth_consistency: ${consistency.status}`,
    ...(consistency.warnings.map((warning) => `warning: ${warning}`)),
    `top_risks:`,
    ...topRisks.map(r => `  - ${r}`),
    `expected_output: execution trace updated`,
    "",
    "===================================================",
    `[ACTION REQUIRED: Proceed immediately with task]`,
    `Run \`${nextCommand}\` to execute under correct profile.`,
    "==================================================="
  ];

  console.log(lines.join("\n"));

  if (verdict === "STOP-AND-REPAIR" || blockedByDrift || blockedByInvalidTruth) {
    process.exitCode = 1;
  }
}
