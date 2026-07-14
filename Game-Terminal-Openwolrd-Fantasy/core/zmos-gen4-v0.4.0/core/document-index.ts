import { promises as fs } from "node:fs";
import * as path from "node:path";

import type { ZmosDocumentContract } from "../contracts/document.js";
import {
  type DocumentValidationIssue,
  type DocumentValidationResult,
  type DocumentValidationStatus,
  validateDocumentFile,
} from "./document-validator.js";

export type DocumentIndexStatus = DocumentValidationStatus;

export type DocumentIndexEntry = {
  filePath: string;
  fileName: string;
  metadata: ZmosDocumentContract | null;
  status: DocumentValidationStatus;
  issues: DocumentValidationIssue[];
  orphan: boolean;
};

export type DocumentIndexResult = {
  rootPath: string;
  status: DocumentIndexStatus;
  summary: {
    total: number;
    healthy: number;
    warning: number;
    blocking: number;
    orphan: number;
    duplicates: number;
  };
  entries: DocumentIndexEntry[];
  duplicateIds: Array<{
    documentId: string;
    files: string[];
  }>;
  globalIssues: DocumentValidationIssue[];
};

const ROOT_DIR = process.cwd();
const DOCS_ROOT = path.join(ROOT_DIR, "docs", "zmos");

async function listMarkdownFiles(targetDir: string): Promise<string[]> {
  const files: string[] = [];

  async function walk(currentDir: string): Promise<void> {
    const dirents = await fs.readdir(currentDir, { withFileTypes: true });
    for (const dirent of dirents) {
      const fullPath = path.join(currentDir, dirent.name);
      if (dirent.isDirectory()) {
        await walk(fullPath);
      } else if (dirent.isFile() && dirent.name.toLowerCase().endsWith(".md")) {
        files.push(fullPath);
      }
    }
  }

  await walk(targetDir);
  return files.sort();
}

function resolveStatusFromEntries(
  entries: DocumentIndexEntry[],
  globalIssues: DocumentValidationIssue[],
): DocumentIndexStatus {
  const statuses = [...entries.map((entry) => entry.status), ...globalIssues.map((issue) => issue.status)];
  if (statuses.includes("blocking")) {
    return "blocking";
  }
  if (statuses.includes("warning")) {
    return "warning";
  }
  return "healthy";
}

export async function buildDocumentIndex(): Promise<DocumentIndexResult> {
  const globalIssues: DocumentValidationIssue[] = [];
  let markdownFiles: string[] = [];

  try {
    markdownFiles = await listMarkdownFiles(DOCS_ROOT);
  } catch {
    globalIssues.push({
      code: "metadata-missing",
      status: "warning",
      message: "docs/zmos directory is missing; document governance scan is skipped.",
    });

    return {
      rootPath: DOCS_ROOT,
      status: "warning",
      summary: {
        total: 0,
        healthy: 0,
        warning: 1,
        blocking: 0,
        orphan: 0,
        duplicates: 0,
      },
      entries: [],
      duplicateIds: [],
      globalIssues,
    };
  }

  const entries: DocumentIndexEntry[] = [];
  const idToFiles = new Map<string, string[]>();

  for (const filePath of markdownFiles) {
    const validation: DocumentValidationResult = await validateDocumentFile(filePath);
    const orphan = validation.metadata === null;
    entries.push({
      filePath: validation.filePath,
      fileName: validation.fileName,
      metadata: validation.metadata,
      status: validation.status,
      issues: validation.issues,
      orphan,
    });

    const documentId = validation.metadata?.document_id;
    if (documentId) {
      const existing = idToFiles.get(documentId) || [];
      existing.push(validation.filePath);
      idToFiles.set(documentId, existing);
    }
  }

  const duplicateIds: Array<{ documentId: string; files: string[] }> = [];
  for (const [documentId, files] of idToFiles.entries()) {
    if (files.length > 1) {
      duplicateIds.push({ documentId, files: files.sort() });
      globalIssues.push({
        code: "metadata-malformed",
        status: "blocking",
        message: `Duplicate document_id "${documentId}" detected.`,
        field: "document_id",
      });
    }
  }

  const summary = {
    total: entries.length,
    healthy: entries.filter((entry) => entry.status === "healthy").length,
    warning: entries.filter((entry) => entry.status === "warning").length,
    blocking: entries.filter((entry) => entry.status === "blocking").length,
    orphan: entries.filter((entry) => entry.orphan).length,
    duplicates: duplicateIds.length,
  };

  return {
    rootPath: DOCS_ROOT,
    status: resolveStatusFromEntries(entries, globalIssues),
    summary,
    entries,
    duplicateIds,
    globalIssues,
  };
}
