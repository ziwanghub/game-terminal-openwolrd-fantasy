import { accessSync, constants, existsSync, realpathSync, promises as fs } from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { evaluateCanonicalStateIntegrity } from "./state-integrity.js";
import { buildDocumentIndex } from "./document-index.js";
import { getTraceFilePath } from "./trace-writer.js";
import { validateTraceFile } from "./trace-validator.js";
import { ensureValidLockOrCleanup } from "./port-lock.js";
import { readManifest } from "./manifest.js";
import { verifyWorktree } from "./worktree.js";
import { validateTruthContractPayload } from "./truth-store.js";
import { getGitContext } from "./git.js";

type CheckStatus = "healthy" | "warning" | "blocking";
export type PreflightStatus = CheckStatus;

export type PreflightCheck = {
  name: string;
  code:
    | "dist-missing"
    | "dependency-invalid"
    | "canonical-missing"
    | "runtime-invalid"
    | "environment-mismatch"
    | "trace-unhealthy"
    | "document-structure"
    | "document-schema"
    | "document-naming"
    | "behavior-missing"
    | "destructive-intent"
    | "runtime-lock"
    | "unknown";
  status: CheckStatus;
  message: string;
  likelyCause: string;
  action: string;
};

export type PreflightReport = {
  status: PreflightStatus;
  checks: PreflightCheck[];
};

export type PreflightOptions = {
  allowMissingCanonical?: boolean;
  executionMode?: "ops-dist" | "dev-ts";
  intendedCommand?: string;
};

const ROOT_DIR = process.cwd();
const DIST_GATEWAY_PATH = path.join(ROOT_DIR, "dist", "cli", "gateway.js");
const TRUTH_CONTRACT_PATH = path.join(ROOT_DIR, ".z-mos", "truth.contract.json");

type TruthContract = Record<string, unknown>;

function aggregateStatus(checks: PreflightCheck[]): PreflightStatus {
  if (checks.some((check) => check.status === "blocking")) {
    return "blocking";
  }
  if (checks.some((check) => check.status === "warning")) {
    return "warning";
  }
  return "healthy";
}

function expectedEsbuildPackage(): string {
  if (process.platform === "darwin" && process.arch === "arm64") {
    return "@esbuild/darwin-arm64";
  }
  if (process.platform === "darwin" && process.arch === "x64") {
    return "@esbuild/darwin-x64";
  }
  if (process.platform === "linux" && process.arch === "x64") {
    return "@esbuild/linux-x64";
  }
  if (process.platform === "linux" && process.arch === "arm64") {
    return "@esbuild/linux-arm64";
  }
  return "";
}

function checkDistIntegrity(): PreflightCheck {
  if (!existsSync(DIST_GATEWAY_PATH)) {
    return {
      name: "dist-integrity",
      code: "dist-missing",
      status: "blocking",
      message: "dist/cli/gateway.js is missing",
      likelyCause: "Operational build artifact is not available.",
      action: "Run npm run ops:build and retry preflight.",
    };
  }

  try {
    accessSync(DIST_GATEWAY_PATH, constants.R_OK);
  } catch {
    return {
      name: "dist-integrity",
      code: "dist-missing",
      status: "blocking",
      message: "dist/cli/gateway.js exists but is not readable",
      likelyCause: "Artifact permissions are invalid.",
      action: "Fix file permissions and rerun npm run ops:build.",
    };
  }

  try {
    const resolvedPath = realpathSync(DIST_GATEWAY_PATH);
    const expectedPrefix = realpathSync(path.join(ROOT_DIR, "dist", "cli"));
    if (!resolvedPath.startsWith(expectedPrefix)) {
      return {
        name: "dist-integrity",
        code: "dist-missing",
        status: "blocking",
        message: "Resolved dist path does not match intended dist/cli location",
        likelyCause: "Artifact path resolution mismatch.",
        action: "Clean dist, rebuild, and verify dist/cli/gateway.js path.",
      };
    }
  } catch {
    return {
      name: "dist-integrity",
      code: "dist-missing",
      status: "blocking",
      message: "Unable to resolve dist/cli/gateway.js path",
      likelyCause: "Dist artifact path is broken or inaccessible.",
      action: "Rebuild dist and verify artifact path.",
    };
  }

  return {
    name: "dist-integrity",
    code: "dist-missing",
    status: "healthy",
    message: "dist/cli/gateway.js is present and readable",
    likelyCause: "none",
    action: "No action required.",
  };
}

function checkNodeRuntime(): PreflightCheck {
  const version = process.versions.node;
  const major = Number.parseInt(version.split(".")[0] ?? "0", 10);
  if (!version || Number.isNaN(major)) {
    return {
      name: "node-runtime",
      code: "runtime-invalid",
      status: "blocking",
      message: "Node runtime version is unavailable",
      likelyCause: "Runtime metadata cannot be resolved.",
      action: "Verify Node.js installation and retry.",
    };
  }

  if (major < 20) {
    return {
      name: "node-runtime",
      code: "runtime-invalid",
      status: "warning",
      message: `Node.js ${version} detected (recommended >= 22 for EVO 1.1 ops path)`,
      likelyCause: "Runtime may be below recommended operational baseline.",
      action: "Use Node.js 20+ for Mac mini M4 operator flow.",
    };
  }

  return {
    name: "node-runtime",
    code: "runtime-invalid",
    status: "healthy",
    message: `Node.js ${version} detected`,
    likelyCause: "none",
    action: "No action required.",
  };
}

function checkDependencyHealth(): PreflightCheck {
  const nodeModulesPath = path.join(ROOT_DIR, "node_modules");
  if (!existsSync(nodeModulesPath)) {
    return {
      name: "dependency-health",
      code: "dependency-invalid",
      status: "blocking",
      message: "node_modules directory is missing",
      likelyCause: "Dependencies are not installed.",
      action: "Run npm install and rerun preflight.",
    };
  }

  const requireFromRoot = createRequire(path.join(ROOT_DIR, "package.json"));
  try {
    requireFromRoot.resolve("typescript/package.json");
  } catch {
    return {
      name: "dependency-health",
      code: "dependency-invalid",
      status: "blocking",
      message: "Required dependency typescript is not resolvable",
      likelyCause: "Install is incomplete or corrupted.",
      action: "Run npm install (or clean reinstall) and rerun preflight.",
    };
  }

  return {
    name: "dependency-health",
    code: "dependency-invalid",
    status: "healthy",
    message: "Core dependencies are present for operational path",
    likelyCause: "none",
    action: "No action required.",
  };
}

async function checkCanonicalStatePresence(
  options?: PreflightOptions,
): Promise<PreflightCheck> {
  const allowMissingCanonical = Boolean(options?.allowMissingCanonical);
  const integrity = await evaluateCanonicalStateIntegrity();
  const topFinding = integrity.findings[0];
  const affectedFiles = topFinding?.affectedFiles.join(", ") || "not enough evidence";

  if (integrity.status === "healthy") {
    return {
      name: "canonical-state",
      code: "canonical-missing",
      status: "healthy",
      message: "Canonical state integrity is healthy",
      likelyCause: "none",
      action: "No action required.",
    };
  }

  if (
    integrity.status === "blocking" &&
    allowMissingCanonical &&
    integrity.recoveryClass === "bootstrap-required"
  ) {
    return {
      name: "canonical-state",
      code: "canonical-missing",
      status: "warning",
      message: `Canonical bootstrap required (${integrity.recoveryClass})`,
      likelyCause:
        topFinding?.reason || "Canonical state is missing and requires bootstrap.",
      action:
        topFinding?.action ||
        "Run init to bootstrap canonical state, then rerun preflight.",
    };
  }

  return {
    name: "canonical-state",
    code: "canonical-missing",
    status: integrity.status,
    message: `Canonical integrity status: ${integrity.status} (${integrity.recoveryClass})`,
    likelyCause:
      topFinding?.reason ||
      `Canonical integrity finding detected. Affected files: ${affectedFiles}`,
    action:
      topFinding?.action ||
      "Review canonical integrity findings and repair state before operator execution.",
  };
}

function checkLoaderRisk(options?: PreflightOptions): PreflightCheck {
  const executionMode = options?.executionMode ?? "ops-dist";

  if (executionMode !== "dev-ts") {
    return {
      name: "loader-risk",
      code: "runtime-invalid",
      status: "healthy",
      message: "TS loader risk check skipped for ops-dist execution mode",
      likelyCause: "none",
      action: "No action required.",
    };
  }

  const requireFromRoot = createRequire(path.join(ROOT_DIR, "package.json"));
  let tsxResolvable = true;
  try {
    requireFromRoot.resolve("tsx/package.json");
  } catch {
    tsxResolvable = false;
  }

  const expectedEsbuild = expectedEsbuildPackage();
  let expectedEsbuildPresent = true;
  if (expectedEsbuild) {
    try {
      requireFromRoot.resolve(`${expectedEsbuild}/package.json`);
    } catch {
      expectedEsbuildPresent = false;
    }
  }

  if (!tsxResolvable && !expectedEsbuildPresent) {
    return {
      name: "loader-risk",
      code: "dependency-invalid",
      status: "warning",
      message:
        "tsx and expected esbuild package are not fully resolvable (dev-mode startup risk)",
      likelyCause: "Dependency set is incomplete for TS runtime path.",
      action:
        "For development mode install/repair tsx and host-matching esbuild package.",
    };
  }

  if (!tsxResolvable) {
    return {
      name: "loader-risk",
      code: "dependency-invalid",
      status: "warning",
      message: "tsx is not resolvable (dev-mode startup risk)",
      likelyCause: "TS runtime dependency missing.",
      action: "Install tsx if development TS runtime path is required.",
    };
  }

  if (!expectedEsbuildPresent) {
    return {
      name: "loader-risk",
      code: "dependency-invalid",
      status: "warning",
      message:
        "Expected host esbuild package is not resolvable (possible platform mismatch risk)",
      likelyCause: `esbuild package mismatch for ${process.platform}-${process.arch}.`,
      action: "Reinstall dependencies on this host to align esbuild platform package.",
    };
  }

  return {
    name: "loader-risk",
    code: "dependency-invalid",
    status: "healthy",
    message: "No immediate TS loader risk detected for development path",
    likelyCause: "none",
    action: "No action required.",
  };
}

function checkEnvironmentConsistency(): PreflightCheck {
  if (process.platform !== "darwin" || process.arch !== "arm64") {
    return {
      name: "environment-consistency",
      code: "environment-mismatch",
      status: "warning",
      message: `Environment mismatch detected: ${process.platform}-${process.arch}`,
      likelyCause: "Runtime is outside EVO 1.1 locked target.",
      action: "Use Mac mini M4 (macOS arm64) for release-gated validation.",
    };
  }

  return {
    name: "environment-consistency",
    code: "environment-mismatch",
    status: "healthy",
    message: "Environment matches EVO 1.1 lock (macOS arm64)",
    likelyCause: "none",
    action: "No action required.",
  };
}

async function loadTruthForPreflight(): Promise<TruthContract | null> {
  try {
    const raw = await fs.readFile(TRUTH_CONTRACT_PATH, "utf8");
    const parsed = JSON.parse(raw) as unknown;
    await validateTruthContractPayload(parsed);
    return parsed as TruthContract;
  } catch {
    return null;
  }
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

async function checkFiveStateCode(truth: TruthContract | null): Promise<PreflightCheck> {
  if (!truth) {
    return {
      name: "phase3-5state-code",
      code: "unknown",
      status: "warning",
      message: "Code state evidence missing from truth.contract",
      likelyCause: "truth.contract.json is missing or invalid.",
      action: "Run `zcl truth build` to refresh code state evidence.",
    };
  }

  const codeRef = truth.code_ref as Record<string, unknown> | undefined;
  const truthCommit = asString(codeRef?.commit);
  const truthBranch = asString(codeRef?.branch);
  const git = getGitContext();

  if (!truthCommit || !truthBranch || !git.commit || !git.branch) {
    return {
      name: "phase3-5state-code",
      code: "unknown",
      status: "warning",
      message: "Code state has incomplete evidence for commit/branch comparison",
      likelyCause: "Missing commit/branch in truth or local git context.",
      action: "Refresh truth and ensure repository git metadata is available.",
    };
  }

  if (truthCommit !== git.commit || truthBranch !== git.branch) {
    return {
      name: "phase3-5state-code",
      code: "unknown",
      status: "warning",
      message: "Code state mismatch between truth.contract and current git HEAD",
      likelyCause: "truth.contract is stale relative to current branch/commit.",
      action: "Rebuild truth contract before mutation (`zcl truth build`).",
    };
  }

  return {
    name: "phase3-5state-code",
    code: "unknown",
    status: "healthy",
    message: "Code state is consistent with current git branch/commit",
    likelyCause: "none",
    action: "No action required.",
  };
}

function checkFiveStateRuntime(truth: TruthContract | null): PreflightCheck {
  if (!truth) {
    return {
      name: "phase3-5state-runtime",
      code: "unknown",
      status: "warning",
      message: "Runtime state evidence missing from truth.contract",
      likelyCause: "truth.contract.json is missing or invalid.",
      action: "Run `zcl truth build` to refresh runtime state evidence.",
    };
  }

  const runtimeRef = truth.runtime_ref as Record<string, unknown> | undefined;
  const runtimePlatform = asString(runtimeRef?.platform);
  if (!runtimePlatform) {
    return {
      name: "phase3-5state-runtime",
      code: "unknown",
      status: "warning",
      message: "Runtime state missing platform evidence in truth.contract",
      likelyCause: "runtime_ref.platform is missing.",
      action: "Rebuild truth contract to capture runtime state.",
    };
  }

  const currentPlatform = `${process.platform}-${process.arch}`;
  if (runtimePlatform !== currentPlatform) {
    return {
      name: "phase3-5state-runtime",
      code: "unknown",
      status: "warning",
      message: `Runtime state mismatch (truth=${runtimePlatform}, current=${currentPlatform})`,
      likelyCause: "truth captured from different runtime host/arch.",
      action: "Rebuild truth contract on this runtime before execution.",
    };
  }

  return {
    name: "phase3-5state-runtime",
    code: "unknown",
    status: "healthy",
    message: "Runtime state is consistent with current platform",
    likelyCause: "none",
    action: "No action required.",
  };
}

function checkFiveStateEnvironment(truth: TruthContract | null): PreflightCheck {
  if (!truth) {
    return {
      name: "phase3-5state-environment",
      code: "unknown",
      status: "warning",
      message: "Environment state evidence missing from truth.contract",
      likelyCause: "truth.contract.json is missing or invalid.",
      action: "Run `zcl truth build` to refresh environment evidence.",
    };
  }

  const envRef = truth.env_ref as Record<string, unknown> | undefined;
  const targetEnv = asString(envRef?.target_env);
  const currentEnv = process.env.NODE_ENV || "development";
  if (!targetEnv) {
    return {
      name: "phase3-5state-environment",
      code: "unknown",
      status: "warning",
      message: "Environment state missing target_env in truth.contract",
      likelyCause: "env_ref.target_env is missing.",
      action: "Rebuild truth contract to include environment evidence.",
    };
  }
  if (targetEnv !== currentEnv) {
    return {
      name: "phase3-5state-environment",
      code: "unknown",
      status: "warning",
      message: `Environment mismatch (truth=${targetEnv}, current=${currentEnv})`,
      likelyCause: "truth captured under different NODE_ENV.",
      action: "Rebuild truth contract or align execution environment.",
    };
  }
  return {
    name: "phase3-5state-environment",
    code: "unknown",
    status: "healthy",
    message: "Environment state is consistent with current NODE_ENV",
    likelyCause: "none",
    action: "No action required.",
  };
}

function checkFiveStateDataConfig(truth: TruthContract | null): PreflightCheck {
  if (!truth) {
    return {
      name: "phase3-5state-data-config",
      code: "unknown",
      status: "warning",
      message: "Data/config state evidence missing from truth.contract",
      likelyCause: "truth.contract.json is missing or invalid.",
      action: "Run `zcl truth build` to refresh data/config evidence.",
    };
  }

  const dataRef = truth.data_ref as Record<string, unknown> | undefined;
  const envRef = truth.env_ref as Record<string, unknown> | undefined;
  const schemaHash = asString(dataRef?.schema_hash);
  const configHash = asString(envRef?.config_hash);
  if (!schemaHash || !configHash) {
    return {
      name: "phase3-5state-data-config",
      code: "unknown",
      status: "warning",
      message: "Data/config state has missing schema_hash or config_hash",
      likelyCause: "truth data_ref/env_ref is incomplete.",
      action: "Rebuild truth contract to restore data/config evidence.",
    };
  }

  return {
    name: "phase3-5state-data-config",
    code: "unknown",
    status: "healthy",
    message: "Data/config state evidence is present",
    likelyCause: "none",
    action: "No action required.",
  };
}

async function checkFiveStateAssetsSchema(truth: TruthContract | null): Promise<PreflightCheck> {
  if (!truth) {
    return {
      name: "phase3-5state-assets-schema",
      code: "unknown",
      status: "warning",
      message: "Assets/schema state evidence missing from truth.contract",
      likelyCause: "truth.contract.json is missing or invalid.",
      action: "Run `zcl truth build` to refresh assets/schema evidence.",
    };
  }

  const schemaExists = existsSync(path.join(ROOT_DIR, ".z-mos", "schemas", "truth.contract.schema.json"));
  const assetRef = truth.asset_ref as Record<string, unknown> | undefined;
  const bundleHash = asString(assetRef?.bundle_hash);
  const cacheHash = asString(assetRef?.cache_hash);

  if (!schemaExists || !bundleHash || !cacheHash) {
    return {
      name: "phase3-5state-assets-schema",
      code: "unknown",
      status: "warning",
      message: "Assets/schema state is incomplete (missing schema file or asset hashes)",
      likelyCause: "Schema path missing or truth asset_ref incomplete.",
      action: "Restore schema files and rebuild truth contract.",
    };
  }

  return {
    name: "phase3-5state-assets-schema",
    code: "unknown",
    status: "healthy",
    message: "Assets/schema state evidence is present",
    likelyCause: "none",
    action: "No action required.",
  };
}

async function runPhase3FiveStateVerification(): Promise<PreflightCheck[]> {
  const truth = await loadTruthForPreflight();
  const checks: PreflightCheck[] = [];
  checks.push(await checkFiveStateCode(truth));
  checks.push(checkFiveStateRuntime(truth));
  checks.push(checkFiveStateEnvironment(truth));
  checks.push(checkFiveStateDataConfig(truth));
  checks.push(await checkFiveStateAssetsSchema(truth));
  return checks;
}

async function checkTraceReadiness(): Promise<PreflightCheck> {
  const tracePath = await getTraceFilePath();
  const traceDir = path.dirname(tracePath);

  try {
    await fs.mkdir(traceDir, { recursive: true });
  } catch {
    return {
      name: "trace-readiness",
      code: "trace-unhealthy",
      status: "blocking",
      message: "Trace directory cannot be created/resolved",
      likelyCause: "Trace path is not writable or path resolution is invalid.",
      action: "Repair .z-mos/trace permissions and canonical trace path settings.",
    };
  }

  try {
    await fs.access(traceDir, constants.W_OK);
  } catch {
    return {
      name: "trace-readiness",
      code: "trace-unhealthy",
      status: "blocking",
      message: "Trace directory is not writable",
      likelyCause: "Permission denied for canonical trace directory.",
      action: "Fix write permissions for .z-mos/trace before command execution.",
    };
  }

  const traceValidation = await validateTraceFile({ maxLines: 50 });
  if (traceValidation.status === "corrupted") {
    const severeCorruption =
      traceValidation.validLines === 0 && traceValidation.totalLines > 0;
    return {
      name: "trace-readiness",
      code: "trace-unhealthy",
      status: severeCorruption ? "blocking" : "warning",
      message: severeCorruption
        ? "Trace file is severely corrupted (no valid recent entries)"
        : "Trace file has corruption issues in recent entries",
      likelyCause: "Broken/truncated JSONL trace entries detected.",
      action:
        "Inspect trace file corruption and recover manually; do not auto-fix trace history.",
    };
  }

  if (traceValidation.status === "warning") {
    return {
      name: "trace-readiness",
      code: "trace-unhealthy",
      status: "warning",
      message: "Trace file is missing or partially healthy",
      likelyCause: "No current trace file or non-critical trace validation warning.",
      action: "Proceed, but run doctor trace diagnostics after command execution.",
    };
  }

  return {
    name: "trace-readiness",
    code: "trace-unhealthy",
    status: "healthy",
    message: "Trace path is writable and recent trace validation is healthy",
    likelyCause: "none",
    action: "No action required.",
  };
}

async function checkDocumentGovernance(): Promise<PreflightCheck[]> {
  const index = await buildDocumentIndex();
  const docsRootExists = existsSync(path.join(ROOT_DIR, "docs", "zmos"));

  const structureCheck: PreflightCheck = docsRootExists
    ? {
        name: "document-structure",
        code: "document-structure",
        status: "healthy",
        message: "docs/zmos structure is present",
        likelyCause: "none",
        action: "No action required.",
      }
    : {
        name: "document-structure",
        code: "document-structure",
        status: "warning",
        message: "docs/zmos directory is missing",
        likelyCause: "Document governance root is missing in workspace.",
        action: "Create docs/zmos structure before enabling document governance checks.",
      };

  const schemaBlockingCount =
    index.entries.filter(
      (entry) =>
        entry.issues.some((issue) =>
          issue.code === "required-missing" ||
          issue.code === "document-type-invalid" ||
          issue.code === "status-invalid" ||
          issue.code === "metadata-malformed" ||
          issue.code === "date-invalid",
        ),
    ).length + index.duplicateIds.length;

  const schemaWarningCount = index.entries.filter((entry) =>
    entry.issues.some((issue) => issue.code === "metadata-missing"),
  ).length;

  const schemaCheck: PreflightCheck =
    schemaBlockingCount > 0
      ? {
          name: "document-schema",
          code: "document-schema",
          status: "blocking",
          message: `Document schema has blocking findings (${schemaBlockingCount})`,
          likelyCause: "Invalid schema or duplicate document_id detected.",
          action: "Run zcl doc:check and resolve schema blockers before command execution.",
        }
      : schemaWarningCount > 0
        ? {
            name: "document-schema",
            code: "document-schema",
            status: "warning",
            message: `Document schema has warning findings (${schemaWarningCount})`,
            likelyCause: "Some documents are missing metadata header and treated as orphan.",
            action: "Review doc:check output and migrate orphan documents into governed schema.",
          }
        : {
            name: "document-schema",
            code: "document-schema",
            status: "healthy",
            message: "Document schema checks are healthy",
            likelyCause: "none",
            action: "No action required.",
          };

  const namingBlockingCount = index.entries.filter((entry) =>
    entry.issues.some((issue) => issue.code === "filename-invalid" || issue.code === "filename-metadata-mismatch"),
  ).length;

  const namingCheck: PreflightCheck =
    namingBlockingCount > 0
      ? {
          name: "document-naming",
          code: "document-naming",
          status: "blocking",
          message: `Document naming has blocking findings (${namingBlockingCount})`,
          likelyCause: "Filename convention mismatch with governance naming standard.",
          action: "Rename documents to ZMOS-<TYPE>-<PROJECT>-<PHASE>-<YEAR>-<SEQ>-<TITLE>.md and align metadata.",
        }
      : {
          name: "document-naming",
          code: "document-naming",
          status: "healthy",
          message: "Document naming checks are healthy",
          likelyCause: "none",
          action: "No action required.",
        };

  return [structureCheck, schemaCheck, namingCheck];
}

async function checkBehaviorGovernance(options?: PreflightOptions): Promise<PreflightCheck> {
  const cmd = options?.intendedCommand || "";
  const cmdLower = cmd.toLowerCase();
  const isRisky = cmdLower.includes("--force") || cmdLower.includes("migrate") || cmdLower.includes("tls update");
  
  if (isRisky) {
    const behaviorDir = path.join(process.cwd(), ".z-mos", "behavior", "decisions");
    let hasRecord = false;
    let boundToContext = false;
    
    if (existsSync(behaviorDir)) {
      try {
        const files = await fs.readdir(behaviorDir);
        const jsonFiles = files.filter((f: string) => f.endsWith(".json"));
        if (jsonFiles.length > 0) {
          hasRecord = true;
          jsonFiles.sort();
          const latestFile = jsonFiles[jsonFiles.length - 1];
          if (latestFile) {
            const content = await fs.readFile(path.join(behaviorDir, latestFile), "utf8");
            const record = JSON.parse(content);
            const recordText = `${record.context} ${record.decision} ${record.reason}`.toLowerCase();
            
            if (cmdLower.includes("migrate") && recordText.includes("migrate")) {
              boundToContext = true;
            } else if (cmdLower.includes("tls update") && recordText.includes("tls")) {
              boundToContext = true;
            } else if (cmdLower.includes("--force") && (recordText.includes("force") || recordText.includes("override") || recordText.includes("bypass"))) {
              boundToContext = true;
            } else if (!cmdLower.includes("migrate") && !cmdLower.includes("tls update") && !cmdLower.includes("--force")) {
              // Fallback just in case an unknown risky pattern is added later
              boundToContext = true;
            }
          }
        }
      } catch {
        hasRecord = false;
      }
    }

    if (!hasRecord) {
      return {
        name: "behavior-required",
        code: "behavior-missing",
        status: "warning",
        message: "Risky command intent detected but no BIL records found",
        likelyCause: "Command involves --force or mutating paths without behavior documentation.",
        action: "Create a behavior record using 'zcl behavior record' before execution.",
      };
    } else if (!boundToContext) {
      return {
        name: "behavior-required",
        code: "behavior-missing",
        status: "warning",
        message: "Unrelated BIL record detected (Binding Failed)",
        likelyCause: "The latest behavior record does not mention the current risky command class.",
        action: "Create a relevant behavior record containing keywords matching your intended action.",
      };
    }
  }

  return {
    name: "behavior-required",
    code: "behavior-missing",
    status: "healthy",
    message: "Behavior governance check passed",
    likelyCause: "none",
    action: "No action required.",
  };
}

async function checkRuntimeLocks(): Promise<PreflightCheck> {
  const manifest = await readManifest().catch(() => null);
  const projectName = manifest?.repository.name;
  const results = await ensureValidLockOrCleanup({
    project: projectName,
    scopeProjectOnly: true,
  });
  const scopedResults = results.filter((entry) => !entry.skipped);
  const staleCount = scopedResults.filter((entry) => entry.stale).length;
  const staleCleanupFailed = scopedResults.filter(
    (entry) => entry.stale && !entry.cleanupSucceeded,
  ).length;
  const activeCount = scopedResults.filter((entry) => !entry.stale).length;
  const skippedCount = results.filter((entry) => entry.skipped).length;

  if (scopedResults.length === 0) {
    return {
      name: "runtime-lock-health",
      code: "runtime-lock",
      status: "healthy",
      message:
        skippedCount > 0
          ? `No runtime lock files found for current project${projectName ? ` (${projectName})` : ""}; ignored other-project locks=${skippedCount}`
          : "No runtime lock files found",
      likelyCause: "none",
      action: "No action required.",
    };
  }

  if (staleCleanupFailed > 0) {
    return {
      name: "runtime-lock-health",
      code: "runtime-lock",
      status: "warning",
      message: `Detected stale locks but cleanup failed (${staleCleanupFailed})`,
      likelyCause: "Lock file permissions or external process interference prevented cleanup.",
      action: "Run zcl runtime clear-stale-locks with proper permissions and inspect lock producer.",
    };
  }

  if (staleCount > 0) {
    return {
      name: "runtime-lock-health",
      code: "runtime-lock",
      status: "healthy",
      message: `Runtime lock self-heal completed (auto-cleared stale locks=${staleCount})`,
      likelyCause: "Dead PID or malformed lock file detected in runtime lock registry.",
      action: `No immediate action required. Active locks preserved: ${activeCount}.`,
    };
  }

  return {
    name: "runtime-lock-health",
    code: "runtime-lock",
    status: "healthy",
    message: `Runtime locks are healthy (active=${activeCount})`,
    likelyCause: "none",
    action: "No action required.",
  };
}

function checkProtectedPathDestructiveIntent(
  options?: PreflightOptions,
): PreflightCheck {
  const intended = (options?.intendedCommand || "").trim();
  if (!intended) {
    return {
      name: "protected-path-destructive-intent",
      code: "destructive-intent",
      status: "healthy",
      message: "No intended command provided for destructive intent analysis",
      likelyCause: "none",
      action: "No action required.",
    };
  }

  const commandLower = intended.toLowerCase();
  const destructivePattern = /\brm\s+-r[f]?\b|\brm\s+-f\b|\bdel\s+\/[sqf]/u;
  const touchesProtectedCorePath =
    /\bcore\/zmos-active\/core\b/u.test(commandLower) ||
    /\bcore\b/u.test(commandLower) ||
    /\bcli\b/u.test(commandLower) ||
    /\bcontracts\b/u.test(commandLower);

  if (destructivePattern.test(commandLower) && touchesProtectedCorePath) {
    return {
      name: "protected-path-destructive-intent",
      code: "destructive-intent",
      status: "warning",
      message:
        "[WARNING] Protected core path detected. Use zcl-managed flow only.",
      likelyCause:
        "Potential destructive shell intent detected against protected core path.",
      action: "Recommended: create snapshot before mutation.",
    };
  }

  return {
    name: "protected-path-destructive-intent",
    code: "destructive-intent",
    status: "healthy",
    message: "No protected-path destructive intent detected",
    likelyCause: "none",
    action: "No action required.",
  };
}

async function checkWorktreeDiscipline(): Promise<PreflightCheck> {
  const rt = await verifyWorktree();
  if (rt.status === "WARN") {
     return {
       name: "worktree-discipline",
       code: "unknown",
       status: "warning",
       message: "Worktree has warnings (sync, handoff, or scope drift)",
       likelyCause: "Uncommitted changes out of scope or outdated handoff state.",
       action: "Run 'zcl verify worktree' to review the warnings and follow recommendations before committing.",
     };
  }
  return {
    name: "worktree-discipline",
    code: "unknown",
    status: "healthy",
    message: "Worktree discipline is clean",
    likelyCause: "none",
    action: "No action required.",
  };
}

export async function runPreflightChecks(
  options?: PreflightOptions,
): Promise<PreflightReport> {
  try {
    const checks = [
      checkDistIntegrity(),
      checkNodeRuntime(),
      checkDependencyHealth(),
      checkLoaderRisk(options),
      checkEnvironmentConsistency(),
    ];
    const canonicalCheck = await checkCanonicalStatePresence(options);
    const traceCheck = await checkTraceReadiness();
    const runtimeLockCheck = await checkRuntimeLocks();
    const behaviorCheck = await checkBehaviorGovernance(options);
    const destructiveIntentCheck = checkProtectedPathDestructiveIntent(options);
    const documentChecks = await checkDocumentGovernance();
    const worktreeCheck = await checkWorktreeDiscipline();
    const phase3Checks = await runPhase3FiveStateVerification();
    checks.splice(
      3,
      0,
      canonicalCheck,
      traceCheck,
      runtimeLockCheck,
      behaviorCheck,
      destructiveIntentCheck,
      worktreeCheck,
      ...phase3Checks,
      ...documentChecks,
    );

    return {
      status: aggregateStatus(checks),
      checks,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown preflight failure";
    const checks: PreflightCheck[] = [
      {
        name: "preflight-runtime",
        code: "unknown",
        status: "blocking",
        message: `Preflight failed unexpectedly: ${message}`,
        likelyCause: "Unexpected preflight runtime error.",
        action: "Review startup environment and preflight module implementation.",
      },
    ];

    return {
      status: "blocking",
      checks,
    };
  }
}
