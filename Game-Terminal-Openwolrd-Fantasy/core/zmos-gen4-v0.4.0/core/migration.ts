import { promises as fs } from "node:fs";
import * as path from "node:path";

import { evaluateMutationGuard } from "./mutation-guard.js";

export type MigrationSourceVersion = "v0.2.x";
export type MigrationTargetVersion = "evo1.0";

export type MigrationActionType =
  | "rename"
  | "move"
  | "create"
  | "rewrite"
  | "preserve"
  | "warning"
  | "blocker";

export type MigrationAction = {
  type: MigrationActionType;
  description: string;
  from?: string;
  to?: string;
};

export type MigrationInspection = {
  projectRoot: string;
  projectRelative: string;
  legacyStateExists: boolean;
  canonicalStateExists: boolean;
  dualStateConflict: boolean;
  rootTraceExists: boolean;
  legacyTraceExists: boolean;
  canonicalTraceExists: boolean;
  missingCanonicalFiles: string[];
  legacyReferences: string[];
  manifestState: {
    path: string;
    exists: boolean;
    lifecycleStatus: "active" | "freeze" | "archived" | "unknown";
    scopeConfigured: boolean;
  };
  warnings: string[];
  blockers: string[];
};

export type MigrationPlan = {
  actions: MigrationAction[];
  warnings: string[];
  blockers: string[];
};

export type MigrationApplyResult = {
  applied: boolean;
  actionsApplied: MigrationAction[];
  rewriteApplied: MigrationRewriteApplied[];
  warnings: string[];
  blockers: string[];
  guardReason: string | null;
};

export type MigrationVerifyResult = {
  canonicalStateExists: boolean;
  requiredFilesPresent: boolean;
  missingCanonicalFiles: string[];
  dualStateConflict: boolean;
  preservedLegacyStatePath: string | null;
  doctorStartImprovement: "not-enough-evidence" | "improved" | "unchanged";
};

export type MigrationExecutionResult = {
  source: MigrationSourceVersion;
  target: MigrationTargetVersion;
  dryRun: boolean;
  force: boolean;
  applyRewriteSafe: boolean;
  inspection: MigrationInspection;
  plan: MigrationPlan;
  apply: MigrationApplyResult;
  verify: MigrationVerifyResult;
  rewriteSummary: MigrationRewriteSummary;
};

export type MigrationExecutionOptions = {
  source: MigrationSourceVersion;
  target: MigrationTargetVersion;
  projectPath: string;
  dryRun: boolean;
  force: boolean;
  applyRewriteSafe: boolean;
};

export type MigrationRewriteCandidate = {
  file: string;
  eligible: boolean;
  reasons: string[];
  detectedPatterns: string[];
  plannedReplacements: number;
};

export type MigrationRewriteApplied = {
  file: string;
  replacements: number;
  patterns: string[];
};

export type MigrationRewriteSummary = {
  candidatesFound: number;
  eligibleCount: number;
  appliedCount: number;
  skippedCount: number;
  blockedCount: number;
  candidates: MigrationRewriteCandidate[];
  applied: MigrationRewriteApplied[];
};

const ROOT_DIR = process.cwd();

const CANONICAL_REQUIRED_FILES = [
  ".z-mos/zmos-manifest.json",
  ".z-mos/state/runtime-state.json",
  ".z-mos/node.json",
  ".z-mos/workflow-policy.json",
  ".z-mos/trace/runtime-trace.jsonl",
];

const REWRITE_ALLOWED_DIR_PREFIXES = [
  "core/",
  "cli/",
  "contracts/",
  "governance/",
  "trace/",
  "docs/standards/",
  "docs/governance/",
  ".z-mos/",
];

const REWRITE_IGNORED_DIRS = new Set([
  "node_modules",
  "dist",
  ".git",
  "coverage",
  ".nyc_output",
  ".cache",
  "tls/templates",
  "tls/modules",
  "tls/registry",
  "tls/schemas",
  "tls/docs",
]);

const REWRITE_ALLOWED_EXTENSIONS = new Set([".ts", ".js", ".json", ".md", ".txt", ".yml", ".yaml"]);

type SafeRewriteRule = {
  id: string;
  search: RegExp;
  replace: string;
};

const SAFE_REWRITE_RULES: SafeRewriteRule[] = [
  {
    id: "path-.zmos-slash",
    search: /\.zmos\//gu,
    replace: ".z-mos/",
  },
  {
    id: "quoted-.zmos-double",
    search: /"\.zmos"/gu,
    replace: '".z-mos"',
  },
  {
    id: "quoted-.zmos-single",
    search: /'\.zmos'/gu,
    replace: "'.z-mos'",
  },
  {
    id: "quoted-.zmos-backtick",
    search: /`\.zmos`/gu,
    replace: "`.z-mos`",
  },
];

function toPosix(input: string): string {
  return input.replace(/\\/gu, "/");
}

function isWithin(rootPath: string, targetPath: string): boolean {
  const relative = path.relative(rootPath, targetPath);
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function ensureDir(targetPath: string): Promise<void> {
  await fs.mkdir(targetPath, { recursive: true });
}

async function readJson(targetPath: string): Promise<Record<string, unknown> | null> {
  try {
    const raw = await fs.readFile(targetPath, "utf8");
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return null;
  }
}

async function writeJson(targetPath: string, value: Record<string, unknown>): Promise<void> {
  await fs.writeFile(targetPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function canonicalManifestSeed(projectName: string): Record<string, unknown> {
  return {
    repository: {
      name: projectName,
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
      updatedAt: new Date().toISOString().slice(0, 10),
      reason: "migration-default",
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
  };
}

function canonicalSessionSeed(projectName: string): Record<string, unknown> {
  return {
    workspace: projectName,
    framework: "Z-MOS",
    sessionState: "bootstrap",
    activeCommand: null,
    lastReport: null,
  };
}

function canonicalNodeSeed(): Record<string, unknown> {
  return {
    node_id: "pc-ai-node",
    node_role: "execution-node",
    runtime: "nodejs-local",
    capabilities: ["cli-execution", "diagnostics", "ai-advisory"],
  };
}

function canonicalWorkflowPolicySeed(): Record<string, unknown> {
  return {
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
  };
}

function hasAllowedRewriteScope(relativePath: string): boolean {
  return REWRITE_ALLOWED_DIR_PREFIXES.some((prefix) => relativePath.startsWith(prefix));
}

function shouldIgnoreRewriteDirectory(relativePath: string): boolean {
  return Array.from(REWRITE_IGNORED_DIRS).some(
    (prefix) => relativePath === prefix || relativePath.startsWith(`${prefix}/`),
  );
}

function countPatternMatches(content: string, rule: SafeRewriteRule): number {
  const matches = content.match(rule.search);
  return matches ? matches.length : 0;
}

async function inspectRewriteCandidates(projectRoot: string): Promise<MigrationRewriteCandidate[]> {
  const candidates: MigrationRewriteCandidate[] = [];
  const stack = [projectRoot];

  while (stack.length > 0 && candidates.length < 120) {
    const current = stack.pop();
    if (!current) {
      continue;
    }

    const entries = await fs.readdir(current, { withFileTypes: true });
    for (const entry of entries) {
      const entryPath = path.join(current, entry.name);
      const relative = toPosix(path.relative(projectRoot, entryPath));

      if (entry.isDirectory()) {
        if (shouldIgnoreRewriteDirectory(relative)) {
          continue;
        }
        stack.push(entryPath);
        continue;
      }

      if (!entry.isFile()) {
        continue;
      }

      const ext = path.extname(entry.name).toLowerCase();
      if (!REWRITE_ALLOWED_EXTENSIONS.has(ext)) {
        continue;
      }

      let content = "";
      try {
        content = await fs.readFile(entryPath, "utf8");
      } catch {
        continue;
      }

      if (!content.includes(".zmos")) {
        continue;
      }

      const detectedPatterns: string[] = [];
      let plannedReplacements = 0;
      for (const rule of SAFE_REWRITE_RULES) {
        const count = countPatternMatches(content, rule);
        if (count > 0) {
          detectedPatterns.push(rule.id);
          plannedReplacements += count;
        }
      }

      const reasons: string[] = [];
      let eligible = true;

      if (!hasAllowedRewriteScope(relative)) {
        eligible = false;
        reasons.push("outside allowed rewrite scope");
      }
      if (plannedReplacements === 0) {
        eligible = false;
        reasons.push("no deterministic safe rewrite pattern match");
      }

      candidates.push({
        file: relative,
        eligible,
        reasons,
        detectedPatterns,
        plannedReplacements,
      });
    }
  }

  return candidates.sort((a, b) => a.file.localeCompare(b.file));
}

async function inspectMigrationState(
  source: MigrationSourceVersion,
  target: MigrationTargetVersion,
  projectPath: string,
): Promise<MigrationInspection> {
  const resolvedProjectRoot = path.resolve(ROOT_DIR, projectPath);
  const projectRelative = toPosix(path.relative(ROOT_DIR, resolvedProjectRoot) || ".");

  const warnings: string[] = [];
  const blockers: string[] = [];

  if (source !== "v0.2.x") {
    blockers.push(`Unsupported migration source: ${source}`);
  }
  if (target !== "evo1.0") {
    blockers.push(`Unsupported migration target: ${target}`);
  }

  if (!(await pathExists(resolvedProjectRoot))) {
    blockers.push(`Project path does not exist: ${resolvedProjectRoot}`);
  } else if (!isWithin(ROOT_DIR, resolvedProjectRoot)) {
    blockers.push("Project path must stay inside current repository scope.");
  }

  const legacyStatePath = path.join(resolvedProjectRoot, ".zmos");
  const canonicalStatePath = path.join(resolvedProjectRoot, ".z-mos");
  const legacyStateExists = await pathExists(legacyStatePath);
  const canonicalStateExists = await pathExists(canonicalStatePath);
  const dualStateConflict = legacyStateExists && canonicalStateExists;

  const rootTracePath = path.join(resolvedProjectRoot, "runtime-trace.jsonl");
  const legacyTracePath = path.join(legacyStatePath, "trace", "runtime-trace.jsonl");
  const canonicalTracePath = path.join(canonicalStatePath, "trace", "runtime-trace.jsonl");

  const rootTraceExists = await pathExists(rootTracePath);
  const legacyTraceExists = await pathExists(legacyTracePath);
  const canonicalTraceExists = await pathExists(canonicalTracePath);

  const missingCanonicalFiles: string[] = [];
  for (const requiredFile of CANONICAL_REQUIRED_FILES) {
    const targetPath = path.join(resolvedProjectRoot, requiredFile);
    if (!(await pathExists(targetPath))) {
      missingCanonicalFiles.push(requiredFile);
    }
  }

  const canonicalManifestPath = path.join(canonicalStatePath, "zmos-manifest.json");
  const canonicalManifest = await readJson(canonicalManifestPath);

  let lifecycleStatus: "active" | "freeze" | "archived" | "unknown" = "unknown";
  let scopeConfigured = false;
  if (canonicalManifest) {
    const lifecycle = canonicalManifest.lifecycle as Record<string, unknown> | undefined;
    const lifecycleValue = lifecycle?.status;
    if (lifecycleValue === "active" || lifecycleValue === "freeze" || lifecycleValue === "archived") {
      lifecycleStatus = lifecycleValue;
    }

    const scope = canonicalManifest.scope as { mutation?: { allowedPaths?: unknown[] } } | undefined;
    scopeConfigured =
      Array.isArray(scope?.mutation?.allowedPaths) && scope?.mutation?.allowedPaths.length > 0;
  }

  if (!legacyStateExists && !canonicalStateExists) {
    warnings.push("Neither .zmos nor .z-mos state exists; migration will bootstrap canonical state.");
  }

  if (dualStateConflict) {
    warnings.push("Dual state conflict detected: .zmos and .z-mos both exist.");
  }

  if (canonicalStateExists && lifecycleStatus === "unknown") {
    warnings.push("Canonical manifest lifecycle.status is missing/invalid.");
  }

  if (canonicalStateExists && !scopeConfigured) {
    warnings.push("Canonical manifest scope.mutation.allowedPaths is missing/empty.");
  }

  const rewriteCandidates = await inspectRewriteCandidates(resolvedProjectRoot);
  const legacyReferences = rewriteCandidates.map((entry) => entry.file);

  return {
    projectRoot: resolvedProjectRoot,
    projectRelative,
    legacyStateExists,
    canonicalStateExists,
    dualStateConflict,
    rootTraceExists,
    legacyTraceExists,
    canonicalTraceExists,
    missingCanonicalFiles,
    legacyReferences,
    manifestState: {
      path: toPosix(path.relative(resolvedProjectRoot, canonicalManifestPath)),
      exists: canonicalManifest !== null,
      lifecycleStatus,
      scopeConfigured,
    },
    warnings,
    blockers,
  };
}

function buildMigrationPlan(
  inspection: MigrationInspection,
  rewriteCandidates: MigrationRewriteCandidate[],
  force: boolean,
): MigrationPlan {
  const actions: MigrationAction[] = [];
  const warnings = [...inspection.warnings];
  const blockers = [...inspection.blockers];

  if (inspection.dualStateConflict && !force) {
    blockers.push("Dual state conflict requires --force to preserve legacy state safely before apply.");
  }

  if (inspection.legacyStateExists && !inspection.canonicalStateExists) {
    actions.push({
      type: "rename",
      description: "Promote legacy state directory to EVO canonical state directory.",
      from: ".zmos",
      to: ".z-mos",
    });
  }

  if (inspection.dualStateConflict) {
    const preserveName = `.zmos.preserved-${Date.now()}`;
    actions.push({
      type: "preserve",
      description: "Preserve legacy state directory to remove unsafe dual-state conflict.",
      from: ".zmos",
      to: preserveName,
    });
  }

  if (!inspection.canonicalStateExists && !inspection.legacyStateExists) {
    actions.push({
      type: "create",
      description: "Create canonical .z-mos directory structure from seed defaults.",
      to: ".z-mos",
    });
  }

  for (const missingFile of inspection.missingCanonicalFiles) {
    actions.push({
      type: "create",
      description: "Create missing canonical file.",
      to: missingFile,
    });
  }

  if (inspection.rootTraceExists) {
    actions.push({
      type: "move",
      description: "Normalize root runtime trace into canonical trace path (copy+append, preserve source).",
      from: "runtime-trace.jsonl",
      to: ".z-mos/trace/runtime-trace.jsonl",
    });
  }

  if (inspection.legacyTraceExists) {
    actions.push({
      type: "move",
      description: "Normalize legacy trace into canonical trace path (copy+append, preserve source).",
      from: ".zmos/trace/runtime-trace.jsonl",
      to: ".z-mos/trace/runtime-trace.jsonl",
    });
  }

  if (inspection.manifestState.exists) {
    if (inspection.manifestState.lifecycleStatus === "unknown") {
      actions.push({
        type: "rewrite",
        description: "Backfill canonical lifecycle contract in manifest.",
        from: ".z-mos/zmos-manifest.json",
        to: ".z-mos/zmos-manifest.json",
      });
    }
    if (!inspection.manifestState.scopeConfigured) {
      actions.push({
        type: "rewrite",
        description: "Backfill canonical scope.mutation contract in manifest.",
        from: ".z-mos/zmos-manifest.json",
        to: ".z-mos/zmos-manifest.json",
      });
    }
  }

  for (const candidate of rewriteCandidates) {
    if (candidate.eligible) {
      actions.push({
        type: "warning",
        description: `Safe rewrite eligible: ${candidate.file} (planned replacements=${candidate.plannedReplacements})`,
      });
    } else {
      actions.push({
        type: "warning",
        description: `Rewrite skipped: ${candidate.file} (${candidate.reasons.join(", ") || "not enough evidence"})`,
      });
    }
  }

  if (actions.length === 0 && blockers.length === 0) {
    warnings.push("No migration actions required; state appears already aligned to EVO canonical baseline.");
  }

  // Keep deterministic action ordering for predictable dry-run output.
  actions.sort((a, b) => a.type.localeCompare(b.type) || (a.to || "").localeCompare(b.to || ""));

  return { actions, warnings, blockers };
}

async function appendTextIfMissing(targetPath: string, content: string): Promise<void> {
  if (!(await pathExists(targetPath))) {
    await ensureDir(path.dirname(targetPath));
    await fs.writeFile(targetPath, content, "utf8");
    return;
  }

  const existing = await fs.readFile(targetPath, "utf8");
  if (!existing.includes(content.trim())) {
    const next = `${existing.trimEnd()}\n${content.trim()}\n`;
    await fs.writeFile(targetPath, next, "utf8");
  }
}

async function ensureCanonicalSeeds(projectRoot: string): Promise<void> {
  const projectName = path.basename(projectRoot);
  const canonicalRoot = path.join(projectRoot, ".z-mos");
  const stateDir = path.join(canonicalRoot, "state");
  const traceDir = path.join(canonicalRoot, "trace");

  await ensureDir(canonicalRoot);
  await ensureDir(stateDir);
  await ensureDir(traceDir);

  const manifestPath = path.join(canonicalRoot, "zmos-manifest.json");
  const sessionPath = path.join(stateDir, "runtime-state.json");
  const nodePath = path.join(canonicalRoot, "node.json");
  const workflowPolicyPath = path.join(canonicalRoot, "workflow-policy.json");
  const tracePath = path.join(traceDir, "runtime-trace.jsonl");

  if (!(await pathExists(manifestPath))) {
    await writeJson(manifestPath, canonicalManifestSeed(projectName));
  }
  if (!(await pathExists(sessionPath))) {
    await writeJson(sessionPath, canonicalSessionSeed(projectName));
  }
  if (!(await pathExists(nodePath))) {
    await writeJson(nodePath, canonicalNodeSeed());
  }
  if (!(await pathExists(workflowPolicyPath))) {
    await writeJson(workflowPolicyPath, canonicalWorkflowPolicySeed());
  }
  if (!(await pathExists(tracePath))) {
    await fs.writeFile(tracePath, "", "utf8");
  }

  const existingManifest = await readJson(manifestPath);
  if (existingManifest) {
    const normalized = { ...existingManifest };

    const workspace = (normalized.workspace as Record<string, unknown> | undefined) || {};
    workspace.root = ".";
    workspace.stateDir = ".z-mos/state";
    workspace.traceDir = ".z-mos/trace";
    normalized.workspace = workspace;

    const lifecycle = (normalized.lifecycle as Record<string, unknown> | undefined) || {};
    const lifecycleStatus = lifecycle.status;
    if (lifecycleStatus !== "active" && lifecycleStatus !== "freeze" && lifecycleStatus !== "archived") {
      lifecycle.status = "active";
      lifecycle.reason = "migration-normalization";
      lifecycle.updatedAt = new Date().toISOString().slice(0, 10);
    }
    normalized.lifecycle = lifecycle;

    const scope = (normalized.scope as Record<string, unknown> | undefined) || {};
    const mutation = (scope.mutation as Record<string, unknown> | undefined) || {};
    const allowedPaths = Array.isArray(mutation.allowedPaths)
      ? mutation.allowedPaths.filter((v): v is string => typeof v === "string" && v.length > 0)
      : [];
    if (allowedPaths.length === 0) {
      mutation.allowedPaths = [".", "tls/templates", "tls/registry", ".z-mos"];
    }
    const protectedPaths = Array.isArray(mutation.protectedPaths)
      ? mutation.protectedPaths.filter((v): v is string => typeof v === "string" && v.length > 0)
      : [];
    if (protectedPaths.length === 0) {
      mutation.protectedPaths = [
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
      ];
    }
    if (mutation.mode !== "strict" && mutation.mode !== "warn") {
      mutation.mode = "strict";
    }
    scope.mutation = mutation;
    normalized.scope = scope;

    await writeJson(manifestPath, normalized);
  }
}

async function copyTraceIntoCanonical(projectRoot: string, fromRelativePath: string): Promise<void> {
  const sourcePath = path.join(projectRoot, fromRelativePath);
  if (!(await pathExists(sourcePath))) {
    return;
  }
  const canonicalTracePath = path.join(projectRoot, ".z-mos", "trace", "runtime-trace.jsonl");
  const content = await fs.readFile(sourcePath, "utf8");
  if (content.trim().length === 0) {
    return;
  }
  await appendTextIfMissing(canonicalTracePath, content);
}

function applyRulesToContent(content: string): {
  next: string;
  replacements: number;
  patterns: string[];
} {
  let next = content;
  let replacements = 0;
  const patterns: string[] = [];

  for (const rule of SAFE_REWRITE_RULES) {
    const count = countPatternMatches(next, rule);
    if (count > 0) {
      next = next.replace(rule.search, rule.replace);
      replacements += count;
      patterns.push(rule.id);
    }
  }

  return { next, replacements, patterns };
}

async function applySafeRewrites(
  projectRoot: string,
  rewriteCandidates: MigrationRewriteCandidate[],
): Promise<MigrationRewriteApplied[]> {
  const applied: MigrationRewriteApplied[] = [];

  for (const candidate of rewriteCandidates) {
    if (!candidate.eligible || candidate.plannedReplacements <= 0) {
      continue;
    }

    const absolutePath = path.join(projectRoot, candidate.file);
    let content = "";
    try {
      content = await fs.readFile(absolutePath, "utf8");
    } catch {
      continue;
    }

    const rewrite = applyRulesToContent(content);
    if (rewrite.replacements <= 0 || rewrite.next === content) {
      continue;
    }

    await fs.writeFile(absolutePath, rewrite.next, "utf8");
    applied.push({
      file: candidate.file,
      replacements: rewrite.replacements,
      patterns: rewrite.patterns,
    });
  }

  return applied;
}

async function applyMigrationPlan(
  inspection: MigrationInspection,
  plan: MigrationPlan,
  rewriteCandidates: MigrationRewriteCandidate[],
  dryRun: boolean,
  force: boolean,
  applyRewriteSafe: boolean,
): Promise<MigrationApplyResult> {
  if (dryRun) {
    return {
      applied: false,
      actionsApplied: [],
      rewriteApplied: [],
      warnings: [...plan.warnings],
      blockers: [...plan.blockers],
      guardReason: null,
    };
  }

  if (plan.blockers.length > 0) {
    return {
      applied: false,
      actionsApplied: [],
      rewriteApplied: [],
      warnings: [...plan.warnings],
      blockers: [...plan.blockers],
      guardReason: null,
    };
  }

  const targetPrefixes = new Set<string>();
  for (const action of plan.actions) {
    if (action.to) {
      const first = action.to.split("/").filter(Boolean)[0];
      if (first) {
        targetPrefixes.add(
          inspection.projectRelative === "." ? first : `${inspection.projectRelative}/${first}`,
        );
      }
    }
    if (action.from) {
      const first = action.from.split("/").filter(Boolean)[0];
      if (first) {
        targetPrefixes.add(
          inspection.projectRelative === "." ? first : `${inspection.projectRelative}/${first}`,
        );
      }
    }
  }

  if (targetPrefixes.size === 0) {
    targetPrefixes.add(inspection.projectRelative === "." ? ".z-mos" : `${inspection.projectRelative}/.z-mos`);
  }

  const guard = await evaluateMutationGuard({
    command: "zcl migrate",
    targetPaths: Array.from(targetPrefixes),
    allowProtectedPrefixes: [".z-mos", `${inspection.projectRelative}/.z-mos`],
  });

  if (!guard.allowed) {
    return {
      applied: false,
      actionsApplied: [],
      rewriteApplied: [],
      warnings: [...plan.warnings, ...guard.warnings],
      blockers: [...plan.blockers, guard.reason],
      guardReason: guard.reason,
    };
  }

  const applied: MigrationAction[] = [];
  const projectRoot = inspection.projectRoot;
  const legacyStatePath = path.join(projectRoot, ".zmos");
  const canonicalStatePath = path.join(projectRoot, ".z-mos");

  if (inspection.legacyStateExists && !inspection.canonicalStateExists) {
    await fs.rename(legacyStatePath, canonicalStatePath);
    applied.push({
      type: "rename",
      description: "Renamed legacy state directory to canonical .z-mos.",
      from: ".zmos",
      to: ".z-mos",
    });
  }

  if (inspection.dualStateConflict && force && (await pathExists(legacyStatePath))) {
    const preservedName = `.zmos.preserved-${Date.now()}`;
    await fs.rename(legacyStatePath, path.join(projectRoot, preservedName));
    applied.push({
      type: "preserve",
      description: "Preserved legacy state directory to resolve dual-state conflict.",
      from: ".zmos",
      to: preservedName,
    });
  }

  await ensureCanonicalSeeds(projectRoot);

  for (const missingFile of inspection.missingCanonicalFiles) {
    applied.push({
      type: "create",
      description: "Created missing canonical file during seed normalization.",
      to: missingFile,
    });
  }

  if (inspection.rootTraceExists) {
    await copyTraceIntoCanonical(projectRoot, "runtime-trace.jsonl");
    applied.push({
      type: "move",
      description: "Normalized root runtime trace into canonical trace path (source preserved).",
      from: "runtime-trace.jsonl",
      to: ".z-mos/trace/runtime-trace.jsonl",
    });
  }

  if (inspection.legacyTraceExists) {
    await copyTraceIntoCanonical(projectRoot, ".zmos/trace/runtime-trace.jsonl");
    applied.push({
      type: "move",
      description: "Normalized legacy trace into canonical trace path (source preserved when available).",
      from: ".zmos/trace/runtime-trace.jsonl",
      to: ".z-mos/trace/runtime-trace.jsonl",
    });
  }

  if (inspection.manifestState.lifecycleStatus === "unknown" || !inspection.manifestState.scopeConfigured) {
    applied.push({
      type: "rewrite",
      description: "Normalized canonical manifest lifecycle/scope contract.",
      from: ".z-mos/zmos-manifest.json",
      to: ".z-mos/zmos-manifest.json",
    });
  }

  let rewrittenFiles: MigrationRewriteApplied[] = [];
  if (applyRewriteSafe) {
    rewrittenFiles = await applySafeRewrites(projectRoot, rewriteCandidates);
    for (const rewrittenFile of rewrittenFiles) {
      applied.push({
        type: "rewrite",
        description: `Applied safe rewrite patterns [${rewrittenFile.patterns.join(", ")}], replacements=${rewrittenFile.replacements}.`,
        from: rewrittenFile.file,
        to: rewrittenFile.file,
      });
    }
  }

  return {
    applied: true,
    actionsApplied: applied,
    rewriteApplied: rewrittenFiles,
    warnings: [...plan.warnings],
    blockers: [...plan.blockers],
    guardReason: null,
  };
}

async function verifyMigrationState(projectRoot: string): Promise<MigrationVerifyResult> {
  const canonicalStatePath = path.join(projectRoot, ".z-mos");
  const legacyStatePath = path.join(projectRoot, ".zmos");
  const canonicalStateExists = await pathExists(canonicalStatePath);
  const legacyStateExists = await pathExists(legacyStatePath);

  const missingCanonicalFiles: string[] = [];
  for (const requiredFile of CANONICAL_REQUIRED_FILES) {
    const requiredPath = path.join(projectRoot, requiredFile);
    if (!(await pathExists(requiredPath))) {
      missingCanonicalFiles.push(requiredFile);
    }
  }

  const entries = await fs.readdir(projectRoot, { withFileTypes: true });
  const preservedLegacy = entries.find(
    (entry) => entry.isDirectory() && entry.name.startsWith(".zmos.preserved-"),
  );

  let doctorStartImprovement: MigrationVerifyResult["doctorStartImprovement"] = "not-enough-evidence";
  if (projectRoot === ROOT_DIR) {
    doctorStartImprovement = canonicalStateExists && missingCanonicalFiles.length === 0 ? "improved" : "unchanged";
  }

  return {
    canonicalStateExists,
    requiredFilesPresent: missingCanonicalFiles.length === 0,
    missingCanonicalFiles,
    dualStateConflict: legacyStateExists && canonicalStateExists,
    preservedLegacyStatePath: preservedLegacy ? preservedLegacy.name : null,
    doctorStartImprovement,
  };
}

function buildRewriteSummary(args: {
  candidates: MigrationRewriteCandidate[];
  applyRewriteSafe: boolean;
  dryRun: boolean;
  applied: MigrationRewriteApplied[];
}): MigrationRewriteSummary {
  const eligibleCount = args.candidates.filter((entry) => entry.eligible).length;
  const blockedCount = args.candidates.filter((entry) => !entry.eligible).length;
  const appliedCount = args.applied.length;

  let skippedCount = 0;
  if (!args.applyRewriteSafe || args.dryRun) {
    skippedCount = eligibleCount;
  } else {
    skippedCount = Math.max(0, eligibleCount - appliedCount);
  }

  return {
    candidatesFound: args.candidates.length,
    eligibleCount,
    appliedCount,
    skippedCount,
    blockedCount,
    candidates: args.candidates,
    applied: args.applied,
  };
}

export async function executeMigration(
  options: MigrationExecutionOptions,
): Promise<MigrationExecutionResult> {
  const inspection = await inspectMigrationState(options.source, options.target, options.projectPath);
  const rewriteCandidates = await inspectRewriteCandidates(inspection.projectRoot);
  const plan = buildMigrationPlan(inspection, rewriteCandidates, options.force);
  const apply = await applyMigrationPlan(
    inspection,
    plan,
    rewriteCandidates,
    options.dryRun,
    options.force,
    options.applyRewriteSafe,
  );
  const verify = await verifyMigrationState(inspection.projectRoot);
  const rewriteSummary = buildRewriteSummary({
    candidates: rewriteCandidates,
    applyRewriteSafe: options.applyRewriteSafe,
    dryRun: options.dryRun,
    applied: apply.rewriteApplied,
  });

  return {
    source: options.source,
    target: options.target,
    dryRun: options.dryRun,
    force: options.force,
    applyRewriteSafe: options.applyRewriteSafe,
    inspection,
    plan,
    apply,
    verify,
    rewriteSummary,
  };
}
