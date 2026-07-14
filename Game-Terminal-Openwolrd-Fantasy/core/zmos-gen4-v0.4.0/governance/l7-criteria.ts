import { promises as fs } from "node:fs";
import * as path from "node:path";

import { readManifest } from "../core/manifest.js";
import { loadNodeIdentity } from "../core/node.js";
import { getWorkflowRegistry } from "../core/workflow-registry.js";
import { evaluateReadiness } from "./readiness.js";
import {
  getWorkflowPolicyPath,
  loadWorkflowPolicy,
  validateDeniedWorkflowActions,
} from "./workflow-policy.js";
import { getTraceFilePath } from "../trace/writer.js";

export type L7CriterionKey =
  | "workflowGovernanceActive"
  | "workflowVisibilityActive"
  | "deniedPathValidationActive"
  | "nodeAwareOrchestrationActive"
  | "appendOnlyTraceWorkflowNodeEvidenceActive"
  | "governanceAwareDiagnosticsActive"
  | "boundedAiInvocationSemanticsActive";

export type L7CriterionResult = {
  key: L7CriterionKey;
  label: string;
  satisfied: boolean;
  detail: string;
};

export type L7CriteriaEvaluation = {
  fullL7Achieved: boolean;
  criteria: L7CriterionResult[];
  missingCriteria: string[];
};

const AI_CLI_OPERATIONAL_STATES = new Set([
  "operational-advisory",
  "provider-agnostic-governance",
]);

async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function hasWorkflowNodeEvidence(tracePath: string): Promise<boolean> {
  try {
    const rawTrace = await fs.readFile(tracePath, "utf8");
    const lines = rawTrace
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(-10);

    return lines.some((line) => {
      try {
        const parsed = JSON.parse(line) as Record<string, unknown>;
        const details =
          typeof parsed.details === "object" && parsed.details !== null
            ? (parsed.details as Record<string, unknown>)
            : null;

        return (
          typeof parsed.node_id === "string" &&
          typeof parsed.node_role === "string" &&
          details !== null &&
          typeof details.workflowName === "string"
        );
      } catch {
        return false;
      }
    });
  } catch {
    return false;
  }
}

export async function evaluateFullL7Criteria(): Promise<L7CriteriaEvaluation> {
  const rootDir = process.cwd();
  const [manifest, node, governance, workflowPolicy, workflowRegistry, tracePath] =
    await Promise.all([
      readManifest(),
      loadNodeIdentity(),
      evaluateReadiness(),
      loadWorkflowPolicy(),
      getWorkflowRegistry(),
      getTraceFilePath(),
    ]);

  let deniedPathValidationActive = true;
  try {
    await validateDeniedWorkflowActions();
  } catch {
    deniedPathValidationActive = false;
  }

  const [
    workflowPolicyPathExists,
    workflowCommandExists,
    doctorCommandExists,
    statusCommandExists,
    tracePathExists,
    workflowNodeEvidenceActive,
    aiTestCommandExists,
    aiRunCommandExists,
    governedRunExists,
  ] = await Promise.all([
    pathExists(getWorkflowPolicyPath()),
    pathExists(path.join(rootDir, "cli", "commands", "workflow.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "doctor.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "status.ts")),
    pathExists(tracePath),
    hasWorkflowNodeEvidence(tracePath),
    pathExists(path.join(rootDir, "cli", "commands", "ai", "ai-test.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "ai", "ai-run.ts")),
    pathExists(path.join(rootDir, "cli", "commands", "ai", "_governed-run.ts")),
  ]);

  const criteria: L7CriterionResult[] = [
    {
      key: "workflowGovernanceActive",
      label: "workflow governance active",
      satisfied:
        workflowPolicyPathExists &&
        workflowPolicy.workflows.length >= 2 &&
        workflowPolicy.workflows.every(
          (entry) => entry.mutationAllowed === false && entry.delegationAllowed === false,
        ),
      detail:
        workflowPolicyPathExists && workflowPolicy.workflows.length >= 2
          ? "workflow policy is present and governs current bounded workflows"
          : "workflow policy is missing or does not cover the current bounded workflow set",
    },
    {
      key: "workflowVisibilityActive",
      label: "workflow visibility active",
      satisfied: workflowRegistry.length >= 2,
      detail:
        workflowRegistry.length >= 2
          ? `workflow registry exposes ${workflowRegistry.length} governed workflows`
          : "governed workflow registry is not sufficiently visible",
    },
    {
      key: "deniedPathValidationActive",
      label: "denied-path validation active",
      satisfied: deniedPathValidationActive,
      detail: deniedPathValidationActive
        ? "mutation and delegation remain explicitly disallowed"
        : "denied actions could not be validated from current runtime evidence",
    },
    {
      key: "nodeAwareOrchestrationActive",
      label: "node-aware orchestration active",
      satisfied:
        node.node_id.trim().length > 0 &&
        node.node_role.trim().length > 0 &&
        workflowCommandExists,
      detail:
        node.node_id.trim().length > 0 &&
        node.node_role.trim().length > 0 &&
        workflowCommandExists
          ? `workflow runtime is node-aware through ${node.node_id}`
          : "node-aware workflow execution is not fully evidenced",
    },
    {
      key: "appendOnlyTraceWorkflowNodeEvidenceActive",
      label: "append-only trace with workflow and node evidence active",
      satisfied: tracePathExists && workflowNodeEvidenceActive,
      detail:
        tracePathExists && workflowNodeEvidenceActive
          ? "recent trace records include workflow and node evidence"
          : "recent trace records do not fully show workflow and node evidence",
    },
    {
      key: "governanceAwareDiagnosticsActive",
      label: "governance-aware diagnostics active",
      satisfied:
        governance.level === "governance-runtime-v1" &&
        doctorCommandExists &&
        statusCommandExists,
      detail:
        governance.level === "governance-runtime-v1" &&
        doctorCommandExists &&
        statusCommandExists
          ? "status and doctor operate with governance-aware runtime evidence"
          : "governance-aware diagnostics are incomplete from current evidence",
    },
    {
      key: "boundedAiInvocationSemanticsActive",
      label: "bounded AI invocation semantics active",
      satisfied:
        AI_CLI_OPERATIONAL_STATES.has(manifest.status.aiCli) &&
        workflowPolicy.workflows.some(
          (entry) => entry.workflowName === "runtime-check" && !entry.advisoryAiAllowed,
        ) &&
        workflowPolicy.workflows.some(
          (entry) => entry.workflowName === "advisory-check" && entry.advisoryAiAllowed,
        ) &&
        aiTestCommandExists &&
        aiRunCommandExists &&
        governedRunExists &&
        workflowPolicy.workflows.some((entry) => entry.workflowName === "ai-test") &&
        workflowPolicy.workflows.some((entry) => entry.workflowName === "ai-run"),
      detail:
        AI_CLI_OPERATIONAL_STATES.has(manifest.status.aiCli) &&
        aiTestCommandExists &&
        aiRunCommandExists &&
        governedRunExists &&
        workflowPolicy.workflows.some((entry) => entry.workflowName === "ai-test") &&
        workflowPolicy.workflows.some((entry) => entry.workflowName === "ai-run")
          ? "AI invocation bounded by workflow policy (ai-test, ai-run) and governed execution gate (_governed-run)"
          : "AI invocation semantics are not sufficiently bounded: missing workflow policy entries for ai-test/ai-run or governed execution gate",
    },
  ];

  const missingCriteria = criteria
    .filter((criterion) => !criterion.satisfied)
    .map((criterion) => criterion.label);

  return {
    fullL7Achieved: missingCriteria.length === 0,
    criteria,
    missingCriteria,
  };
}
