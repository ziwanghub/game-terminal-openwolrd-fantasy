import { promises as fs } from "node:fs";
import * as path from "node:path";

import { validateTemplate } from "./tls-engine.js";
import type { TemplateManifest } from "./tls-engine.js";

export type TlsTemplateRecord = {
  name: string;
  type: string;
  version: string;
  status: string;
  path: string;
  absolutePath: string;
  manifest: TemplateManifest;
};

export type TlsValidationResult = {
  template: {
    name: string;
    path: string;
    type: string;
    version: string;
    status: string;
  };
  pass: boolean;
  issues: string[];
  warnings: string[];
};

export type TlsRegistryEntry = {
  name?: string;
  type?: string;
  version?: string;
  status?: string;
  path?: string;
};

export type TlsRegistrySyncReport = {
  registryPath: string;
  filesystemTemplateCount: number;
  registryTemplateCount: number;
  missingInRegistry: Array<{
    name: string;
    path: string;
    type: string;
    version: string;
    status: string;
  }>;
  missingOnFilesystem: Array<{
    name: string;
    path: string;
    type: string;
    version: string;
    status: string;
  }>;
  mismatched: Array<{
    name: string;
    path: string;
    differences: Array<"type" | "version" | "status" | "path">;
    filesystem: {
      type: string;
      version: string;
      status: string;
      path: string;
    };
    registry: {
      type: string;
      version: string;
      status: string;
      path: string;
    };
  }>;
  suggested: {
    add: number;
    update: number;
    remove: number;
  };
};

export type TlsUninstallOptions = {
  dryRun?: boolean;
};

export type TlsInstallOptions = {
  sourcePath: string;
  type: "landing" | "booking" | "admin" | "member" | "bundle";
  name: string;
  dryRun?: boolean;
  force?: boolean;
};

export type TlsUpdateOptions = {
  name: string;
  sourcePath: string;
  dryRun?: boolean;
  force?: boolean;
};

export type TlsUpdateChangeType = "same-version" | "minor-or-patch" | "major";

export type TlsUpdateResult = {
  ok: boolean;
  dryRun: boolean;
  templateName: string;
  resolvedPath: string;
  oldVersion: string;
  newVersion: string;
  changeType: TlsUpdateChangeType;
  replacedFiles: string[];
  registryAction: "updated" | "already-clean";
  steps: Array<{
    step: string;
    status: "pass" | "warn" | "fail";
    detail: string;
  }>;
  error?: string;
};

export type TlsInstallResult = {
  ok: boolean;
  dryRun: boolean;
  templateName: string;
  resolvedPath: string;
  installedFiles: number;
  registryAction: "added" | "updated" | "already-clean";
  steps: Array<{
    step: string;
    status: "pass" | "warn" | "fail";
    detail: string;
  }>;
  error?: string;
};

export type TlsUninstallResult = {
  ok: boolean;
  dryRun: boolean;
  templateName: string;
  resolvedPath: string;
  removedFiles: number;
  registryRemovedEntries: number;
  registryAction: "updated" | "already-clean";
  steps: Array<{
    step: string;
    status: "pass" | "warn" | "fail";
    detail: string;
  }>;
  error?: string;
};

const TLS_ROOT = path.join(process.cwd(), "tls");
const TLS_TEMPLATES_ROOT = path.join(TLS_ROOT, "templates");
const TLS_MODULES_ROOT = path.join(TLS_ROOT, "modules");
const TEMPLATE_REGISTRY_PATH = path.join(TLS_ROOT, "registry", "template-registry.json");
const TEMPLATE_SCHEMA_PATH = path.join(TLS_ROOT, "schemas", "template.schema.json");

function toPosix(relativePath: string): string {
  return relativePath.replace(/\\/gu, "/");
}

function normalizeTypeFolder(type: string): string {
  return type === "bundle" ? "bundles" : type;
}

async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function listTemplateManifestPaths(
  directory: string,
): Promise<string[]> {
  const output: string[] = [];
  const stack = [directory];

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }

    const entries = await fs.readdir(current, { withFileTypes: true });
    for (const entry of entries) {
      const entryPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(entryPath);
        continue;
      }
      if (entry.isFile() && entry.name === "template.json") {
        output.push(entryPath);
      }
    }
  }

  return output.sort((a, b) => a.localeCompare(b));
}

async function readTemplateManifest(absoluteTemplatePath: string): Promise<TemplateManifest> {
  const raw = await fs.readFile(path.join(absoluteTemplatePath, "template.json"), "utf8");
  return JSON.parse(raw) as TemplateManifest;
}

export async function listTlsTemplates(): Promise<TlsTemplateRecord[]> {
  const manifestPaths = await listTemplateManifestPaths(TLS_TEMPLATES_ROOT);
  const templates: TlsTemplateRecord[] = [];

  for (const manifestPath of manifestPaths) {
    const absolutePath = path.dirname(manifestPath);
    const relativePath = toPosix(path.relative(TLS_TEMPLATES_ROOT, absolutePath));
    let manifest: TemplateManifest;
    try {
      manifest = await readTemplateManifest(absolutePath);
    } catch {
      continue;
    }

    templates.push({
      name: manifest.name,
      type: manifest.type,
      version: manifest.version,
      status: manifest.status,
      path: relativePath,
      absolutePath,
      manifest,
    });
  }

  return templates.sort((a, b) => a.path.localeCompare(b.path));
}

export async function getTlsTemplateByName(name: string): Promise<TlsTemplateRecord | null> {
  const templates = await listTlsTemplates();
  return (
    templates.find((entry) => entry.name === name) ||
    templates.find((entry) => path.basename(entry.path) === name) ||
    templates.find((entry) => entry.path === name) ||
    null
  );
}

type TemplateSchema = {
  required?: unknown;
  properties?: Record<string, unknown>;
  additionalProperties?: boolean;
};

async function readTemplateSchema(): Promise<TemplateSchema | null> {
  if (!(await pathExists(TEMPLATE_SCHEMA_PATH))) {
    return null;
  }

  try {
    const raw = await fs.readFile(TEMPLATE_SCHEMA_PATH, "utf8");
    return JSON.parse(raw) as TemplateSchema;
  } catch {
    return null;
  }
}

async function loadRegistryEntries(): Promise<TlsRegistryEntry[]> {
  try {
    const raw = await fs.readFile(TEMPLATE_REGISTRY_PATH, "utf8");
    const parsed = JSON.parse(raw) as { templates?: unknown };
    if (!Array.isArray(parsed.templates)) {
      return [];
    }
    return parsed.templates as TlsRegistryEntry[];
  } catch {
    return [];
  }
}

async function saveRegistryEntries(entries: TlsRegistryEntry[]): Promise<void> {
  const payload = {
    templates: entries,
  };
  await fs.writeFile(TEMPLATE_REGISTRY_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function isWithin(absolutePath: string, root: string): boolean {
  const relative = path.relative(root, absolutePath);
  return relative !== "" && !relative.startsWith("..") && !path.isAbsolute(relative);
}

function isForbiddenUninstallPath(targetPath: string): boolean {
  const resolvedTarget = path.resolve(targetPath);
  const protectedRoots = [TLS_ROOT, TLS_TEMPLATES_ROOT, TLS_MODULES_ROOT].map((entry) =>
    path.resolve(entry),
  );
  return protectedRoots.includes(resolvedTarget);
}

function isForbiddenInstallPath(targetPath: string): boolean {
  const resolvedTarget = path.resolve(targetPath);
  const protectedRoots = [TLS_ROOT, TLS_TEMPLATES_ROOT, TLS_MODULES_ROOT].map((entry) =>
    path.resolve(entry),
  );
  return protectedRoots.includes(resolvedTarget);
}

async function countDirectoryFiles(directory: string): Promise<number> {
  let count = 0;
  const stack = [directory];

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }

    const entries = await fs.readdir(current, { withFileTypes: true });
    for (const entry of entries) {
      const entryPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(entryPath);
      } else {
        count += 1;
      }
    }
  }

  return count;
}

async function validateTemplateStructureAtPath(
  absoluteTemplatePath: string,
): Promise<{ issues: string[]; warnings: string[]; manifest: TemplateManifest | null }> {
  const issues: string[] = [];
  const warnings: string[] = [];
  let manifest: TemplateManifest | null = null;

  const manifestPath = path.join(absoluteTemplatePath, "template.json");
  if (!(await pathExists(manifestPath))) {
    issues.push("missing required file: template.json");
    return { issues, warnings, manifest };
  }

  try {
    manifest = await readTemplateManifest(absoluteTemplatePath);
  } catch {
    issues.push("template.json is not valid JSON");
    return { issues, warnings, manifest };
  }

  const manifestErrors = validateTemplate(manifest);
  for (const manifestError of manifestErrors) {
    issues.push(manifestError);
  }

  const schema = await readTemplateSchema();
  if (schema && Array.isArray(schema.required)) {
    const requiredFields = schema.required.filter(
      (field): field is string => typeof field === "string" && field.trim().length > 0,
    );
    for (const field of requiredFields) {
      if (!(field in manifest)) {
        issues.push(`template.schema required field missing: ${field}`);
      }
    }
  } else {
    warnings.push("template.schema.json not available or unreadable; required-field validation is partial.");
  }

  const requiredFiles = ["config.default.json", "README.md"];
  for (const fileName of requiredFiles) {
    const filePath = path.join(absoluteTemplatePath, fileName);
    if (!(await pathExists(filePath))) {
      issues.push(`missing required file: ${fileName}`);
    }
  }

  const hasSrcDir = await pathExists(path.join(absoluteTemplatePath, "src"));
  const hasAppDir = await pathExists(path.join(absoluteTemplatePath, "app"));
  if (!hasSrcDir && !hasAppDir) {
    issues.push("missing source directory: expected src/ (preferred) or app/ (legacy-compatible).");
  } else if (hasAppDir && !hasSrcDir) {
    warnings.push("legacy app/ source layout detected; src/ is preferred for new/updated templates.");
  }

  return { issues, warnings, manifest };
}

function validateInstallName(name: string): boolean {
  return /^[a-z0-9-]+$/u.test(name);
}

type SemverParts = { major: number; minor: number; patch: number };

function parseSemver(version: string): SemverParts | null {
  const match = /^(\d+)\.(\d+)\.(\d+)$/u.exec(version);
  if (!match) {
    return null;
  }
  return {
    major: Number.parseInt(match[1] || "0", 10),
    minor: Number.parseInt(match[2] || "0", 10),
    patch: Number.parseInt(match[3] || "0", 10),
  };
}

function compareSemver(a: SemverParts, b: SemverParts): -1 | 0 | 1 {
  if (a.major !== b.major) {
    return a.major < b.major ? -1 : 1;
  }
  if (a.minor !== b.minor) {
    return a.minor < b.minor ? -1 : 1;
  }
  if (a.patch !== b.patch) {
    return a.patch < b.patch ? -1 : 1;
  }
  return 0;
}

function resolveChangeType(oldVersion: SemverParts, nextVersion: SemverParts): TlsUpdateChangeType {
  if (
    oldVersion.major === nextVersion.major &&
    oldVersion.minor === nextVersion.minor &&
    oldVersion.patch === nextVersion.patch
  ) {
    return "same-version";
  }
  if (oldVersion.major === nextVersion.major) {
    return "minor-or-patch";
  }
  return "major";
}

async function listDirectoryFilesRelative(directory: string): Promise<string[]> {
  const output: string[] = [];
  const stack = [directory];

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) {
      continue;
    }

    const entries = await fs.readdir(current, { withFileTypes: true });
    for (const entry of entries) {
      const entryPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(entryPath);
        continue;
      }
      if (entry.isFile()) {
        output.push(toPosix(path.relative(directory, entryPath)));
      }
    }
  }

  return output.sort((a, b) => a.localeCompare(b));
}

function hasLiveUsageEvidence(manifest: TemplateManifest): boolean {
  const value = (manifest as unknown as Record<string, unknown>).customer_live_status;
  if (typeof value !== "string") {
    return false;
  }
  const normalized = value.trim().toLowerCase();
  return normalized === "live" || normalized === "feedback-loop";
}

function resolveUsageEvidenceMessage(manifest: TemplateManifest): string {
  const value = (manifest as unknown as Record<string, unknown>).customer_live_status;
  if (typeof value === "string" && value.trim().length > 0) {
    return `customer_live_status=${value}`;
  }
  return "customer_live_status evidence not available";
}

export async function validateTlsTemplate(template: TlsTemplateRecord): Promise<TlsValidationResult> {
  const issues: string[] = [];
  const warnings: string[] = [];
  const manifest = template.manifest;
  const schema = await readTemplateSchema();

  const manifestErrors = validateTemplate(manifest);
  for (const manifestError of manifestErrors) {
    issues.push(manifestError);
  }

  if (schema && Array.isArray(schema.required)) {
    const requiredFields = schema.required.filter(
      (field): field is string => typeof field === "string" && field.trim().length > 0,
    );
    for (const field of requiredFields) {
      if (!(field in manifest)) {
        issues.push(`template.schema required field missing: ${field}`);
      }
    }
  } else {
    warnings.push("template.schema.json not available or unreadable; required-field validation is partial.");
  }

  const requiredFiles = ["template.json", "config.default.json", "README.md"];
  for (const fileName of requiredFiles) {
    const filePath = path.join(template.absolutePath, fileName);
    if (!(await pathExists(filePath))) {
      issues.push(`missing required file: ${fileName}`);
    }
  }

  const hasSrcDir = await pathExists(path.join(template.absolutePath, "src"));
  const hasAppDir = await pathExists(path.join(template.absolutePath, "app"));
  if (!hasSrcDir && !hasAppDir) {
    issues.push("missing source directory: expected src/ (preferred) or app/ (legacy-compatible).");
  }
  if (hasAppDir && !hasSrcDir) {
    warnings.push("legacy app/ source layout detected; src/ is preferred for new/updated templates.");
  }

  const folderParts = template.path.split("/").filter(Boolean);
  const folderType = folderParts[0] || "";
  const expectedFolderType = normalizeTypeFolder(manifest.type);
  if (folderType !== expectedFolderType) {
    issues.push(
      `template type/folder mismatch: type=${manifest.type} expects folder '${expectedFolderType}' but found '${folderType || "(none)"}'`,
    );
  }

  const registryEntries = await loadRegistryEntries();
  const registryEntry = registryEntries.find((entry) => entry.name === manifest.name);
  if (!registryEntry) {
    warnings.push("template is not registered in tls/registry/template-registry.json");
  }

  return {
    template: {
      name: manifest.name,
      path: template.path,
      type: manifest.type,
      version: manifest.version,
      status: manifest.status,
    },
    pass: issues.length === 0,
    issues,
    warnings,
  };
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function buildRegistryShape(entry: TlsRegistryEntry): {
  type: string;
  version: string;
  status: string;
  path: string;
} {
  return {
    type: asString(entry.type),
    version: asString(entry.version),
    status: asString(entry.status),
    path: asString(entry.path),
  };
}

export async function evaluateTlsRegistrySync(): Promise<TlsRegistrySyncReport> {
  const filesystemTemplates = await listTlsTemplates();
  const registryTemplates = await loadRegistryEntries();

  const filesystemByName = new Map(filesystemTemplates.map((entry) => [entry.name, entry]));
  const registryByName = new Map(
    registryTemplates
      .filter((entry) => typeof entry.name === "string" && entry.name.trim().length > 0)
      .map((entry) => [entry.name as string, entry]),
  );

  const missingInRegistry = filesystemTemplates
    .filter((template) => !registryByName.has(template.name))
    .map((template) => ({
      name: template.name,
      path: `templates/${template.path}`,
      type: template.type,
      version: template.version,
      status: template.status,
    }));

  const missingOnFilesystem = Array.from(registryByName.entries())
    .filter(([name]) => !filesystemByName.has(name))
    .map(([, entry]) => ({
      name: asString(entry.name),
      path: asString(entry.path),
      type: asString(entry.type),
      version: asString(entry.version),
      status: asString(entry.status),
    }));

  const mismatched: TlsRegistrySyncReport["mismatched"] = [];
  for (const template of filesystemTemplates) {
    const registryEntry = registryByName.get(template.name);
    if (!registryEntry) {
      continue;
    }

    const registryShape = buildRegistryShape(registryEntry);
    const fsPath = `templates/${template.path}`;
    const differences: Array<"type" | "version" | "status" | "path"> = [];
    if (registryShape.type !== template.type) {
      differences.push("type");
    }
    if (registryShape.version !== template.version) {
      differences.push("version");
    }
    if (registryShape.status !== template.status) {
      differences.push("status");
    }
    if (registryShape.path !== fsPath) {
      differences.push("path");
    }

    if (differences.length > 0) {
      mismatched.push({
        name: template.name,
        path: fsPath,
        differences,
        filesystem: {
          type: template.type,
          version: template.version,
          status: template.status,
          path: fsPath,
        },
        registry: registryShape,
      });
    }
  }

  return {
    registryPath: TEMPLATE_REGISTRY_PATH,
    filesystemTemplateCount: filesystemTemplates.length,
    registryTemplateCount: registryTemplates.length,
    missingInRegistry,
    missingOnFilesystem,
    mismatched,
    suggested: {
      add: missingInRegistry.length,
      update: mismatched.length,
      remove: missingOnFilesystem.length,
    },
  };
}

export async function updateTlsTemplate(
  options: TlsUpdateOptions,
): Promise<TlsUpdateResult> {
  const dryRun = options.dryRun === true;
  const steps: TlsUpdateResult["steps"] = [];

  const existing = await getTlsTemplateByName(options.name);
  if (!existing) {
    steps.push({
      step: "validate-template-exists",
      status: "fail",
      detail: `Template not found: ${options.name}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: options.name,
      resolvedPath: "not enough evidence",
      oldVersion: "not enough evidence",
      newVersion: "not enough evidence",
      changeType: "same-version",
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Template not found; update cannot fallback to install.",
    };
  }

  steps.push({
    step: "validate-template-exists",
    status: "pass",
    detail: `Found existing template: ${existing.name}`,
  });

  const sourcePath = path.resolve(options.sourcePath);
  if (!(await pathExists(sourcePath))) {
    steps.push({
      step: "validate-source-exists",
      status: "fail",
      detail: `Source path does not exist: ${sourcePath}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: "not enough evidence",
      changeType: "same-version",
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Source path does not exist.",
    };
  }

  const sourceStats = await fs.stat(sourcePath);
  if (!sourceStats.isDirectory()) {
    steps.push({
      step: "validate-source-exists",
      status: "fail",
      detail: `Source path is not a directory: ${sourcePath}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: "not enough evidence",
      changeType: "same-version",
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Source path must be a directory.",
    };
  }

  steps.push({
    step: "validate-source-exists",
    status: "pass",
    detail: `Source template directory found: ${sourcePath}`,
  });

  const sourceValidation = await validateTemplateStructureAtPath(sourcePath);
  if (sourceValidation.issues.length > 0 || sourceValidation.manifest === null) {
    steps.push({
      step: "validate-source-structure",
      status: "fail",
      detail: sourceValidation.issues.join("; "),
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: "not enough evidence",
      changeType: "same-version",
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Source template structure validation failed.",
    };
  }

  steps.push({
    step: "validate-source-structure",
    status: "pass",
    detail:
      sourceValidation.warnings.length > 0
        ? sourceValidation.warnings.join("; ")
        : "Source template structure is valid.",
  });

  const sourceManifest = sourceValidation.manifest;
  if (sourceManifest.name !== existing.manifest.name) {
    steps.push({
      step: "validate-identity-compatibility",
      status: "fail",
      detail: `Manifest name mismatch: existing=${existing.manifest.name}, source=${sourceManifest.name}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: sourceManifest.version,
      changeType: "same-version",
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Update blocked due to template identity mismatch (name).",
    };
  }

  if (sourceManifest.type !== existing.manifest.type) {
    steps.push({
      step: "validate-identity-compatibility",
      status: "fail",
      detail: `Manifest type mismatch: existing=${existing.manifest.type}, source=${sourceManifest.type}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: sourceManifest.version,
      changeType: "same-version",
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Update blocked due to template identity mismatch (type).",
    };
  }

  steps.push({
    step: "validate-identity-compatibility",
    status: "pass",
    detail: "Template identity is compatible (name + type match).",
  });

  const oldSemver = parseSemver(existing.version);
  const newSemver = parseSemver(sourceManifest.version);
  if (!oldSemver || !newSemver) {
    steps.push({
      step: "validate-version-contract",
      status: "fail",
      detail: `Semver parse failed (old=${existing.version}, new=${sourceManifest.version}).`,
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: sourceManifest.version,
      changeType: "same-version",
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Version contract validation failed.",
    };
  }

  const versionComparison = compareSemver(newSemver, oldSemver);
  if (versionComparison < 0) {
    steps.push({
      step: "validate-version-contract",
      status: "fail",
      detail: `Downgrade is blocked (old=${existing.version}, new=${sourceManifest.version}).`,
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: sourceManifest.version,
      changeType: "same-version",
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Downgrade is not allowed.",
    };
  }

  const changeType = resolveChangeType(oldSemver, newSemver);
  if (changeType === "major" && !options.force) {
    steps.push({
      step: "validate-version-contract",
      status: "fail",
      detail: `Major update requires --force (old=${existing.version}, new=${sourceManifest.version}).`,
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: sourceManifest.version,
      changeType,
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Major update blocked without --force.",
    };
  }

  steps.push({
    step: "validate-version-contract",
    status: changeType === "major" ? "warn" : "pass",
    detail: `Version transition accepted (old=${existing.version}, new=${sourceManifest.version}, change=${changeType}).`,
  });

  const oldInterface = (existing.manifest as unknown as Record<string, unknown>).interface_version;
  const newInterface = (sourceManifest as unknown as Record<string, unknown>).interface_version;
  if (
    typeof oldInterface === "string" &&
    typeof newInterface === "string" &&
    oldInterface !== newInterface
  ) {
    steps.push({
      step: "validate-compatibility",
      status: "fail",
      detail: `interface_version mismatch (old=${oldInterface}, new=${newInterface}).`,
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: sourceManifest.version,
      changeType,
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Interface compatibility check failed.",
    };
  }

  steps.push({
    step: "validate-compatibility",
    status: "pass",
    detail: "Structure and interface compatibility checks passed.",
  });

  const destinationPath = existing.absolutePath;
  if (!isWithin(destinationPath, TLS_TEMPLATES_ROOT) || isForbiddenInstallPath(destinationPath)) {
    steps.push({
      step: "validate-safe-path",
      status: "fail",
      detail: `Unsafe destination blocked: ${destinationPath}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: sourceManifest.version,
      changeType,
      replacedFiles: [],
      registryAction: "already-clean",
      steps,
      error: "Unsafe destination path.",
    };
  }

  steps.push({
    step: "validate-safe-path",
    status: "pass",
    detail: `Safe destination resolved: ${toPosix(path.relative(process.cwd(), destinationPath))}`,
  });

  const replacedFiles = await listDirectoryFilesRelative(sourcePath);
  const registryEntries = await loadRegistryEntries();
  const registryIndex = registryEntries.findIndex((entry) => entry.name === existing.name);
  const nextRegistryEntry: TlsRegistryEntry = {
    name: existing.name,
    type: existing.manifest.type,
    version: sourceManifest.version,
    status: sourceManifest.status,
    path: `templates/${existing.path}`,
  };

  const registryAction: TlsUpdateResult["registryAction"] =
    registryIndex < 0
      ? "updated"
      : asString(registryEntries[registryIndex]?.version) === nextRegistryEntry.version &&
          asString(registryEntries[registryIndex]?.status) === nextRegistryEntry.status &&
          asString(registryEntries[registryIndex]?.path) === nextRegistryEntry.path &&
          asString(registryEntries[registryIndex]?.type) === nextRegistryEntry.type
        ? "already-clean"
        : "updated";

  if (dryRun) {
    steps.push({
      step: "plan-replacement",
      status: "warn",
      detail: `Dry-run only. Files to replace: ${replacedFiles.length}`,
    });
    steps.push({
      step: "update-registry",
      status: "warn",
      detail:
        registryIndex < 0
          ? "Dry-run only. Would add registry entry for updated template."
          : registryAction === "updated"
            ? "Dry-run only. Would update registry entry."
            : "Dry-run only. Registry already clean.",
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: sourceManifest.version,
      changeType,
      replacedFiles,
      registryAction,
      steps,
    };
  }

  const backupPath = path.join(
    TLS_ROOT,
    ".tmp",
    `tls-update-backup-${existing.name}-${Date.now()}`,
  );
  await fs.mkdir(path.dirname(backupPath), { recursive: true });

  let backupCreated = false;
  try {
    await fs.cp(destinationPath, backupPath, { recursive: true });
    backupCreated = true;
    await fs.rm(destinationPath, { recursive: true, force: false });
    await fs.cp(sourcePath, destinationPath, { recursive: true });

    const installedManifestPath = path.join(destinationPath, "template.json");
    const installedManifestRaw = await fs.readFile(installedManifestPath, "utf8");
    const installedManifest = JSON.parse(installedManifestRaw) as TemplateManifest & Record<string, unknown>;
    installedManifest.name = existing.name;
    installedManifest.type = existing.manifest.type;
    installedManifest.version = sourceManifest.version;
    await fs.writeFile(installedManifestPath, `${JSON.stringify(installedManifest, null, 2)}\n`, "utf8");

    steps.push({
      step: "apply-update",
      status: "pass",
      detail: `Template files replaced: ${replacedFiles.length}`,
    });

    const nextRegistryEntries = [...registryEntries];
    if (registryIndex >= 0) {
      nextRegistryEntries[registryIndex] = {
        ...nextRegistryEntries[registryIndex],
        ...nextRegistryEntry,
      };
    } else {
      nextRegistryEntries.push(nextRegistryEntry);
    }
    await saveRegistryEntries(nextRegistryEntries);
    steps.push({
      step: "update-registry",
      status: "pass",
      detail: registryIndex < 0 ? "Registry entry added." : "Registry entry updated.",
    });
  } catch (error) {
    if (backupCreated) {
      try {
        await fs.rm(destinationPath, { recursive: true, force: true });
        await fs.cp(backupPath, destinationPath, { recursive: true });
      } catch {
        // Best-effort rollback; primary error is returned below.
      }
    }
    steps.push({
      step: "apply-update",
      status: "fail",
      detail: error instanceof Error ? error.message : "Update apply failed.",
    });
    return {
      ok: false,
      dryRun,
      templateName: existing.name,
      resolvedPath: `tls/templates/${existing.path}`,
      oldVersion: existing.version,
      newVersion: sourceManifest.version,
      changeType,
      replacedFiles,
      registryAction: "already-clean",
      steps,
      error: "Update failed and rollback applied.",
    };
  } finally {
    if (backupCreated) {
      await fs.rm(backupPath, { recursive: true, force: true });
    }
  }

  return {
    ok: true,
    dryRun,
    templateName: existing.name,
    resolvedPath: `tls/templates/${existing.path}`,
    oldVersion: existing.version,
    newVersion: sourceManifest.version,
    changeType,
    replacedFiles,
    registryAction,
    steps,
  };
}

export async function installTlsTemplate(
  options: TlsInstallOptions,
): Promise<TlsInstallResult> {
  const steps: TlsInstallResult["steps"] = [];
  const dryRun = options.dryRun === true;
  const sourcePath = path.resolve(options.sourcePath);
  const folderType = normalizeTypeFolder(options.type);
  const destinationPath = path.join(TLS_TEMPLATES_ROOT, folderType, options.name);

  if (!(await pathExists(sourcePath))) {
    steps.push({
      step: "validate-source-exists",
      status: "fail",
      detail: `Source path does not exist: ${sourcePath}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: options.name,
      resolvedPath: toPosix(path.relative(process.cwd(), destinationPath)),
      installedFiles: 0,
      registryAction: "already-clean",
      steps,
      error: "Source path does not exist.",
    };
  }

  const sourceStats = await fs.stat(sourcePath);
  if (!sourceStats.isDirectory()) {
    steps.push({
      step: "validate-source-exists",
      status: "fail",
      detail: `Source path is not a directory: ${sourcePath}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: options.name,
      resolvedPath: toPosix(path.relative(process.cwd(), destinationPath)),
      installedFiles: 0,
      registryAction: "already-clean",
      steps,
      error: "Source path must be a directory.",
    };
  }

  steps.push({
    step: "validate-source-exists",
    status: "pass",
    detail: `Source template directory found: ${sourcePath}`,
  });

  if (!validateInstallName(options.name)) {
    steps.push({
      step: "validate-install-name",
      status: "fail",
      detail: `Install name must be kebab-case [a-z0-9-]: ${options.name}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: options.name,
      resolvedPath: toPosix(path.relative(process.cwd(), destinationPath)),
      installedFiles: 0,
      registryAction: "already-clean",
      steps,
      error: "Invalid install name format.",
    };
  }

  steps.push({
    step: "validate-install-name",
    status: "pass",
    detail: "Install name is valid kebab-case.",
  });

  const sourceValidation = await validateTemplateStructureAtPath(sourcePath);
  if (sourceValidation.issues.length > 0 || sourceValidation.manifest === null) {
    steps.push({
      step: "validate-source-structure",
      status: "fail",
      detail: sourceValidation.issues.join("; "),
    });
    return {
      ok: false,
      dryRun,
      templateName: options.name,
      resolvedPath: toPosix(path.relative(process.cwd(), destinationPath)),
      installedFiles: 0,
      registryAction: "already-clean",
      steps,
      error: "Source template structure validation failed.",
    };
  }

  steps.push({
    step: "validate-source-structure",
    status: "pass",
    detail:
      sourceValidation.warnings.length > 0
        ? sourceValidation.warnings.join("; ")
        : "Source template structure is valid.",
  });

  const resolvedDestination = path.resolve(destinationPath);
  if (!isWithin(resolvedDestination, TLS_TEMPLATES_ROOT) || isForbiddenInstallPath(resolvedDestination)) {
    steps.push({
      step: "validate-safe-destination",
      status: "fail",
      detail: `Unsafe destination path blocked: ${resolvedDestination}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: options.name,
      resolvedPath: toPosix(path.relative(process.cwd(), destinationPath)),
      installedFiles: 0,
      registryAction: "already-clean",
      steps,
      error: "Unsafe destination path.",
    };
  }

  steps.push({
    step: "validate-safe-destination",
    status: "pass",
    detail: `Destination constrained to tls/templates: ${toPosix(path.relative(process.cwd(), resolvedDestination))}`,
  });

  const destinationExists = await pathExists(resolvedDestination);
  if (destinationExists && !options.force) {
    steps.push({
      step: "validate-overwrite-policy",
      status: "fail",
      detail: "Destination already exists. Re-run with --force to overwrite.",
    });
    return {
      ok: false,
      dryRun,
      templateName: options.name,
      resolvedPath: toPosix(path.relative(process.cwd(), destinationPath)),
      installedFiles: await countDirectoryFiles(sourcePath),
      registryAction: "already-clean",
      steps,
      error: "Destination already exists and overwrite is disabled.",
    };
  }

  steps.push({
    step: "validate-overwrite-policy",
    status: destinationExists ? "warn" : "pass",
    detail: destinationExists
      ? "Destination exists and will be overwritten due to --force."
      : "Destination does not exist.",
  });

  const registryEntries = await loadRegistryEntries();
  const existingRegistryIndex = registryEntries.findIndex((entry) => entry.name === options.name);
  const sourceManifest = sourceValidation.manifest;
  const plannedRegistryEntry: TlsRegistryEntry = {
    name: options.name,
    type: options.type,
    version: sourceManifest.version,
    status: sourceManifest.status,
    path: `templates/${folderType}/${options.name}`,
  };

  const currentRegistryEntry = existingRegistryIndex >= 0 ? registryEntries[existingRegistryIndex] : null;
  const registryAction: TlsInstallResult["registryAction"] =
    currentRegistryEntry === null
      ? "added"
      : asString(currentRegistryEntry.type) === plannedRegistryEntry.type &&
          asString(currentRegistryEntry.version) === plannedRegistryEntry.version &&
          asString(currentRegistryEntry.status) === plannedRegistryEntry.status &&
          asString(currentRegistryEntry.path) === plannedRegistryEntry.path
        ? "already-clean"
        : "updated";

  const installedFiles = await countDirectoryFiles(sourcePath);
  if (dryRun) {
    steps.push({
      step: "install-template-directory",
      status: "warn",
      detail: `Dry-run only. Would copy to ${toPosix(path.relative(process.cwd(), resolvedDestination))}`,
    });
    steps.push({
      step: "update-registry",
      status: "warn",
      detail:
        registryAction === "added"
          ? "Dry-run only. Would add registry entry."
          : registryAction === "updated"
            ? "Dry-run only. Would update registry entry."
            : "Dry-run only. Registry already clean.",
    });
    return {
      ok: false,
      dryRun,
      templateName: options.name,
      resolvedPath: toPosix(path.relative(process.cwd(), destinationPath)),
      installedFiles,
      registryAction,
      steps,
    };
  }

  await fs.mkdir(path.dirname(resolvedDestination), { recursive: true });
  if (destinationExists && options.force) {
    await fs.rm(resolvedDestination, { recursive: true, force: false });
  }
  await fs.cp(sourcePath, resolvedDestination, { recursive: true });

  const installedManifestPath = path.join(resolvedDestination, "template.json");
  const installedManifestRaw = await fs.readFile(installedManifestPath, "utf8");
  const installedManifest = JSON.parse(installedManifestRaw) as TemplateManifest & Record<string, unknown>;
  installedManifest.name = options.name;
  installedManifest.type = options.type;
  await fs.writeFile(installedManifestPath, `${JSON.stringify(installedManifest, null, 2)}\n`, "utf8");

  steps.push({
    step: "install-template-directory",
    status: "pass",
    detail: `Installed template to ${toPosix(path.relative(process.cwd(), resolvedDestination))}`,
  });

  const nextRegistryEntries = [...registryEntries];
  if (existingRegistryIndex >= 0) {
    nextRegistryEntries[existingRegistryIndex] = {
      ...nextRegistryEntries[existingRegistryIndex],
      ...plannedRegistryEntry,
    };
  } else {
    nextRegistryEntries.push(plannedRegistryEntry);
  }
  await saveRegistryEntries(nextRegistryEntries);

  steps.push({
    step: "update-registry",
    status: "pass",
    detail:
      registryAction === "added"
        ? "Registry entry added."
        : registryAction === "updated"
          ? "Registry entry updated."
          : "Registry already clean.",
  });

  return {
    ok: true,
    dryRun,
    templateName: options.name,
    resolvedPath: toPosix(path.relative(process.cwd(), destinationPath)),
    installedFiles,
    registryAction,
    steps,
  };
}

export async function uninstallTlsTemplate(
  name: string,
  options?: TlsUninstallOptions,
): Promise<TlsUninstallResult> {
  const dryRun = options?.dryRun === true;
  const steps: TlsUninstallResult["steps"] = [];

  const template = await getTlsTemplateByName(name);
  if (!template) {
    steps.push({
      step: "validate-template-exists",
      status: "fail",
      detail: `Template not found: ${name}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: name,
      resolvedPath: "not enough evidence",
      removedFiles: 0,
      registryRemovedEntries: 0,
      registryAction: "already-clean",
      steps,
      error: `Template not found: ${name}`,
    };
  }

  steps.push({
    step: "validate-template-exists",
    status: "pass",
    detail: `Found template: ${template.name}`,
  });

  const resolvedPath = template.absolutePath;
  if (!isWithin(resolvedPath, TLS_TEMPLATES_ROOT)) {
    steps.push({
      step: "validate-safe-path",
      status: "fail",
      detail: `Resolved path is outside tls/templates: ${resolvedPath}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: template.name,
      resolvedPath: toPosix(path.relative(process.cwd(), resolvedPath)),
      removedFiles: 0,
      registryRemovedEntries: 0,
      registryAction: "already-clean",
      steps,
      error: "Unsafe uninstall path blocked.",
    };
  }

  if (isForbiddenUninstallPath(resolvedPath)) {
    steps.push({
      step: "validate-safe-path",
      status: "fail",
      detail: `Protected TLS path cannot be removed: ${resolvedPath}`,
    });
    return {
      ok: false,
      dryRun,
      templateName: template.name,
      resolvedPath: toPosix(path.relative(process.cwd(), resolvedPath)),
      removedFiles: 0,
      registryRemovedEntries: 0,
      registryAction: "already-clean",
      steps,
      error: "Protected TLS path uninstall blocked.",
    };
  }

  steps.push({
    step: "validate-safe-path",
    status: "pass",
    detail: "Resolved uninstall path is constrained within tls/templates.",
  });

  if (hasLiveUsageEvidence(template.manifest)) {
    steps.push({
      step: "validate-template-not-in-use",
      status: "fail",
      detail: `Template has live usage evidence (${resolveUsageEvidenceMessage(template.manifest)}).`,
    });
    return {
      ok: false,
      dryRun,
      templateName: template.name,
      resolvedPath: toPosix(path.relative(process.cwd(), resolvedPath)),
      removedFiles: 0,
      registryRemovedEntries: 0,
      registryAction: "already-clean",
      steps,
      error: "Template uninstall blocked due to live usage evidence.",
    };
  }

  steps.push({
    step: "validate-template-not-in-use",
    status: "pass",
    detail: "No live usage evidence detected.",
  });

  const removedFiles = await countDirectoryFiles(resolvedPath);
  const registryEntries = await loadRegistryEntries();
  const nextRegistryEntries = registryEntries.filter((entry) => entry.name !== template.name);
  const registryRemovedEntries = registryEntries.length - nextRegistryEntries.length;
  const registryAction: TlsUninstallResult["registryAction"] =
    registryRemovedEntries > 0 ? "updated" : "already-clean";

  if (dryRun) {
    steps.push({
      step: "remove-directory",
      status: "warn",
      detail: `Dry-run only. Would remove: ${toPosix(path.relative(process.cwd(), resolvedPath))}`,
    });
    steps.push({
      step: "update-registry",
      status: registryRemovedEntries > 0 ? "warn" : "warn",
      detail:
        registryRemovedEntries > 0
          ? `Dry-run only. Would remove ${registryRemovedEntries} registry entr${registryRemovedEntries === 1 ? "y" : "ies"}.`
          : "Dry-run only. Registry already clean (no matching entry).",
    });
    return {
      ok: false,
      dryRun,
      templateName: template.name,
      resolvedPath: toPosix(path.relative(process.cwd(), resolvedPath)),
      removedFiles,
      registryRemovedEntries,
      registryAction,
      steps,
    };
  }

  await fs.rm(resolvedPath, { recursive: true, force: false });
  steps.push({
    step: "remove-directory",
    status: "pass",
    detail: `Removed directory: ${toPosix(path.relative(process.cwd(), resolvedPath))}`,
  });

  if (registryRemovedEntries > 0) {
    await saveRegistryEntries(nextRegistryEntries);
    steps.push({
      step: "update-registry",
      status: "pass",
      detail: `Removed ${registryRemovedEntries} registry entr${registryRemovedEntries === 1 ? "y" : "ies"}.`,
    });
  } else {
    steps.push({
      step: "update-registry",
      status: "warn",
      detail: "Registry already clean (no matching entry).",
    });
  }

  return {
    ok: true,
    dryRun,
    templateName: template.name,
    resolvedPath: toPosix(path.relative(process.cwd(), resolvedPath)),
    removedFiles,
    registryRemovedEntries,
    registryAction,
    steps,
  };
}
