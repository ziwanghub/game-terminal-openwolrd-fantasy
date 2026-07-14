import { promises as fs } from "node:fs";
import * as path from "node:path";

import type { ZmosManifest } from "./manifest.js";
import type { ZmosNodeIdentity } from "./node.js";
import type { WorkflowPolicyFileContract } from "../contracts/workflow-policy.js";
import { getManifestPath } from "./manifest.js";
import { getNodePath } from "./node.js";
import { getWorkflowPolicyPath } from "../governance/workflow-policy.js";
import { SUPPORTED_WORKFLOWS } from "./workflow.js";
import { validateTruthContractPayload } from "./truth-store.js";

export type IntegrityStatus = "healthy" | "warning" | "blocking";

export type RecoveryClass =
  | "bootstrap-required"
  | "repair-required"
  | "unsafe-reuse-blocked"
  | "policy-rebuild-required"
  | "state-consistency-warning";

export type CanonicalIntegrityCode =
  | "manifest-missing"
  | "manifest-malformed"
  | "manifest-invalid"
  | "truth-missing"
  | "truth-malformed"
  | "truth-invalid"
  | "node-missing"
  | "node-malformed"
  | "node-invalid"
  | "workflow-policy-missing"
  | "workflow-policy-malformed"
  | "workflow-policy-invalid"
  | "workflow-policy-unsupported"
  | "workflow-policy-denied-action-invalid"
  | "invariant-failure"
  | "invariant-warning";

export type CanonicalIntegrityFinding = {
  code: CanonicalIntegrityCode;
  status: IntegrityStatus;
  recoveryClass: RecoveryClass;
  reason: string;
  action: string;
  affectedFiles: string[];
  invariantName?: string;
};

export type CanonicalInvariantResult = {
  name: string;
  status: IntegrityStatus;
  detail: string;
};

export type CanonicalIntegrityResult = {
  status: IntegrityStatus;
  safeReuse: boolean;
  recoveryClass: RecoveryClass;
  findings: CanonicalIntegrityFinding[];
  invariants: CanonicalInvariantResult[];
  files: {
    zmosDir: string;
    manifestPath: string;
    truthPath: string;
    nodePath: string;
    workflowPolicyPath: string;
  };
};

type ParsedFile<T> = {
  exists: boolean;
  valid: boolean;
  value: T | null;
};

const ROOT_DIR = process.cwd();
const ZMOS_DIR = path.join(ROOT_DIR, ".z-mos");

const MANIFEST_PATH = getManifestPath();
const TRUTH_PATH = path.join(ROOT_DIR, ".z-mos", "truth.contract.json");
const NODE_PATH = getNodePath();
const WORKFLOW_POLICY_PATH = getWorkflowPolicyPath();

function toRelative(absolutePath: string): string {
  return path.relative(ROOT_DIR, absolutePath);
}

function buildFinding(
  code: CanonicalIntegrityCode,
  status: IntegrityStatus,
  recoveryClass: RecoveryClass,
  reason: string,
  action: string,
  affectedFiles: string[],
  invariantName?: string,
): CanonicalIntegrityFinding {
  return {
    code,
    status,
    recoveryClass,
    reason,
    action,
    affectedFiles,
    invariantName,
  };
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isNullableString(value: unknown): value is string | null {
  return typeof value === "string" || value === null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === "string");
}

async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function parseJsonFile<T>(
  targetPath: string,
): Promise<ParsedFile<T> & { raw: unknown | null }> {
  if (!(await pathExists(targetPath))) {
    return {
      exists: false,
      valid: false,
      value: null,
      raw: null,
    };
  }

  let raw: unknown;
  try {
    const content = await fs.readFile(targetPath, "utf8");
    raw = JSON.parse(content) as unknown;
  } catch {
    return {
      exists: true,
      valid: false,
      value: null,
      raw: null,
    };
  }

  return {
    exists: true,
    valid: true,
    value: raw as T,
    raw,
  };
}

function validateManifestShape(value: unknown): value is ZmosManifest {
  if (!isObject(value)) {
    return false;
  }

  const { repository, workspace, runtime, status } = value;
  if (!isObject(repository) || !isObject(workspace) || !isObject(runtime) || !isObject(status)) {
    return false;
  }

  return (
    isNonEmptyString(repository.name) &&
    isNonEmptyString(repository.framework) &&
    isNonEmptyString(repository.version) &&
    isNonEmptyString(workspace.root) &&
    isNonEmptyString(workspace.stateDir) &&
    isNonEmptyString(workspace.traceDir) &&
    isNonEmptyString(runtime.platform) &&
    isNonEmptyString(runtime.moduleSystem) &&
    isNonEmptyString(runtime.entryCommand) &&
    isNonEmptyString(status.stage) &&
    isNonEmptyString(status.aiCli)
  );
}


function validateNodeShape(value: unknown): value is ZmosNodeIdentity {
  if (!isObject(value)) {
    return false;
  }

  return (
    isNonEmptyString(value.node_id) &&
    isNonEmptyString(value.node_role) &&
    isNonEmptyString(value.runtime) &&
    isStringArray(value.capabilities)
  );
}

function validateWorkflowPolicyShape(value: unknown): value is WorkflowPolicyFileContract {
  if (!isObject(value) || !Array.isArray(value.workflows)) {
    return false;
  }

  return value.workflows.every((entry) => {
    if (!isObject(entry)) {
      return false;
    }

    return (
      isNonEmptyString(entry.workflowName) &&
      typeof entry.advisoryAiAllowed === "boolean" &&
      typeof entry.mutationAllowed === "boolean" &&
      typeof entry.delegationAllowed === "boolean" &&
      isStringArray(entry.allowedSteps)
    );
  });
}

function resolveOverallStatus(findings: CanonicalIntegrityFinding[]): IntegrityStatus {
  if (findings.some((finding) => finding.status === "blocking")) {
    return "blocking";
  }

  if (findings.some((finding) => finding.status === "warning")) {
    return "warning";
  }

  return "healthy";
}

function resolveRecoveryClass(
  status: IntegrityStatus,
  findings: CanonicalIntegrityFinding[],
): RecoveryClass {
  if (status === "healthy") {
    return "state-consistency-warning";
  }

  const classes = new Set(findings.map((finding) => finding.recoveryClass));
  if (classes.has("unsafe-reuse-blocked")) {
    return "unsafe-reuse-blocked";
  }
  if (classes.has("policy-rebuild-required")) {
    return "policy-rebuild-required";
  }
  if (classes.has("repair-required")) {
    return "repair-required";
  }
  if (classes.has("bootstrap-required")) {
    return "bootstrap-required";
  }

  return "state-consistency-warning";
}

export async function evaluateCanonicalStateIntegrity(): Promise<CanonicalIntegrityResult> {
  const findings: CanonicalIntegrityFinding[] = [];
  const invariants: CanonicalInvariantResult[] = [];

  const [zmosDirExists, manifestRaw, truthRaw, nodeRaw, policyRaw] = await Promise.all([
    pathExists(ZMOS_DIR),
    parseJsonFile<ZmosManifest>(MANIFEST_PATH),
    parseJsonFile<unknown>(TRUTH_PATH),
    parseJsonFile<ZmosNodeIdentity>(NODE_PATH),
    parseJsonFile<WorkflowPolicyFileContract>(WORKFLOW_POLICY_PATH),
  ]);

  const canonicalFiles = [MANIFEST_PATH, TRUTH_PATH, NODE_PATH, WORKFLOW_POLICY_PATH];
  const existingCanonicalFileCount = [manifestRaw.exists, truthRaw.exists, nodeRaw.exists, policyRaw.exists]
    .filter(Boolean)
    .length;

  const freshBootstrapState = !zmosDirExists && existingCanonicalFileCount === 0;

  if (!manifestRaw.exists) {
    findings.push(
      buildFinding(
        "manifest-missing",
        "blocking",
        freshBootstrapState ? "bootstrap-required" : "repair-required",
        "Canonical manifest is missing.",
        freshBootstrapState
          ? "Run zcl init to bootstrap canonical state."
          : "Restore .z-mos/zmos-manifest.json from a known-good source.",
        [toRelative(MANIFEST_PATH)],
      ),
    );
  } else if (!manifestRaw.valid) {
    findings.push(
      buildFinding(
        "manifest-malformed",
        "blocking",
        "unsafe-reuse-blocked",
        "Canonical manifest contains malformed JSON and cannot be trusted.",
        "Restore a valid manifest JSON or remove invalid state intentionally before bootstrap.",
        [toRelative(MANIFEST_PATH)],
      ),
    );
  } else if (!validateManifestShape(manifestRaw.raw)) {
    findings.push(
      buildFinding(
        "manifest-invalid",
        "blocking",
        "unsafe-reuse-blocked",
        "Canonical manifest structure is invalid.",
        "Repair required keys in manifest before runtime reuse.",
        [toRelative(MANIFEST_PATH)],
      ),
    );
  }

  let truthValid = false;
  if (!truthRaw.exists) {
    findings.push(
      buildFinding(
        "truth-missing",
        "blocking",
        freshBootstrapState ? "bootstrap-required" : "repair-required",
        "Truth contract file is missing.",
        freshBootstrapState
          ? "Run zcl truth build to bootstrap truth-first canonical state."
          : "Restore .z-mos/truth.contract.json from a known-good source or rebuild via zcl truth build.",
        [toRelative(TRUTH_PATH)],
      ),
    );
  } else if (!truthRaw.valid) {
    findings.push(
      buildFinding(
        "truth-malformed",
        "blocking",
        "unsafe-reuse-blocked",
        "Truth contract contains malformed JSON.",
        "Restore a valid truth contract JSON or regenerate via zcl truth build.",
        [toRelative(TRUTH_PATH)],
      ),
    );
  } else {
    try {
      await validateTruthContractPayload(truthRaw.raw);
      truthValid = true;
    } catch {
      findings.push(
        buildFinding(
          "truth-invalid",
          "blocking",
          "unsafe-reuse-blocked",
          "Truth contract schema validation failed.",
          "Repair or regenerate .z-mos/truth.contract.json via zcl truth build before runtime reuse.",
          [toRelative(TRUTH_PATH)],
        ),
      );
    }
  }


  if (!nodeRaw.exists) {
    findings.push(
      buildFinding(
        "node-missing",
        "blocking",
        freshBootstrapState ? "bootstrap-required" : "repair-required",
        "Canonical node identity file is missing.",
        freshBootstrapState
          ? "Run zcl init to bootstrap canonical node identity."
          : "Restore .z-mos/node.json from a known-good source.",
        [toRelative(NODE_PATH)],
      ),
    );
  } else if (!nodeRaw.valid) {
    findings.push(
      buildFinding(
        "node-malformed",
        "blocking",
        "unsafe-reuse-blocked",
        "Canonical node identity contains malformed JSON.",
        "Restore a valid node.json or remove invalid state intentionally before bootstrap.",
        [toRelative(NODE_PATH)],
      ),
    );
  } else if (!validateNodeShape(nodeRaw.raw)) {
    findings.push(
      buildFinding(
        "node-invalid",
        "blocking",
        "unsafe-reuse-blocked",
        "Canonical node identity structure is invalid.",
        "Repair node_id/node_role/runtime/capabilities before runtime reuse.",
        [toRelative(NODE_PATH)],
      ),
    );
  }

  if (!policyRaw.exists) {
    findings.push(
      buildFinding(
        "workflow-policy-missing",
        "blocking",
        freshBootstrapState ? "bootstrap-required" : "policy-rebuild-required",
        "Workflow policy file is missing.",
        freshBootstrapState
          ? "Run zcl init to bootstrap workflow policy."
          : "Restore .z-mos/workflow-policy.json from a known-good source.",
        [toRelative(WORKFLOW_POLICY_PATH)],
      ),
    );
  } else if (!policyRaw.valid) {
    findings.push(
      buildFinding(
        "workflow-policy-malformed",
        "blocking",
        "policy-rebuild-required",
        "Workflow policy contains malformed JSON.",
        "Restore a valid workflow policy JSON before runtime reuse.",
        [toRelative(WORKFLOW_POLICY_PATH)],
      ),
    );
  } else if (!validateWorkflowPolicyShape(policyRaw.raw)) {
    findings.push(
      buildFinding(
        "workflow-policy-invalid",
        "blocking",
        "policy-rebuild-required",
        "Workflow policy structure is invalid.",
        "Repair policy workflows structure before runtime reuse.",
        [toRelative(WORKFLOW_POLICY_PATH)],
      ),
    );
  } else {
    const workflowPolicy = policyRaw.raw as WorkflowPolicyFileContract;
    const unsupported = workflowPolicy.workflows
      .map((entry) => entry.workflowName)
      .filter((workflowName) => !SUPPORTED_WORKFLOWS.includes(workflowName));
    if (unsupported.length > 0) {
      findings.push(
        buildFinding(
          "workflow-policy-unsupported",
          "blocking",
          "policy-rebuild-required",
          `Workflow policy contains unsupported workflow names: ${unsupported.join(", ")}.`,
          "Remove unsupported workflow names or align with supported workflow registry.",
          [toRelative(WORKFLOW_POLICY_PATH)],
        ),
      );
    }

    const deniedActionInvalid = workflowPolicy.workflows.filter(
      (entry) => entry.mutationAllowed || entry.delegationAllowed,
    );
    if (deniedActionInvalid.length > 0) {
      findings.push(
        buildFinding(
          "workflow-policy-denied-action-invalid",
          "blocking",
          "policy-rebuild-required",
          "Workflow policy enables disallowed actions (mutation/delegation).",
          "Set mutationAllowed and delegationAllowed to false for all workflows.",
          [toRelative(WORKFLOW_POLICY_PATH)],
        ),
      );
    }
  }

  const manifest = validateManifestShape(manifestRaw.raw) ? (manifestRaw.raw as ZmosManifest) : null;
  const node = validateNodeShape(nodeRaw.raw) ? (nodeRaw.raw as ZmosNodeIdentity) : null;
  const policy = validateWorkflowPolicyShape(policyRaw.raw)
    ? (policyRaw.raw as WorkflowPolicyFileContract)
    : null;

  if (manifest) {
    const expectedStateDir = path.join(ROOT_DIR, ".z-mos", "state");
    const expectedTraceDir = path.join(ROOT_DIR, ".z-mos", "trace");
    const resolvedStateDir = path.resolve(ROOT_DIR, manifest.workspace.stateDir);
    const resolvedTraceDir = path.resolve(ROOT_DIR, manifest.workspace.traceDir);
    const pathsCoherent =
      manifest.workspace.root === "." &&
      resolvedStateDir === expectedStateDir &&
      resolvedTraceDir === expectedTraceDir;

    invariants.push({
      name: "manifest-workspace-layout",
      status: pathsCoherent ? "healthy" : "blocking",
      detail: pathsCoherent
        ? "manifest workspace paths align with canonical .z-mos layout"
        : "manifest workspace paths are inconsistent with canonical .z-mos layout",
    });

    if (!pathsCoherent) {
      findings.push(
        buildFinding(
          "invariant-failure",
          "blocking",
          "unsafe-reuse-blocked",
          "Manifest workspace paths do not match canonical .z-mos layout.",
          "Repair manifest.workspace.{root,stateDir,traceDir} to canonical values.",
          [toRelative(MANIFEST_PATH)],
          "manifest-workspace-layout",
        ),
      );
    }
  }


  if (policy) {
    const coverageComplete = SUPPORTED_WORKFLOWS.every((workflowName) =>
      policy.workflows.some((entry) => entry.workflowName === workflowName),
    );
    invariants.push({
      name: "workflow-policy-coverage",
      status: coverageComplete ? "healthy" : "blocking",
      detail: coverageComplete
        ? "workflow policy covers all supported workflows"
        : "workflow policy does not cover all supported workflows",
    });

    if (!coverageComplete) {
      findings.push(
        buildFinding(
          "invariant-failure",
          "blocking",
          "policy-rebuild-required",
          "Workflow policy is missing one or more supported workflows.",
          `Ensure policy defines: ${SUPPORTED_WORKFLOWS.join(", ")}.`,
          [toRelative(WORKFLOW_POLICY_PATH)],
          "workflow-policy-coverage",
        ),
      );
    }
  }

  if (node) {
    const nodeRuntimeCoherent = node.runtime === "nodejs-local";
    invariants.push({
      name: "node-runtime-coherence",
      status: nodeRuntimeCoherent ? "healthy" : "warning",
      detail: nodeRuntimeCoherent
        ? "node runtime matches current environment assumption"
        : "node runtime differs from current environment assumption",
    });

    if (!nodeRuntimeCoherent) {
      findings.push(
        buildFinding(
          "invariant-warning",
          "warning",
          "state-consistency-warning",
          "Node runtime value is outside current expected runtime profile.",
          "Review node.runtime and align with current operational target if required.",
          [toRelative(NODE_PATH)],
          "node-runtime-coherence",
        ),
      );
    }
  }

  if (manifest) {
    const tracePathCoherent =
      path.resolve(ROOT_DIR, manifest.workspace.traceDir) === path.join(ROOT_DIR, ".z-mos", "trace");
    invariants.push({
      name: "manifest-trace-path",
      status: tracePathCoherent ? "healthy" : "blocking",
      detail: tracePathCoherent
        ? "manifest trace path is coherent with runtime trace structure"
        : "manifest trace path is inconsistent with runtime trace structure",
    });

    if (!tracePathCoherent) {
      findings.push(
        buildFinding(
          "invariant-failure",
          "blocking",
          "unsafe-reuse-blocked",
          "Manifest trace path contradicts canonical runtime trace structure.",
          "Repair manifest.workspace.traceDir to .z-mos/trace.",
          [toRelative(MANIFEST_PATH)],
          "manifest-trace-path",
        ),
      );
    }
  }


  const status = resolveOverallStatus(findings);
  const recoveryClass = resolveRecoveryClass(status, findings);

  return {
    status,
    safeReuse: status !== "blocking",
    recoveryClass,
    findings,
    invariants,
    files: {
      zmosDir: toRelative(ZMOS_DIR),
      manifestPath: toRelative(MANIFEST_PATH),
      truthPath: toRelative(TRUTH_PATH),
      nodePath: toRelative(NODE_PATH),
      workflowPolicyPath: toRelative(WORKFLOW_POLICY_PATH),
    },
  };
}
