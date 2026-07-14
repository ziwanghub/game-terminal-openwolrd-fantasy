import * as path from "node:path";
import { promises as fs } from "node:fs";

import { renderCommandExecutionResult } from "../../core/execution-contract.js";
import { buildDocumentIndex } from "../../core/document-index.js";

type DocIndexFilters = {
  type?: string;
  phase?: string;
  status?: string;
};

function parseFilters(args: string[]): DocIndexFilters {
  const filters: DocIndexFilters = {};
  for (const arg of args) {
    if (arg.startsWith("--type=")) {
      filters.type = arg.slice("--type=".length).trim().toLowerCase();
    } else if (arg.startsWith("--phase=")) {
      filters.phase = arg.slice("--phase=".length).trim().toUpperCase();
    } else if (arg.startsWith("--status=")) {
      filters.status = arg.slice("--status=".length).trim().toLowerCase();
    }
  }
  return filters;
}

function classifyExecution(indexStatus: "healthy" | "warning" | "blocking"): {
  status: "success" | "warning" | "blocked";
  resultClass: "success" | "warning-execution" | "blocked-policy";
} {
  if (indexStatus === "blocking") {
    return { status: "blocked", resultClass: "blocked-policy" };
  }
  if (indexStatus === "warning") {
    return { status: "warning", resultClass: "warning-execution" };
  }
  return { status: "success", resultClass: "success" };
}

export async function runDocCheckCommand(): Promise<void> {
  const index = await buildDocumentIndex();
  const classification = classifyExecution(index.status);

  const lines = [
    "Z-MOS Document Check",
    "",
    `Root: ${index.rootPath}`,
    `Overall Status: ${index.status.toUpperCase()}`,
    "",
    "Summary",
    `- total: ${index.summary.total}`,
    `- healthy: ${index.summary.healthy}`,
    `- warning: ${index.summary.warning}`,
    `- blocking: ${index.summary.blocking}`,
    `- orphan: ${index.summary.orphan}`,
    `- duplicate_ids: ${index.summary.duplicates}`,
  ];

  if (index.globalIssues.length > 0) {
    lines.push("", "Global Issues");
    for (const issue of index.globalIssues) {
      lines.push(`- [${issue.status}] ${issue.message}`);
    }
  }

  if (index.duplicateIds.length > 0) {
    lines.push("", "Duplicate IDs");
    for (const duplicate of index.duplicateIds) {
      lines.push(`- ${duplicate.documentId}`);
      for (const file of duplicate.files) {
        lines.push(`  - ${file}`);
      }
    }
  }

  lines.push(
    "",
    renderCommandExecutionResult({
      command: "doc-check",
      status: classification.status,
      resultClass: classification.resultClass,
      reason:
        classification.status === "blocked"
          ? "Document governance contains blocking issues."
          : undefined,
      warningReason:
        classification.status === "warning"
          ? "Document governance contains warning-level issues."
          : undefined,
      traceExpectation: "optional-by-design",
      traceResult: "not-emitted-by-design",
      nextAction:
        classification.status === "blocked"
          ? "Resolve document schema/naming/duplicate-id blockers and rerun doc:check."
          : undefined,
    }),
  );

  console.log(lines.join("\n"));
  if (classification.status === "blocked") {
    process.exitCode = 1;
  }
}

export async function runDocIndexCommand(args: string[]): Promise<void> {
  const filters = parseFilters(args);
  const index = await buildDocumentIndex();
  const filtered = index.entries.filter((entry) => {
    const metadata = entry.metadata;
    if (filters.type && metadata?.document_type !== filters.type) {
      return false;
    }
    if (filters.phase && metadata?.phase !== filters.phase) {
      return false;
    }
    if (filters.status && metadata?.status !== filters.status) {
      return false;
    }
    return true;
  });

  const classification = classifyExecution(index.status);
  const lines = [
    "Z-MOS Document Index",
    "",
    `Root: ${index.rootPath}`,
    `Total Documents: ${index.summary.total}`,
    `Filtered Documents: ${filtered.length}`,
    `Filters: type=${filters.type || "*"}, phase=${filters.phase || "*"}, status=${filters.status || "*"}`,
    "",
    "Documents",
  ];

  for (const entry of filtered) {
    const relPath = path.relative(process.cwd(), entry.filePath);
    const metadata = entry.metadata;
    lines.push(
      `- ${entry.fileName} [${entry.status}]${entry.orphan ? " (orphan)" : ""}`,
      `  - path: ${relPath}`,
      `  - id: ${metadata?.document_id || "(none)"}`,
      `  - type: ${metadata?.document_type || "(none)"}`,
      `  - phase: ${metadata?.phase || "(none)"}`,
      `  - status: ${metadata?.status || "(none)"}`,
    );
  }

  lines.push(
    "",
    renderCommandExecutionResult({
      command: "doc-index",
      status: classification.status,
      resultClass: classification.resultClass,
      warningReason:
        classification.status === "warning"
          ? "Document index contains warning-level governance issues."
          : undefined,
      reason:
        classification.status === "blocked"
          ? "Document index contains blocking governance issues."
          : undefined,
      traceExpectation: "optional-by-design",
      traceResult: "not-emitted-by-design",
      nextAction:
        classification.status === "blocked"
          ? "Run doc:check and resolve blocking findings."
          : undefined,
    }),
  );

  console.log(lines.join("\n"));
  if (classification.status === "blocked") {
    process.exitCode = 1;
  }
}

export async function runDocDoctorCommand(): Promise<void> {
  const index = await buildDocumentIndex();
  const docsRoot = path.join(process.cwd(), "docs", "zmos");
  let docsRootExists = true;
  try {
    await fs.access(docsRoot);
  } catch {
    docsRootExists = false;
  }

  const classification = classifyExecution(index.status);
  const linkageWarnings = index.entries
    .flatMap((entry) => entry.issues)
    .filter((issue) => issue.code === "trace-id-not-found").length;

  const lines = [
    "Z-MOS Document Doctor",
    "",
    "Structure Checks",
    `- docs/zmos exists: ${docsRootExists ? "yes" : "no"}`,
    `- markdown documents discovered: ${index.summary.total}`,
    "",
    "Validation Checks",
    `- healthy: ${index.summary.healthy}`,
    `- warning: ${index.summary.warning}`,
    `- blocking: ${index.summary.blocking}`,
    `- duplicate IDs: ${index.summary.duplicates}`,
    `- orphan documents: ${index.summary.orphan}`,
    "",
    "Linkage Hints",
    `- trace linkage warnings: ${linkageWarnings}`,
    `- recommendation: ${linkageWarnings > 0 ? "review related_trace_ids against runtime trace evidence" : "no immediate linkage warning"}`,
  ];

  if (index.globalIssues.length > 0) {
    lines.push("", "Global Governance Findings");
    for (const issue of index.globalIssues) {
      lines.push(`- [${issue.status}] ${issue.message}`);
    }
  }

  lines.push(
    "",
    renderCommandExecutionResult({
      command: "doc-doctor",
      status: classification.status,
      resultClass: classification.resultClass,
      warningReason:
        classification.status === "warning"
          ? "Document governance has warning findings."
          : undefined,
      reason:
        classification.status === "blocked"
          ? "Document governance has blocking findings."
          : undefined,
      traceExpectation: "optional-by-design",
      traceResult: "not-emitted-by-design",
      nextAction:
        classification.status === "blocked"
          ? "Resolve document blockers and rerun doc:doctor."
          : undefined,
    }),
  );

  console.log(lines.join("\n"));
  if (classification.status === "blocked") {
    process.exitCode = 1;
  }
}
