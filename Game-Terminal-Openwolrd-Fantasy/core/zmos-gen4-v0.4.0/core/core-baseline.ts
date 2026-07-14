import { promises as fs } from "node:fs";
import * as path from "node:path";

export type CoreContaminantType = "approved-generated" | "unapproved-non-core";

export type CoreContaminant = {
  path: string;
  type: CoreContaminantType;
  approvedForRemoval: boolean;
  reason: string;
};

export type CoreBaselineReport = {
  rootDir: string;
  baselineCorePaths: string[];
  protectedPaths: string[];
  removableGeneratedPaths: string[];
  presentCorePaths: string[];
  missingCorePaths: string[];
  contaminants: CoreContaminant[];
  summary: {
    totalContaminants: number;
    approvedGeneratedContaminants: number;
    unapprovedContaminants: number;
  };
};

export type CoreCleanAction = {
  path: string;
  action: "removed" | "would-remove" | "skipped-unapproved" | "failed";
  reason: string;
};

export type CoreCleanResult = {
  dryRun: boolean;
  actions: CoreCleanAction[];
  summary: {
    removed: number;
    wouldRemove: number;
    skippedUnapproved: number;
    failures: number;
  };
};

export const BASELINE_CORE_PATHS = [
  ".z-mos",
  "bin",
  "cli",
  "contracts",
  "core",
  "governance",
  "trace",
  "docs",
  "tls",
  "scripts",
  "ai",
  "package.json",
  "package-lock.json",
  "tsconfig.json",
  "zmos-core.md",
  "LICENSE",
  ".gitignore",
];

export const PROTECTED_PATH_PREFIXES = [
  ".z-mos",
  "bin",
  "cli",
  "contracts",
  "core",
  "governance",
  "trace",
  "docs",
  "tls",
  "scripts",
  "ai",
  "dist",
  "node_modules",
  "package.json",
  "package-lock.json",
  "tsconfig.json",
  "zmos-core.md",
  "LICENSE",
  ".gitignore",
];

export const REMOVABLE_GENERATED_PREFIXES = [
  "test-execution-output",
  "tls-extract-test-001",
  "coverage",
  ".nyc_output",
  ".cache",
  ".tmp",
  "tmp",
];

const ROOT_LEVEL_REMOVABLE_FILE_PATTERNS = [
  /^\.DS_Store$/u,
  /\.log$/u,
  /\.tmp$/u,
  /^npm-debug\.log/u,
];

function isPathWithinRoot(rootDir: string, absolutePath: string): boolean {
  const relativePath = path.relative(rootDir, absolutePath);
  return relativePath !== "" && !relativePath.startsWith("..") && !path.isAbsolute(relativePath);
}

function normalizePath(relativePath: string): string {
  return relativePath.replace(/\\/gu, "/");
}

function matchesPrefix(relativePath: string, prefixes: string[]): boolean {
  const normalized = normalizePath(relativePath);
  return prefixes.some((prefix) => normalized === prefix || normalized.startsWith(`${prefix}/`));
}

function isProtectedPath(relativePath: string): boolean {
  return matchesPrefix(relativePath, PROTECTED_PATH_PREFIXES);
}

function isApprovedRemovablePath(relativePath: string): boolean {
  if (matchesPrefix(relativePath, REMOVABLE_GENERATED_PREFIXES)) {
    return true;
  }

  const fileName = path.basename(relativePath);
  return ROOT_LEVEL_REMOVABLE_FILE_PATTERNS.some((pattern) => pattern.test(fileName));
}

async function safeRemoveRelativePath(rootDir: string, relativePath: string): Promise<void> {
  if (isProtectedPath(relativePath)) {
    throw new Error(`Path is protected and cannot be removed: ${relativePath}`);
  }
  if (!isApprovedRemovablePath(relativePath)) {
    throw new Error(`Path is not approved for removal: ${relativePath}`);
  }

  const targetPath = path.resolve(rootDir, relativePath);
  if (!isPathWithinRoot(rootDir, targetPath)) {
    throw new Error(`Refusing to remove path outside root: ${relativePath}`);
  }

  await fs.rm(targetPath, { recursive: true, force: true });
}

export async function evaluateCoreBaseline(): Promise<CoreBaselineReport> {
  const rootDir = process.cwd();
  const entries = await fs.readdir(rootDir, { withFileTypes: true });
  const entryNames = entries.map((entry) => entry.name);
  const contaminants: CoreContaminant[] = [];

  for (const entry of entries) {
    const relativePath = normalizePath(entry.name);

    if (isProtectedPath(relativePath)) {
      continue;
    }

    if (isApprovedRemovablePath(relativePath)) {
      contaminants.push({
        path: relativePath,
        type: "approved-generated",
        approvedForRemoval: true,
        reason: "Matches approved generated/non-core removal policy.",
      });
      continue;
    }

    contaminants.push({
      path: relativePath,
      type: "unapproved-non-core",
      approvedForRemoval: false,
      reason: "Not part of canonical core baseline and not approved for auto-removal.",
    });
  }

  const presentCorePaths = BASELINE_CORE_PATHS.filter((corePath) => entryNames.includes(corePath));
  const missingCorePaths = BASELINE_CORE_PATHS.filter((corePath) => !entryNames.includes(corePath));

  const approvedGeneratedContaminants = contaminants.filter(
    (contaminant) => contaminant.type === "approved-generated",
  ).length;
  const unapprovedContaminants = contaminants.filter(
    (contaminant) => contaminant.type === "unapproved-non-core",
  ).length;

  return {
    rootDir,
    baselineCorePaths: BASELINE_CORE_PATHS,
    protectedPaths: PROTECTED_PATH_PREFIXES,
    removableGeneratedPaths: REMOVABLE_GENERATED_PREFIXES,
    presentCorePaths,
    missingCorePaths,
    contaminants,
    summary: {
      totalContaminants: contaminants.length,
      approvedGeneratedContaminants,
      unapprovedContaminants,
    },
  };
}

export async function cleanCoreContamination(
  report: CoreBaselineReport,
  options?: { dryRun?: boolean },
): Promise<CoreCleanResult> {
  const dryRun = options?.dryRun === true;
  const actions: CoreCleanAction[] = [];

  for (const contaminant of report.contaminants) {
    if (!contaminant.approvedForRemoval) {
      actions.push({
        path: contaminant.path,
        action: "skipped-unapproved",
        reason: contaminant.reason,
      });
      continue;
    }

    if (dryRun) {
      actions.push({
        path: contaminant.path,
        action: "would-remove",
        reason: "Dry-run mode enabled.",
      });
      continue;
    }

    try {
      await safeRemoveRelativePath(report.rootDir, contaminant.path);
      actions.push({
        path: contaminant.path,
        action: "removed",
        reason: "Removed approved generated/non-core artifact.",
      });
    } catch (error) {
      actions.push({
        path: contaminant.path,
        action: "failed",
        reason: error instanceof Error ? error.message : "Unknown removal error.",
      });
    }
  }

  return {
    dryRun,
    actions,
    summary: {
      removed: actions.filter((action) => action.action === "removed").length,
      wouldRemove: actions.filter((action) => action.action === "would-remove").length,
      skippedUnapproved: actions.filter((action) => action.action === "skipped-unapproved").length,
      failures: actions.filter((action) => action.action === "failed").length,
    },
  };
}
