import { existsSync, promises as fs } from "node:fs";
import * as path from "node:path";

import type { WorkflowDiagnosticsSummary } from "../contracts/workflow.js";
import { resolveAiProvider, type AiProvider } from "./ai-provider.js";

const ROOT_DIR = process.cwd();
const ADVISORY_DIR = path.join(ROOT_DIR, ".z-mos", "advisory");
const DEFAULT_OPTIONAL_DOCS = ["README.md", "zmos-core.md"];

type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue };

type TraceEntry = {
  timestamp?: string;
  command?: string;
  execution_status?: string;
  result_class?: string;
};

export type AdvisoryContext = {
  generatedAt: string;
  provider: AiProvider;
  manifest: JsonValue | null;
  session: JsonValue | null;
  workflowPolicy: JsonValue | null;
  recentTrace: TraceEntry[];
  optionalDocs: Array<{ file: string; contentPreview: string }>;
  warnings: string[];
};

export type AdvisoryBundleResult = {
  context: AdvisoryContext;
  inputPath: string;
  promptPath: string;
  advisoryMode: "external-code-agent" | "local-deterministic" | "degraded";
};

async function readJsonFile(filePath: string): Promise<JsonValue | null> {
  try {
    const raw = await fs.readFile(filePath, "utf8");
    return JSON.parse(raw) as JsonValue;
  } catch {
    return null;
  }
}

async function readRecentTrace(tracePath: string, limit: number): Promise<TraceEntry[]> {
  if (!existsSync(tracePath)) {
    return [];
  }
  try {
    const raw = await fs.readFile(tracePath, "utf8");
    const lines = raw
      .trim()
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);

    const parsed: TraceEntry[] = [];
    for (const line of lines.slice(-limit)) {
      try {
        const row = JSON.parse(line) as TraceEntry;
        parsed.push({
          timestamp: row.timestamp,
          command: row.command,
          execution_status: row.execution_status,
          result_class: row.result_class,
        });
      } catch {
        // ignore malformed rows
      }
    }
    return parsed;
  } catch {
    return [];
  }
}

async function readOptionalDocs(): Promise<Array<{ file: string; contentPreview: string }>> {
  const docs: Array<{ file: string; contentPreview: string }> = [];
  for (const file of DEFAULT_OPTIONAL_DOCS) {
    const fullPath = path.join(ROOT_DIR, file);
    if (!existsSync(fullPath)) {
      continue;
    }
    try {
      const raw = await fs.readFile(fullPath, "utf8");
      docs.push({
        file,
        contentPreview: raw.slice(0, 1200),
      });
    } catch {
      // skip unreadable docs
    }
  }
  return docs;
}

export async function buildAdvisoryContext(): Promise<AdvisoryContext> {
  const manifestPath = path.join(ROOT_DIR, ".z-mos", "zmos-manifest.json");
  const sessionPath = path.join(ROOT_DIR, ".z-mos", "state", "runtime-state.json");
  const workflowPolicyPath = path.join(ROOT_DIR, ".z-mos", "workflow-policy.json");
  const tracePath = path.join(ROOT_DIR, ".z-mos", "trace", "runtime-trace.jsonl");

  const [manifest, session, workflowPolicy, recentTrace, optionalDocs] = await Promise.all([
    readJsonFile(manifestPath),
    readJsonFile(sessionPath),
    readJsonFile(workflowPolicyPath),
    readRecentTrace(tracePath, 20),
    readOptionalDocs(),
  ]);

  const warnings: string[] = [];
  if (manifest === null) warnings.push("missing .z-mos/zmos-manifest.json");
  if (session === null) warnings.push("missing .z-mos/state/runtime-state.json");
  if (workflowPolicy === null) warnings.push("missing .z-mos/workflow-policy.json");
  if (recentTrace.length === 0) warnings.push("trace not found or empty");

  return {
    generatedAt: new Date().toISOString(),
    provider: resolveAiProvider(),
    manifest,
    session,
    workflowPolicy,
    recentTrace,
    optionalDocs,
    warnings,
  };
}

function deterministicSummary(
  diagnosticsSummary: WorkflowDiagnosticsSummary,
  context: AdvisoryContext,
): string {
  const findings: string[] = [];
  if (diagnosticsSummary.blocking > 0) findings.push("blocking diagnostics present");
  if (diagnosticsSummary.warning > 0) findings.push("warning diagnostics present");
  if (context.warnings.length > 0) findings.push(`context warnings: ${context.warnings.join(", ")}`);
  if (findings.length === 0) findings.push("no critical advisory finding");

  return [
    "Deterministic Advisory Summary",
    `- healthy: ${diagnosticsSummary.healthy}`,
    `- warning: ${diagnosticsSummary.warning}`,
    `- blocking: ${diagnosticsSummary.blocking}`,
    ...findings.map((item) => `- ${item}`),
  ].join("\n");
}

function buildPrompt(context: AdvisoryContext, deterministic: string): string {
  const policySummary =
    context.workflowPolicy !== null ? JSON.stringify(context.workflowPolicy, null, 2) : "not enough evidence";
  const sessionSummary =
    context.session !== null ? JSON.stringify(context.session, null, 2) : "not enough evidence";

  return [
    "# Z-MOS Advisory Prompt Bundle",
    "",
    "Use this bundle as the only advisory input.",
    "Rules:",
    "- evidence-first reasoning only",
    "- no code mutation",
    '- if evidence is insufficient, output exactly "not enough evidence"',
    "",
    "## Deterministic Baseline",
    deterministic,
    "",
    "## Session",
    "```json",
    sessionSummary,
    "```",
    "",
    "## Workflow Policy",
    "```json",
    policySummary,
    "```",
  ].join("\n");
}

export async function createAdvisoryBundle(
  diagnosticsSummary: WorkflowDiagnosticsSummary,
): Promise<AdvisoryBundleResult> {
  const context = await buildAdvisoryContext();
  await fs.mkdir(ADVISORY_DIR, { recursive: true });

  const deterministic = deterministicSummary(diagnosticsSummary, context);
  const advisoryMode =
    context.provider === "external-code-agent"
      ? "external-code-agent"
      : context.provider === "none"
        ? "local-deterministic"
        : context.warnings.length > 0
          ? "degraded"
          : "external-code-agent";

  const inputPayload = {
    mode: advisoryMode,
    generatedAt: context.generatedAt,
    provider: context.provider,
    deterministicSummary: deterministic,
    context,
  };

  const stamp = context.generatedAt.replace(/[:.]/g, "-");
  const inputPath = path.join(ADVISORY_DIR, `advisory-input-${stamp}.json`);
  const promptPath = path.join(ADVISORY_DIR, `advisory-prompt-${stamp}.md`);

  await Promise.all([
    fs.writeFile(inputPath, JSON.stringify(inputPayload, null, 2), "utf8"),
    fs.writeFile(promptPath, buildPrompt(context, deterministic), "utf8"),
  ]);

  return {
    context,
    inputPath,
    promptPath,
    advisoryMode,
  };
}
