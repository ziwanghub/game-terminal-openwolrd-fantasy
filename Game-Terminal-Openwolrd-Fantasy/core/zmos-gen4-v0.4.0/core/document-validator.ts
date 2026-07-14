import { promises as fs } from "node:fs";
import * as path from "node:path";

import {
  DOCUMENT_STATUSES,
  DOCUMENT_TYPES,
  type ZmosDocumentContract,
  normalizeDocumentToken,
  normalizeDocumentType,
  parseDocumentFilename,
} from "../contracts/document.js";

export type DocumentValidationStatus = "healthy" | "warning" | "blocking";

export type DocumentValidationIssue = {
  code:
    | "metadata-missing"
    | "metadata-malformed"
    | "required-missing"
    | "document-type-invalid"
    | "status-invalid"
    | "date-invalid"
    | "trace-id-format-invalid"
    | "trace-id-not-found"
    | "related-command-invalid"
    | "filename-invalid"
    | "filename-metadata-mismatch"
    | "lifecycle-invalid";
  status: DocumentValidationStatus;
  message: string;
  field?: string;
};

export type DocumentValidationResult = {
  filePath: string;
  fileName: string;
  status: DocumentValidationStatus;
  metadata: ZmosDocumentContract | null;
  issues: DocumentValidationIssue[];
};

const ROOT_DIR = process.cwd();
const TRACE_PATH = path.join(ROOT_DIR, ".z-mos", "trace", "runtime-trace.jsonl");
const TRACE_ID_PATTERN = /^trace-\d{4}-\d{2}-\d{2}-\d{3}$/;
const FILENAME_GOVERNANCE_EXEMPTIONS = new Set([
  "START-GUIDE.md",
  "AI-START-PROMPT.md",
  "Z-MOS-SESSION-ENTRY-STANDARD.md",
]);

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asNonEmptyString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function parseIsoDate(value: string): boolean {
  const time = Date.parse(value);
  return Number.isFinite(time);
}

function addIssue(
  issues: DocumentValidationIssue[],
  code: DocumentValidationIssue["code"],
  status: DocumentValidationStatus,
  message: string,
  field?: string,
): void {
  issues.push({ code, status, message, field });
}

function resolveStatus(issues: DocumentValidationIssue[]): DocumentValidationStatus {
  if (issues.some((issue) => issue.status === "blocking")) {
    return "blocking";
  }
  if (issues.some((issue) => issue.status === "warning")) {
    return "warning";
  }
  return "healthy";
}

function parseHeaderValue(rawValue: string): string {
  const trimmed = rawValue.trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1).trim();
  }
  return trimmed;
}

function parseMarkdownHeader(content: string): Record<string, unknown> | null {
  const lines = content.split("\n");
  if (lines[0]?.trim() !== "---") {
    return null;
  }

  let end = -1;
  for (let i = 1; i < lines.length; i += 1) {
    if (lines[i].trim() === "---") {
      end = i;
      break;
    }
  }

  if (end < 0) {
    return null;
  }

  const metadata: Record<string, unknown> = {};
  let activeListKey: string | null = null;
  for (let i = 1; i < end; i += 1) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    if ((trimmed.startsWith("- ") || trimmed.startsWith("* ")) && activeListKey) {
      const list = metadata[activeListKey];
      if (Array.isArray(list)) {
        list.push(parseHeaderValue(trimmed.slice(2)));
      }
      continue;
    }

    const separator = rawLine.indexOf(":");
    if (separator < 0) {
      activeListKey = null;
      continue;
    }

    const key = rawLine.slice(0, separator).trim();
    const value = rawLine.slice(separator + 1);
    if (!key) {
      activeListKey = null;
      continue;
    }

    const parsed = parseHeaderValue(value);
    if (!parsed) {
      metadata[key] = [];
      activeListKey = key;
      continue;
    }

    metadata[key] = parsed;
    activeListKey = null;
  }

  return metadata;
}

function parseDocumentMetadata(
  value: unknown,
  issues: DocumentValidationIssue[],
): ZmosDocumentContract | null {
  if (!isObject(value)) {
    addIssue(
      issues,
      "metadata-malformed",
      "blocking",
      "Document metadata header is malformed.",
    );
    return null;
  }

  const requiredFields = [
    "document_id",
    "document_type",
    "project_code",
    "phase",
    "version",
    "status",
    "created_at",
    "updated_at",
  ] as const;

  for (const field of requiredFields) {
    if (!asNonEmptyString(value[field])) {
      addIssue(
        issues,
        "required-missing",
        "blocking",
        `Required metadata field "${field}" is missing or empty.`,
        field,
      );
    }
  }

  const documentType = asNonEmptyString(value.document_type);
  const status = asNonEmptyString(value.status);
  const projectCode = asNonEmptyString(value.project_code);
  const phase = asNonEmptyString(value.phase);
  const version = asNonEmptyString(value.version);
  const createdAt = asNonEmptyString(value.created_at);
  const updatedAt = asNonEmptyString(value.updated_at);
  const documentId = asNonEmptyString(value.document_id);

  if (!documentType || !DOCUMENT_TYPES.includes(normalizeDocumentType(documentType) as (typeof DOCUMENT_TYPES)[number])) {
    addIssue(
      issues,
      "document-type-invalid",
      "blocking",
      `document_type "${documentType || "(empty)"}" is not supported.`,
      "document_type",
    );
  }

  if (!status || !DOCUMENT_STATUSES.includes(status as (typeof DOCUMENT_STATUSES)[number])) {
    addIssue(
      issues,
      "status-invalid",
      "blocking",
      `status "${status || "(empty)"}" is not supported.`,
      "status",
    );
  }

  if (createdAt && !parseIsoDate(createdAt)) {
    addIssue(issues, "date-invalid", "blocking", "created_at is not a valid ISO date.", "created_at");
  }

  if (updatedAt && !parseIsoDate(updatedAt)) {
    addIssue(issues, "date-invalid", "blocking", "updated_at is not a valid ISO date.", "updated_at");
  }

  const relatedTraceIds = value.related_trace_ids;
  if (relatedTraceIds !== undefined && !Array.isArray(relatedTraceIds)) {
    addIssue(
      issues,
      "metadata-malformed",
      "blocking",
      "related_trace_ids must be an array when provided.",
      "related_trace_ids",
    );
  }

  const relatedCommands = value.related_commands;
  if (relatedCommands !== undefined && !Array.isArray(relatedCommands)) {
    addIssue(
      issues,
      "metadata-malformed",
      "blocking",
      "related_commands must be an array when provided.",
      "related_commands",
    );
  }

  if (Array.isArray(relatedTraceIds)) {
    for (const traceId of relatedTraceIds) {
      if (!asNonEmptyString(traceId) || !TRACE_ID_PATTERN.test(String(traceId).trim())) {
        addIssue(
          issues,
          "trace-id-format-invalid",
          "blocking",
          `related_trace_ids contains invalid trace id "${String(traceId)}".`,
          "related_trace_ids",
        );
      }
    }
  }

  if (Array.isArray(relatedCommands)) {
    for (const command of relatedCommands) {
      if (!asNonEmptyString(command)) {
        addIssue(
          issues,
          "related-command-invalid",
          "warning",
          "related_commands contains empty command reference.",
          "related_commands",
        );
      }
    }
  }

  const supersededBy = asNonEmptyString(value.superseded_by);
  if (status === "superseded" && !supersededBy) {
    addIssue(
      issues,
      "lifecycle-invalid",
      "blocking",
      "superseded status requires superseded_by reference.",
      "superseded_by",
    );
  }

  if (status === "archived" && normalizeDocumentType(documentType || "") === "playbook") {
    addIssue(
      issues,
      "lifecycle-invalid",
      "blocking",
      "archived playbook is not allowed in active playbook set.",
      "status",
    );
  }

  if (
    !documentId ||
    !documentType ||
    !projectCode ||
    !phase ||
    !version ||
    !status ||
    !createdAt ||
    !updatedAt
  ) {
    return null;
  }

  return {
    document_id: documentId,
    document_type: normalizeDocumentType(documentType) as ZmosDocumentContract["document_type"],
    project_code: normalizeDocumentToken(projectCode),
    phase: normalizeDocumentToken(phase),
    version,
    status: status as ZmosDocumentContract["status"],
    created_at: createdAt,
    updated_at: updatedAt,
    related_trace_ids: Array.isArray(relatedTraceIds)
      ? relatedTraceIds.map((entry) => String(entry).trim())
      : undefined,
    related_commands: Array.isArray(relatedCommands)
      ? relatedCommands.map((entry) => String(entry).trim())
      : undefined,
    superseded_by: supersededBy || undefined,
  };
}

async function validateRelatedTraceReferences(
  metadata: ZmosDocumentContract | null,
  issues: DocumentValidationIssue[],
): Promise<void> {
  if (!metadata?.related_trace_ids?.length) {
    return;
  }

  let traceContent = "";
  try {
    traceContent = await fs.readFile(TRACE_PATH, "utf8");
  } catch {
    addIssue(
      issues,
      "trace-id-not-found",
      "warning",
      "related_trace_ids provided but trace file is not readable for linkage check.",
      "related_trace_ids",
    );
    return;
  }

  for (const traceId of metadata.related_trace_ids) {
    if (!traceContent.includes(traceId)) {
      addIssue(
        issues,
        "trace-id-not-found",
        "warning",
        `related_trace_id "${traceId}" not found in runtime trace.`,
        "related_trace_ids",
      );
    }
  }
}

function validateFilenameAgainstMetadata(
  fileName: string,
  metadata: ZmosDocumentContract | null,
  issues: DocumentValidationIssue[],
): void {
  if (!metadata) {
    return;
  }

  if (FILENAME_GOVERNANCE_EXEMPTIONS.has(fileName)) {
    return;
  }

  const parts = parseDocumentFilename(fileName);
  if (!parts) {
    addIssue(
      issues,
      "filename-invalid",
      "blocking",
      "Filename does not match ZMOS naming convention.",
    );
    return;
  }

  const expectedType = normalizeDocumentToken(metadata.document_type);
  const expectedProject = normalizeDocumentToken(metadata.project_code);
  const expectedPhase = normalizeDocumentToken(metadata.phase);

  if (
    parts.type !== expectedType ||
    parts.project !== expectedProject ||
    parts.phase !== expectedPhase
  ) {
    addIssue(
      issues,
      "filename-metadata-mismatch",
      "blocking",
      "Filename tokens (TYPE/PROJECT/PHASE) do not match metadata.",
    );
  }
}

export async function validateDocumentFile(filePath: string): Promise<DocumentValidationResult> {
  const fileName = path.basename(filePath);
  const issues: DocumentValidationIssue[] = [];

  let content = "";
  try {
    content = await fs.readFile(filePath, "utf8");
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown read failure";
    addIssue(issues, "metadata-malformed", "blocking", `Cannot read document: ${message}`);
    return {
      filePath,
      fileName,
      status: "blocking",
      metadata: null,
      issues,
    };
  }

  const rawHeader = parseMarkdownHeader(content);
  if (!rawHeader) {
    const governedByFilename = parseDocumentFilename(fileName) !== null;
    if (!governedByFilename) {
      return {
        filePath,
        fileName,
        status: "healthy",
        metadata: null,
        issues: [],
      };
    }
    addIssue(
      issues,
      "metadata-missing",
      "warning",
      "Document is missing markdown metadata header and is treated as orphan.",
    );
    validateFilenameAgainstMetadata(fileName, null, issues);
    return {
      filePath,
      fileName,
      status: resolveStatus(issues),
      metadata: null,
      issues,
    };
  }

  const metadata = parseDocumentMetadata(rawHeader, issues);
  validateFilenameAgainstMetadata(fileName, metadata, issues);
  await validateRelatedTraceReferences(metadata, issues);

  return {
    filePath,
    fileName,
    status: resolveStatus(issues),
    metadata,
    issues,
  };
}
