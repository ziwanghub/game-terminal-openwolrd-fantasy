import { promises as fs } from "node:fs";

import { getTraceFilePath, validateTraceRecord } from "./trace-writer.js";
import type { TraceRecord } from "../trace/types.js";

export type TraceValidationStatus = "healthy" | "warning" | "corrupted";

export type TraceValidationIssue = {
  line: number;
  type:
    | "json-parse-error"
    | "schema-error"
    | "truncated-line"
    | "completeness-mismatch"
    | "legacy-schema";
  message: string;
};

export type TraceCompletenessSummary = {
  emittedExpectedButMissing: number;
  blockedButEmitted: number;
};

export type TraceValidationReport = {
  status: TraceValidationStatus;
  tracePath: string;
  fileExists: boolean;
  readable: boolean;
  totalLines: number;
  validLines: number;
  checkedLines: number;
  issues: TraceValidationIssue[];
  completeness: TraceCompletenessSummary;
};

function evaluateReportStatus(
  fileExists: boolean,
  readable: boolean,
  issues: TraceValidationIssue[],
): TraceValidationStatus {
  if (!fileExists || !readable) {
    return "warning";
  }

  if (
    issues.some(
      (issue) =>
        issue.type === "json-parse-error" ||
        issue.type === "schema-error" ||
        issue.type === "truncated-line",
    )
  ) {
    return "corrupted";
  }

  if (issues.some((issue) => issue.type === "completeness-mismatch")) {
    return "warning";
  }

  return "healthy";
}

function isLikelyTruncated(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed) {
    return false;
  }
  if (trimmed.endsWith("}") || trimmed.endsWith("]") || trimmed.endsWith('"')) {
    return false;
  }
  return true;
}

function collectCompletenessIssues(
  record: TraceRecord,
  line: number,
): TraceValidationIssue[] {
  const issues: TraceValidationIssue[] = [];

  if (
    (record.execution_status === "success" || record.execution_status === "warning") &&
    record.trace_expectation === "required-if-business-logic" &&
    record.trace_result !== "emitted"
  ) {
    issues.push({
      line,
      type: "completeness-mismatch",
      message:
        "execution_status indicates logic executed but trace_result is not emitted.",
    });
  }

  if (
    (record.result_class === "blocked-preflight" ||
      record.result_class === "blocked-canonical-integrity" ||
      record.result_class === "blocked-policy") &&
    record.trace_result === "emitted"
  ) {
    issues.push({
      line,
      type: "completeness-mismatch",
      message:
        "blocked result class should not have trace_result emitted for blocked-before-logic path.",
    });
  }

  return issues;
}

function isLegacyTraceShape(value: unknown): boolean {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.timestamp === "string" &&
    typeof record.command === "string" &&
    typeof record.status === "string" &&
    typeof record.actor === "string" &&
    typeof record.repository === "string" &&
    typeof record.framework === "string" &&
    typeof record.details === "object" &&
    record.details !== null
  );
}

export async function validateTraceFile(
  options?: { maxLines?: number },
): Promise<TraceValidationReport> {
  const tracePath = await getTraceFilePath();
  const maxLines = options?.maxLines ?? 200;
  const issues: TraceValidationIssue[] = [];
  let fileExists = true;
  let readable = true;
  let totalLines = 0;
  let validLines = 0;
  let checkedLines = 0;
  const completeness: TraceCompletenessSummary = {
    emittedExpectedButMissing: 0,
    blockedButEmitted: 0,
  };

  let content = "";
  try {
    content = await fs.readFile(tracePath, "utf8");
  } catch {
    fileExists = false;
    readable = false;
    return {
      status: evaluateReportStatus(fileExists, readable, issues),
      tracePath,
      fileExists,
      readable,
      totalLines,
      validLines,
      checkedLines,
      issues,
      completeness,
    };
  }

  const allLines = content.split("\n").filter((line) => line.trim().length > 0);
  totalLines = allLines.length;
  const startIndex = Math.max(0, totalLines - maxLines);
  const lines = allLines.slice(startIndex);
  checkedLines = lines.length;

  lines.forEach((line, index) => {
    const lineNumber = startIndex + index + 1;
    if (isLikelyTruncated(line)) {
      issues.push({
        line: lineNumber,
        type: "truncated-line",
        message: "trace line appears truncated",
      });
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(line) as unknown;
    } catch {
      issues.push({
        line: lineNumber,
        type: "json-parse-error",
        message: "invalid JSON line",
      });
      return;
    }

    try {
      const record = validateTraceRecord(parsed as TraceRecord);
      validLines += 1;
      const completenessIssues = collectCompletenessIssues(record, lineNumber);
      for (const issue of completenessIssues) {
        issues.push(issue);
      }
      completeness.emittedExpectedButMissing += completenessIssues.filter((issue) =>
        issue.message.includes("not emitted"),
      ).length;
      completeness.blockedButEmitted += completenessIssues.filter((issue) =>
        issue.message.includes("blocked result class"),
      ).length;
    } catch (error) {
      if (isLegacyTraceShape(parsed)) {
        validLines += 1;
        issues.push({
          line: lineNumber,
          type: "legacy-schema",
          message:
            "legacy trace schema detected (compatible warning; migration recommended).",
        });
      } else {
        issues.push({
          line: lineNumber,
          type: "schema-error",
          message: error instanceof Error ? error.message : "schema validation error",
        });
      }
    }
  });

  return {
    status: evaluateReportStatus(fileExists, readable, issues),
    tracePath,
    fileExists,
    readable,
    totalLines,
    validLines,
    checkedLines,
    issues,
    completeness,
  };
}
