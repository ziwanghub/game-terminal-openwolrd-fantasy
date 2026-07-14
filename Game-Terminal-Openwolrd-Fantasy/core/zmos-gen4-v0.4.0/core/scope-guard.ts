import { promises as fs } from "node:fs";
import * as path from "node:path";
import { getGitChangedFiles } from "./git.js";

export interface ScopeGuardConfig {
  schema_version: string;
  mode: "advisory" | "strict";
  allowed_files?: string[];
  protected_files?: string[];
  allowed_patterns?: string[];
  protected_patterns?: string[];
  do_not_touch?: string[];
  stop_conditions?: string[];
  bypass_policy?: string;
}

export interface ScopeGuardViolation {
  file: string;
  reason: string;
}

export interface ScopeGuardResult {
  status: "PASS" | "WARN" | "FAIL";
  violations: ScopeGuardViolation[];
  mode: "advisory" | "strict";
  configLoaded: boolean;
}

export function globToRegExp(glob: string): RegExp {
  const escaped = glob.replace(/[.+^${}()|[\]\\]/g, "\\$&");
  const regexStr = escaped.replace(/\\\*\\\*/g, ".*").replace(/\\\*/g, "[^/]*");
  return new RegExp(`^${regexStr}$`);
}

export async function readScopeGuardConfig(): Promise<ScopeGuardConfig | null> {
  const configPath = path.join(
    process.cwd(),
    ".z-mos/quality/scope-guard.json"
  );
  try {
    const raw = await fs.readFile(configPath, "utf8");
    return JSON.parse(raw) as ScopeGuardConfig;
  } catch {
    return null;
  }
}

export async function validateScopeGuard(): Promise<ScopeGuardResult> {
  const config = await readScopeGuardConfig();
  if (!config) {
    return {
      status: "PASS",
      violations: [],
      mode: "advisory",
      configLoaded: false,
    };
  }

  const rawChangedFiles = getGitChangedFiles();
  const changedFiles = rawChangedFiles.map((s) => path.normalize(s).replace(/^\.\//, ""));
  return evaluateScopeGuard(config, changedFiles);
}

export function evaluateScopeGuard(
  config: ScopeGuardConfig,
  changedFiles: string[],
): ScopeGuardResult {
  const mode = config.mode === "strict" ? "strict" : "advisory";
  const violations: ScopeGuardViolation[] = [];

  const allowedFiles = new Set(config.allowed_files || []);
  const protectedFiles = new Set(config.protected_files || []);
  const allowedPatterns = (config.allowed_patterns || []).map((p) => globToRegExp(p));
  const protectedPatterns = (config.protected_patterns || []).map((p) => globToRegExp(p));
  const hasAllowRestrictions = allowedFiles.size > 0 || allowedPatterns.length > 0;

  if (mode === "strict" && !hasAllowRestrictions) {
    return {
      status: "FAIL",
      violations: [
        {
          file: "*",
          reason: "EMPTY_SCOPE_NOT_ALLOWED_IN_STRICT_MODE",
        },
      ],
      mode,
      configLoaded: true,
    };
  }

  for (const file of changedFiles) {
    let isProtected = protectedFiles.has(file);
    if (!isProtected) {
      for (const pattern of protectedPatterns) {
        if (pattern.test(file)) {
          isProtected = true;
          break;
        }
      }
    }

    if (isProtected) {
      violations.push({
        file,
        reason: "Matches protected_files or protected_patterns",
      });
      continue;
    }

    if (hasAllowRestrictions) {
      let isAllowed = allowedFiles.has(file);
      if (!isAllowed) {
        for (const pattern of allowedPatterns) {
          if (pattern.test(file)) {
            isAllowed = true;
            break;
          }
        }
      }
      if (!isAllowed) {
        violations.push({
          file,
          reason: "Not in allowed_files or allowed_patterns",
        });
      }
    }
  }

  let status: "PASS" | "WARN" | "FAIL" = "PASS";
  if (violations.length > 0) {
    status = mode === "strict" ? "FAIL" : "WARN";
  }

  return { status, violations, mode, configLoaded: true };
}
