import * as readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";

import { tlsCreate } from "../../core/tls-engine.js";
import type { TlsCreateOptions } from "../../core/tls-engine.js";
import {
  evaluateTlsRegistrySync,
  getTlsTemplateByName,
  installTlsTemplate,
  listTlsTemplates,
  uninstallTlsTemplate,
  updateTlsTemplate,
  validateTlsTemplate,
} from "../../core/tls-library.js";
import { evaluateMutationGuard } from "../../core/mutation-guard.js";
import { appendTraceRecord } from "../../trace/writer.js";

function parseCreateArgs(argv: string[]): TlsCreateOptions | null {
  let templatePath = "";
  let configPath = "";
  let outputDir = "";
  let packageOverride: string | undefined;
  let force = false;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];

    if (arg === "--template" && argv[i + 1]) {
      templatePath = argv[++i];
      continue;
    }
    if (arg?.startsWith("--template=")) {
      templatePath = arg.split("=")[1];
      continue;
    }

    if (arg === "--config" && argv[i + 1]) {
      configPath = argv[++i];
      continue;
    }
    if (arg?.startsWith("--config=")) {
      configPath = arg.split("=")[1];
      continue;
    }

    if (arg === "--output" && argv[i + 1]) {
      outputDir = argv[++i];
      continue;
    }
    if (arg?.startsWith("--output=")) {
      outputDir = arg.split("=")[1];
      continue;
    }

    if (arg === "--package" && argv[i + 1]) {
      packageOverride = argv[++i];
      continue;
    }
    if (arg?.startsWith("--package=")) {
      packageOverride = arg.split("=")[1];
      continue;
    }

    if (arg === "--force") {
      force = true;
      continue;
    }
  }

  if (!templatePath || !configPath || !outputDir) {
    return null;
  }

  return { templatePath, configPath, outputDir, packageOverride, force };
}

function parseListArgs(argv: string[]): {
  type?: string;
  status?: string;
  json: boolean;
} {
  let type: string | undefined;
  let status: string | undefined;
  let json = false;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--json") {
      json = true;
      continue;
    }

    if (arg === "--type" && argv[i + 1]) {
      type = argv[++i];
      continue;
    }
    if (arg.startsWith("--type=")) {
      type = arg.split("=")[1];
      continue;
    }

    if (arg === "--status" && argv[i + 1]) {
      status = argv[++i];
      continue;
    }
    if (arg.startsWith("--status=")) {
      status = arg.split("=")[1];
      continue;
    }
  }

  return { type, status, json };
}

function parseUninstallArgs(argv: string[]): {
  name: string;
  dryRun: boolean;
  force: boolean;
} | null {
  let name = "";
  let dryRun = false;
  let force = false;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--dry-run") {
      dryRun = true;
      continue;
    }
    if (arg === "--force") {
      force = true;
      continue;
    }
    if (!arg.startsWith("-") && !name) {
      name = arg;
    }
  }

  if (!name) {
    return null;
  }

  return { name, dryRun, force };
}

function parseInstallArgs(argv: string[]): {
  sourcePath: string;
  type: "landing" | "booking" | "admin" | "member" | "bundle";
  name: string;
  dryRun: boolean;
  force: boolean;
} | null {
  let sourcePath = "";
  let type = "";
  let name = "";
  let dryRun = false;
  let force = false;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--dry-run") {
      dryRun = true;
      continue;
    }
    if (arg === "--force") {
      force = true;
      continue;
    }
    if ((arg === "--source" || arg === "-s") && argv[i + 1]) {
      sourcePath = argv[++i];
      continue;
    }
    if (arg.startsWith("--source=")) {
      sourcePath = arg.split("=")[1] || "";
      continue;
    }
    if ((arg === "--type" || arg === "-t") && argv[i + 1]) {
      type = argv[++i];
      continue;
    }
    if (arg.startsWith("--type=")) {
      type = arg.split("=")[1] || "";
      continue;
    }
    if ((arg === "--name" || arg === "-n") && argv[i + 1]) {
      name = argv[++i];
      continue;
    }
    if (arg.startsWith("--name=")) {
      name = arg.split("=")[1] || "";
      continue;
    }
  }

  if (!sourcePath || !type || !name) {
    return null;
  }

  if (!["landing", "booking", "admin", "member", "bundle"].includes(type)) {
    return null;
  }

  return {
    sourcePath,
    type: type as "landing" | "booking" | "admin" | "member" | "bundle",
    name,
    dryRun,
    force,
  };
}

function parseUpdateArgs(argv: string[]): {
  name: string;
  sourcePath: string;
  dryRun: boolean;
  force: boolean;
} | null {
  let name = "";
  let sourcePath = "";
  let dryRun = false;
  let force = false;

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--dry-run") {
      dryRun = true;
      continue;
    }
    if (arg === "--force") {
      force = true;
      continue;
    }
    if ((arg === "--name" || arg === "-n") && argv[i + 1]) {
      name = argv[++i] || "";
      continue;
    }
    if (arg.startsWith("--name=")) {
      name = arg.split("=")[1] || "";
      continue;
    }
    if ((arg === "--source" || arg === "-s") && argv[i + 1]) {
      sourcePath = argv[++i] || "";
      continue;
    }
    if (arg.startsWith("--source=")) {
      sourcePath = arg.split("=")[1] || "";
      continue;
    }
  }

  if (!name || !sourcePath) {
    return null;
  }

  return { name, sourcePath, dryRun, force };
}

function printUninstallTaskHeader(status: "PASS" | "FAIL" | "WARNING"): void {
  console.log("Agent: Codex");
  console.log("Task: ZMOS-TLS-UNINSTALL-001");
  console.log("Tier: TIER 2");
  console.log(`Status: ${status}`);
  console.log("Memory: MEDIUM");
  console.log("");
}

function printInstallTaskHeader(status: "PASS" | "FAIL" | "WARNING"): void {
  console.log("Agent: Codex");
  console.log("Task: ZMOS-TLS-INSTALL-001");
  console.log("Tier: TIER 2");
  console.log(`Status: ${status}`);
  console.log("Memory: MEDIUM");
  console.log("");
}

function printUpdateTaskHeader(status: "PASS" | "FAIL" | "WARNING"): void {
  console.log("Agent: Codex");
  console.log("Task: ZMOS-TLS-UPDATE-001");
  console.log("Tier: TIER 1");
  console.log(`Status: ${status}`);
  console.log("Memory: HIGH");
  console.log("");
}

function stepIcon(status: "pass" | "warn" | "fail"): string {
  if (status === "pass") {
    return "✅";
  }
  if (status === "warn") {
    return "⚠️";
  }
  return "❌";
}

function printInstallUsage(): void {
  console.error(
    [
      "Usage:",
      "  zcl tls install --source <path> --type <type> --name <name> [--dry-run] [--force]",
      "",
      "Types:",
      "  landing | booking | admin | member | bundle",
      "",
      "Examples:",
      "  zcl tls install --source ./backup/template --type landing --name spa-landing-v1 --dry-run",
      "  zcl tls install --source ./backup/template --type landing --name spa-landing-v1",
      "  zcl tls install --source ./backup/template --type landing --name spa-landing-v1 --force",
    ].join("\n"),
  );
}

function printUpdateUsage(): void {
  console.error(
    [
      "Usage:",
      "  zcl tls update --name <name> --source <path> [--dry-run] [--force]",
      "",
      "Examples:",
      "  zcl tls update --name premium-massage-v1 --source /tmp/premium-massage-v1.next --dry-run",
      "  zcl tls update --name premium-massage-v1 --source /tmp/premium-massage-v1.next",
      "  zcl tls update --name premium-massage-v1 --source /tmp/premium-massage-v1.v2 --force",
    ].join("\n"),
  );
}

function printUninstallReport(args: {
  status: "PASS" | "FAIL" | "WARNING";
  template: string;
  path: string;
  steps: Array<{ step: string; status: "pass" | "warn" | "fail"; detail: string }>;
  resultLine: string;
  removedLine: string;
  registryLine: string;
}): void {
  printUninstallTaskHeader(args.status);
  console.log("Z-MOS TLS Uninstall");
  console.log("");
  console.log(`Template: ${args.template}`);
  console.log(`Path: ${args.path}`);
  console.log("");
  console.log("Execution:");
  for (const step of args.steps) {
    console.log(`- ${step.step} ${stepIcon(step.status)}`);
    console.log(`  ${step.detail}`);
  }
  console.log("");
  console.log(args.resultLine);
  console.log(args.removedLine);
  console.log(args.registryLine);
}

async function confirmUninstall(name: string, resolvedPath: string): Promise<boolean> {
  const rl = readline.createInterface({ input, output });
  try {
    const answer = await rl.question(
      `Confirm uninstall template '${name}' at '${resolvedPath}'? (y/N): `,
    );
    const normalized = answer.trim().toLowerCase();
    return normalized === "y" || normalized === "yes";
  } finally {
    rl.close();
  }
}

function printCreateUsage(): void {
  console.error(
    [
      "Usage:",
      "  zcl tls create --template <path> --config <file> --output <dir>",
      "",
      "Options:",
      "  --template  Template path relative to tls/templates/",
      "  --config    Path to shop-config.json",
      "  --output    Output directory for new project",
      "  --package   Override package tier (basic|pro|premium)",
      "  --force     Overwrite output directory if exists",
      "",
      "Example:",
      "  zcl tls create \\",
      "    --template landing/premium-massage-v1 \\",
      "    --config ./shop-config.json \\",
      "    --output ./projects/my-new-shop",
    ].join("\n"),
  );
}

function printMutationBlockedResult(args: {
  title: string;
  reason: string;
  warnings: string[];
}): void {
  console.log(args.title);
  console.log("");
  console.log("Result: FAILED");
  console.log(`Reason: ${args.reason}`);
  if (args.warnings.length > 0) {
    console.log(`Warnings: ${args.warnings.join(" | ")}`);
  }
  console.log("Action: Set lifecycle.status=active and align manifest scope.mutation before retrying.");
}

export async function runTlsCreateCommand(argv: string[]): Promise<void> {
  const options = parseCreateArgs(argv);

  if (!options) {
    printCreateUsage();
    process.exitCode = 1;
    return;
  }

  const mutationGuard = await evaluateMutationGuard({
    command: "zcl tls create",
    targetPaths: [options.outputDir],
  });
  if (!mutationGuard.allowed) {
    printMutationBlockedResult({
      title: "Z-MOS TLS Create",
      reason: mutationGuard.reason,
      warnings: mutationGuard.warnings,
    });
    process.exitCode = 1;
    return;
  }

  console.log("Z-MOS TLS Create");
  console.log(`  Template: ${options.templatePath}`);
  console.log(`  Config:   ${options.configPath}`);
  console.log(`  Output:   ${options.outputDir}`);
  if (options.packageOverride) {
    console.log(`  Package:  ${options.packageOverride} (override)`);
  }
  if (options.force) {
    console.log("  Force:    yes");
  }
  console.log("");

  const result = await tlsCreate(options);

  console.log("Execution Steps:");
  for (const step of result.steps) {
    const icon =
      step.status === "pass" ? "✅" : step.status === "fail" ? "❌" : "⏭️";
    console.log(`  ${icon} ${step.step}`);
    if (step.detail) {
      console.log(`     ${step.detail}`);
    }
  }

  console.log("");

  if (result.success) {
    console.log("Result: SUCCESS");
    console.log(`  Project created at: ${result.projectPath}`);
    console.log(`  Template: ${result.templateName} v${result.templateVersion}`);
    console.log(`  Config applied: ${result.configApplied}`);
    process.exitCode = 0;
  } else {
    console.log("Result: FAILED");
    console.log(`  Error: ${result.error}`);
    process.exitCode = 1;
  }
}

export async function runTlsListCommand(argv: string[]): Promise<void> {
  const options = parseListArgs(argv);
  const templates = await listTlsTemplates();

  const filtered = templates.filter((template) => {
    if (options.type && template.type !== options.type) {
      return false;
    }
    if (options.status && template.status !== options.status) {
      return false;
    }
    return true;
  });

  const records = filtered.map((template) => ({
    name: template.name,
    type: template.type,
    version: template.version,
    status: template.status,
    path: `tls/templates/${template.path}`,
  }));

  if (options.json) {
    console.log(JSON.stringify({ templates: records }, null, 2));
    return;
  }

  console.log("Z-MOS TLS Template List");
  console.log(`- total: ${records.length}`);
  if (options.type) {
    console.log(`- filter type: ${options.type}`);
  }
  if (options.status) {
    console.log(`- filter status: ${options.status}`);
  }
  console.log("");

  if (records.length === 0) {
    console.log("(no templates matched)");
    return;
  }

  for (const record of records) {
    console.log(`${record.name}`);
    console.log(`  type: ${record.type}`);
    console.log(`  version: ${record.version}`);
    console.log(`  status: ${record.status}`);
    console.log(`  path: ${record.path}`);
  }
}

export async function runTlsShowCommand(name: string): Promise<void> {
  const template = await getTlsTemplateByName(name);
  if (!template) {
    console.error(`TLS template not found: ${name}`);
    process.exitCode = 1;
    return;
  }

  console.log("Z-MOS TLS Template Details");
  console.log(`- query: ${name}`);
  console.log(`- resolved: ${template.name}`);
  console.log(`- path: tls/templates/${template.path}`);
  console.log("");
  console.log(JSON.stringify(template.manifest, null, 2));
}

export async function runTlsValidateCommand(name: string): Promise<void> {
  const template = await getTlsTemplateByName(name);
  if (!template) {
    console.error(`TLS template not found: ${name}`);
    process.exitCode = 1;
    return;
  }

  const result = await validateTlsTemplate(template);
  console.log("Z-MOS TLS Template Validation");
  console.log(`- template: ${result.template.name}`);
  console.log(`- path: tls/templates/${result.template.path}`);
  console.log(`- status: ${result.pass ? "PASS" : "FAIL"}`);
  console.log("");

  console.log("Issues");
  if (result.issues.length === 0) {
    console.log("- (none)");
  } else {
    for (const issue of result.issues) {
      console.log(`- ${issue}`);
    }
  }

  console.log("");
  console.log("Warnings");
  if (result.warnings.length === 0) {
    console.log("- (none)");
  } else {
    for (const warning of result.warnings) {
      console.log(`- ${warning}`);
    }
  }

  if (!result.pass) {
    process.exitCode = 1;
  }
}

export async function runTlsSyncCommand(argv: string[]): Promise<void> {
  if (argv.includes("--apply") || argv.includes("--write")) {
    console.error("TLS sync runs in safe report-only mode in Phase 1; mutation flags are not supported.");
    process.exitCode = 1;
    return;
  }

  const report = await evaluateTlsRegistrySync();
  console.log("Z-MOS TLS Registry Sync (Safe Mode)");
  console.log(`- registry: ${report.registryPath}`);
  console.log(`- filesystem templates: ${report.filesystemTemplateCount}`);
  console.log(`- registry templates: ${report.registryTemplateCount}`);
  console.log("");

  console.log("Drift: Missing In Registry (should add)");
  if (report.missingInRegistry.length === 0) {
    console.log("- (none)");
  } else {
    for (const entry of report.missingInRegistry) {
      console.log(
        `- ${entry.name} | type=${entry.type} version=${entry.version} status=${entry.status} path=${entry.path}`,
      );
    }
  }

  console.log("");
  console.log("Drift: Missing On Filesystem (registry stale; should remove/deprecate)");
  if (report.missingOnFilesystem.length === 0) {
    console.log("- (none)");
  } else {
    for (const entry of report.missingOnFilesystem) {
      console.log(
        `- ${entry.name} | type=${entry.type} version=${entry.version} status=${entry.status} path=${entry.path}`,
      );
    }
  }

  console.log("");
  console.log("Drift: Mismatched Entries (should update)");
  if (report.mismatched.length === 0) {
    console.log("- (none)");
  } else {
    for (const entry of report.mismatched) {
      console.log(`- ${entry.name} | fields=${entry.differences.join(", ")}`);
      console.log(
        `  filesystem: type=${entry.filesystem.type} version=${entry.filesystem.version} status=${entry.filesystem.status} path=${entry.filesystem.path}`,
      );
      console.log(
        `  registry:   type=${entry.registry.type} version=${entry.registry.version} status=${entry.registry.status} path=${entry.registry.path}`,
      );
    }
  }

  console.log("");
  console.log("Suggested Actions (report only)");
  console.log(`- add: ${report.suggested.add}`);
  console.log(`- update: ${report.suggested.update}`);
  console.log(`- remove/deprecate: ${report.suggested.remove}`);
}

export async function runTlsUninstallCommand(argv: string[]): Promise<void> {
  const options = parseUninstallArgs(argv);
  if (!options) {
    throw new Error("Usage: zcl tls uninstall <name> [--dry-run] [--force]");
  }

  const dryRunPreview = await uninstallTlsTemplate(options.name, { dryRun: true });
  if (dryRunPreview.error) {
    printUninstallReport({
      status: "FAIL",
      template: options.name,
      path: dryRunPreview.resolvedPath,
      steps: dryRunPreview.steps,
      resultLine: "Result: FAILED",
      removedLine: "Removed: 0 template",
      registryLine: "Registry: unchanged",
    });
    process.exitCode = 1;
    return;
  }

  if (options.dryRun) {
    printUninstallReport({
      status: "WARNING",
      template: dryRunPreview.templateName,
      path: dryRunPreview.resolvedPath,
      steps: dryRunPreview.steps,
      resultLine: "Result: DRY-RUN (no mutation)",
      removedLine: `Removed: 0 template (would remove files: ${dryRunPreview.removedFiles})`,
      registryLine:
        dryRunPreview.registryRemovedEntries > 0
          ? `Registry: would remove ${dryRunPreview.registryRemovedEntries} entr${dryRunPreview.registryRemovedEntries === 1 ? "y" : "ies"}`
          : "Registry: already clean",
    });
    process.exitCode = 1;
    return;
  }

  const mutationGuard = await evaluateMutationGuard({
    command: "zcl tls uninstall",
    targetPaths: ["tls/templates", "tls/registry/template-registry.json"],
    allowProtectedPrefixes: ["tls/templates", "tls/registry"],
  });
  if (!mutationGuard.allowed) {
    printUninstallReport({
      status: "FAIL",
      template: dryRunPreview.templateName,
      path: dryRunPreview.resolvedPath,
      steps: [
        ...dryRunPreview.steps,
        {
          step: "validate-mutation-guard",
          status: "fail",
          detail: `${mutationGuard.reason} ${
            mutationGuard.warnings.length > 0 ? `(${mutationGuard.warnings.join(" | ")})` : ""
          }`.trim(),
        },
      ],
      resultLine: "Result: FAILED",
      removedLine: "Removed: 0 template",
      registryLine: "Registry: unchanged",
    });
    process.exitCode = 1;
    return;
  }

  if (!options.force) {
    printUninstallTaskHeader("WARNING");
    console.log("Z-MOS TLS Uninstall");
    console.log("");
    console.log(`Template: ${dryRunPreview.templateName}`);
    console.log(`Path: ${dryRunPreview.resolvedPath}`);
    console.log("");
    console.log("Planned Execution:");
    for (const step of dryRunPreview.steps) {
      console.log(`- ${step.step} ${stepIcon(step.status)}`);
      console.log(`  ${step.detail}`);
    }
    console.log("");

    const confirmed = await confirmUninstall(dryRunPreview.templateName, dryRunPreview.resolvedPath);
    if (!confirmed) {
      console.log("Result: CANCELLED");
      console.log("Removed: 0 template");
      console.log("Registry: unchanged");
      process.exitCode = 1;
      return;
    }
  }

  const result = await uninstallTlsTemplate(options.name, { dryRun: false });
  if (!result.ok || result.error) {
    printUninstallReport({
      status: "FAIL",
      template: result.templateName,
      path: result.resolvedPath,
      steps: result.steps,
      resultLine: "Result: FAILED",
      removedLine: "Removed: 0 template",
      registryLine: "Registry: unchanged",
    });
    process.exitCode = 1;
    return;
  }

  printUninstallReport({
    status: result.registryAction === "already-clean" ? "WARNING" : "PASS",
    template: result.templateName,
    path: result.resolvedPath,
    steps: result.steps,
    resultLine: "Result: SUCCESS",
    removedLine: `Removed: 1 template (files: ${result.removedFiles})`,
    registryLine:
      result.registryAction === "updated"
        ? `Registry: removed ${result.registryRemovedEntries} entr${result.registryRemovedEntries === 1 ? "y" : "ies"}`
        : "Registry: unchanged (already clean)",
  });
}

export async function runTlsInstallCommand(argv: string[]): Promise<void> {
  const options = parseInstallArgs(argv);
  if (!options) {
    printInstallUsage();
    process.exitCode = 1;
    return;
  }

  if (!options.dryRun) {
    const mutationGuard = await evaluateMutationGuard({
      command: "zcl tls install",
      targetPaths: [
        `tls/templates/${options.type === "bundle" ? "bundles" : options.type}/${options.name}`,
        "tls/registry/template-registry.json",
      ],
      allowProtectedPrefixes: ["tls/templates", "tls/registry"],
    });
    if (!mutationGuard.allowed) {
      printInstallTaskHeader("FAIL");
      printMutationBlockedResult({
        title: "Z-MOS TLS Install",
        reason: mutationGuard.reason,
        warnings: mutationGuard.warnings,
      });
      process.exitCode = 1;
      return;
    }
  }

  const result = await installTlsTemplate({
    sourcePath: options.sourcePath,
    type: options.type,
    name: options.name,
    dryRun: options.dryRun,
    force: options.force,
  });

  const status: "PASS" | "FAIL" | "WARNING" =
    !result.ok ? (result.dryRun ? "WARNING" : "FAIL") : "PASS";

  printInstallTaskHeader(status);
  console.log("Z-MOS TLS Install");
  console.log("");
  console.log(`Source: ${options.sourcePath}`);
  console.log(`Type: ${options.type}`);
  console.log(`Name: ${options.name}`);
  console.log(`Path: ${result.resolvedPath}`);
  console.log(`Mode: ${result.dryRun ? "DRY-RUN" : options.force ? "FORCE" : "SAFE"}`);
  console.log("");
  console.log("Execution:");
  for (const step of result.steps) {
    console.log(`- ${step.step} ${stepIcon(step.status)}`);
    console.log(`  ${step.detail}`);
  }
  console.log("");

  if (result.ok) {
    console.log("Result: SUCCESS");
    console.log(`Installed: 1 template (files: ${result.installedFiles})`);
    console.log(`Registry: ${result.registryAction}`);
    process.exitCode = 0;
    return;
  }

  if (result.dryRun) {
    console.log("Result: DRY-RUN (no mutation)");
    console.log(`Installed: 0 template (would install files: ${result.installedFiles})`);
    console.log(`Registry: would-${result.registryAction}`);
    process.exitCode = 1;
    return;
  }

  console.log("Result: FAILED");
  console.log("Installed: 0 template");
  console.log("Registry: unchanged");
  if (result.error) {
    console.log(`Error: ${result.error}`);
  }
  process.exitCode = 1;
}

export async function runTlsUpdateCommand(argv: string[]): Promise<void> {
  const options = parseUpdateArgs(argv);
  if (!options) {
    printUpdateUsage();
    process.exitCode = 1;
    return;
  }

  if (!options.dryRun) {
    const mutationGuard = await evaluateMutationGuard({
      command: "zcl tls update",
      targetPaths: ["tls/templates", "tls/registry/template-registry.json"],
      allowProtectedPrefixes: ["tls/templates", "tls/registry"],
    });
    if (!mutationGuard.allowed) {
      printUpdateTaskHeader("FAIL");
      printMutationBlockedResult({
        title: "Z-MOS TLS Update",
        reason: mutationGuard.reason,
        warnings: mutationGuard.warnings,
      });
      process.exitCode = 1;
      return;
    }
  }

  const result = await updateTlsTemplate({
    name: options.name,
    sourcePath: options.sourcePath,
    dryRun: options.dryRun,
    force: options.force,
  });

  const status: "PASS" | "FAIL" | "WARNING" =
    result.ok ? "PASS" : result.dryRun ? "WARNING" : "FAIL";

  printUpdateTaskHeader(status);
  console.log("Z-MOS TLS Update");
  console.log("");
  console.log(`Name: ${options.name}`);
  console.log(`Source: ${options.sourcePath}`);
  console.log(`Path: ${result.resolvedPath}`);
  console.log(`Version: ${result.oldVersion} -> ${result.newVersion}`);
  console.log(`Change Type: ${result.changeType}`);
  console.log(`Mode: ${result.dryRun ? "DRY-RUN" : options.force ? "FORCE" : "SAFE"}`);
  console.log("");
  console.log("Execution:");
  for (const step of result.steps) {
    console.log(`- ${step.step} ${stepIcon(step.status)}`);
    console.log(`  ${step.detail}`);
  }
  console.log("");

  if (result.ok) {
    try {
      await appendTraceRecord({
        command: "zcl tls update",
        status: "success",
        actor: "system",
        details: {
          templateName: result.templateName,
          sourcePath: options.sourcePath,
          oldVersion: result.oldVersion,
          newVersion: result.newVersion,
          changeType: result.changeType,
          replacedFiles: result.replacedFiles.length,
          registryAction: result.registryAction,
        },
      });
    } catch (error) {
      console.log("Result: FAILED");
      console.log(`Updated: 1 template (files: ${result.replacedFiles.length})`);
      console.log(`Registry: ${result.registryAction}`);
      console.log(
        `Error: update applied but trace logging failed (${error instanceof Error ? error.message : "unknown error"})`,
      );
      process.exitCode = 1;
      return;
    }

    console.log("Result: SUCCESS");
    console.log(`Updated: 1 template (files replaced: ${result.replacedFiles.length})`);
    console.log(`Registry: ${result.registryAction}`);
    process.exitCode = 0;
    return;
  }

  if (result.dryRun) {
    console.log("Result: DRY-RUN (no mutation)");
    console.log(`Update Plan: files to replace = ${result.replacedFiles.length}`);
    console.log(`Registry: would-${result.registryAction}`);
    process.exitCode = 1;
    return;
  }

  console.log("Result: FAILED");
  console.log("Updated: 0 template");
  console.log("Registry: unchanged");
  if (result.error) {
    console.log(`Error: ${result.error}`);
  }
  process.exitCode = 1;
}
