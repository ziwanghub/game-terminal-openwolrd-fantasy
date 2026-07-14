import { promises as fs } from "node:fs";
import * as path from "node:path";
export type LoadDataType =
  | "new-room-prompt"
  | "zmos-usage-prompt"
  | "zmos-master"
  | "team-onboarding";

export type LoadDataMode = "full" | "compact";

export type LoadDataOptions = {
  type: LoadDataType;
  mode?: LoadDataMode;
  projectPath?: string;
};

type ManifestLifecycleStatus = "active" | "freeze" | "archived" | "stabilized" | "unknown";

type ManifestSnapshot = {
  repositoryName: string;
  framework: string;
  version: string;
  lifecycleStatus: ManifestLifecycleStatus;
  lifecycleReason: string;
  scopeMode: string;
  scopeAllowedPaths: string[];
  scopeProtectedPaths: string[];
};

type LoadDataContext = {
  projectRoot: string;
  projectRelative: string;
  manifest: ManifestSnapshot;
  docAvailability: Record<string, boolean>;
  structure: string[];
  hasBehavior: boolean;
  hasMetrics: boolean;
  hasSnapshot: boolean;
};

const ZMOS_DOC_PATHS = {
  resume: path.join("docs", "zmos", "AI-RESUME-PROMPT.md"),
  taskTemplate: path.join("docs", "zmos", "ZMOS-TASK-TEMPLATE.md"),
  guard: path.join("docs", "zmos", "AI-GUARD-PROMPT.md"),
  communicationStandard: path.join("docs", "standards", "ZMOS-COMMUNICATION-STANDARD.md"),
  migrationStandard: path.join("docs", "standards", "ZMOS-LEGACY-MIGRATION-PLAN.md"),
  resumptionBrief: path.join("docs", "zmos", "RESUMPTION-BRIEF-PHASE2.md"),
  aiGuide: path.join("docs", "zmos", "zmos_ai_guide.md"),
};

async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

function toPosix(input: string): string {
  return input.replace(/\\/gu, "/");
}

function normalizeLifecycleStatus(value: unknown): ManifestLifecycleStatus {
  if (value === "active" || value === "freeze" || value === "archived" || value === "stabilized") {
    return value;
  }
  return "unknown";
}

function ensureString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim().length > 0 ? value : fallback;
}

function ensureStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter((entry): entry is string => typeof entry === "string" && entry.trim().length > 0)
    .map((entry) => entry.trim());
}

async function readManifestSnapshot(projectRoot: string): Promise<ManifestSnapshot> {
  const fallback: ManifestSnapshot = {
    repositoryName: "not enough evidence to conclude",
    framework: "not enough evidence to conclude",
    version: "not enough evidence to conclude",
    lifecycleStatus: "unknown",
    lifecycleReason: "not enough evidence to conclude",
    scopeMode: "not enough evidence to conclude",
    scopeAllowedPaths: [],
    scopeProtectedPaths: [],
  };

  const manifestPath = path.join(projectRoot, ".z-mos", "zmos-manifest.json");
  if (!(await pathExists(manifestPath))) {
    return fallback;
  }

  try {
    const raw = await fs.readFile(manifestPath, "utf8");
    const parsed = JSON.parse(raw) as Record<string, unknown>;

    const repository = (parsed.repository as Record<string, unknown> | undefined) || {};
    const lifecycle = (parsed.lifecycle as Record<string, unknown> | undefined) || {};
    const scope = (parsed.scope as Record<string, unknown> | undefined) || {};
    const mutationScope = (scope.mutation as Record<string, unknown> | undefined) || {};

    return {
      repositoryName: ensureString(repository.name, fallback.repositoryName),
      framework: ensureString(repository.framework, fallback.framework),
      version: ensureString(repository.version, fallback.version),
      lifecycleStatus: normalizeLifecycleStatus(lifecycle.status),
      lifecycleReason: ensureString(lifecycle.reason, fallback.lifecycleReason),
      scopeMode: ensureString(mutationScope.mode, fallback.scopeMode),
      scopeAllowedPaths: ensureStringArray(mutationScope.allowedPaths),
      scopeProtectedPaths: ensureStringArray(mutationScope.protectedPaths),
    };
  } catch {
    return fallback;
  }
}

async function resolveDocAvailability(projectRoot: string): Promise<Record<string, boolean>> {
  return {
    [ZMOS_DOC_PATHS.resume]: await pathExists(path.join(projectRoot, ZMOS_DOC_PATHS.resume)),
    [ZMOS_DOC_PATHS.taskTemplate]: await pathExists(path.join(projectRoot, ZMOS_DOC_PATHS.taskTemplate)),
    [ZMOS_DOC_PATHS.guard]: await pathExists(path.join(projectRoot, ZMOS_DOC_PATHS.guard)),
    [ZMOS_DOC_PATHS.communicationStandard]: await pathExists(
      path.join(projectRoot, ZMOS_DOC_PATHS.communicationStandard),
    ),
    [ZMOS_DOC_PATHS.migrationStandard]: await pathExists(
      path.join(projectRoot, ZMOS_DOC_PATHS.migrationStandard),
    ),
    [ZMOS_DOC_PATHS.resumptionBrief]: await pathExists(
      path.join(projectRoot, ZMOS_DOC_PATHS.resumptionBrief),
    ),
    [ZMOS_DOC_PATHS.aiGuide]: await pathExists(
      path.join(projectRoot, ZMOS_DOC_PATHS.aiGuide),
    ),
  };
}

async function resolveRootStructure(projectRoot: string): Promise<string[]> {
  try {
    const entries = await fs.readdir(projectRoot, { withFileTypes: true });
    return entries
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name)
      .sort((a, b) => a.localeCompare(b));
  } catch {
    return [];
  }
}

function hasDir(structure: string[], dirName: string): string {
  return structure.includes(dirName) ? "present" : "not enough evidence to conclude";
}

async function resolveLoadDataContext(options?: {
  projectPath?: string;
}): Promise<LoadDataContext> {
  const runtimeRoot = process.cwd();
  const projectRoot = path.resolve(runtimeRoot, options?.projectPath || ".");
  const projectRelative = toPosix(path.relative(runtimeRoot, projectRoot) || ".");

  const [manifest, docAvailability, structure] = await Promise.all([
    readManifestSnapshot(projectRoot),
    resolveDocAvailability(projectRoot),
    resolveRootStructure(projectRoot),
  ]);

  const hasBehavior = await pathExists(path.join(projectRoot, ".z-mos", "behavior", "decisions"));
  const hasMetrics = await pathExists(path.join(projectRoot, ".z-mos", "metrics", "token-baseline.jsonl"));
  const hasSnapshot = await pathExists(path.join(projectRoot, ".z-mos", "state", "phase-snapshot.json"));

  return {
    projectRoot,
    projectRelative,
    manifest,
    docAvailability,
    structure,
    hasBehavior,
    hasMetrics,
    hasSnapshot,
  };
}

export async function buildNewRoomPrompt(options?: { projectPath?: string }): Promise<string> {
  const { projectRelative, manifest, docAvailability, structure, hasBehavior, hasMetrics, hasSnapshot } = await resolveLoadDataContext(
    options,
  );

  const lines = [
    "Z-MOS NEW ROOM PROMPT",
    "",
    "1. System Overview",
    "- This is NOT a new project.",
    "- This workspace is under Z-MOS governance.",
    "- Continue current project state; do not restart framework setup.",
    `- Project root in current session: ${projectRelative}`,
    "",
    "2. Current Z-MOS Status",
    "- Z-MOS EVO is in active operational use.",
    "- Core safety layer exists (lifecycle + scope + mutation guard).",
    "- Migration layer exists (`zcl migrate --from v0.2.x --to evo1.0`).",
    "- AI operation docs are available for controlled execution:",
    `  - ${ZMOS_DOC_PATHS.resume}: ${docAvailability[ZMOS_DOC_PATHS.resume] ? "available" : "not enough evidence to conclude"}`,
    `  - ${ZMOS_DOC_PATHS.taskTemplate}: ${docAvailability[ZMOS_DOC_PATHS.taskTemplate] ? "available" : "not enough evidence to conclude"}`,
    `  - ${ZMOS_DOC_PATHS.guard}: ${docAvailability[ZMOS_DOC_PATHS.guard] ? "available" : "not enough evidence to conclude"}`,
    `  - ${ZMOS_DOC_PATHS.resumptionBrief}: ${docAvailability[ZMOS_DOC_PATHS.resumptionBrief] ? "available" : "not enough evidence to conclude"}`,
    `  - ${ZMOS_DOC_PATHS.aiGuide}: ${docAvailability[ZMOS_DOC_PATHS.aiGuide] ? "available" : "not enough evidence to conclude"}`,
    "- Do not expand Z-MOS framework unless a real pain point is evidenced.",
    "",
    "3. Current Objective",
    "- Use Z-MOS to continue project development from current state.",
    "- Phase 1 Decision-Aware rules are ACTIVE. Never bypass BIL or Preflight.",
    "- Do not redesign the framework.",
    "- Execute scoped tasks with evidence and validation.",
    "",
    "4. Project Structure",
    `- .z-mos/: ${hasDir(structure, ".z-mos")}`,
    `- apps/: ${hasDir(structure, "apps")}`,
    `- modules/: ${hasDir(structure, "modules")}`,
    `- docs/: ${hasDir(structure, "docs")}`,
    "- Respect existing structure and mutate only in explicit task scope.",
    "",
    "5. Execution Flow",
    "- Step 1: run doctor (`node ./bin/zcl.js doctor`).",
    "- Step 2: run migrate dry-run if legacy risk exists (`node ./bin/zcl.js migrate --from v0.2.x --to evo1.0 --dry-run`).",
    "- Step 4: run preflight check contextually (`node ./bin/zcl.js preflight --check-command='...'`).",
    "- Step 5: for risky mutations, create BIL record first (`node ./bin/zcl.js behavior record --auto-fill`).",
    "- Step 6: execute only within approved scope.",
    "- Step 7: record token usage metrics (`node ./bin/zcl.js metrics record --task ... --type ... --size ...`).",
    "- Step 8: verify behavior and report evidence.",
    "",
    "6. Team Communication Standard",
    "- Use Z-MOS TASK BRIEF format.",
    "- Scope is REQUIRED.",
    "- Freeze is REQUIRED.",
    "- Report must include: Files Changed / What Was Done / Validation / Limitations / Next Step.",
    "",
    "7. Safety Rules",
    "- Never modify `.z-mos/` manually.",
    "- Never bypass migration when legacy `.zmos` state is detected.",
    "- Never mutate outside explicit scope.",
    "- Never mutate freeze/archived lifecycle projects.",
    "",
    "8. AI Drift Rule",
    "- If scope drifts or assumptions become uncertain: STOP.",
    "- Reload Z-MOS context from manifest + AI operation docs.",
    "- Re-align scope/freeze/lifecycle before continuing.",
    "",
    "9. Final Instruction",
    "- Continue project.",
    "- Do not restart.",
    "- Do not redesign.",
    "- Work within Z-MOS rules.",
    "",
    "Runtime Snapshot",
    `- repository: ${manifest.repositoryName}`,
    `- framework: ${manifest.framework}`,
    `- version: ${manifest.version}`,
    `- lifecycle.status: ${manifest.lifecycleStatus}`,
    `- lifecycle.reason: ${manifest.lifecycleReason}`,
    `- behavior intelligence enabled: ${hasBehavior ? "yes" : "no"}`,
    `- metrics tracking enabled: ${hasMetrics ? "yes" : "no"}`,
    `- phase 1 snapshot present: ${hasSnapshot ? "yes" : "no"}`,
    `- scope.mode: ${manifest.scopeMode}`,
    `- standards: ${docAvailability[ZMOS_DOC_PATHS.communicationStandard] ? "available" : "not enough evidence to conclude"}`,
    `- migration standard: ${docAvailability[ZMOS_DOC_PATHS.migrationStandard] ? "available" : "not enough evidence to conclude"}`,
  ];

  return lines.join("\n");
}

export async function buildZmosUsagePrompt(options?: {
  projectPath?: string;
}): Promise<string> {
  const { projectRelative, manifest, docAvailability, structure, hasBehavior, hasMetrics, hasSnapshot } = await resolveLoadDataContext(
    options,
  );

  const lines = [
    "Z-MOS USAGE PROMPT",
    "",
    "1. Z-MOS system identity",
    "- You are operating inside a Z-MOS governed project.",
    "- Z-MOS is the execution control layer; do not bypass it.",
    "- Governance sources: manifest, standards, task template, and guard prompt.",
    "",
    "2. project continuation rule",
    "- This is NOT a new project.",
    "- Continue existing project state.",
    "- Do not restart architecture.",
    "- Do not redesign framework behavior.",
    `- Current project root: ${projectRelative}`,
    "",
    "3. core operational rules",
    "- Use local command path only: `node ./bin/zcl.js ...`.",
    "- Run read checks before mutation tasks.",
    "- Use evidence-first execution and validation output.",
    "- If evidence is missing, state: not enough evidence to conclude.",
    "",
    "4. mandatory precheck and decision flow",
    "- Step 1: `node ./bin/zcl.js doctor`",
    "- Step 2: if legacy risk exists, run `node ./bin/zcl.js migrate --from v0.2.x --to evo1.0 --dry-run`",
    "- Step 3: `node ./bin/zcl.js start`",
    "- Step 4: `node ./bin/zcl.js preflight --check-command='...'` (MUST run before mutation)",
    "- Step 5: if risky, `node ./bin/zcl.js behavior record --auto-fill` (MUST exist for preflight to pass)",
    "- Step 6: confirm task Scope + Freeze are explicit",
    "- Step 7: execute only within approved scope",
    "- Step 8: `node ./bin/zcl.js metrics record` to log token usage baseline",
    "- Step 9: verify and report",
    "",
    "5. lifecycle control",
    `- lifecycle.status source: .z-mos/zmos-manifest.json -> ${manifest.lifecycleStatus}`,
    "- active: mutation may proceed only with scope compliance.",
    "- freeze: mutation blocked; read-only only.",
    "- archived: read-only only.",
    "- missing/invalid lifecycle: treat as risk; stop mutation.",
    "",
    "6. mutation safety rules",
    "- Never mutate without precheck evidence.",
    "- Never mutate outside declared scope.",
    "- Never modify `.z-mos/` manually.",
    "- Never bypass governed migration for legacy `.zmos` state.",
    `- scope.mode: ${manifest.scopeMode}`,
    `- scope.allowedPaths: ${manifest.scopeAllowedPaths.length > 0 ? manifest.scopeAllowedPaths.join(", ") : "not enough evidence to conclude"}`,
    `- scope.protectedPaths: ${manifest.scopeProtectedPaths.length > 0 ? manifest.scopeProtectedPaths.join(", ") : "not enough evidence to conclude"}`,
    "",
    "7. TLS usage rules",
    "- Use TLS only through controlled Z-MOS commands (`zcl tls ...`).",
    "- Do not mutate TLS files manually.",
    "- Keep TLS operations safe-mode first (list/show/validate/sync) before mutation commands.",
    "- Do not expand TLS behavior beyond explicit task scope.",
    "",
    "8. stop conditions",
    "- Scope missing or ambiguous.",
    "- Ambiguity checklist in task template has 'no' values for scoped work.",
    "- Freeze declaration missing for mutation tasks.",
    "- Freeze conflict with requested action.",
    "- Risky command intent without a valid BIL record (Preflight failure).",
    "- lifecycle.status is freeze/archived for requested mutation.",
    "- lifecycle/scope evidence missing for mutation decision.",
    "- target path outside allowed scope.",
    "- migration blockers unresolved.",
    "",
    "9. fail-safe response behavior",
    "- When blocked, respond exactly in operational format:",
    "- STATUS: BLOCKED",
    "- REASON: <explicit rule violated>",
    "- EVIDENCE: <file/field/command output>",
    "- NEXT SAFE ACTION: <doctor/migrate/scope clarification>",
    "",
    "10. task brief requirement",
    "- Every execution must begin with Z-MOS TASK BRIEF.",
    "- Required fields: Agent, Task ID, Tier, Scope, Freeze, Objective, Constraints, Allowed Actions, Forbidden Actions, Expected Output.",
    "- If Scope missing -> STOP.",
    "- If Freeze conflict -> STOP.",
    "",
    "11. AI drift prevention rule",
    "- If output starts drifting from scope, stop execution immediately.",
    "- Reload context from manifest + docs/zmos + standards.",
    "- Re-align task scope/freeze/lifecycle before resuming.",
    "",
    "12. final execution intent",
    "- Continue project safely under Z-MOS rules.",
    "- Do not restart.",
    "- Do not redesign.",
    "- Execute only bounded, validated, governed changes.",
    "",
    "Context Snapshot",
    `- project name: ${manifest.repositoryName}`,
    `- lifecycle: ${manifest.lifecycleStatus} (${manifest.lifecycleReason})`,
    `- current phase: ${hasSnapshot ? "PHASE 1 LOCKED" : "IN-PROGRESS"}`,
    `- behavior/metrics components: behavior=${hasBehavior}, metrics=${hasMetrics}`,
    `- runtime snapshot: framework=${manifest.framework}, scope.mode=${manifest.scopeMode}`,
    `- current objective: continue governed project execution (not enough evidence to conclude for task-specific objective)`,
    `- .z-mos/: ${hasDir(structure, ".z-mos")}`,
    `- docs/: ${hasDir(structure, "docs")}`,
    `- apps/: ${hasDir(structure, "apps")}`,
    `- modules/: ${hasDir(structure, "modules")}`,
    `- resume prompt source: ${docAvailability[ZMOS_DOC_PATHS.resume] ? "available" : "not enough evidence to conclude"}`,
    `- task template source: ${docAvailability[ZMOS_DOC_PATHS.taskTemplate] ? "available" : "not enough evidence to conclude"}`,
    `- guard prompt source: ${docAvailability[ZMOS_DOC_PATHS.guard] ? "available" : "not enough evidence to conclude"}`,
    `- resumption brief source: ${docAvailability[ZMOS_DOC_PATHS.resumptionBrief] ? "available" : "not enough evidence to conclude"}`,
    `- ai guide source: ${docAvailability[ZMOS_DOC_PATHS.aiGuide] ? "available" : "not enough evidence to conclude"}`,
    `- communication standard source: ${docAvailability[ZMOS_DOC_PATHS.communicationStandard] ? "available" : "not enough evidence to conclude"}`,
    `- migration standard source: ${docAvailability[ZMOS_DOC_PATHS.migrationStandard] ? "available" : "not enough evidence to conclude"}`,
  ];

  return lines.join("\n");
}

export async function buildTeamOnboardingPrompt(options?: {
  projectPath?: string;
}): Promise<string> {
  const {
    projectRoot,
    projectRelative,
    manifest,
    docAvailability,
    structure,
    hasBehavior,
    hasMetrics,
    hasSnapshot,
  } = await resolveLoadDataContext(options);

  const lines = [
    "Z-MOS TEAM ONBOARDING PROMPT",
    "",
    "Layering Model",
    "- Layer 1 (Global): zmos-active governance baseline.",
    "- Layer 2 (Local): target project operational context.",
    "",
    "Precedence Rule",
    "- Global governance overrides local ambiguity.",
    "- Local context may extend execution detail but must not override Z-MOS safety rules.",
    "",
    "Project Target",
    `- target root: ${projectRelative}`,
    `- repository: ${manifest.repositoryName}`,
    `- framework: ${manifest.framework}`,
    `- version: ${manifest.version}`,
    `- lifecycle.status: ${manifest.lifecycleStatus}`,
    `- lifecycle.reason: ${manifest.lifecycleReason}`,
    "",

    "Required Start Flow",
    "- Step 1: load Layer 1 baseline (`zcl load-data --type zmos-usage-prompt --project .`).",
    "- Step 2: load Layer 2 context (`zcl load-data --type team-onboarding --project <project-path>`).",
    "- Step 3: run `zcl doctor --project <project-path>` and `zcl status --project <project-path>`.",
    "- Step 4: do not mutate until safe-start evidence is explicit.",
    "",
    "Evidence Snapshot",
    `- .z-mos/: ${hasDir(structure, ".z-mos")}`,
    `- docs/: ${hasDir(structure, "docs")}`,
    `- apps/: ${hasDir(structure, "apps")}`,
    `- behavior evidence: ${hasBehavior ? "present" : "not enough evidence to conclude"}`,
    `- metrics evidence: ${hasMetrics ? "present" : "not enough evidence to conclude"}`,
    `- phase snapshot evidence: ${hasSnapshot ? "present" : "not enough evidence to conclude"}`,
    `- communication standard: ${docAvailability[ZMOS_DOC_PATHS.communicationStandard] ? "available" : "not enough evidence to conclude"}`,
    "",
    "Drift Prevention",
    "- If local instructions conflict with global governance, STOP and resolve at governance layer first.",
    "- If evidence is missing, explicitly state: not enough evidence to conclude.",
  ];

  return lines.join("\n");
}

export async function buildZmosMasterPrompt(options?: {
  projectPath?: string;
}): Promise<string> {
  const usage = await buildZmosUsagePrompt(options);
  const lines = [
    usage,
    "",
    "13. PHASE 1 FINAL DIRECTIVE",
    "---------------------------",
    "This system is now in the 'STABILIZED' Phase 1 state.",
    "The 3-Memory Pillar architecture is partially active:",
    "- Pillar 1 (Trace): ACTIVE and hash-chained.",
    "- Pillar 2 (Behavior): ACTIVE via BIL records.",
    "- Pillar 3 (Evolution): DESIGNED (Phase 2 target).",
    "",
    "NEW OPERATIONAL LAW:",
    "1. Every risky command MUST be validated by 'zcl preflight --check-command'.",
    "2. Every preflight for risky commands MUST have a matching BIL record.",
    "3. Use '--auto-fill' for deterministic BIL data, but provide manual logic for decision/reason.",
    "4. All SA-to-Coder communication MUST pass the Ambiguity Checklist (Docs).",
    "5. Log proxy token size via 'zcl metrics record' to establish optimization baseline.",
    "",
    "STATUS: PHASE 1 COMPLIANCE MANDATORY",
  ];
  return lines.join("\n");
}

export async function loadDataPrompt(options: LoadDataOptions): Promise<string> {
  const mode = options.mode === "compact" ? "compact" : "full";
  let fullPrompt = "";

  if (options.type === "new-room-prompt") {
    fullPrompt = await buildNewRoomPrompt({ projectPath: options.projectPath });
  } else if (options.type === "zmos-usage-prompt") {
    fullPrompt = await buildZmosUsagePrompt({ projectPath: options.projectPath });
  } else if (options.type === "zmos-master") {
    fullPrompt = await buildZmosMasterPrompt({ projectPath: options.projectPath });
  } else if (options.type === "team-onboarding") {
    fullPrompt = await buildTeamOnboardingPrompt({ projectPath: options.projectPath });
  } else {
    throw new Error(`Unsupported load-data type: ${options.type}`);
  }

  if (mode === "full") {
    return fullPrompt;
  }

  const lines = fullPrompt.split("\n");
  const compactRules: Record<LoadDataType, RegExp[]> = {
    "new-room-prompt": [
      /^Z-MOS NEW ROOM PROMPT/u,
      /^1\. System Overview/u,
      /^- This is NOT a new project\./u,
      /^- Continue current project state/u,
      /^2\. Current Z-MOS Status/u,
      /^3\. Current Objective/u,
      /^5\. Execution Flow/u,
      /^- Step [1-8]:/u,
      /^7\. Safety Rules/u,
      /^- Never /u,
      /^Runtime Snapshot/u,
      /^- repository:/u,
      /^- framework:/u,
      /^- lifecycle\.status:/u,
      /^- scope\.mode:/u,
    ],
    "zmos-usage-prompt": [
      /^Z-MOS USAGE PROMPT/u,
      /^1\. Z-MOS system identity/u,
      /^2\. project continuation rule/u,
      /^3\. core operational rules/u,
      /^4\. mandatory precheck and decision flow/u,
      /^- Step [1-9]:/u,
      /^5\. lifecycle control/u,
      /^6\. mutation safety rules/u,
      /^8\. stop conditions/u,
      /^- Scope missing or ambiguous\./u,
      /^- Freeze declaration missing/u,
      /^- lifecycle\.status is freeze\/archived/u,
      /^9\. fail-safe response behavior/u,
      /^- STATUS: BLOCKED/u,
      /^- REASON:/u,
      /^- EVIDENCE:/u,
      /^- NEXT SAFE ACTION:/u,
      /^Context Snapshot/u,
      /^- project name:/u,
      /^- lifecycle:/u,
      /^- behavior\/metrics components:/u,
      /^- runtime snapshot:/u,
    ],
    "zmos-master": [
      /^Z-MOS USAGE PROMPT/u,
      /^4\. mandatory precheck and decision flow/u,
      /^- Step [1-9]:/u,
      /^6\. mutation safety rules/u,
      /^8\. stop conditions/u,
      /^9\. fail-safe response behavior/u,
      /^Context Snapshot/u,
      /^13\. PHASE 1 FINAL DIRECTIVE/u,
      /^NEW OPERATIONAL LAW:/u,
      /^[1-5]\. /u,
      /^STATUS: PHASE 1 COMPLIANCE MANDATORY/u,
    ],
    "team-onboarding": [
      /^Z-MOS TEAM ONBOARDING PROMPT/u,
      /^Layering Model/u,
      /^Precedence Rule/u,
      /^Project Target/u,
      /^- target root:/u,
      /^- repository:/u,
      /^- framework:/u,
      /^- lifecycle\.status:/u,

      /^Required Start Flow/u,
      /^- Step [1-4]:/u,
      /^Evidence Snapshot/u,
      /^- \.z-mos\/:/u,
      /^- docs\/:/u,
      /^- behavior evidence:/u,
      /^Drift Prevention/u,
    ],
  };

  const rules = compactRules[options.type];
  const compact: string[] = [];
  let previousWasBlank = false;

  for (const line of lines) {
    const keep = rules.some((rule) => rule.test(line));
    if (!keep) {
      continue;
    }
    if (line.trim() === "") {
      if (previousWasBlank) {
        continue;
      }
      previousWasBlank = true;
      compact.push(line);
      continue;
    }
    previousWasBlank = false;
    compact.push(line);
  }

  return [
    `${compact[0] || "Z-MOS PROMPT"} (COMPACT MODE)`,
    "",
    ...compact.slice(1),
    "",
    "Compact note:",
    "- This is a token-optimized context.",
    "- For high-risk mutation tasks, reload with `--mode full` before execution.",
  ].join("\n");
}
