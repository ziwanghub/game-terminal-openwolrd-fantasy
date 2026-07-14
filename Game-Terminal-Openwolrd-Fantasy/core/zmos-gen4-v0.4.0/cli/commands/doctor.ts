import { promises as fs } from "node:fs";
import * as path from "node:path";
import { getGitContext } from "../../core/git.js";

import { getManifestPath, readManifest } from "../../core/manifest.js";
import { evaluateMutationGuard } from "../../core/mutation-guard.js";
import { renderCommandExecutionResult } from "../../core/execution-contract.js";
import { getNodePath, loadNodeIdentity } from "../../core/node.js";
import {
  evaluateCanonicalStateIntegrity,
  type CanonicalIntegrityResult,
} from "../../core/state-integrity.js";
import { normalizeBootstrapLikeManifestIfSafe } from "../../core/manifest-normalization.js";
import { validateTraceFile } from "../../core/trace-validator.js";
import { SUPPORTED_WORKFLOWS } from "../../core/workflow.js";
import { getWorkflowRegistry } from "../../core/workflow-registry.js";
import {
  evaluateFullL7Criteria,
  type L7CriteriaEvaluation,
} from "../../governance/l7-criteria.js";
import { getGovernanceRuntimeStatus } from "../../governance/runtime.js";
import {
  getWorkflowPolicyPath,
  loadWorkflowPolicy,
  validateDeniedWorkflowActions,
} from "../../governance/workflow-policy.js";
import { appendTraceRecord, getTraceFilePath } from "../../trace/writer.js";

export type DiagnosticStatus = "healthy" | "warning" | "blocking";

export type DoctorCheck = {
  label: string;
  status: DiagnosticStatus;
  detail: string;
};

export type DoctorEvaluation = {
  profile: "core-control" | "product-project";
  checks: DoctorCheck[];
  overallStatus: DiagnosticStatus;
  diagnosticsSummary: {
    healthy: number;
    warning: number;
    blocking: number;
  };
  governance: Awaited<ReturnType<typeof getGovernanceRuntimeStatus>>;
  detectedGaps: string[];
  recommendedAction: string;
  manifest: Awaited<ReturnType<typeof readManifest>>;
  nodeIdentity: Awaited<ReturnType<typeof loadNodeIdentity>> | null;
  l7Criteria: L7CriteriaEvaluation | null;
  paths: {
    manifestPath: string;
    nodePath: string;
    tracePath: string;
  };
  observations: {
    recentTraceEntriesPresent: boolean;
    recentTraceEntryCount: number;
    recentTraceNodeMetadataPresent: boolean;
    recentTraceNodeCheckedCount: number;
    nodeIdentityPresent: boolean;
  };
};

function formatCheck(check: DoctorCheck): string {
  return `- ${check.label} — ${check.status}: ${check.detail}`;
}

async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function canAppendTrace(tracePath: string): Promise<boolean> {
  try {
    await fs.access(tracePath, fs.constants.R_OK | fs.constants.W_OK);
    return true;
  } catch {
    return false;
  }
}

async function readRecentTraceInfo(
  tracePath: string,
): Promise<{ recentEntriesPresent: boolean; recentEntryCount: number }> {
  try {
    const rawTrace = await fs.readFile(tracePath, "utf8");
    const lines = rawTrace
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    return {
      recentEntriesPresent: lines.length > 0,
      recentEntryCount: Math.min(lines.length, 5),
    };
  } catch {
    return {
      recentEntriesPresent: false,
      recentEntryCount: 0,
    };
  }
}

async function readRecentTraceNodeMetadata(
  tracePath: string,
): Promise<{ nodeMetadataPresent: boolean; recentCheckedCount: number }> {
  try {
    const rawTrace = await fs.readFile(tracePath, "utf8");
    const lines = rawTrace
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(-5);

    if (lines.length === 0) {
      return { nodeMetadataPresent: false, recentCheckedCount: 0 };
    }

    const nodeMetadataPresent = lines.every((line) => {
      try {
        const parsed = JSON.parse(line) as Record<string, unknown>;
        return (
          typeof parsed.node_id === "string" &&
          parsed.node_id.trim().length > 0 &&
          typeof parsed.node_role === "string" &&
          parsed.node_role.trim().length > 0
        );
      } catch {
        return false;
      }
    });

    return {
      nodeMetadataPresent,
      recentCheckedCount: lines.length,
    };
  } catch {
    return { nodeMetadataPresent: false, recentCheckedCount: 0 };
  }
}

function resolveOverallStatus(checks: DoctorCheck[]): DiagnosticStatus {
  if (checks.some((check) => check.status === "blocking")) {
    return "blocking";
  }

  if (checks.some((check) => check.status === "warning")) {
    return "warning";
  }

  return "healthy";
}

function resolveDoctorProfile(): "core-control" | "product-project" {
  return process.env.ZMOS_EXEC_TARGET_KIND === "project"
    ? "product-project"
    : "core-control";
}

async function evaluateCoreDoctorDiagnostics(): Promise<DoctorEvaluation> {
  const rootDir = process.cwd();
  const manifestPath = getManifestPath();
  const nodePath = getNodePath();
  const tracePath = await getTraceFilePath();
  const workflowPolicyPath = getWorkflowPolicyPath();
  const canonicalIntegrity = await evaluateCanonicalStateIntegrity();

  let nodeIdentity:
    | Awaited<ReturnType<typeof loadNodeIdentity>>
    | null = null;
  let nodeIdentityError: string | null = null;
  let workflowPolicy:
    | Awaited<ReturnType<typeof loadWorkflowPolicy>>
    | null = null;
  let workflowPolicyError: string | null = null;
  let deniedActionsError: string | null = null;
  let l7Criteria:
    | Awaited<ReturnType<typeof evaluateFullL7Criteria>>
    | null = null;
  let l7CriteriaError: string | null = null;
  let entrypointJson: any = null;
  let missingEntrypointReferences: string[] = [];

  try {
    const raw = await fs.readFile(path.join(rootDir, ".z-mos/entrypoint.json"), "utf8");
    entrypointJson = JSON.parse(raw);
    for (const key of Object.keys(entrypointJson.runtime_state_paths || {})) {
      if (!(await pathExists(path.join(rootDir, entrypointJson.runtime_state_paths[key])))) {
        missingEntrypointReferences.push(`runtime_state_paths.${key}`);
      }
    }
  } catch (err) {
    // entrypoint missing is handled elsewhere
  }


  try {
    nodeIdentity = await loadNodeIdentity();
  } catch (error) {
    nodeIdentityError =
      error instanceof Error ? error.message : "Unknown node identity error";
  }

  try {
    workflowPolicy = await loadWorkflowPolicy();
  } catch (error) {
    workflowPolicyError =
      error instanceof Error ? error.message : "Unknown workflow policy error";
  }

  try {
    await validateDeniedWorkflowActions();
  } catch (error) {
    deniedActionsError =
      error instanceof Error ? error.message : "Unknown denied action validation error";
  }

  try {
    l7Criteria = await evaluateFullL7Criteria();
  } catch (error) {
    l7CriteriaError =
      error instanceof Error ? error.message : "Unknown L7 criteria evaluation error";
  }

  const [manifest, governance, zmosDirExists, manifestExists] =
    await Promise.all([
      readManifest(),
      getGovernanceRuntimeStatus(),
      pathExists(path.join(rootDir, ".z-mos")),
      pathExists(manifestPath),
    ]);
  const legacyZmosExists = await pathExists(path.join(rootDir, ".zmos"));
  const runtimeStateOutsideCanonical =
    manifest.workspace.stateDir !== ".z-mos/state" || manifest.workspace.traceDir !== ".z-mos/trace";
  const manifestLifecycleDefined = manifest.lifecycle.status !== "unknown";
  const manifestScopeDefined =
    Array.isArray(manifest.scope.mutation.allowedPaths) &&
    manifest.scope.mutation.allowedPaths.length > 0;
  const rootDirName = path.basename(rootDir).toLowerCase();
  const freezeNameHint = /-freeze$/u.test(rootDirName);
  const archivedNameHint = /-archived$/u.test(rootDirName);
  const freezeNamingMismatch =
    freezeNameHint && manifest.lifecycle.status !== "freeze";
  const archivedNamingMismatch =
    archivedNameHint && manifest.lifecycle.status !== "archived";

  const [
    traceExists,
    traceAccessible,
    manifestContractExists,
    sessionContractExists,
    traceContractExists,
    governanceRuntimeExists,
    governanceReadinessExists,
    l7CriteriaFileExists,
    nodeIdentityExists,
    workflowPolicyExists,
    aiStatusExists,
    aiContextBuildExists,
    aiRunExists,
    aiTestExists,
    initCommandExists,
    statusCommandExists,
    doctorCommandExists,
    workflowCommandExists,
    workflowRegistryVisible,
    repoStructureConsistent,
    recentTraceInfo,
    recentTraceNodeInfo,
    traceValidation,
  ] = await Promise.all([
    pathExists(tracePath),
    canAppendTrace(tracePath),
    pathExists(path.join(rootDir, "contracts", "manifest.ts")),
    pathExists(path.join(rootDir, "contracts", "session.ts")),
    pathExists(path.join(rootDir, "contracts", "trace.ts")),
    pathExists(path.join(rootDir, "governance", "runtime.ts")),
    pathExists(path.join(rootDir, "governance", "readiness.ts")),
    pathExists(path.join(rootDir, "governance", "l7-criteria.ts")),
    pathExists(nodePath),
    pathExists(workflowPolicyPath),
    pathExists(path.join(rootDir, "cli", "commands", "ai", "ai-status.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "ai", "context-build.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "ai", "ai-run.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "ai", "ai-test.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "init.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "status.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "doctor.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "workflow.ts")),
    pathExists(path.join(rootDir, "core", "workflow-registry.ts")),
    Promise.all([
      pathExists(path.join(rootDir, "cli")),
      pathExists(path.join(rootDir, "core")),
      pathExists(path.join(rootDir, "contracts")),
      pathExists(path.join(rootDir, "governance")),
      pathExists(path.join(rootDir, "trace")),
      pathExists(path.join(rootDir, ".z-mos/entrypoint.json")),
      pathExists(path.join(rootDir, ".z-mos/intent.card.json")),
      pathExists(path.join(rootDir, "docs", "zmos")),
    pathExists(path.join(rootDir, "core", "advisory-context.ts")),
    pathExists(path.join(rootDir, ".z-mos")),
  ]).then((states) => states.every(Boolean)),
    readRecentTraceInfo(tracePath),
    readRecentTraceNodeMetadata(tracePath),
    validateTraceFile({ maxLines: 100 }),
  ]);
  const canonicalFilesMissing =
    !manifestExists || !nodeIdentityExists || !workflowPolicyExists || !traceExists;
  const dualStateConflict = zmosDirExists && legacyZmosExists;

  const stateDirExists = await pathExists(path.join(rootDir, manifest.workspace.stateDir));
  const traceDirExists = await pathExists(path.join(rootDir, manifest.workspace.traceDir));
  const manifestRootAligned = manifest.workspace.root === ".";
  const canonicalPathsAligned =
    stateDirExists &&
    traceDirExists &&
    manifestRootAligned &&
    path.dirname(tracePath) === path.join(rootDir, manifest.workspace.traceDir);

  const requiredRuntimeCommandPresence =
    initCommandExists &&
    statusCommandExists &&
    doctorCommandExists &&
    workflowCommandExists &&
    aiStatusExists &&
    aiContextBuildExists &&
    aiRunExists &&
    aiTestExists;

  const governanceReadinessCoherent =
    governance.level === "governance-runtime-v1"
      ? governance.signals.manifestAvailable &&
        governance.signals.truthAvailable &&
        governance.signals.traceAvailable &&
        governance.signals.contractsPresent &&
        governance.signals.aiCliOperational &&
        governance.activeCapabilities.includes("manifest-runtime-state") &&
        governance.activeCapabilities.includes("truth-runtime-state") &&
        governance.activeCapabilities.includes("append-only-trace") &&
        governance.activeCapabilities.includes("contracts-and-validation") &&
        governance.activeCapabilities.includes("ai-cli-advisory")
      : true;

  const runtimeLoopConsistent =
    requiredRuntimeCommandPresence &&
    governance.level === "governance-runtime-v1" &&
    traceExists &&
    traceAccessible;
  const runtimeCheckWorkflowAvailable = SUPPORTED_WORKFLOWS.includes("runtime-check");
  const advisoryCheckWorkflowAvailable = SUPPORTED_WORKFLOWS.includes("advisory-check");
  const workflowPolicyReadable = workflowPolicy !== null;
  const workflowPolicyCoverageComplete =
    workflowPolicy !== null &&
    SUPPORTED_WORKFLOWS.every((workflowName) =>
      workflowPolicy.workflows.some((entry) => entry.workflowName === workflowName),
    );
  const advisoryAiGovernedCorrectly =
    workflowPolicy !== null &&
    workflowPolicy.workflows.some(
      (entry) =>
        entry.workflowName === "runtime-check" && entry.advisoryAiAllowed === false,
    ) &&
    workflowPolicy.workflows.some(
      (entry) =>
        entry.workflowName === "advisory-check" && entry.advisoryAiAllowed === true,
    );
  const workflowRegistry = workflowPolicy !== null ? await getWorkflowRegistry() : [];
  const workflowRegistryAligned =
    workflowRegistry.length > 0 &&
    workflowRegistry.length === SUPPORTED_WORKFLOWS.length &&
    SUPPORTED_WORKFLOWS.every((workflowName) =>
      workflowRegistry.some((entry) => entry.workflowName === workflowName),
    );
  const deniedActionsStillDisallowed = deniedActionsError === null;
  const l7CriteriaEvaluable = l7Criteria !== null;

  const nodeMetadataCompatible =
    nodeIdentity !== null &&
    nodeIdentity.runtime.trim().length > 0 &&
    nodeIdentity.capabilities.length > 0;
  const nodeRuntimeSupported =
    nodeIdentity !== null && nodeIdentity.runtime === "nodejs-local";
  const nodeRoleRecognized =
    nodeIdentity !== null &&
    ["control-node", "execution-node", "ai-advisory-node"].includes(
      nodeIdentity.node_role,
    );
  const traceNodeMetadataConsistent = recentTraceNodeInfo.nodeMetadataPresent;
  const nodeConsistencyValidated =
    nodeMetadataCompatible &&
    nodeRuntimeSupported &&
    nodeRoleRecognized &&
    traceNodeMetadataConsistent;

  const checks: DoctorCheck[] = [
    {
      label: "entrypoint reference integrity",
      status: missingEntrypointReferences.length > 0 ? "warning" : "healthy",
      detail: missingEntrypointReferences.length > 0 
        ? `entrypoint.json points to missing files: ${missingEntrypointReferences.join(", ")}` 
        : "all entrypoint references are resolving",
    },
    {
      label: "canonical integrity status",
      status: canonicalIntegrity.status,
      detail: `status=${canonicalIntegrity.status}, recovery=${canonicalIntegrity.recoveryClass}`,
    },
    {
      label: "canonical state safe reuse eligibility",
      status: canonicalIntegrity.safeReuse ? "healthy" : "blocking",
      detail: canonicalIntegrity.safeReuse
        ? "canonical state eligible for safe runtime reuse"
        : "canonical state reuse blocked until recovery action is completed",
    },
    {
      label: ".z-mos workspace",
      status: zmosDirExists ? "healthy" : "blocking",
      detail: zmosDirExists ? "present" : "missing",
    },
    {
      label: "manifest file",
      status: manifestExists ? "healthy" : "blocking",
      detail: manifestExists ? `readable at ${manifestPath}` : "missing or unreadable",
    },
    {
      label: "node identity file",
      status: nodeIdentityExists ? "healthy" : "blocking",
      detail: nodeIdentityExists ? `present at ${nodePath}` : "missing",
    },
    {
      label: "node identity readability",
      status: nodeIdentity !== null ? "healthy" : "blocking",
      detail:
        nodeIdentity !== null
          ? `${nodeIdentity.node_id} detected`
          : nodeIdentityError || "node identity could not be read",
    },
    {
      label: "node metadata compatibility",
      status: nodeMetadataCompatible ? "healthy" : "warning",
      detail: nodeMetadataCompatible
        ? `${nodeIdentity?.node_role || "not enough evidence"} is compatible with runtime ${nodeIdentity?.runtime || "not enough evidence"}`
        : "node metadata is incomplete for current runtime expectations",
    },
    {
      label: "node runtime compatibility",
      status: nodeRuntimeSupported ? "healthy" : "warning",
      detail: nodeRuntimeSupported
        ? `${nodeIdentity?.runtime || "not enough evidence"} supported`
        : `${nodeIdentity?.runtime || "not enough evidence"} is not yet recognized as a supported runtime`,
    },
    {
      label: "node role validation",
      status: nodeRoleRecognized ? "healthy" : "warning",
      detail: nodeRoleRecognized
        ? `${nodeIdentity?.node_role || "not enough evidence"} recognized`
        : `${nodeIdentity?.node_role || "not enough evidence"} is not recognized in current node role set`,
    },
    {
      label: "canonical path completeness",
      status: canonicalPathsAligned ? "healthy" : "blocking",
      detail: canonicalPathsAligned
        ? "state, trace, and root paths align with canonical workspace expectations"
        : "manifest canonical paths are incomplete or inconsistent with current filesystem state",
    },
    {
      label: "legacy .zmos state",
      status: legacyZmosExists ? "warning" : "healthy",
      detail: legacyZmosExists
        ? "legacy .zmos directory detected (migration risk)."
        : "legacy .zmos directory not detected",
    },
    {
      label: "dual state conflict (.zmos + .z-mos)",
      status: dualStateConflict ? "warning" : "healthy",
      detail: dualStateConflict
        ? "both legacy and canonical state directories exist; runtime ambiguity risk."
        : "no dual-state conflict detected",
    },
    {
      label: "manifest lifecycle contract",
      status: manifestLifecycleDefined ? "healthy" : "warning",
      detail: manifestLifecycleDefined
        ? `lifecycle.status=${manifest.lifecycle.status}`
        : "manifest lifecycle.status missing/invalid (mutation safety risk).",
    },
    {
      label: "manifest mutation scope contract",
      status: manifestScopeDefined ? "healthy" : "warning",
      detail: manifestScopeDefined
        ? `scope.mutation.allowedPaths=${manifest.scope.mutation.allowedPaths.join(", ")}`
        : "manifest scope.mutation.allowedPaths missing/empty (boundary risk).",
    },
    {
      label: "runtime state outside canonical path",
      status: runtimeStateOutsideCanonical ? "warning" : "healthy",
      detail: runtimeStateOutsideCanonical
        ? `workspace paths not canonical (stateDir=${manifest.workspace.stateDir}, traceDir=${manifest.workspace.traceDir})`
        : "stateDir and traceDir align to .z-mos canonical paths",
    },
    {
      label: "missing canonical files",
      status: canonicalFilesMissing ? "blocking" : "healthy",
      detail: canonicalFilesMissing
        ? "one or more canonical files are missing (manifest/session/node/workflow-policy/trace)."
        : "canonical manifest/session/node/workflow-policy/trace files are present",
    },
    {
      label: "freeze naming mismatch",
      status: freezeNamingMismatch ? "warning" : "healthy",
      detail: freezeNamingMismatch
        ? `directory suffix implies freeze but manifest lifecycle is ${manifest.lifecycle.status}`
        : "freeze naming and lifecycle contract are coherent from current evidence",
    },
    {
      label: "archived naming mismatch",
      status: archivedNamingMismatch ? "warning" : "healthy",
      detail: archivedNamingMismatch
        ? `directory suffix implies archived but manifest lifecycle is ${manifest.lifecycle.status}`
        : "archived naming and lifecycle contract are coherent from current evidence",
    },
    {
      label: "path/reference mutation risk",
      status: runtimeStateOutsideCanonical || !canonicalPathsAligned ? "warning" : "healthy",
      detail:
        runtimeStateOutsideCanonical || !canonicalPathsAligned
          ? "path/reference mismatch detectable; mutation may target non-canonical state."
          : "no high-confidence path/reference mutation risk detected",
    },
    {
      label: "trace appendability",
      status: traceExists && traceAccessible ? "healthy" : "blocking",
      detail:
        traceExists && traceAccessible
          ? `append-capable at ${tracePath}`
          : "missing or not append-capable",
    },
    {
      label: "trace health",
      status:
        traceValidation.status === "corrupted"
          ? "blocking"
          : recentTraceInfo.recentEntriesPresent
            ? "healthy"
            : "warning",
      detail: recentTraceInfo.recentEntriesPresent
        ? `trace file exists, is appendable, and contains recent entries (${recentTraceInfo.recentEntryCount} observed in recent window)`
        : traceValidation.status === "corrupted"
          ? `trace validation detected corruption (${traceValidation.issues.length} issues)`
          : "trace file is present but recent entries were not observed from current evidence",
    },
    {
      label: "trace validation status",
      status:
        traceValidation.status === "healthy"
          ? "healthy"
          : traceValidation.status === "warning"
            ? "warning"
            : "blocking",
      detail: `status=${traceValidation.status}, checked=${traceValidation.checkedLines}, valid=${traceValidation.validLines}, issues=${traceValidation.issues.length}`,
    },
    {
      label: "trace completeness alignment",
      status:
        traceValidation.completeness.emittedExpectedButMissing > 0 ||
        traceValidation.completeness.blockedButEmitted > 0
          ? "warning"
          : "healthy",
      detail:
        traceValidation.completeness.emittedExpectedButMissing > 0 ||
        traceValidation.completeness.blockedButEmitted > 0
          ? `mismatch detected (expected-emitted-missing=${traceValidation.completeness.emittedExpectedButMissing}, blocked-but-emitted=${traceValidation.completeness.blockedButEmitted})`
          : "trace completeness model is aligned with execution evidence",
    },
    {
      label: "trace node metadata consistency",
      status: traceNodeMetadataConsistent ? "healthy" : "warning",
      detail: traceNodeMetadataConsistent
        ? `node_id and node_role present in recent trace entries (${recentTraceNodeInfo.recentCheckedCount} checked)`
        : "recent trace entries do not consistently include node metadata",
    },
    {
      label: "contracts layer",
      status:
        manifestContractExists && traceContractExists
          ? "healthy"
          : "blocking",
      detail:
        manifestContractExists && traceContractExists
          ? "manifest and trace contracts present"
          : "one or more contract files missing",
    },
    {
      label: "workflow policy file",
      status: workflowPolicyExists ? "healthy" : "blocking",
      detail: workflowPolicyExists
        ? `present at ${workflowPolicyPath}`
        : "missing",
    },
    {
      label: "workflow policy readability",
      status: workflowPolicyReadable ? "healthy" : "blocking",
      detail: workflowPolicyReadable
        ? "workflow policy loaded successfully"
        : workflowPolicyError || "workflow policy could not be read",
    },
    {
      label: "workflow policy validation",
      status: workflowPolicyCoverageComplete ? "healthy" : "warning",
      detail: workflowPolicyCoverageComplete
        ? "workflows align with current policy coverage"
        : "policy does not fully cover supported workflow set",
    },
    {
      label: "workflow advisory policy boundary",
      status: advisoryAiGovernedCorrectly ? "healthy" : "warning",
      detail: advisoryAiGovernedCorrectly
        ? "advisory AI allowed only where current policy permits"
        : "advisory AI permissions do not fully align with current workflow set",
    },
    {
      label: "workflow registry availability",
      status: workflowRegistryVisible ? "healthy" : "blocking",
      detail: workflowRegistryVisible
        ? "workflow registry module is available"
        : "workflow registry module is missing",
    },
    {
      label: "governed workflow visibility",
      status: workflowRegistry.length > 0 ? "healthy" : "warning",
      detail:
        workflowRegistry.length > 0
          ? `workflow registry exposes ${workflowRegistry.length} governed workflow entries`
          : "governed workflow registry is not visible from current runtime evidence",
    },
    {
      label: "workflow policy and registry alignment",
      status: workflowRegistryAligned ? "healthy" : "warning",
      detail: workflowRegistryAligned
        ? "workflow policy and runtime registry are aligned"
        : "workflow policy and runtime registry are not fully aligned",
    },
    {
      label: "denied actions validation",
      status: deniedActionsStillDisallowed ? "healthy" : "warning",
      detail: deniedActionsStillDisallowed
        ? "mutation and delegation remain disallowed for governed workflows"
        : deniedActionsError || "denied action validation could not be confirmed",
    },
    {
      label: "Full L7 criteria definition",
      status: l7CriteriaFileExists ? "healthy" : "blocking",
      detail: l7CriteriaFileExists
        ? "Full L7 criteria definition exists"
        : "Full L7 criteria definition is missing",
    },
    {
      label: "Full L7 criteria evaluation",
      status: l7CriteriaEvaluable ? "healthy" : "warning",
      detail: l7CriteriaEvaluable
        ? `Full L7 evaluation completed (${l7Criteria?.fullL7Achieved ? "achieved" : "not yet achieved"})`
        : l7CriteriaError || "Full L7 criteria could not be evaluated",
    },
    ...((l7Criteria?.criteria.map((criterion): DoctorCheck => ({
      label: `Full L7 criterion: ${criterion.label}`,
      status: criterion.satisfied ? "healthy" : "warning",
      detail: criterion.detail,
    })) ?? []) as DoctorCheck[]),
    {
      label: "required runtime commands",
      status: requiredRuntimeCommandPresence ? "healthy" : "blocking",
      detail:
        requiredRuntimeCommandPresence
          ? "init, status, doctor, workflow, ai-status, ai-context-build, ai-run, and ai-test handlers present"
          : "one or more required runtime command handlers missing",
    },
    {
      label: "runtime-check workflow availability",
      status: runtimeCheckWorkflowAvailable ? "healthy" : "blocking",
      detail: runtimeCheckWorkflowAvailable
        ? "runtime-check workflow is available"
        : "runtime-check workflow is missing from supported workflow set",
    },
    {
      label: "advisory-check workflow availability",
      status: advisoryCheckWorkflowAvailable ? "healthy" : "warning",
      detail: advisoryCheckWorkflowAvailable
        ? "advisory-check workflow is available"
        : "bounded advisory workflow is not available from current workflow set",
    },
    {
      label: "governance runtime presence",
      status:
        governanceRuntimeExists && governanceReadinessExists ? "healthy" : "blocking",
      detail:
        governanceRuntimeExists && governanceReadinessExists
          ? "runtime and readiness modules present"
          : "governance runtime files incomplete",
    },
    {
      label: "governance readiness coherence",
      status: governanceReadinessCoherent ? "healthy" : "warning",
      detail: governanceReadinessCoherent
        ? `readiness level ${governance.level} is coherent with active signals`
        : "readiness interpretation does not fully align with runtime signals",
    },
    {
      label: "AI CLI path",
      status:
        aiStatusExists && aiContextBuildExists && aiRunExists && aiTestExists
          ? "healthy"
          : "blocking",
      detail:
        aiStatusExists && aiContextBuildExists && aiRunExists && aiTestExists
          ? "ai-status, ai-context-build, ai-run, and ai-test handlers present"
          : "one or more AI command handlers missing",
    },
    {
      label: "repository structure",
      status: repoStructureConsistent ? "healthy" : "warning",
      detail: repoStructureConsistent
        ? "core runtime directories are minimally consistent with current Z-MOS stage"
        : "one or more required top-level runtime directories are missing",
    },
    {
      label: "runtime loop consistency",
      status: runtimeLoopConsistent ? "healthy" : "warning",
      detail: runtimeLoopConsistent
        ? "init, status, doctor, workflow, trace, and AI advisory loop appear coherent"
        : "runtime loop is present but not fully coherent from current evidence",
    },
    {
      label: "node consistency",
      status: nodeConsistencyValidated ? "healthy" : "warning",
      detail: nodeConsistencyValidated
        ? `${nodeIdentity?.node_role || "not enough evidence"} validated for runtime ${nodeIdentity?.runtime || "not enough evidence"}`
        : "node identity, runtime, or trace metadata are not fully aligned from current evidence",
    },
  ];

  const detectedGaps = checks
    .filter((check) => check.status !== "healthy")
    .map((check) => `${check.label} (${check.status})`);
  const overallStatus = resolveOverallStatus(checks);
  const healthyCount = checks.filter((check) => check.status === "healthy").length;
  const warningCount = checks.filter((check) => check.status === "warning").length;
  const blockingCount = checks.filter((check) => check.status === "blocking").length;
  const recommendedAction =
    overallStatus === "healthy"
      ? "Continue with the next runtime milestone; current workspace diagnostics pass."
      : overallStatus === "warning"
        ? `Review the following consistency warnings: ${detectedGaps.join(", ")}`
        : `Resolve the following blocking runtime issues first: ${detectedGaps.join(", ")}`;

  return {
    profile: "core-control",
    checks,
    overallStatus,
    diagnosticsSummary: {
      healthy: healthyCount,
      warning: warningCount,
      blocking: blockingCount,
    },
    governance,
    detectedGaps,
    recommendedAction,
    manifest,
    nodeIdentity,
    l7Criteria,
    paths: {
      manifestPath,
      nodePath,
      tracePath,
    },
    observations: {
      recentTraceEntriesPresent: recentTraceInfo.recentEntriesPresent,
      recentTraceEntryCount: recentTraceInfo.recentEntryCount,
      recentTraceNodeMetadataPresent: recentTraceNodeInfo.nodeMetadataPresent,
      recentTraceNodeCheckedCount: recentTraceNodeInfo.recentCheckedCount,
      nodeIdentityPresent: nodeIdentityExists,
    },
  };
}

async function evaluateProjectDoctorDiagnostics(): Promise<DoctorEvaluation> {
  const rootDir = process.cwd();
  const manifestPath = getManifestPath();
  const nodePath = getNodePath();
  const tracePath = await getTraceFilePath();
  const workflowPolicyPath = getWorkflowPolicyPath();
  const normalization = await normalizeBootstrapLikeManifestIfSafe(rootDir);

  const [manifest, governance, workflowPolicyLoaded, nodeIdentityLoaded] = await Promise.all([
    readManifest(),
    getGovernanceRuntimeStatus(),
    loadWorkflowPolicy()
      .then(() => true)
      .catch(() => false),
    loadNodeIdentity()
      .then(() => true)
      .catch(() => false),
  ]);
  const [zmosDirExists, manifestExists, traceExists, traceAccessible, nodeExists] =
    await Promise.all([
      pathExists(path.join(rootDir, ".z-mos")),
      pathExists(manifestPath),
      pathExists(tracePath),
      canAppendTrace(tracePath),
      pathExists(nodePath),
    ]);
  const recentTraceInfo = await readRecentTraceInfo(tracePath);
  const recentTraceNodeInfo = await readRecentTraceNodeMetadata(tracePath);

  const checks: DoctorCheck[] = [
    {
      label: ".z-mos workspace",
      status: zmosDirExists ? "healthy" : "blocking",
      detail: zmosDirExists ? "present" : "missing",
    },
    {
      label: "manifest file",
      status: manifestExists ? "healthy" : "blocking",
      detail: manifestExists ? `readable at ${manifestPath}` : "missing or unreadable",
    },

    {
      label: "trace file",
      status: traceExists ? "healthy" : "warning",
      detail: traceExists ? `present at ${tracePath}` : "not enough evidence to conclude",
    },
    {
      label: "trace appendability",
      status: traceExists && traceAccessible ? "healthy" : "warning",
      detail: traceExists && traceAccessible ? "append-capable" : "not append-capable from current evidence",
    },
    {
      label: "workflow policy presence",
      status: workflowPolicyLoaded ? "healthy" : "warning",
      detail: workflowPolicyLoaded
        ? `loaded from ${workflowPolicyPath}`
        : "not enough evidence to conclude",
    },
    {
      label: "node identity presence",
      status: nodeExists && nodeIdentityLoaded ? "healthy" : "warning",
      detail: nodeExists && nodeIdentityLoaded
        ? `present at ${nodePath}`
        : "not enough evidence to conclude",
    },
    {
      label: "manifest lifecycle contract",
      status: manifest.lifecycle.status === "unknown" ? "warning" : "healthy",
      detail: `lifecycle.status=${manifest.lifecycle.status}`,
    },
    {
      label: "manifest scope mutation contract",
      status:
        Array.isArray(manifest.scope.mutation.allowedPaths) &&
        manifest.scope.mutation.allowedPaths.length > 0
          ? "healthy"
          : "warning",
      detail:
        manifest.scope.mutation.allowedPaths.length > 0
          ? manifest.scope.mutation.allowedPaths.join(", ")
          : "not enough evidence to conclude",
    },

    {
      label: "trace node metadata consistency",
      status: recentTraceNodeInfo.nodeMetadataPresent ? "healthy" : "warning",
      detail: recentTraceNodeInfo.nodeMetadataPresent
        ? `node_id and node_role present in recent trace entries (${recentTraceNodeInfo.recentCheckedCount} checked)`
        : "recent trace entries do not consistently include node metadata",
    },
    {
      label: "core-runtime criteria applicability",
      status: "healthy",
      detail:
        "core-only runtime checks are intentionally excluded in product-project doctor profile",
    },
    {
      label: "manifest normalization safety",
      status: normalization.safe ? "healthy" : "warning",
      detail: normalization.reason,
    },
  ];

  const detectedGaps = checks
    .filter((check) => check.status !== "healthy")
    .map((check) => `${check.label} (${check.status})`);
  const overallStatus = resolveOverallStatus(checks);
  const healthyCount = checks.filter((check) => check.status === "healthy").length;
  const warningCount = checks.filter((check) => check.status === "warning").length;
  const blockingCount = checks.filter((check) => check.status === "blocking").length;
  const recommendedAction =
    overallStatus === "healthy"
      ? "Project profile checks are healthy; continue with scoped work."
      : overallStatus === "warning"
        ? `Review project-profile warnings before mutation: ${detectedGaps.join(", ")}`
        : `Resolve blocking project-profile issues first: ${detectedGaps.join(", ")}`;

  return {
    profile: "product-project",
    checks,
    overallStatus,
    diagnosticsSummary: {
      healthy: healthyCount,
      warning: warningCount,
      blocking: blockingCount,
    },
    governance,
    detectedGaps,
    recommendedAction,
    manifest,
    nodeIdentity: nodeIdentityLoaded ? await loadNodeIdentity().catch(() => null) : null,
    l7Criteria: null,
    paths: {
      manifestPath,
      nodePath,
      tracePath,
    },
    observations: {
      recentTraceEntriesPresent: recentTraceInfo.recentEntriesPresent,
      recentTraceEntryCount: recentTraceInfo.recentEntryCount,
      recentTraceNodeMetadataPresent: recentTraceNodeInfo.nodeMetadataPresent,
      recentTraceNodeCheckedCount: recentTraceNodeInfo.recentCheckedCount,
      nodeIdentityPresent: nodeExists,
    },
  };
}

export async function evaluateDoctorDiagnostics(): Promise<DoctorEvaluation> {
  const profile = resolveDoctorProfile();
  if (profile === "product-project") {
    return evaluateProjectDoctorDiagnostics();
  }
  return evaluateCoreDoctorDiagnostics();
}

function renderDoctorReport(evaluation: DoctorEvaluation): string {
  const {
    checks,
    overallStatus,
    diagnosticsSummary,
    governance,
    detectedGaps,
    recommendedAction,
    manifest,
    l7Criteria,
  } = evaluation;

  return [
    "Z-MOS Doctor Report",
    "",
    `Profile: ${evaluation.profile}`,
    "",
    `Overall Status: ${overallStatus}`,
    "",
    "Checks",
    ...checks.map(formatCheck),
    "",
    "Diagnostics Summary",
    `- healthy: ${diagnosticsSummary.healthy}`,
    `- warning: ${diagnosticsSummary.warning}`,
    `- blocking: ${diagnosticsSummary.blocking}`,
    "",
    `Readiness Level: ${governance.level}`,
    `Active Capabilities: ${governance.activeCapabilities.join(", ") || "not enough evidence"}`,
    `Readiness Evidence: manifest=${String(governance.signals.manifestAvailable)}, truth=${String(governance.signals.truthAvailable)}, trace=${String(governance.signals.traceAvailable)}, contracts=${String(governance.signals.contractsPresent)}, ai_cli=${String(governance.signals.aiCliOperational)}, node_identity=${String(governance.signals.nodeIdentityActive)}`,
    "",
    "Full L7 Criteria",
    `Full L7: ${l7Criteria?.fullL7Achieved ? "yes" : "no"}`,
    `Missing Criteria: ${l7Criteria?.missingCriteria.join(", ") || "(none)"}`,
    "",
    `Detected Gaps: ${detectedGaps.length > 0 ? detectedGaps.join(", ") : "(none)"}`,
    `Recommended Action: ${recommendedAction}`,
    "",
    `Repository: ${manifest.repository.name}`,
    "",
    renderCommandExecutionResult({
      command: "doctor",
      status: overallStatus === "blocking" ? "blocked" : overallStatus === "warning" ? "warning" : "success",
      resultClass:
        overallStatus === "blocking"
          ? "blocked-canonical-integrity"
          : overallStatus === "warning"
            ? "warning-execution"
            : "success",
      warningReason: overallStatus === "warning" ? detectedGaps.join(", ") : undefined,
      traceExpectation: "required-if-business-logic",
      traceResult: "emitted",
      nextAction: recommendedAction,
    }),
  ].join("\n");
}

function renderCanonicalIntegrityFallbackReport(
  integrity: CanonicalIntegrityResult,
  reason: string,
): string {
  const lines = [
    "Z-MOS Doctor Report",
    "",
    "Overall Status: blocking",
    "",
    "Checks",
    `- canonical integrity status — ${integrity.status}: recovery=${integrity.recoveryClass}`,
    `- doctor runtime execution — blocking: ${reason}`,
    "",
    "Canonical Findings",
  ];

  if (integrity.findings.length === 0) {
    lines.push("- (none)");
  } else {
    for (const finding of integrity.findings) {
      lines.push(
        `- ${finding.code} [${finding.status}]`,
        `  recovery class: ${finding.recoveryClass}`,
        `  files: ${finding.affectedFiles.join(", ") || "not enough evidence"}`,
        `  reason: ${finding.reason}`,
        `  action: ${finding.action}`,
      );
    }
  }

  lines.push("", "Canonical Invariants");
  if (integrity.invariants.length === 0) {
    lines.push("- (none)");
  } else {
    for (const invariant of integrity.invariants) {
      lines.push(`- ${invariant.name} — ${invariant.status}: ${invariant.detail}`);
    }
  }

  lines.push(
    "",
    renderCommandExecutionResult({
      command: "doctor",
      status: "blocked",
      resultClass: "blocked-canonical-integrity",
      reason,
      traceExpectation: "required-if-business-logic",
      traceResult: "not-emitted-due-failure",
      nextAction:
        integrity.findings[0]?.action ||
        "Repair canonical integrity blockers before rerunning doctor.",
    }),
  );

  return lines.join("\n");
}

export async function runDoctorCommand(): Promise<void> {
  const traceMutationGuard = await evaluateMutationGuard({
    command: "zcl doctor (trace)",
    targetPaths: [".z-mos/trace/runtime-trace.jsonl"],
    allowProtectedPrefixes: [".z-mos"],
  });

  try {
    const evaluation = await evaluateDoctorDiagnostics();
    const {
      overallStatus,
      diagnosticsSummary,
      governance,
      detectedGaps,
      nodeIdentity,
      l7Criteria,
      paths,
      observations,
    } = evaluation;

    if (traceMutationGuard.allowed) {
      await appendTraceRecord({
        command: "zcl doctor",
        status: overallStatus === "blocking" ? "failed" : "success",
        actor: "system",
        details: {
          overallStatus,
          diagnosticsClassification: overallStatus,
          profile: "product-project",
          diagnosticsSummary,
          readinessLevel: governance.level,
          readinessSignals: governance.signals,
          activeCapabilities: governance.activeCapabilities,
          fullL7Achieved: l7Criteria?.fullL7Achieved ?? false,
          missingL7Criteria: l7Criteria?.missingCriteria ?? ["not enough evidence"],
          detectedGaps,
          recentTraceEntriesPresent: observations.recentTraceEntriesPresent,
          nodeIdentityPresent: observations.nodeIdentityPresent,
          nodeId: nodeIdentity?.node_id ?? null,
          nodeRole: nodeIdentity?.node_role ?? null,
          tracePath: paths.tracePath,
        },
      });
    }

    console.log(renderDoctorReport(evaluation));
  } catch (error) {
    const integrity = await evaluateCanonicalStateIntegrity();
    const reason = error instanceof Error ? error.message : "Unknown doctor runtime error";
    let tracePath = "not enough evidence";
    try {
      tracePath = await getTraceFilePath();
      if (traceMutationGuard.allowed) {
        await appendTraceRecord({
          command: "zcl doctor",
          status: "failed",
          actor: "system",
          details: {
            overallStatus: "blocking",
            diagnosticsClassification: "blocking",
            canonicalIntegrity: integrity.status,
            canonicalRecoveryClass: integrity.recoveryClass,
            detectedGaps: integrity.findings.map((finding) => finding.code),
            tracePath,
            reason,
          },
        });
      }
    } catch {
      // trace failure should not suppress doctor fallback report
    }

    console.log(renderCanonicalIntegrityFallbackReport(integrity, reason));
    process.exitCode = 1;
  }
}
