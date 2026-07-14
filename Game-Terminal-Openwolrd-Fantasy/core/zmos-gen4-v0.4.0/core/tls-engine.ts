import { promises as fs } from "node:fs";
import * as path from "node:path";
import { execSync } from "node:child_process";

// ─── Types ────────────────────────────────────────────────────────────

export interface TemplateManifest {
  name: string;
  version: string;
  type: "landing" | "booking" | "admin" | "member" | "bundle";
  status: string;
  description: string;
  compatible_with: string[];
  required_modules: string[];
  config_schema: string;
  package_support: string[];
  created_from_project: string;
  source_project: string;
  source_project_version: string;
  last_extracted_at: string;
  last_promoted_at: string;
  promotion_history: Array<{
    status: string;
    date: string;
    agent: string;
    note?: string;
  }>;
  last_validated_at: string;
  author: string;
  entry_point?: string;
  build_command?: string;
  install_command?: string;
}

export interface FeatureFlags {
  visible: boolean;
  enabled: boolean;
}

export interface ShopConfig {
  shop: { name: string; slug: string; [key: string]: unknown };
  branding: { primary_color: string; [key: string]: unknown };
  services: Array<{ name: string; price: number; [key: string]: unknown }>;
  hours: Record<string, unknown>;
  features: Record<string, FeatureFlags>;
  package: "basic" | "pro" | "premium";
  [key: string]: unknown;
}

export interface TlsCreateOptions {
  templatePath: string;
  configPath: string;
  outputDir: string;
  packageOverride?: string;
  force?: boolean;
}

export interface TlsCreateResult {
  success: boolean;
  projectPath: string;
  templateName: string;
  templateVersion: string;
  configApplied: boolean;
  steps: StepResult[];
  error?: string;
}

interface StepResult {
  step: string;
  status: "pass" | "fail" | "skip";
  detail?: string;
}

// ─── Package Definitions ──────────────────────────────────────────────

const PACKAGE_FEATURES: Record<string, string[]> = {
  basic: ["landing", "services", "map", "contact"],
  pro: [
    "landing", "services", "map", "contact",
    "staff", "gallery", "booking", "admin",
  ],
  premium: [
    "landing", "services", "map", "contact",
    "staff", "gallery", "booking", "admin",
    "promotions", "payments", "reviews",
  ],
};

// ─── Helpers ──────────────────────────────────────────────────────────

function resolveTlsRoot(): string {
  return path.join(process.cwd(), "tls");
}

function resolveTemplatePath(templateRelative: string): string {
  return path.join(resolveTlsRoot(), "templates", templateRelative);
}

// ─── Core Functions ───────────────────────────────────────────────────

export async function loadTemplate(
  templateDir: string,
): Promise<TemplateManifest> {
  const manifestPath = path.join(templateDir, "template.json");

  let raw: string;
  try {
    raw = await fs.readFile(manifestPath, "utf8");
  } catch {
    throw new Error(`Template manifest not found: ${manifestPath}`);
  }

  let manifest: unknown;
  try {
    manifest = JSON.parse(raw) as unknown;
  } catch {
    throw new Error(`Invalid JSON in template manifest: ${manifestPath}`);
  }

  return manifest as TemplateManifest;
}

export function validateTemplate(manifest: TemplateManifest): string[] {
  const errors: string[] = [];

  if (!manifest.name || typeof manifest.name !== "string") {
    errors.push("template.json: missing or invalid 'name'");
  }
  if (!manifest.version || !/^\d+\.\d+\.\d+$/.test(manifest.version)) {
    errors.push("template.json: missing or invalid 'version' (must be semver)");
  }
  if (
    !manifest.type ||
    !["landing", "booking", "admin", "member", "bundle"].includes(manifest.type)
  ) {
    errors.push(
      "template.json: missing or invalid 'type' (must be landing|booking|admin|member|bundle)",
    );
  }
  if (!manifest.description || typeof manifest.description !== "string") {
    errors.push("template.json: missing or invalid 'description'");
  }
  if (!Array.isArray(manifest.package_support) || manifest.package_support.length === 0) {
    errors.push("template.json: missing or empty 'package_support'");
  }

  return errors;
}

export function validateConfig(config: ShopConfig): string[] {
  const errors: string[] = [];

  if (!config.shop || typeof config.shop.name !== "string") {
    errors.push("config: missing shop.name");
  }
  if (!config.shop || typeof config.shop.slug !== "string") {
    errors.push("config: missing shop.slug");
  }
  if (
    !config.branding ||
    typeof config.branding.primary_color !== "string" ||
    !/^#[0-9A-Fa-f]{6}$/.test(config.branding.primary_color)
  ) {
    errors.push("config: missing or invalid branding.primary_color (must be #HEX)");
  }
  if (!Array.isArray(config.services) || config.services.length === 0) {
    errors.push("config: services must be a non-empty array");
  }
  if (!config.features || typeof config.features !== "object") {
    errors.push("config: missing features object");
  }
  if (!config.package || !["basic", "pro", "premium"].includes(config.package)) {
    errors.push("config: package must be basic|pro|premium");
  }

  // Validate each feature has visible + enabled
  if (config.features) {
    for (const [key, value] of Object.entries(config.features)) {
      if (typeof value.visible !== "boolean" || typeof value.enabled !== "boolean") {
        errors.push(
          `config: feature '${key}' must have boolean 'visible' and 'enabled'`,
        );
      }
    }
  }

  return errors;
}

export function validatePackageFeatures(
  config: ShopConfig,
  packageTier?: string,
): string[] {
  const errors: string[] = [];
  const tier = packageTier || config.package;
  const allowed = PACKAGE_FEATURES[tier];

  if (!allowed) {
    errors.push(`Unknown package tier: ${tier}`);
    return errors;
  }

  for (const [feature, flags] of Object.entries(config.features)) {
    if ((flags.visible || flags.enabled) && !allowed.includes(feature)) {
      errors.push(
        `Feature '${feature}' is enabled/visible but not included in package '${tier}'`,
      );
    }
  }

  return errors;
}

export async function applyConfig(
  outputDir: string,
  config: ShopConfig,
): Promise<void> {
  const configPath = path.join(outputDir, "shop-config.json");
  await fs.writeFile(configPath, JSON.stringify(config, null, 2), "utf8");
}

export async function resolveModules(
  manifest: TemplateManifest,
): Promise<{ resolved: string[]; missing: string[] }> {
  const tlsRoot = resolveTlsRoot();
  const resolved: string[] = [];
  const missing: string[] = [];

  for (const moduleName of manifest.required_modules) {
    // Check if module exists in TLS modules directory
    const parts = moduleName.split("-");
    const moduleType = parts[0]; // e.g., "auth" from "auth-line-v1"
    const modulePath = path.join(tlsRoot, "modules", moduleType);

    try {
      await fs.access(modulePath);
      resolved.push(moduleName);
    } catch {
      missing.push(moduleName);
    }
  }

  return { resolved, missing };
}

export async function scaffoldProject(
  templateDir: string,
  outputDir: string,
  options: { force?: boolean },
): Promise<void> {
  // Check if output directory already exists
  try {
    await fs.access(outputDir);
    if (!options.force) {
      throw new Error(
        `Output directory already exists: ${outputDir} — use --force to overwrite`,
      );
    }
    // Force mode: remove existing
    await fs.rm(outputDir, { recursive: true });
  } catch (error) {
    if (
      error instanceof Error &&
      error.message.includes("already exists")
    ) {
      throw error;
    }
    // Directory doesn't exist — good, proceed
  }

  // Copy template to output
  await fs.cp(templateDir, outputDir, { recursive: true });
}

export function runPostSetup(
  outputDir: string,
  manifest: TemplateManifest,
): { installResult: string; buildResult: string } {
  const installCmd = manifest.install_command || "npm install";
  const buildCmd = manifest.build_command || "npm run build";

  let installResult: string;
  try {
    installResult = execSync(installCmd, {
      cwd: outputDir,
      encoding: "utf8",
      timeout: 120_000,
      stdio: ["pipe", "pipe", "pipe"],
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    installResult = `FAILED: ${message}`;
  }

  let buildResult: string;
  try {
    buildResult = execSync(buildCmd, {
      cwd: outputDir,
      encoding: "utf8",
      timeout: 120_000,
      stdio: ["pipe", "pipe", "pipe"],
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    buildResult = `FAILED: ${message}`;
  }

  return { installResult, buildResult };
}

// ─── Main Orchestrator ────────────────────────────────────────────────

export async function tlsCreate(
  options: TlsCreateOptions,
): Promise<TlsCreateResult> {
  const steps: StepResult[] = [];
  const templateDir = resolveTemplatePath(options.templatePath);
  const outputDir = path.resolve(options.outputDir);

  // Step 1: Validate template exists
  try {
    await fs.access(templateDir);
    steps.push({ step: "validate-template-exists", status: "pass" });
  } catch {
    steps.push({
      step: "validate-template-exists",
      status: "fail",
      detail: `Template not found: ${templateDir}`,
    });
    return {
      success: false,
      projectPath: outputDir,
      templateName: options.templatePath,
      templateVersion: "unknown",
      configApplied: false,
      steps,
      error: `Template not found: ${options.templatePath}`,
    };
  }

  // Step 2: Load template.json
  let manifest: TemplateManifest;
  try {
    manifest = await loadTemplate(templateDir);
    steps.push({ step: "load-template-manifest", status: "pass" });
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    steps.push({
      step: "load-template-manifest",
      status: "fail",
      detail: msg,
    });
    return {
      success: false,
      projectPath: outputDir,
      templateName: options.templatePath,
      templateVersion: "unknown",
      configApplied: false,
      steps,
      error: msg,
    };
  }

  // Step 2c: Status Enforcement
  const restrictedStatuses = ["draft", "deprecated"];
  const warningStatuses = ["tested", "proven"];

  if (restrictedStatuses.includes(manifest.status)) {
    steps.push({
      step: "status-enforcement",
      status: "fail",
      detail: `Template status '${manifest.status}' is restricted from creation.`,
    });
    return {
      success: false,
      projectPath: outputDir,
      templateName: manifest.name,
      templateVersion: manifest.version,
      configApplied: false,
      steps,
      error: `Restricted template status: ${manifest.status}`,
    };
  }

  if (warningStatuses.includes(manifest.status)) {
    steps.push({
      step: "status-enforcement",
      status: "pass",
      detail: `WARNING: Template status is '${manifest.status}'. Use with caution.`,
    });
  } else {
    steps.push({ step: "status-enforcement", status: "pass", detail: `Status: ${manifest.status}` });
  }

  // Step 2b: Validate template manifest
  const templateErrors = validateTemplate(manifest);
  if (templateErrors.length > 0) {
    steps.push({
      step: "validate-template-manifest",
      status: "fail",
      detail: templateErrors.join("; "),
    });
    return {
      success: false,
      projectPath: outputDir,
      templateName: manifest.name || options.templatePath,
      templateVersion: manifest.version || "unknown",
      configApplied: false,
      steps,
      error: `Template validation failed: ${templateErrors.join("; ")}`,
    };
  }
  steps.push({ step: "validate-template-manifest", status: "pass" });

  // Step 3: Load and validate config
  let config: ShopConfig;
  try {
    const configRaw = await fs.readFile(path.resolve(options.configPath), "utf8");
    config = JSON.parse(configRaw) as ShopConfig;
    steps.push({ step: "load-config", status: "pass" });
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    steps.push({ step: "load-config", status: "fail", detail: msg });
    return {
      success: false,
      projectPath: outputDir,
      templateName: manifest.name,
      templateVersion: manifest.version,
      configApplied: false,
      steps,
      error: `Config load failed: ${msg}`,
    };
  }

  const configErrors = validateConfig(config);
  if (configErrors.length > 0) {
    steps.push({
      step: "validate-config",
      status: "fail",
      detail: configErrors.join("; "),
    });
    return {
      success: false,
      projectPath: outputDir,
      templateName: manifest.name,
      templateVersion: manifest.version,
      configApplied: false,
      steps,
      error: `Config validation failed: ${configErrors.join("; ")}`,
    };
  }
  steps.push({ step: "validate-config", status: "pass" });

  // Step 4: Validate package vs feature flags
  if (options.packageOverride) {
    config.package = options.packageOverride as "basic" | "pro" | "premium";
  }
  const packageErrors = validatePackageFeatures(config);
  if (packageErrors.length > 0) {
    steps.push({
      step: "validate-package-features",
      status: "fail",
      detail: packageErrors.join("; "),
    });
    return {
      success: false,
      projectPath: outputDir,
      templateName: manifest.name,
      templateVersion: manifest.version,
      configApplied: false,
      steps,
      error: `Package validation failed: ${packageErrors.join("; ")}`,
    };
  }
  steps.push({ step: "validate-package-features", status: "pass" });

  // Step 5: Copy template → output directory
  try {
    await scaffoldProject(templateDir, outputDir, { force: options.force });
    steps.push({ step: "scaffold-project", status: "pass" });
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    steps.push({ step: "scaffold-project", status: "fail", detail: msg });
    return {
      success: false,
      projectPath: outputDir,
      templateName: manifest.name,
      templateVersion: manifest.version,
      configApplied: false,
      steps,
      error: `Scaffold failed: ${msg}`,
    };
  }

  // Step 6: Inject config
  try {
    await applyConfig(outputDir, config);
    steps.push({ step: "apply-config", status: "pass" });
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    steps.push({ step: "apply-config", status: "fail", detail: msg });
    return {
      success: false,
      projectPath: outputDir,
      templateName: manifest.name,
      templateVersion: manifest.version,
      configApplied: false,
      steps,
      error: `Config apply failed: ${msg}`,
    };
  }

  // Step 7: Resolve required modules
  const moduleResult = await resolveModules(manifest);
  if (moduleResult.missing.length > 0) {
    steps.push({
      step: "resolve-modules",
      status: "pass",
      detail: `resolved: ${moduleResult.resolved.join(", ") || "none"}; missing: ${moduleResult.missing.join(", ")}`,
    });
  } else {
    steps.push({
      step: "resolve-modules",
      status: "pass",
      detail:
        manifest.required_modules.length === 0
          ? "no modules required"
          : `all resolved: ${moduleResult.resolved.join(", ")}`,
    });
  }

  // Step 8-9: Install + Build (only if package.json exists in output)
  const hasPackageJson = await fs
    .access(path.join(outputDir, "package.json"))
    .then(() => true)
    .catch(() => false);

  if (hasPackageJson) {
    const postSetup = runPostSetup(outputDir, manifest);

    if (postSetup.installResult.startsWith("FAILED")) {
      steps.push({
        step: "install-dependencies",
        status: "fail",
        detail: postSetup.installResult,
      });
    } else {
      steps.push({ step: "install-dependencies", status: "pass" });
    }

    if (postSetup.buildResult.startsWith("FAILED")) {
      steps.push({
        step: "build-project",
        status: "fail",
        detail: postSetup.buildResult,
      });
    } else {
      steps.push({ step: "build-project", status: "pass" });
    }
  } else {
    steps.push({
      step: "install-dependencies",
      status: "skip",
      detail: "no package.json in template",
    });
    steps.push({
      step: "build-project",
      status: "skip",
      detail: "no package.json in template",
    });
  }

  const hasFailed = steps.some((s) => s.status === "fail");

  return {
    success: !hasFailed,
    projectPath: outputDir,
    templateName: manifest.name,
    templateVersion: manifest.version,
    configApplied: true,
    steps,
    error: hasFailed ? "One or more steps failed (see steps for details)" : undefined,
  };
}
