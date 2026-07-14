import { promises as fs } from "node:fs";
import * as path from "node:path";

type NormalizationFieldChange = {
  field: string;
  from: string;
  to: string;
};

export type ManifestNormalizationResult = {
  attempted: boolean;
  applied: boolean;
  safe: boolean;
  reason: string;
  manifestPath: string;
  changes: NormalizationFieldChange[];
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeRepositoryNameFromPath(projectRoot: string): string {
  const base = path.basename(projectRoot).trim();
  return base.length > 0 ? base : "not enough evidence to conclude";
}

function isBootstrapLikeManifest(
  repositoryName: string,
  lifecycleReason: string,
): boolean {
  const normalizedRepository = repositoryName.trim().toLowerCase();
  const normalizedReason = lifecycleReason.trim().toLowerCase();
  return normalizedRepository === "zmos-core" || normalizedReason.includes("bootstrap");
}

export async function normalizeBootstrapLikeManifestIfSafe(
  projectRoot: string,
): Promise<ManifestNormalizationResult> {
  const manifestPath = path.join(projectRoot, ".z-mos", "zmos-manifest.json");

  let raw: string;
  try {
    raw = await fs.readFile(manifestPath, "utf8");
  } catch {
    return {
      attempted: false,
      applied: false,
      safe: false,
      reason: "manifest not readable; not enough evidence to conclude",
      manifestPath,
      changes: [],
    };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw) as unknown;
  } catch {
    return {
      attempted: true,
      applied: false,
      safe: false,
      reason: "manifest JSON malformed; normalization skipped",
      manifestPath,
      changes: [],
    };
  }

  if (!isObject(parsed)) {
    return {
      attempted: true,
      applied: false,
      safe: false,
      reason: "manifest root is not object; normalization skipped",
      manifestPath,
      changes: [],
    };
  }

  const repository = isObject(parsed.repository) ? parsed.repository : null;
  const lifecycle = isObject(parsed.lifecycle) ? parsed.lifecycle : null;

  const repositoryName = isNonEmptyString(repository?.name) ? repository.name.trim() : "";
  const lifecycleReason = isNonEmptyString(lifecycle?.reason) ? lifecycle.reason.trim() : "";

  if (!isBootstrapLikeManifest(repositoryName, lifecycleReason)) {
    return {
      attempted: true,
      applied: false,
      safe: true,
      reason: "manifest is not bootstrap-like; no normalization required",
      manifestPath,
      changes: [],
    };
  }

  const nextRepositoryName = normalizeRepositoryNameFromPath(projectRoot);
  const changes: NormalizationFieldChange[] = [];

  if (
    repository &&
    repositoryName.toLowerCase() === "zmos-core" &&
    nextRepositoryName !== "not enough evidence to conclude" &&
    nextRepositoryName !== repositoryName
  ) {
    changes.push({
      field: "repository.name",
      from: repositoryName,
      to: nextRepositoryName,
    });
    repository.name = nextRepositoryName;
  }

  if (
    lifecycle &&
    lifecycleReason.toLowerCase() === "default bootstrap lifecycle"
  ) {
    const normalizedReason =
      "normalized bootstrap lifecycle for product project context";
    changes.push({
      field: "lifecycle.reason",
      from: lifecycleReason,
      to: normalizedReason,
    });
    lifecycle.reason = normalizedReason;
  }

  if (changes.length === 0) {
    return {
      attempted: true,
      applied: false,
      safe: true,
      reason: "bootstrap-like manifest already safe; no changes applied",
      manifestPath,
      changes: [],
    };
  }

  await fs.writeFile(manifestPath, `${JSON.stringify(parsed, null, 2)}\n`, "utf8");

  return {
    attempted: true,
    applied: true,
    safe: true,
    reason: "bootstrap-like manifest normalized conservatively",
    manifestPath,
    changes,
  };
}

