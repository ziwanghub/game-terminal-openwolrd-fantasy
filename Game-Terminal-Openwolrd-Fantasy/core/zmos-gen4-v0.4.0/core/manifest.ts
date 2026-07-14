import { promises as fs } from "node:fs";
import * as path from "node:path";

import type {
  ManifestLifecycleStatus,
  ZmosManifestContract,
} from "../contracts/manifest.js";

const ROOT_DIR = process.cwd();
const MANIFEST_PATH = path.join(ROOT_DIR, ".z-mos", "zmos-manifest.json");

export type ZmosManifest = ZmosManifestContract;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function assertString(
  value: unknown,
  fieldPath: string,
): asserts value is string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Invalid manifest: ${fieldPath} must be a non-empty string`);
  }
}

function normalizeLifecycleStatus(value: unknown): ManifestLifecycleStatus {
  if (value === "active" || value === "freeze" || value === "archived" || value === "stabilized") {
    return value;
  }
  return "unknown";
}

function normalizeString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim().length > 0 ? value : fallback;
}

function normalizeStringArray(value: unknown, fallback: string[]): string[] {
  if (!Array.isArray(value)) {
    return [...fallback];
  }
  const normalized = value.filter(
    (entry): entry is string => typeof entry === "string" && entry.trim().length > 0,
  );
  return normalized.length > 0 ? normalized : [...fallback];
}

function validateManifest(value: unknown): ZmosManifest {
  if (!isObject(value)) {
    throw new Error("Invalid manifest: root value must be an object");
  }

  const { repository, workspace, runtime, status, lifecycle, scope } = value;

  if (!isObject(repository)) {
    throw new Error("Invalid manifest: repository must be an object");
  }

  if (!isObject(workspace)) {
    throw new Error("Invalid manifest: workspace must be an object");
  }

  if (!isObject(runtime)) {
    throw new Error("Invalid manifest: runtime must be an object");
  }

  if (!isObject(status)) {
    throw new Error("Invalid manifest: status must be an object");
  }

  assertString(repository.name, "repository.name");
  assertString(repository.framework, "repository.framework");
  assertString(repository.version, "repository.version");
  assertString(workspace.root, "workspace.root");
  assertString(workspace.stateDir, "workspace.stateDir");
  assertString(workspace.traceDir, "workspace.traceDir");
  assertString(runtime.platform, "runtime.platform");
  assertString(runtime.moduleSystem, "runtime.moduleSystem");
  assertString(runtime.entryCommand, "runtime.entryCommand");
  assertString(status.stage, "status.stage");
  assertString(status.aiCli, "status.aiCli");

  const normalizedLifecycle = isObject(lifecycle) ? lifecycle : {};
  const normalizedScope = isObject(scope) ? scope : {};
  const normalizedScopeMutation = isObject(normalizedScope.mutation)
    ? normalizedScope.mutation
    : {};

  return {
    repository: {
      name: repository.name,
      framework: repository.framework,
      version: repository.version,
    },
    workspace: {
      root: workspace.root,
      stateDir: workspace.stateDir,
      traceDir: workspace.traceDir,
    },
    runtime: {
      platform: runtime.platform,
      moduleSystem: runtime.moduleSystem,
      entryCommand: runtime.entryCommand,
    },
    status: {
      stage: status.stage,
      aiCli: status.aiCli,
    },
    lifecycle: {
      status: normalizeLifecycleStatus(normalizedLifecycle.status),
      updatedAt: normalizeString(normalizedLifecycle.updatedAt, "not enough evidence"),
      reason: normalizeString(normalizedLifecycle.reason, "not enough evidence"),
    },
    scope: {
      mutation: {
        mode:
          normalizedScopeMutation.mode === "strict" || normalizedScopeMutation.mode === "warn"
            ? normalizedScopeMutation.mode
            : "strict",
        allowedPaths: normalizeStringArray(normalizedScopeMutation.allowedPaths, []),
        protectedPaths: normalizeStringArray(normalizedScopeMutation.protectedPaths, [
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
          "dist",
        ]),
      },
    },
  };
}

export async function readManifest(): Promise<ZmosManifest> {
  const rawManifest = await fs.readFile(MANIFEST_PATH, "utf8");
  let parsedManifest: unknown;

  try {
    parsedManifest = JSON.parse(rawManifest) as unknown;
  } catch {
    throw new Error(`Invalid manifest: ${MANIFEST_PATH} is not valid JSON`);
  }

  return validateManifest(parsedManifest);
}

export function getManifestPath(): string {
  return MANIFEST_PATH;
}
