import fs from "node:fs";
import path from "node:path";

export const FORBIDDEN_NETWORK_MODULES = [
  "http",
  "https",
  "net",
  "tls",
  "dgram",
  "ws",
  "child_process",
] as const;

export const APPROVED_LOCAL_FS_MODULES = ["fs", "fs/promises", "path"] as const;

type Finding = {
  file_path: string;
  line: number;
  kind:
    | "forbidden-es-import"
    | "forbidden-dynamic-import"
    | "forbidden-require"
    | "forbidden-direct-string"
    | "unapproved-fs-import";
  module_name: string;
  snippet: string;
};

function toLines(input: string): string[] {
  return input.split("\n");
}

function normalize(inputPath: string): string {
  return path.resolve(inputPath);
}

function collectTsFiles(rootPath: string): string[] {
  const entries = fs.readdirSync(rootPath, { withFileTypes: true });
  const files: string[] = [];

  for (const entry of entries) {
    const fullPath = path.join(rootPath, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectTsFiles(fullPath));
      continue;
    }
    if (entry.isFile() && fullPath.endsWith(".ts")) {
      files.push(fullPath);
    }
  }

  return files.sort((a, b) => a.localeCompare(b));
}

function pushIfMatch(params: {
  findings: Finding[];
  filePath: string;
  line: string;
  lineNumber: number;
  kind: Finding["kind"];
  moduleName: string;
  regex: RegExp;
}) {
  if (!params.regex.test(params.line)) {
    return;
  }

  params.findings.push({
    file_path: params.filePath,
    line: params.lineNumber,
    kind: params.kind,
    module_name: params.moduleName,
    snippet: params.line.trim(),
  });
}

export function scanTextForBoundaryViolations(input: {
  source_text: string;
  file_path: string;
  allow_fs_modules?: boolean;
}): Finding[] {
  const lines = toLines(input.source_text);
  const findings: Finding[] = [];

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const lineNumber = index + 1;

    for (const moduleName of FORBIDDEN_NETWORK_MODULES) {
      pushIfMatch({
        findings,
        filePath: input.file_path,
        line,
        lineNumber,
        kind: "forbidden-es-import",
        moduleName,
        regex: new RegExp(`\\bimport\\s+[^\\n]*[\"'](?:node:)?${moduleName}[\"']`),
      });

      pushIfMatch({
        findings,
        filePath: input.file_path,
        line,
        lineNumber,
        kind: "forbidden-dynamic-import",
        moduleName,
        regex: new RegExp(`\\bimport\\(\\s*[\"'](?:node:)?${moduleName}[\"']\\s*\\)`),
      });

      pushIfMatch({
        findings,
        filePath: input.file_path,
        line,
        lineNumber,
        kind: "forbidden-require",
        moduleName,
        regex: new RegExp(`\\brequire\\(\\s*[\"'](?:node:)?${moduleName}[\"']\\s*\\)`),
      });

      pushIfMatch({
        findings,
        filePath: input.file_path,
        line,
        lineNumber,
        kind: "forbidden-direct-string",
        moduleName,
        regex: new RegExp(`[\"'](?:node:)?${moduleName}[\"']`),
      });
    }

    if (!input.allow_fs_modules) {
      for (const moduleName of APPROVED_LOCAL_FS_MODULES) {
        pushIfMatch({
          findings,
          filePath: input.file_path,
          line,
          lineNumber,
          kind: "unapproved-fs-import",
          moduleName,
          regex: new RegExp(`\\b(import\\s+[^\\n]*|require\\(|import\\()\\s*[\"'](?:node:)?${moduleName}[\"']`),
        });
      }
    }
  }

  return findings;
}

export function scanLocalKernelBoundary(options?: {
  localKernelRoot?: string;
  fsAllowedFiles?: string[];
}): Finding[] {
  const localKernelRoot = normalize(options?.localKernelRoot ?? path.resolve("core/gen4/local-kernel"));
  const fsAllowedFiles = new Set(
    (options?.fsAllowedFiles ?? [path.resolve("core/gen4/local-kernel/trace-persistence.ts")]).map((value) =>
      normalize(value),
    ),
  );

  const files = collectTsFiles(localKernelRoot);
  const findings: Finding[] = [];

  for (const filePath of files) {
    const content = fs.readFileSync(filePath, "utf8");
    const allowFsModules = fsAllowedFiles.has(normalize(filePath));
    findings.push(
      ...scanTextForBoundaryViolations({
        source_text: content,
        file_path: normalize(filePath),
        allow_fs_modules: allowFsModules,
      }),
    );
  }

  return findings.sort((a, b) => {
    const byFile = a.file_path.localeCompare(b.file_path);
    if (byFile !== 0) return byFile;
    if (a.line !== b.line) return a.line - b.line;
    const byKind = a.kind.localeCompare(b.kind);
    if (byKind !== 0) return byKind;
    return a.module_name.localeCompare(b.module_name);
  });
}

export function formatBoundaryFindings(findings: Finding[]): string {
  if (findings.length === 0) {
    return "NO_FINDINGS";
  }

  return findings
    .map((finding) =>
      `${finding.file_path}:${finding.line} [${finding.kind}] ${finding.module_name} :: ${finding.snippet}`,
    )
    .join("\n");
}
