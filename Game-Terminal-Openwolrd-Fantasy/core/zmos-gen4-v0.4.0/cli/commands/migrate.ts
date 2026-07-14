import { renderCommandExecutionResult } from "../../core/execution-contract.js";
import {
  executeMigration,
  type MigrationSourceVersion,
  type MigrationTargetVersion,
} from "../../core/migration.js";
import { appendTraceRecord } from "../../trace/writer.js";

type MigrateArgs = {
  source: MigrationSourceVersion;
  target: MigrationTargetVersion;
  projectPath: string;
  dryRun: boolean;
  force: boolean;
  applyRewriteSafe: boolean;
};

function parseMigrateArgs(argv: string[]): MigrateArgs | null {
  let source = "";
  let target = "";
  let projectPath = ".";
  let dryRun = false;
  let force = false;
  let applyRewriteSafe = false;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];

    if (arg === "--dry-run") {
      dryRun = true;
      continue;
    }
    if (arg === "--force") {
      force = true;
      continue;
    }
    if (arg === "--apply-rewrite-safe") {
      applyRewriteSafe = true;
      continue;
    }

    if (arg === "--from" && argv[i + 1]) {
      source = argv[++i] || "";
      continue;
    }
    if (arg.startsWith("--from=")) {
      source = arg.split("=")[1] || "";
      continue;
    }

    if (arg === "--to" && argv[i + 1]) {
      target = argv[++i] || "";
      continue;
    }
    if (arg.startsWith("--to=")) {
      target = arg.split("=")[1] || "";
      continue;
    }

    if (arg === "--project" && argv[i + 1]) {
      projectPath = argv[++i] || ".";
      continue;
    }
    if (arg.startsWith("--project=")) {
      projectPath = arg.split("=")[1] || ".";
      continue;
    }
  }

  if (!source || !target) {
    return null;
  }

  if (source !== "v0.2.x" || target !== "evo1.0") {
    return null;
  }

  return {
    source: source as MigrationSourceVersion,
    target: target as MigrationTargetVersion,
    projectPath,
    dryRun,
    force,
    applyRewriteSafe,
  };
}

function printUsage(): void {
  console.error(
    [
      "Usage:",
      "  zcl migrate --from v0.2.x --to evo1.0 [--project <path>] [--dry-run] [--force]",
      "  zcl migrate --from v0.2.x --to evo1.0 [--project <path>] [--dry-run] [--force] [--apply-rewrite-safe]",
      "",
      "Examples:",
      "  zcl migrate --from v0.2.x --to evo1.0 --dry-run",
      "  zcl migrate --from v0.2.x --to evo1.0 --project .",
      "  zcl migrate --from v0.2.x --to evo1.0 --force",
      "  zcl migrate --from v0.2.x --to evo1.0 --apply-rewrite-safe",
    ].join("\n"),
  );
}

export async function runMigrateCommand(argv: string[]): Promise<void> {
  const parsed = parseMigrateArgs(argv);
  if (!parsed) {
    printUsage();
    process.exitCode = 1;
    return;
  }

  const result = await executeMigration({
    source: parsed.source,
    target: parsed.target,
    projectPath: parsed.projectPath,
    dryRun: parsed.dryRun,
    force: parsed.force,
    applyRewriteSafe: parsed.applyRewriteSafe,
  });

  const lines = [
    "Z-MOS Migration Report",
    "",
    "Command",
    `- source: ${result.source}`,
    `- target: ${result.target}`,
    `- project: ${result.inspection.projectRelative}`,
    `- mode: ${parsed.dryRun ? "DRY-RUN" : "APPLY"}`,
    `- force: ${parsed.force ? "yes" : "no"}`,
    `- apply-rewrite-safe: ${parsed.applyRewriteSafe ? "yes" : "no"}`,
    "",
    "Inspect",
    `- legacy .zmos: ${result.inspection.legacyStateExists ? "yes" : "no"}`,
    `- canonical .z-mos: ${result.inspection.canonicalStateExists ? "yes" : "no"}`,
    `- dual-state conflict: ${result.inspection.dualStateConflict ? "yes" : "no"}`,
    `- root trace: ${result.inspection.rootTraceExists ? "yes" : "no"}`,
    `- legacy trace: ${result.inspection.legacyTraceExists ? "yes" : "no"}`,
    `- canonical trace: ${result.inspection.canonicalTraceExists ? "yes" : "no"}`,
    `- manifest lifecycle: ${result.inspection.manifestState.lifecycleStatus}`,
    `- manifest scope configured: ${result.inspection.manifestState.scopeConfigured ? "yes" : "no"}`,
    "",
    "Plan",
    `- actions: ${result.plan.actions.length}`,
    `- warnings: ${result.plan.warnings.length}`,
    `- blockers: ${result.plan.blockers.length}`,
    "",
    "Safe Rewrite",
    `- candidates found: ${result.rewriteSummary.candidatesFound}`,
    `- eligible: ${result.rewriteSummary.eligibleCount}`,
    `- applied: ${result.rewriteSummary.appliedCount}`,
    `- skipped: ${result.rewriteSummary.skippedCount}`,
    `- blocked: ${result.rewriteSummary.blockedCount}`,
  ];

  if (result.plan.actions.length > 0) {
    lines.push("", "Planned Actions");
    for (const action of result.plan.actions) {
      lines.push(
        `- [${action.type}] ${action.description}${
          action.from || action.to
            ? ` (${action.from || "n/a"} -> ${action.to || "n/a"})`
            : ""
        }`,
      );
    }
  }

  if (result.rewriteSummary.candidates.length > 0) {
    lines.push("", "Rewrite Candidates");
    for (const candidate of result.rewriteSummary.candidates) {
      lines.push(
        `- ${candidate.file} | eligible=${candidate.eligible ? "yes" : "no"} | replacements=${candidate.plannedReplacements}` +
          (candidate.reasons.length > 0 ? ` | reason=${candidate.reasons.join(", ")}` : ""),
      );
    }
  }

  if (result.rewriteSummary.applied.length > 0) {
    lines.push("", "Rewrites Applied");
    for (const rewritten of result.rewriteSummary.applied) {
      lines.push(
        `- ${rewritten.file} | replacements=${rewritten.replacements} | patterns=${rewritten.patterns.join(", ")}`,
      );
    }
  }

  if (result.plan.warnings.length > 0) {
    lines.push("", "Warnings", ...result.plan.warnings.map((warning) => `- ${warning}`));
  }

  if (result.plan.blockers.length > 0) {
    lines.push("", "Blockers", ...result.plan.blockers.map((blocker) => `- ${blocker}`));
  }

  lines.push(
    "",
    "Apply",
    `- applied: ${result.apply.applied ? "yes" : "no"}`,
    `- actions applied: ${result.apply.actionsApplied.length}`,
    `- guard: ${result.apply.guardReason || "pass"}`,
    "",
    "Verify",
    `- canonical state exists: ${result.verify.canonicalStateExists ? "yes" : "no"}`,
    `- required files present: ${result.verify.requiredFilesPresent ? "yes" : "no"}`,
    `- dual-state remains: ${result.verify.dualStateConflict ? "yes" : "no"}`,
    `- preserved legacy state: ${result.verify.preservedLegacyStatePath || "(none)"}`,
    `- doctor/start improvement: ${result.verify.doctorStartImprovement}`,
  );

  if (result.verify.missingCanonicalFiles.length > 0) {
    lines.push(
      "",
      "Missing Canonical Files",
      ...result.verify.missingCanonicalFiles.map((entry) => `- ${entry}`),
    );
  }

  const hasBlockers = result.plan.blockers.length > 0 || result.apply.blockers.length > 0;
  const hasWarnings = result.plan.warnings.length > 0 || result.apply.warnings.length > 0;

  const executionStatus = hasBlockers ? "blocked" : hasWarnings ? "warning" : "success";
  const resultClass = hasBlockers ? "blocked-policy" : hasWarnings ? "warning-execution" : "success";

  lines.push(
    "",
    renderCommandExecutionResult({
      command: "migrate",
      status: executionStatus,
      resultClass,
      warningReason: hasWarnings ? "Migration warnings detected; review report details." : undefined,
      reason: hasBlockers ? "Migration blockers detected; apply path is blocked." : undefined,
      traceExpectation: parsed.dryRun ? "optional-by-design" : "required-if-business-logic",
      traceResult: parsed.dryRun ? "not-emitted-by-design" : result.apply.applied ? "emitted" : "not-emitted-blocked-before-logic",
      nextAction: hasBlockers
        ? "Resolve migration blockers and rerun with --dry-run first."
        : "Run zcl doctor and zcl start to confirm post-migration runtime state.",
    }),
  );

  if (!parsed.dryRun && result.apply.applied) {
    await appendTraceRecord({
      command: "zcl migrate",
      status: hasBlockers ? "failed" : "success",
      actor: "system",
      details: {
        source: result.source,
        target: result.target,
        project: result.inspection.projectRelative,
        dryRun: parsed.dryRun,
        force: parsed.force,
        planActions: result.plan.actions.length,
        actionsApplied: result.apply.actionsApplied.length,
        applyRewriteSafe: parsed.applyRewriteSafe,
        rewriteSummary: result.rewriteSummary,
        warnings: result.plan.warnings,
        blockers: result.plan.blockers,
        verification: result.verify,
      },
    });
  }

  console.log(lines.join("\n"));

  if (hasBlockers) {
    process.exitCode = 1;
  }
}
