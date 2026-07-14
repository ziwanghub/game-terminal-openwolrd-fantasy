import { renderCommandExecutionResult } from "../../core/execution-contract.js";
import {
  cleanCoreContamination,
  evaluateCoreBaseline,
} from "../../core/core-baseline.js";
import { evaluateMutationGuard } from "../../core/mutation-guard.js";
import { runPreflightChecks } from "../../core/preflight.js";
import { evaluateCanonicalStateIntegrity } from "../../core/state-integrity.js";
import { appendTraceRecord } from "../../trace/writer.js";

type CoreRestoreVerdict =
  | "SAFE-TO-CONTINUE"
  | "CONTINUE-WITH-CAUTION"
  | "STOP-AND-REPAIR";

function parseDryRun(argv: string[]): boolean {
  return argv.includes("--dry-run");
}

function formatContaminants(
  contaminants: Awaited<ReturnType<typeof evaluateCoreBaseline>>["contaminants"],
): string[] {
  if (contaminants.length === 0) {
    return ["- (none)"];
  }

  return contaminants.map((contaminant) => {
    const flag = contaminant.approvedForRemoval ? "APPROVED-REMOVABLE" : "UNAPPROVED";
    return `- ${contaminant.path} [${flag}] — ${contaminant.reason}`;
  });
}

export async function runCoreDoctorCommand(): Promise<void> {
  const baseline = await evaluateCoreBaseline();

  const hasUnapproved = baseline.summary.unapprovedContaminants > 0;
  const hasApprovedContamination = baseline.summary.approvedGeneratedContaminants > 0;
  const hasMissingCore = baseline.missingCorePaths.length > 0;
  const hasWarning = hasUnapproved || hasApprovedContamination || hasMissingCore;

  const lines = [
    "Z-MOS Core Doctor Report",
    "",
    "Baseline Summary",
    `- baseline core paths: ${baseline.baselineCorePaths.length}`,
    `- present core paths: ${baseline.presentCorePaths.length}`,
    `- missing core paths: ${baseline.missingCorePaths.length}`,
    `- contamination count: ${baseline.summary.totalContaminants}`,
    `- contamination (approved removable): ${baseline.summary.approvedGeneratedContaminants}`,
    `- contamination (unapproved): ${baseline.summary.unapprovedContaminants}`,
    "",
    "Missing Core Paths",
    ...(baseline.missingCorePaths.length > 0
      ? baseline.missingCorePaths.map((entry) => `- ${entry}`)
      : ["- (none)"]),
    "",
    "Detected Contamination",
    ...formatContaminants(baseline.contaminants),
    "",
    renderCommandExecutionResult({
      command: "core-doctor",
      status: hasWarning ? "warning" : "success",
      resultClass: hasWarning ? "warning-execution" : "success",
      warningReason: hasWarning
        ? "Core baseline mismatch or contamination detected."
        : undefined,
      traceExpectation: "optional-by-design",
      traceResult: "not-emitted-by-design",
      nextAction: hasWarning
        ? "Run zcl core clean (optionally --dry-run first), then zcl core restore."
        : "Core baseline is clean.",
    }),
  ];

  console.log(lines.join("\n"));
  if (hasWarning) {
    process.exitCode = 1;
  }
}

export async function runCoreCleanCommand(argv: string[]): Promise<void> {
  const dryRun = parseDryRun(argv);
  const baseline = await evaluateCoreBaseline();
  if (!dryRun) {
    const approvedTargets = baseline.contaminants
      .filter((entry) => entry.approvedForRemoval)
      .map((entry) => entry.path);
    if (approvedTargets.length > 0) {
      const guard = await evaluateMutationGuard({
        command: "zcl core clean",
        targetPaths: approvedTargets,
      });
      if (!guard.allowed) {
        console.log(
          renderCommandExecutionResult({
            command: "core-clean",
            status: "blocked",
            resultClass: "blocked-policy",
            reason: guard.reason,
            warningReason: guard.warnings.length > 0 ? guard.warnings.join(" | ") : undefined,
            traceExpectation: "required-if-business-logic",
            traceResult: "not-emitted-blocked-before-logic",
            nextAction:
              "Set lifecycle.status=active and align scope.mutation policy before mutating cleanup.",
          }),
        );
        process.exitCode = 1;
        return;
      }
    }
  }
  const cleanResult = await cleanCoreContamination(baseline, { dryRun });
  const after = await evaluateCoreBaseline();

  const hasFailures = cleanResult.summary.failures > 0;
  const hasResidualContamination = after.summary.totalContaminants > 0;
  const hasWarning = hasResidualContamination || cleanResult.summary.skippedUnapproved > 0;

  if (!dryRun) {
    await appendTraceRecord({
      command: "zcl core clean",
      status: hasFailures ? "failed" : hasWarning ? "failed" : "success",
      actor: "system",
      details: {
        dryRun,
        removed: cleanResult.summary.removed,
        skippedUnapproved: cleanResult.summary.skippedUnapproved,
        failures: cleanResult.summary.failures,
        residualContamination: after.summary.totalContaminants,
        residualUnapproved: after.summary.unapprovedContaminants,
      },
    });
  }

  const lines = [
    "Z-MOS Core Clean Report",
    "",
    `Mode: ${dryRun ? "DRY-RUN" : "APPLY"}`,
    "Actions",
    ...(cleanResult.actions.length > 0
      ? cleanResult.actions.map(
          (action) => `- ${action.path} [${action.action}] — ${action.reason}`,
        )
      : ["- (no actions)"]),
    "",
    "Summary",
    `- removed: ${cleanResult.summary.removed}`,
    `- would remove: ${cleanResult.summary.wouldRemove}`,
    `- skipped unapproved: ${cleanResult.summary.skippedUnapproved}`,
    `- failures: ${cleanResult.summary.failures}`,
    `- residual contamination: ${after.summary.totalContaminants}`,
    `- residual unapproved: ${after.summary.unapprovedContaminants}`,
    "",
    renderCommandExecutionResult({
      command: "core-clean",
      status: hasFailures ? "failed" : hasWarning ? "warning" : "success",
      resultClass: hasFailures
        ? "failed-runtime"
        : hasWarning
          ? "warning-execution"
          : "success",
      warningReason: !hasFailures && hasWarning
        ? "Residual contamination exists (typically unapproved paths)."
        : undefined,
      reason: hasFailures ? "One or more approved path removals failed." : undefined,
      traceExpectation: dryRun ? "optional-by-design" : "required-if-business-logic",
      traceResult: dryRun ? "not-emitted-by-design" : "emitted",
      nextAction: hasFailures || hasWarning
        ? "Review unapproved/failure paths and resolve manually."
        : "Core repository is clean against baseline policy.",
    }),
  ];

  console.log(lines.join("\n"));

  if (hasFailures || hasWarning) {
    process.exitCode = 1;
  }
}

function resolveRestoreVerdict(args: {
  cleanFailures: number;
  unapprovedContaminants: number;
  missingCorePaths: number;
  preflightStatus: "healthy" | "warning" | "blocking";
  canonicalStatus: "healthy" | "warning" | "blocking";
  canonicalRecoveryClass: string;
  dryRun: boolean;
  approvedContaminantsRemaining: number;
}): CoreRestoreVerdict {
  const canonicalBlockingAllowed =
    args.canonicalStatus === "blocking" && args.canonicalRecoveryClass === "bootstrap-required";
  const hardBlockingCanonical = args.canonicalStatus === "blocking" && !canonicalBlockingAllowed;

  if (
    args.cleanFailures > 0 ||
    args.unapprovedContaminants > 0 ||
    args.missingCorePaths > 0 ||
    args.preflightStatus === "blocking" ||
    hardBlockingCanonical
  ) {
    return "STOP-AND-REPAIR";
  }

  if (
    args.preflightStatus === "warning" ||
    args.canonicalStatus !== "healthy" ||
    args.dryRun ||
    args.approvedContaminantsRemaining > 0
  ) {
    return "CONTINUE-WITH-CAUTION";
  }

  return "SAFE-TO-CONTINUE";
}

export async function runCoreRestoreCommand(argv: string[]): Promise<void> {
  const dryRun = parseDryRun(argv);
  const before = await evaluateCoreBaseline();
  if (!dryRun) {
    const approvedTargets = before.contaminants
      .filter((entry) => entry.approvedForRemoval)
      .map((entry) => entry.path);
    if (approvedTargets.length > 0) {
      const guard = await evaluateMutationGuard({
        command: "zcl core restore",
        targetPaths: approvedTargets,
      });
      if (!guard.allowed) {
        console.log(
          renderCommandExecutionResult({
            command: "core-restore",
            status: "blocked",
            resultClass: "blocked-policy",
            reason: guard.reason,
            warningReason: guard.warnings.length > 0 ? guard.warnings.join(" | ") : undefined,
            traceExpectation: "required-if-business-logic",
            traceResult: "not-emitted-blocked-before-logic",
            nextAction:
              "Set lifecycle.status=active and align scope.mutation policy before core restore.",
          }),
        );
        process.exitCode = 1;
        return;
      }
    }
  }
  const cleanResult = await cleanCoreContamination(before, { dryRun });
  const after = await evaluateCoreBaseline();
  const preflight = await runPreflightChecks({
    allowMissingCanonical: true,
    executionMode: "ops-dist",
  });
  const canonical = await evaluateCanonicalStateIntegrity();

  const verdict = resolveRestoreVerdict({
    cleanFailures: cleanResult.summary.failures,
    unapprovedContaminants: after.summary.unapprovedContaminants,
    missingCorePaths: after.missingCorePaths.length,
    preflightStatus: preflight.status,
    canonicalStatus: canonical.status,
    canonicalRecoveryClass: canonical.recoveryClass,
    dryRun,
    approvedContaminantsRemaining: after.summary.approvedGeneratedContaminants,
  });

  const status =
    verdict === "STOP-AND-REPAIR"
      ? "blocked"
      : verdict === "CONTINUE-WITH-CAUTION"
        ? "warning"
        : "success";
  const resultClass =
    verdict === "STOP-AND-REPAIR"
      ? "blocked-preflight"
      : verdict === "CONTINUE-WITH-CAUTION"
        ? "warning-execution"
        : "success";

  if (!dryRun) {
    await appendTraceRecord({
      command: "zcl core restore",
      status: verdict === "STOP-AND-REPAIR" ? "failed" : "success",
      actor: "system",
      details: {
        dryRun,
        cleanSummary: cleanResult.summary,
        contaminationAfterRestore: after.summary,
        missingCorePaths: after.missingCorePaths,
        preflightStatus: preflight.status,
        canonicalStatus: canonical.status,
        canonicalRecoveryClass: canonical.recoveryClass,
        verdict,
      },
    });
  }

  const lines = [
    "Z-MOS Core Restore Report",
    "",
    `Mode: ${dryRun ? "DRY-RUN" : "APPLY"}`,
    "Clean Phase",
    `- removed: ${cleanResult.summary.removed}`,
    `- would remove: ${cleanResult.summary.wouldRemove}`,
    `- skipped unapproved: ${cleanResult.summary.skippedUnapproved}`,
    `- failures: ${cleanResult.summary.failures}`,
    "",
    "Baseline Verification",
    `- missing core paths: ${after.missingCorePaths.length}`,
    `- contamination (approved removable): ${after.summary.approvedGeneratedContaminants}`,
    `- contamination (unapproved): ${after.summary.unapprovedContaminants}`,
    "",
    "Baseline Checks",
    `- preflight status (allow canonical bootstrap): ${preflight.status}`,
    `- canonical integrity: ${canonical.status} (${canonical.recoveryClass})`,
    "",
    `Final Restore Verdict: ${verdict}`,
    "",
    renderCommandExecutionResult({
      command: "core-restore",
      status,
      resultClass,
      warningReason:
        verdict === "CONTINUE-WITH-CAUTION"
          ? "Baseline is mostly clean but caution conditions remain."
          : undefined,
      reason:
        verdict === "STOP-AND-REPAIR"
          ? "Unapproved contamination, missing core paths, or blocking checks remain."
          : undefined,
      traceExpectation: dryRun ? "optional-by-design" : "required-if-business-logic",
      traceResult: dryRun ? "not-emitted-by-design" : "emitted",
      nextAction:
        verdict === "SAFE-TO-CONTINUE"
          ? "Core baseline restored and verified."
          : "Resolve remaining blockers/warnings and rerun zcl core restore.",
    }),
  ];

  if (after.missingCorePaths.length > 0) {
    lines.push("", "Missing Core Paths", ...after.missingCorePaths.map((entry) => `- ${entry}`));
  }

  if (after.summary.totalContaminants > 0) {
    lines.push("", "Residual Contamination", ...formatContaminants(after.contaminants));
  }

  console.log(lines.join("\n"));

  if (verdict !== "SAFE-TO-CONTINUE") {
    process.exitCode = 1;
  }
}
