import { writeCanonicalTraceRecord } from "../../../trace/writer.js";
import { evaluateCanonicalStateIntegrity } from "../../../core/state-integrity.js";
import { loadWorkflowPolicy } from "../../../governance/workflow-policy.js";
import type { TraceGateStatus } from "../../../contracts/trace.js";
import { promises as fs } from "node:fs";
import * as path from "node:path";
import {
  type TrustTier,
  getRequiredTierForTask,
  tierSatisfies,
} from "../../../contracts/trust-tier.js";
import { resolveAiProvider } from "../../../core/ai-provider.js";

// Hardcoded fallbacks — authoritative source is workflow-policy.json ai-run entry
const FALLBACK_ALLOWED_TASKS = ["system-check", "code-task"];
const FALLBACK_FORBIDDEN_PATTERNS = ["delete", "remove", "rm -rf", "overwrite package.json"];

// Hybrid forbidden pattern rules — these are always enforced regardless of policy config.
// Each rule has a regex and a human-readable label.
// These catch dangerous intent that simple substring matching misses (e.g., "rm" alone is fine,
// "rm -rf" or "rm -r" is not; "delete" as a standalone word is blocked but "deleteHandler" is not).
type HybridForbiddenRule = { pattern: RegExp; label: string };

const HYBRID_FORBIDDEN_RULES: HybridForbiddenRule[] = [
  { pattern: /\brm\s+-[rRfF]{1,4}\b/, label: "rm -rf destructive shell command" },
  { pattern: /\btruncate\s+table\b/i, label: "SQL TRUNCATE TABLE" },
  { pattern: /\bdrop\s+table\b/i, label: "SQL DROP TABLE" },
  { pattern: /\bdrop\s+database\b/i, label: "SQL DROP DATABASE" },
  { pattern: /\bformat\s+[a-z]:\\/i, label: "Windows disk format command" },
  { pattern: /\bsudo\s+rm\b/, label: "sudo rm command" },
  { pattern: /\boverwrite\s+package\.json\b/i, label: "overwrite package.json" },
];

function checkHybridForbiddenRules(text: string, field: string): void {
  const lower = text.toLowerCase();
  for (const rule of HYBRID_FORBIDDEN_RULES) {
    if (rule.pattern.test(lower) || rule.pattern.test(text)) {
      throw new Error(`CONTRACT_FAIL: forbidden pattern "${rule.label}" detected in ${field}`);
    }
  }
}

// Checks a policy-sourced pattern string against a text value.
// Uses word-boundary matching for simple alphabetic patterns to avoid false positives
// (e.g., "remove" does not match "removeHandler" but does match "please remove the file").
function matchesPolicyPattern(text: string, pattern: string): boolean {
  const lower = text.toLowerCase();
  const pat = pattern.toLowerCase();
  // If pattern contains non-word characters (e.g., "rm -rf"), use substring match
  if (/[^a-z]/.test(pat)) {
    return lower.includes(pat);
  }
  // For pure-word patterns, use word-boundary matching
  const wordBoundary = new RegExp(`\\b${pat.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`);
  return wordBoundary.test(lower);
}

export type AiTaskPayload = {
  task: string;
  goal: string;
  input: string;
  constraints: string[];
};

export type AiRunMode = "execute" | "dry-run" | "describe";

async function writeExecutionBundle(
  command: string,
  payload: AiTaskPayload,
  provider: "external-code-agent" | "ollama",
): Promise<string> {
  const outDir = path.join(process.cwd(), ".z-mos", "ai-bundles");
  await fs.mkdir(outDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const outPath = path.join(outDir, `${command.replace(/\s+/g, "-")}-${stamp}.json`);
  const bundle = {
    generatedAt: new Date().toISOString(),
    command,
    provider,
    payload,
    constraints: {
      mode: "governed-read-only",
      noMutation: true,
      noExternalApiDependency: true,
    },
  };
  await fs.writeFile(outPath, JSON.stringify(bundle, null, 2), "utf8");
  return outPath;
}

export function validatePayload(p: AiTaskPayload): void {
  if (typeof p.task !== "string" || p.task.trim() === "")
    throw new Error("VALIDATION_FAIL: task must be a non-empty string");
  if (typeof p.goal !== "string" || p.goal.trim() === "")
    throw new Error("VALIDATION_FAIL: goal must be a non-empty string");
  if (typeof p.input !== "string" || p.input.trim() === "")
    throw new Error("VALIDATION_FAIL: input must be a non-empty string");
  if (
    !Array.isArray(p.constraints) ||
    p.constraints.length === 0 ||
    p.constraints.some((c) => typeof c !== "string" || c.trim() === "")
  )
    throw new Error("VALIDATION_FAIL: constraints must be an array of non-empty strings");
}

export function enforceContract(
  p: AiTaskPayload,
  allowedTasks: string[],
  forbiddenPatterns: string[],
): void {
  if (!allowedTasks.includes(p.task))
    throw new Error(
      `CONTRACT_FAIL: task "${p.task}" is not allowed. Allowed: ${allowedTasks.join(", ")}`,
    );

  // Always-on hybrid rules (regex-based, not configurable)
  checkHybridForbiddenRules(p.goal, "goal");
  checkHybridForbiddenRules(p.input, "input");

  // Policy-sourced patterns (word-boundary aware for pure-word patterns)
  for (const pattern of forbiddenPatterns) {
    if (matchesPolicyPattern(p.goal, pattern))
      throw new Error(`CONTRACT_FAIL: forbidden pattern "${pattern}" found in goal`);
    if (matchesPolicyPattern(p.input, pattern))
      throw new Error(`CONTRACT_FAIL: forbidden pattern "${pattern}" found in input`);
  }
}

// Fallback Trust Tier when policy cannot be loaded — TIER_2 (bounded tasks only, no code mutation)
const FALLBACK_TRUST_TIER: TrustTier = "TIER_2";

async function loadAiRunPolicy(
  workflowName: "ai-run" | "ai-test",
): Promise<{ allowedTasks: string[]; forbiddenPatterns: string[]; trustTier: TrustTier }> {
  try {
    const policy = await loadWorkflowPolicy();
    const entry = policy.workflows.find((w) => w.workflowName === workflowName);
    return {
      allowedTasks: entry?.allowedTasks ?? FALLBACK_ALLOWED_TASKS,
      forbiddenPatterns: entry?.forbiddenPatterns ?? FALLBACK_FORBIDDEN_PATTERNS,
      trustTier: (entry?.trustTier as TrustTier | undefined) ?? FALLBACK_TRUST_TIER,
    };
  } catch (err) {
    const reason = err instanceof Error ? err.message : "unknown";
    // Never silent — emit degraded-governance trace before falling back
    try {
      await writeCanonicalTraceRecord({
        command: `zcl ai ${workflowName}`,
        actor: "system",
        execution_status: "warning",
        result_class: "warning-execution",
        preflight_status: "not-evaluated",
        canonical_status: "warning",
        policy_status: "not-applicable",
        trace_expectation: "required-if-business-logic",
        trace_result: "emitted",
        details: {
          reason: `POLICY_LOAD_FAILED: ${reason}`,
          fallback: "hardcoded-defaults",
          workflowName,
        },
      });
    } catch {
      // Trace write failure must not suppress the governance warning
      console.error(`GOVERNANCE_WARN: policy load failed AND trace write failed. Reason: ${reason}`);
    }
    console.warn(`GOVERNANCE_WARN: workflow-policy.json could not be loaded — using hardcoded fallback. Reason: ${reason}`);
    return {
      allowedTasks: FALLBACK_ALLOWED_TASKS,
      forbiddenPatterns: FALLBACK_FORBIDDEN_PATTERNS,
      trustTier: FALLBACK_TRUST_TIER,
    };
  }
}


export async function runGovernedAiTask(
  command: string,
  payload: AiTaskPayload,
  payloadPath?: string,
  mode: AiRunMode = "execute",
): Promise<void> {
  // Determine workflow name from command for policy lookup
  const workflowName: "ai-run" | "ai-test" = command === "zcl ai test" ? "ai-test" : "ai-run";
  const { allowedTasks, forbiddenPatterns, trustTier } = await loadAiRunPolicy(workflowName);
  const provider = resolveAiProvider();

  // Trust Tier enforcement: check that the requested task meets the workflow's tier ceiling
  const requiredTier = getRequiredTierForTask(payload.task);
  if (!tierSatisfies(trustTier, requiredTier)) {
    const reason = `TRUST_TIER_FAIL: task "${payload.task}" requires ${requiredTier} but workflow "${workflowName}" ceiling is ${trustTier}`;
    await writeCanonicalTraceRecord({
      command,
      actor: "system",
      execution_status: "blocked",
      result_class: "blocked-policy",
      preflight_status: "not-evaluated",
      canonical_status: "not-evaluated",
      policy_status: "blocking",
      trace_expectation: "required-if-business-logic",
      trace_result: "not-emitted-blocked-before-logic",
      details: {
        task: payload.task,
        requiredTier,
        workflowTier: trustTier,
        reason,
        ...(payloadPath !== undefined ? { payloadPath } : {}),
      },
    });
    throw new Error(reason);
  }

  // Phase A2: evaluate canonical state before any execution
  const canonicalResult = await evaluateCanonicalStateIntegrity();
  const canonicalStatus = canonicalResult.status as TraceGateStatus;

  if (canonicalResult.status === "blocking") {
    const blockingFindings = canonicalResult.findings
      .filter((f) => f.status === "blocking")
      .map((f) => f.reason)
      .join("; ");
    await writeCanonicalTraceRecord({
      command,
      actor: "system",
      execution_status: "blocked",
      result_class: "blocked-canonical-integrity",
      preflight_status: "not-evaluated",
      canonical_status: "blocking",
      policy_status: "not-applicable",
      trace_expectation: "required-if-business-logic",
      trace_result: "not-emitted-blocked-before-logic",
      details: {
        task: payload.task,
        reason: `CANONICAL_INTEGRITY_BLOCKING: ${blockingFindings}`,
        ...(payloadPath !== undefined ? { payloadPath } : {}),
      },
    });
    throw new Error(`CANONICAL_INTEGRITY_BLOCKING: ${blockingFindings}`);
  }

  try {
    validatePayload(payload);
    enforceContract(payload, allowedTasks, forbiddenPatterns);
  } catch (err) {
    const reason = err instanceof Error ? err.message : "unknown gate failure";
    await writeCanonicalTraceRecord({
      command,
      actor: "system",
      execution_status: "blocked",
      result_class: "blocked-policy",
      preflight_status: "not-evaluated",
      canonical_status: canonicalStatus,
      policy_status: "blocking",
      trace_expectation: "required-if-business-logic",
      trace_result: "not-emitted-blocked-before-logic",
      details: {
        task: payload.task,
        reason,
        ...(payloadPath !== undefined ? { payloadPath } : {}),
      },
    });
    throw err;
  }

  // --describe: print resolved payload + contract verdict, no AI call, no trace
  if (mode === "describe") {
    console.log([
      "Z-MOS AI Payload Description",
      "",
      "PAYLOAD:",
      JSON.stringify(payload, null, 2),
      "",
      "CONTRACT_VERDICT: PASS",
      `  allowed_tasks: ${allowedTasks.join(", ")}`,
      `  forbidden_patterns: ${forbiddenPatterns.join(", ")}`,
      ...(payloadPath !== undefined ? [`  payload_source: ${payloadPath}`] : []),
    ].join("\n"));
    return;
  }

  // --dry-run: validate + contract passed, no AI call, emit dry-run trace
  if (mode === "dry-run") {
    console.log([
      "DRY_RUN: payload validated and contract passed",
      `  task: ${payload.task}`,
      `  goal: ${payload.goal}`,
      "  AI call: SKIPPED",
    ].join("\n"));

    const traceResult = await writeCanonicalTraceRecord({
      command,
      actor: "system",
      execution_status: "success",
      result_class: "success",
      preflight_status: "not-evaluated",
      canonical_status: canonicalStatus,
      policy_status: "not-applicable",
      trace_expectation: "optional-by-design",
      trace_result: "not-emitted-by-design",
      details: {
        task: payload.task,
        mode: "dry-run",
        ...(payloadPath !== undefined ? { payloadPath } : {}),
      },
    });

    if (!traceResult.ok) {
      console.warn(`TRACE_WARN: trace write failed — ${traceResult.error}`);
    }
    return;
  }

  if (provider === "external-code-agent" || provider === "ollama") {
    const bundlePath = await writeExecutionBundle(command, payload, provider);
    console.log(
      [
        `AI_PROVIDER: ${provider}`,
        "EXECUTION_MODE: bundle-export",
        `BUNDLE_PATH: ${bundlePath}`,
      ].join("\n"),
    );
    await writeCanonicalTraceRecord({
      command,
      actor: "system",
      execution_status: "success",
      result_class: "success",
      preflight_status: "not-evaluated",
      canonical_status: canonicalStatus,
      policy_status: "healthy",
      trace_expectation: "required-if-business-logic",
      trace_result: "emitted",
      details: {
        task: payload.task,
        trustTier,
        provider,
        executionMode: "bundle-export",
        bundlePath,
        ...(payloadPath !== undefined ? { payloadPath } : {}),
      },
    });
    return;
  }

  const deterministicSummary =
    "AI_PROVIDER=none; governance checks passed; execution skipped by design.";
  console.log(deterministicSummary);
  await writeCanonicalTraceRecord({
    command,
    actor: "system",
    execution_status: "warning",
    result_class: "warning-execution",
    preflight_status: "not-evaluated",
    canonical_status: canonicalStatus,
    policy_status: "warning",
    trace_expectation: "required-if-business-logic",
    trace_result: "emitted",
    details: {
      task: payload.task,
      trustTier,
      provider,
      summary: deterministicSummary,
      ...(payloadPath !== undefined ? { payloadPath } : {}),
    },
  });
}
