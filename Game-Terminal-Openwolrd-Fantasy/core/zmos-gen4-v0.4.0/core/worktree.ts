import { promises as fs } from "node:fs";
import * as path from "node:path";
import { getGitContext, getGitChangedFiles } from "./git.js";

export interface HandoffValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  parsedHandoff?: any;
}

export interface ScopeValidationResult {
  status: "PASS" | "WARN_NO_SCOPE" | "WARN_DRIFT";
  expectedScope: string[];
  changedFiles: string[];
  outsideScope: string[];
}

export interface SyncValidationResult {
  status: "PASS" | "WARN_DESYNC";
  reasons: string[];
}

export interface WorktreeStatus {
  status: "PASS" | "WARN";
  sync: SyncValidationResult;
  handoff: HandoffValidationResult;
  scope: ScopeValidationResult;
}

export async function validateHandoffPure(): Promise<HandoffValidationResult> {
  const rootDir = process.cwd();
  const handoffPath = path.join(rootDir, ".z-mos/intent.card.json");
  let raw = "";
  try {
    raw = await fs.readFile(handoffPath, "utf8");
  } catch {
    return { valid: false, errors: [`handoff file missing or unreadable: ${handoffPath}`], warnings: [] };
  }

  let handoff;
  try {
    handoff = JSON.parse(raw);
  } catch {
    return { valid: false, errors: ["handoff is not valid JSON."], warnings: [] };
  }

  const errors: string[] = [];
  const warnings: string[] = [];

  if (!handoff.schema_version) errors.push("Missing schema_version");
  if (!handoff.current_phase) errors.push("Missing current_phase");
  if (!handoff.next_safe_action || handoff.next_safe_action.trim() === "") errors.push("next_safe_action is empty");
  
  if (handoff.safe_to_resume === true && handoff.reverify_required === true) {
    errors.push("Contradictory status: cannot be strictly safe_to_resume while reverify_required is strictly true");
  }
  
  if (!Array.isArray(handoff.latest_evidence_refs)) {
    errors.push("latest_evidence_refs must be an array");
  }

  if (!handoff.quality) {
    warnings.push("Missing top-level 'quality' block");
  } else {
    const q = handoff.quality;
    if (!Array.isArray(q.allowed_scope)) warnings.push("quality.allowed_scope missing or invalid");
    if (!Array.isArray(q.do_not_touch)) warnings.push("quality.do_not_touch missing or invalid");
    if (!Array.isArray(q.known_risks)) warnings.push("quality.known_risks missing or invalid");
    if (!Array.isArray(q.required_tests)) warnings.push("quality.required_tests missing or invalid");
    if (!Array.isArray(q.stop_conditions)) warnings.push("quality.stop_conditions missing or invalid");
  }
  
  const isDeprecatedHandoff = handoff.deprecation_status === "deprecated";

  if (handoff.generated_at) {
    const ageMs = Date.now() - new Date(handoff.generated_at).getTime();
    if (!isDeprecatedHandoff && ageMs > 7 * 24 * 60 * 60 * 1000) {
      warnings.push("Handoff generated_at is more than 7 days old. Action may be extremely stale.");
    }
  } else {
    errors.push("Missing generated_at timestamp");
  }

  const sunsetDate =
    typeof handoff.deprecation_sunset_date === "string"
      ? handoff.deprecation_sunset_date
      : null;
  if (!sunsetDate) {
    warnings.push("Missing deprecation_sunset_date for legacy handoff file");
  } else {
    warnings.push(
      `Legacy handoff is deprecated and will sunset on ${sunsetDate}. Migrate to .z-mos/intent.card.json.`,
    );
    const sunsetTs = Date.parse(sunsetDate);
    if (!Number.isNaN(sunsetTs) && Date.now() > sunsetTs) {
      warnings.push("Handoff sunset date has passed; cleanup migration should be prioritized.");
    }
  }

  return { valid: errors.length === 0, errors, warnings, parsedHandoff: handoff };
}

export async function validateScopePure(handoffJson?: any): Promise<ScopeValidationResult> {
  let handoff = handoffJson;
  if (!handoff) {
    const rootDir = process.cwd();
    try {
      const raw = await fs.readFile(path.join(rootDir, ".z-mos/intent.card.json"), "utf8");
      handoff = JSON.parse(raw);
    } catch {
      return { status: "WARN_NO_SCOPE", expectedScope: [], changedFiles: [], outsideScope: [] };
    }
  }

  if (!handoff || !handoff.scope_files || !Array.isArray(handoff.scope_files)) {
    return { status: "WARN_NO_SCOPE", expectedScope: [], changedFiles: [], outsideScope: [] };
  }

  const expectedScopeArray = handoff.scope_files.map((s: string) => path.normalize(s).replace(/^\.\//, ""));
  const expectedScope = new Set(expectedScopeArray);
  const changedFiles = getGitChangedFiles().map(s => path.normalize(s).replace(/^\.\//, ""));

  const outsideScope: string[] = [];
  for (const changedFile of changedFiles) {
    if (!expectedScope.has(changedFile)) {
      outsideScope.push(changedFile);
    }
  }

  if (outsideScope.length > 0) {
    return { status: "WARN_DRIFT", expectedScope: expectedScopeArray, changedFiles, outsideScope };
  }

  return { status: "PASS", expectedScope: expectedScopeArray, changedFiles, outsideScope: [] };
}

export async function validateSyncPure(handoffJson?: any): Promise<SyncValidationResult> {
  const git = getGitContext();
  const rootDir = process.cwd();
  const reasons: string[] = [];

  let stateJson;
  try {
    const rawState = await fs.readFile(path.join(rootDir, ".z-mos/state/project-state.json"), "utf8");
    stateJson = JSON.parse(rawState);
  } catch {}

  let handoff = handoffJson;
  if (!handoff) {
    try {
      const rawHandoff = await fs.readFile(path.join(rootDir, ".z-mos/intent.card.json"), "utf8");
      handoff = JSON.parse(rawHandoff);
    } catch {}
  }

  if (git.commit && stateJson?.synchronized_commit_hash) {
    if (git.commit !== stateJson.synchronized_commit_hash || git.branch !== stateJson.synchronized_branch) {
      reasons.push("Project state is desynced from Git HEAD or branch");
    }
  }

  if (git.commit && handoff?.synchronized_commit_hash) {
    if (git.commit !== handoff.synchronized_commit_hash || git.branch !== handoff.synchronized_branch) {
      reasons.push("Handoff context is stale compared to Git HEAD or branch");
    }
  }

  if (reasons.length > 0) {
    return { status: "WARN_DESYNC", reasons };
  }
  return { status: "PASS", reasons };
}

export async function verifyWorktree(): Promise<WorktreeStatus> {
  const handoff = await validateHandoffPure();
  const scope = await validateScopePure(handoff.parsedHandoff);
  const sync = await validateSyncPure(handoff.parsedHandoff);

  const isWarn = !handoff.valid || scope.status !== "PASS" || sync.status !== "PASS";

  return {
    status: isWarn ? "WARN" : "PASS",
    sync,
    handoff,
    scope
  };
}
