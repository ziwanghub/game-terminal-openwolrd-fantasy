import { promises as fs } from "node:fs";
import * as path from "node:path";

import { getManifestPath, readManifest } from "../../core/manifest.js";
import { evaluateMutationGuard } from "../../core/mutation-guard.js";
import { getNodePath, loadNodeIdentity } from "../../core/node.js";
import { renderCommandExecutionResult } from "../../core/execution-contract.js";
import { evaluateCanonicalStateIntegrity } from "../../core/state-integrity.js";
import { getWorkflowPolicyPath, loadWorkflowPolicy } from "../../governance/workflow-policy.js";
import { appendTraceRecord, getTraceFilePath } from "../../trace/writer.js";

const ROOT_DIR = process.cwd();
const ZMOS_DIR = path.join(ROOT_DIR, ".z-mos");
const STATE_DIR = path.join(ZMOS_DIR, "state");
const TRACE_DIR = path.join(ZMOS_DIR, "trace");

const MANIFEST_SEED = {
  repository: {
    name: "zmos-core",
    framework: "Z-MOS",
    version: "1.0.2",
  },
  workspace: {
    root: ".",
    stateDir: ".z-mos/state",
    traceDir: ".z-mos/trace",
  },
  runtime: {
    platform: "node",
    moduleSystem: "esm",
    entryCommand: "zcl",
  },
  status: {
    stage: "manifest-bootstrap-v1",
    aiCli: "operational-advisory",
  },
  lifecycle: {
    status: "active",
    updatedAt: "bootstrap",
    reason: "default bootstrap lifecycle",
  },
  scope: {
    mutation: {
      mode: "strict",
      allowedPaths: [".", "tls/templates", "tls/registry", ".z-mos"],
      protectedPaths: [
        ".z-mos",
        "bin",
        "cli",
        "contracts",
        "core",
        "governance",
        "trace",
        "docs",
        "tls/modules",
        "tls/schemas",
      ],
    },
  },
} as const;


const NODE_SEED = {
  node_id: "pc-ai-node",
  node_role: "execution-node",
  runtime: "nodejs-local",
  capabilities: ["cli-execution", "diagnostics", "ai-advisory"],
} as const;

const WORKFLOW_POLICY_SEED = {
  workflows: [
    {
      workflowName: "runtime-check",
      advisoryAiAllowed: false,
      mutationAllowed: false,
      delegationAllowed: false,
      allowedSteps: [
        "inspect runtime state",
        "read status evidence",
        "read doctor diagnostics",
        "advisory AI invocation",
      ],
    },
    {
      workflowName: "advisory-check",
      advisoryAiAllowed: true,
      mutationAllowed: false,
      delegationAllowed: false,
      allowedSteps: [
        "inspect runtime state",
        "read status evidence",
        "read doctor diagnostics",
        "invoke advisory AI",
      ],
    },
  ],
} as const;

type InitOutcome = "already initialized" | "partially initialized" | "bootstrap completed";

async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function ensureDir(
  targetPath: string,
  created: string[],
  skipped: string[],
): Promise<void> {
  if (await pathExists(targetPath)) {
    skipped.push(`${path.relative(ROOT_DIR, targetPath)}/`);
    return;
  }

  await fs.mkdir(targetPath, { recursive: true });
  created.push(`${path.relative(ROOT_DIR, targetPath)}/`);
}

async function ensureSeedFile(
  targetPath: string,
  seed: unknown,
  created: string[],
  skipped: string[],
): Promise<void> {
  if (await pathExists(targetPath)) {
    skipped.push(path.relative(ROOT_DIR, targetPath));
    return;
  }

  await fs.writeFile(`${targetPath}`, `${JSON.stringify(seed, null, 2)}\n`, "utf8");
  created.push(path.relative(ROOT_DIR, targetPath));
}

function resolveOutcome(created: string[], skipped: string[]): InitOutcome {
  if (created.length === 0) {
    return "already initialized";
  }

  if (skipped.length > 0) {
    return "partially initialized";
  }

  return "bootstrap completed";
}

function formatIntegrityBlockMessage(
  integrity: Awaited<ReturnType<typeof evaluateCanonicalStateIntegrity>>,
): string {
  const firstFinding = integrity.findings[0];
  const fileList = firstFinding?.affectedFiles.join(", ") || "not enough evidence";
  return [
    `Canonical state is not safe to reuse (${integrity.recoveryClass}).`,
    `Reason: ${firstFinding?.reason || "not enough evidence"}`,
    `Affected files: ${fileList}`,
    `Action: ${firstFinding?.action || "Repair canonical state before rerunning init."}`,
    "zcl init will not overwrite canonical state automatically.",
  ].join(" ");
}

export async function runInitCommand(): Promise<void> {
  const created: string[] = [];
  const skipped: string[] = [];
  const manifestPath = getManifestPath();
  const nodePath = getNodePath();
  const workflowPolicyPath = getWorkflowPolicyPath();
  const integrity = await evaluateCanonicalStateIntegrity();
  const mutationGuard = await evaluateMutationGuard({
    command: "zcl init",
    targetPaths: [".z-mos"],
    allowMissingManifest: true,
    allowProtectedPrefixes: [".z-mos"],
  });

  if (!mutationGuard.allowed) {
    console.log(
      renderCommandExecutionResult({
        command: "init",
        status: "blocked",
        resultClass: "blocked-policy",
        reason: mutationGuard.reason,
        warningReason:
          mutationGuard.warnings.length > 0 ? mutationGuard.warnings.join(" | ") : undefined,
        traceExpectation: "required-if-business-logic",
        traceResult: "not-emitted-blocked-before-logic",
        nextAction: "Set lifecycle.status=active and align scope.mutation policy before retrying zcl init.",
      }),
    );
    process.exitCode = 1;
    return;
  }

  if (integrity.status === "blocking" && integrity.recoveryClass !== "bootstrap-required") {
    const firstFinding = integrity.findings[0];
    console.log(
      renderCommandExecutionResult({
        command: "init",
        status: "blocked",
        resultClass: "blocked-canonical-integrity",
        reason: firstFinding?.reason || "Canonical state is not safe to reuse.",
        traceExpectation: "required-if-business-logic",
        traceResult: "not-emitted-blocked-before-logic",
        nextAction:
          firstFinding?.action || formatIntegrityBlockMessage(integrity),
      }),
    );
    process.exitCode = 1;
    return;
  }

  if (await pathExists(manifestPath)) {
    try {
      await readManifest();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown manifest error";
      throw new Error(
        `Existing manifest is not safe to reuse: ${message}. zcl init will not overwrite canonical state.`,
      );
    }
  }

  if (await pathExists(nodePath)) {
    try {
      await loadNodeIdentity();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown node identity error";
      throw new Error(
        `Existing node identity is not safe to reuse: ${message}. zcl init will not overwrite canonical state.`,
      );
    }
  }

  if (await pathExists(workflowPolicyPath)) {
    try {
      await loadWorkflowPolicy();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown workflow policy error";
      throw new Error(
        `Existing workflow policy is not safe to reuse: ${message}. zcl init will not overwrite canonical state.`,
      );
    }
  }

  await ensureDir(ZMOS_DIR, created, skipped);
  await ensureDir(STATE_DIR, created, skipped);
  await ensureDir(TRACE_DIR, created, skipped);
  await ensureSeedFile(manifestPath, MANIFEST_SEED, created, skipped);
  await ensureSeedFile(nodePath, NODE_SEED, created, skipped);
  await ensureSeedFile(workflowPolicyPath, WORKFLOW_POLICY_SEED, created, skipped);

  const entrypointPath = path.join(ZMOS_DIR, "entrypoint.json");
  const readinessPolicyPath = path.join(ZMOS_DIR, "readiness-policy.json");
  const projectStatePath = path.join(STATE_DIR, "project-state.json");
  const runtimeStatePath = path.join(STATE_DIR, "runtime-state.json");
  const intentCardPath = path.join(ZMOS_DIR, "intent.card.json");

  // Repair legacy session path in entrypoint.json if found during init
  if (await pathExists(entrypointPath)) {
    try {
      const raw = await fs.readFile(entrypointPath, "utf8");
      const parsed = JSON.parse(raw);
      if (
        parsed &&
        parsed.runtime_state_paths &&
        parsed.runtime_state_paths.session === ".z-mos/state/session.json"
      ) {
        parsed.runtime_state_paths.session = ".z-mos/state/runtime-state.json";
        await fs.writeFile(entrypointPath, JSON.stringify(parsed, null, 2), "utf8");
        console.log("Repaired entrypoint.json: updated legacy session path to runtime-state.json");
      }
    } catch {
      // ignore
    }
  }

  const ENTRYPOINT_SEED = {
    schema_version: "1.3.2",
    generated_at: new Date().toISOString(),
    standard_path: "docs/standards/ZMOS-COMMUNICATION-STANDARD.md",
    runtime_state_paths: {
      manifest: ".z-mos/zmos-manifest.json",
      session: ".z-mos/state/runtime-state.json",
      project_state: ".z-mos/state/project-state.json"
    },
    policy_paths: {
      workflow_policy: ".z-mos/workflow-policy.json",
      readiness_policy: ".z-mos/readiness-policy.json"
    },
    latest_artifacts: {
      latest_handoff: ".z-mos/intent.card.json",
      latest_report: ".z-mos/reports/latest.json",
      latest_advisory_bundle: ".z-mos/advisory/latest.json"
    },
    trace_path: ".z-mos/trace/runtime-trace.jsonl",
    rehydration_order: [
      "runtime_state_paths.manifest",
      "runtime_state_paths.project_state",
      "latest_artifacts.latest_handoff"
    ]
  };

  const READINESS_POLICY_SEED = {
    version: "1.0.0",
    defaultProfile: "standard",
    profiles: {
      standard: {
        description: "Controlled rollout mode: pass with explicitly budgeted warnings.",
        allowlistedPreflightWarnings: [
          "runtime-lock-health",
          "document-schema"
        ],
        allowDoctorWarning: true,
        allowStartWarning: true
      },
      strict: {
        description: "Hard production mode: zero-warning only.",
        allowlistedPreflightWarnings: [
          "worktree-discipline",
          "phase3-5state-code",
          "phase3-5state-runtime",
          "phase3-5state-environment",
          "phase3-5state-data-config",
          "phase3-5state-assets-schema",
          "document-structure"
        ],
        allowDoctorWarning: true,
        allowStartWarning: true
      }
    }
  };

  const RUNTIME_STATE_SEED = {
    workspace: path.basename(ROOT_DIR),
    framework: "Z-MOS",
    sessionState: "bootstrap",
    activeCommand: null,
    lastReport: null
  };

  const PROJECT_STATE_SEED = {
    schema_version: "1.3.2",
    current_phase: "unknown",
    active_gate: "standard",
    next_safe_action: "initiate system",
    current_working_blocker: null,
    last_updated: new Date().toISOString(),
    updated_by_task: "system",
    staleness_threshold_hours: 24,
    auto_stale_at: new Date(Date.now() + 24*60*60*1000).toISOString()
  };

  const INTENT_CARD_SEED = {
    schema_version: "3.0.0-agent",
    intent: {
      objective: "Define task objective",
      strategy: "Document chosen implementation path",
      risk_acknowledgement: "None"
    },
    system: {
      scope_files: [],
      required_tests: ["node ./scripts/verify/verify.mjs core"],
      stop_conditions: ["schema validation fail", "critical drift detected"],
      rollback_plan: "Revert to previous known-good commit and re-run verify:core",
      truth_snapshot_ref: ".z-mos/truth.contract.json",
      allowed_hosts: ["localhost"],
      allowed_databases: ["zmos_local_dev"]
    },
    agent: {
      allowed_tools: ["functions.exec_command", "functions.apply_patch"],
      allowed_actions: ["read", "write", "test", "command"],
      max_steps: 50,
      termination_conditions: ["attempted out-of-scope mutation"],
      enforcement: "hard-block"
    }
  };

  await ensureSeedFile(entrypointPath, ENTRYPOINT_SEED, created, skipped);
  await ensureSeedFile(readinessPolicyPath, READINESS_POLICY_SEED, created, skipped);
  await ensureSeedFile(projectStatePath, PROJECT_STATE_SEED, created, skipped);
  await ensureSeedFile(runtimeStatePath, RUNTIME_STATE_SEED, created, skipped);
  await ensureSeedFile(intentCardPath, INTENT_CARD_SEED, created, skipped);

  const outcome = resolveOutcome(created, skipped);
  const tracePath = await getTraceFilePath();

  await appendTraceRecord({
    command: "zcl init",
    status: "success",
    actor: "system",
    details: {
      outcome,
      created,
      skipped,
      tracePath,
    },
  });

  const lines = [
    "Z-MOS Init Report",
    "",
    `Result: ${outcome}`,
    "",
    "Created",
    ...(created.length > 0 ? created.map((entry) => `- ${entry}`) : ["- (none)"]),
    "",
    "Skipped",
    ...(skipped.length > 0 ? skipped.map((entry) => `- ${entry}`) : ["- (none)"]),
    "",
    renderCommandExecutionResult({
      command: "init",
      status: "success",
      resultClass: "success",
      traceExpectation: "required-if-business-logic",
      traceResult: "emitted",
    }),
  ];

  console.log(lines.join("\n"));
}
