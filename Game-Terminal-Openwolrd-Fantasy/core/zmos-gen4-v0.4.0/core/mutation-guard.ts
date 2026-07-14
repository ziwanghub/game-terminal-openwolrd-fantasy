import * as path from "node:path";

import { readManifest, type ZmosManifest } from "./manifest.js";

const ROOT_DIR = process.cwd();

export type MutationGuardResult = {
  allowed: boolean;
  lifecycleStatus: ZmosManifest["lifecycle"]["status"];
  reason: string;
  warnings: string[];
  blockedCheck:
    | "manifest-unreadable"
    | "missing-lifecycle"
    | "freeze"
    | "archived"
    | "missing-scope"
    | "scope-violation"
    | "protected-path"
    | null;
};

export type MutationGuardInput = {
  command: string;
  targetPaths: string[];
  allowMissingManifest?: boolean;
  allowProtectedPrefixes?: string[];
};

function toRelative(targetPath: string): string {
  return path.relative(ROOT_DIR, targetPath).replace(/\\/gu, "/");
}

function isWithin(rootPath: string, targetPath: string): boolean {
  const relative = path.relative(rootPath, targetPath);
  return relative !== "" && !relative.startsWith("..") && !path.isAbsolute(relative);
}

function matchesPrefix(targetPath: string, prefixes: string[]): boolean {
  const normalized = targetPath.replace(/\\/gu, "/");
  return prefixes.some((prefix) => normalized === prefix || normalized.startsWith(`${prefix}/`));
}

function normalizeTargets(targetPaths: string[]): string[] {
  const resolved = targetPaths
    .map((entry) => path.resolve(ROOT_DIR, entry))
    .filter((entry, index, list) => list.indexOf(entry) === index);

  if (resolved.length === 0) {
    return [ROOT_DIR];
  }

  return resolved;
}

function isScopeConfigured(manifest: ZmosManifest): boolean {
  const scope = manifest.scope?.mutation;
  return Array.isArray(scope?.allowedPaths) && scope.allowedPaths.length > 0;
}

export async function evaluateMutationGuard(
  input: MutationGuardInput,
): Promise<MutationGuardResult> {
  const targets = normalizeTargets(input.targetPaths);
  let manifest: ZmosManifest;

  try {
    manifest = await readManifest();
  } catch (error) {
    if (input.allowMissingManifest) {
      return {
        allowed: true,
        lifecycleStatus: "unknown",
        reason: "Manifest is not readable; mutation allowed only for bootstrap path.",
        warnings: [error instanceof Error ? error.message : "Manifest read failure."],
        blockedCheck: null,
      };
    }

    return {
      allowed: false,
      lifecycleStatus: "unknown",
      reason: "Manifest is not readable; mutation is blocked until canonical manifest is repaired.",
      warnings: [error instanceof Error ? error.message : "Manifest read failure."],
      blockedCheck: "manifest-unreadable",
    };
  }

  if (manifest.lifecycle.status === "unknown") {
    return {
      allowed: false,
      lifecycleStatus: manifest.lifecycle.status,
      reason: "Manifest lifecycle.status is missing/invalid; mutation is blocked by safety guard.",
      warnings: ["Add lifecycle.status = active|freeze|archived to manifest."],
      blockedCheck: "missing-lifecycle",
    };
  }

  if (manifest.lifecycle.status === "freeze") {
    return {
      allowed: false,
      lifecycleStatus: manifest.lifecycle.status,
      reason: "Project lifecycle is freeze; mutation is blocked.",
      warnings: ["Use read-only commands only while lifecycle.status=freeze."],
      blockedCheck: "freeze",
    };
  }

  if (manifest.lifecycle.status === "archived") {
    return {
      allowed: false,
      lifecycleStatus: manifest.lifecycle.status,
      reason: "Project lifecycle is archived; mutation is blocked (read-only mode).",
      warnings: ["Archived projects are read-only by contract."],
      blockedCheck: "archived",
    };
  }

  if (!isScopeConfigured(manifest)) {
    return {
      allowed: false,
      lifecycleStatus: manifest.lifecycle.status,
      reason: "Manifest mutation scope is missing; mutation is blocked by boundary policy.",
      warnings: ["Define scope.mutation.allowedPaths in manifest."],
      blockedCheck: "missing-scope",
    };
  }

  const allowedRoots = manifest.scope.mutation.allowedPaths.map((entry) =>
    path.resolve(ROOT_DIR, entry),
  );
  const protectedPaths = manifest.scope.mutation.protectedPaths;
  const allowProtectedPrefixes = input.allowProtectedPrefixes || [];

  for (const absoluteTarget of targets) {
    if (absoluteTarget === ROOT_DIR) {
      return {
        allowed: false,
        lifecycleStatus: manifest.lifecycle.status,
        reason: `Target path resolves to repository root (${toRelative(absoluteTarget) || "."}); mutation is blocked.`,
        warnings: ["Use explicit bounded target paths for mutation commands."],
        blockedCheck: "scope-violation",
      };
    }

    if (!isWithin(ROOT_DIR, absoluteTarget)) {
      return {
        allowed: false,
        lifecycleStatus: manifest.lifecycle.status,
        reason: `Target path is outside repository scope: ${absoluteTarget}`,
        warnings: ["Mutation targets must stay inside repository root."],
        blockedCheck: "scope-violation",
      };
    }

    const targetRelative = toRelative(absoluteTarget);
    const protectedButAllowed =
      matchesPrefix(targetRelative, protectedPaths) &&
      matchesPrefix(targetRelative, allowProtectedPrefixes);

    if (matchesPrefix(targetRelative, protectedPaths) && !protectedButAllowed) {
      return {
        allowed: false,
        lifecycleStatus: manifest.lifecycle.status,
        reason: `Target path is protected by policy: ${targetRelative}`,
        warnings: ["Protected paths cannot be mutated by generic command flow."],
        blockedCheck: "protected-path",
      };
    }

    const inAllowedScope = allowedRoots.some(
      (allowedRoot) =>
        absoluteTarget === allowedRoot || isWithin(allowedRoot, absoluteTarget),
    );

    if (!inAllowedScope) {
      return {
        allowed: false,
        lifecycleStatus: manifest.lifecycle.status,
        reason: `Target path is outside allowed mutation scope: ${targetRelative}`,
        warnings: [
          `Allowed scope: ${manifest.scope.mutation.allowedPaths.join(", ") || "not enough evidence"}`,
        ],
        blockedCheck: "scope-violation",
      };
    }
  }

  return {
    allowed: true,
    lifecycleStatus: manifest.lifecycle.status,
    reason: `Mutation allowed for command '${input.command}' under lifecycle.status=${manifest.lifecycle.status}.`,
    warnings: [],
    blockedCheck: null,
  };
}

export async function evaluateLifecycleReadiness(): Promise<{
  status: ZmosManifest["lifecycle"]["status"];
  okForMutation: boolean;
  reason: string;
}> {
  try {
    const manifest = await readManifest();
    const lifecycleStatus = manifest.lifecycle.status;
    if (lifecycleStatus === "active" || lifecycleStatus === "stabilized") {
      return {
        status: lifecycleStatus,
        okForMutation: true,
        reason:
          lifecycleStatus === "active"
            ? "active lifecycle"
            : "stabilized lifecycle (controlled mutation allowed)",
      };
    }
    if (lifecycleStatus === "freeze") {
      return {
        status: lifecycleStatus,
        okForMutation: false,
        reason: "freeze lifecycle blocks mutation",
      };
    }
    if (lifecycleStatus === "archived") {
      return {
        status: lifecycleStatus,
        okForMutation: false,
        reason: "archived lifecycle is read-only",
      };
    }
    return {
      status: lifecycleStatus,
      okForMutation: false,
      reason: "missing/invalid lifecycle status",
    };
  } catch (error) {
    return {
      status: "unknown",
      okForMutation: false,
      reason: error instanceof Error ? error.message : "manifest read failure",
    };
  }
}
