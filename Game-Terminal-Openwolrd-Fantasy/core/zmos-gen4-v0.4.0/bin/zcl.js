#!/usr/bin/env node

import { accessSync, constants, existsSync, statSync } from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const invocationCwd = process.cwd();
const distGateway = path.join(rootDir, "dist", "cli", "gateway.js");
const sourceGateway = path.join(rootDir, "cli", "gateway.ts");
const rawArgs = process.argv.slice(2);
const devModeArgIndex = rawArgs.indexOf("--dev-ts");
const isDevTsMode =
  devModeArgIndex >= 0 || process.env.ZMOS_EXEC_MODE === "dev-ts";

if (devModeArgIndex >= 0) {
  rawArgs.splice(devModeArgIndex, 1);
}

const PROJECT_FACING_COMMANDS = new Set([
  "budget",
  "context",
  "doctor",
  "help",
  "lane",
  "load-data",
  "status",
  "sync",
  "recover",
  "stabilize",
]);

function classifyStartupFailure(output) {
  const normalized = output.toLowerCase();
  if (normalized.includes("dist not found")) {
    return {
      code: "dist-missing",
      likelyCause: "Compiled gateway artifact is missing.",
      nextAction: "Run npm run build, then retry zcl command.",
    };
  }
  if (
    normalized.includes("err_module_not_found") &&
    normalized.includes("tsx")
  ) {
    return {
      code: "tsx-missing",
      likelyCause: "TS runtime dependency tsx is not installed/resolved.",
      nextAction: "Run npm install and verify tsx resolves, or use ops-dist mode.",
    };
  }
  if (
    normalized.includes("transformerror") &&
    normalized.includes("esbuild")
  ) {
    return {
      code: "esbuild-mismatch",
      likelyCause: "esbuild platform package does not match current host architecture.",
      nextAction:
        "Remove node_modules and reinstall on this host, then rebuild dist.",
    };
  }
  if (
    normalized.includes("enotfound registry.npmjs.org") ||
    normalized.includes("npm err") ||
    normalized.includes("cannot find module")
  ) {
    return {
      code: "dependency-install-failure",
      likelyCause: "Dependencies are incomplete or install/network failed.",
      nextAction: "Restore network/dependencies (npm install), then rebuild/retry.",
    };
  }
  if (normalized.includes("trace write failed")) {
    return {
      code: "trace-write-failure",
      likelyCause: "Command reached runtime logic but trace append failed.",
      nextAction:
        "Check .z-mos/trace write permission/path health, then rerun doctor and command.",
    };
  }
  return {
    code: "unknown-startup-failure",
    likelyCause: "Startup failed before stable command execution.",
    nextAction: "Collect error output, run preflight checks, and retry.",
  };
}

function isDirectory(targetPath) {
  try {
    return statSync(targetPath).isDirectory();
  } catch {
    return false;
  }
}

function hasCanonicalProjectState(targetRoot) {
  const zmosRoot = path.join(targetRoot, ".z-mos");
  return (
    existsSync(path.join(zmosRoot, "zmos-manifest.json")) ||
    existsSync(zmosRoot)
  );
}

function findNearestProjectRoot(startDir) {
  let current = path.resolve(startDir);

  while (true) {
    if (hasCanonicalProjectState(current)) {
      return {
        root: current,
        source: current === path.resolve(startDir) ? "cwd" : "parent-discovery",
      };
    }

    const parent = path.dirname(current);
    if (parent === current) {
      break;
    }
    current = parent;
  }

  return null;
}

function parseProjectFlag(argv) {
  let projectPath = null;
  const forwardedArgs = [];

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];

    if (arg === "--project") {
      const value = argv[i + 1];
      if (!value) {
        return {
          projectPath: null,
          forwardedArgs: argv,
          error: "Missing value for --project.",
        };
      }
      projectPath = value;
      i += 1;
      continue;
    }

    if (arg.startsWith("--project=")) {
      const value = arg.split("=")[1] || "";
      if (!value) {
        return {
          projectPath: null,
          forwardedArgs: argv,
          error: "Missing value for --project.",
        };
      }
      projectPath = value;
      continue;
    }

    forwardedArgs.push(arg);
  }

  return {
    projectPath,
    forwardedArgs,
    error: null,
  };
}

function isProjectFacingCommand(argv) {
  const [group] = argv;
  return group ? PROJECT_FACING_COMMANDS.has(group) : false;
}

function isArchiveOrDesignPath(targetRoot) {
  const segments = path.resolve(targetRoot).split(path.sep).filter(Boolean);
  return segments.includes("archive") || segments.includes("design");
}

function resolveExecutionTarget(argv) {
  const projectFacing = isProjectFacingCommand(argv);

  if (!projectFacing) {
    return {
      projectFacing: false,
      forwardedArgs: argv,
      targetRoot: rootDir,
      targetKind: "core",
      resolutionSource: "core-default",
    };
  }

  const parsed = parseProjectFlag(argv);
  if (parsed.error) {
    return {
      projectFacing: true,
      forwardedArgs: parsed.forwardedArgs,
      targetRoot: null,
      targetKind: "unresolved",
      resolutionSource: "invalid-project-flag",
      error: parsed.error,
    };
  }

  const [group] = parsed.forwardedArgs;

  if (parsed.projectPath) {
    const resolvedProjectRoot = path.resolve(invocationCwd, parsed.projectPath);

    if (!isDirectory(resolvedProjectRoot)) {
      return {
        projectFacing: true,
        forwardedArgs: parsed.forwardedArgs,
        targetRoot: null,
        targetKind: "unresolved",
        resolutionSource: "explicit-project-flag",
        error: `Project path is not a directory: ${resolvedProjectRoot}`,
      };
    }

    if (!hasCanonicalProjectState(resolvedProjectRoot)) {
      return {
        projectFacing: true,
        forwardedArgs: parsed.forwardedArgs,
        targetRoot: null,
        targetKind: "unresolved",
        resolutionSource: "explicit-project-flag",
        error:
          `Project context required. Target has no canonical .z-mos state: ${resolvedProjectRoot}`,
      };
    }

    if (group === "doctor" && isArchiveOrDesignPath(resolvedProjectRoot)) {
      return {
        projectFacing: true,
        forwardedArgs: parsed.forwardedArgs,
        targetRoot: null,
        targetKind: "unresolved",
        resolutionSource: "explicit-project-flag",
        error:
          "Project context is in archive/design scope. Doctor is blocked to prevent mutation-oriented diagnostics outside active project context.",
      };
    }

    return {
      projectFacing: true,
      forwardedArgs: parsed.forwardedArgs,
      targetRoot: resolvedProjectRoot,
      targetKind: path.resolve(resolvedProjectRoot) === path.resolve(rootDir) ? "core" : "project",
      resolutionSource: "explicit-project-flag",
    };
  }

  const discovered = findNearestProjectRoot(invocationCwd);
  if (discovered) {
    if (group === "doctor" && isArchiveOrDesignPath(discovered.root)) {
      return {
        projectFacing: true,
        forwardedArgs: parsed.forwardedArgs,
        targetRoot: null,
        targetKind: "unresolved",
        resolutionSource: discovered.source,
        error:
          "Project context resolved inside archive/design scope. Doctor is blocked to avoid unsafe diagnostics target.",
      };
    }

    return {
      projectFacing: true,
      forwardedArgs: parsed.forwardedArgs,
      targetRoot: discovered.root,
      targetKind: path.resolve(discovered.root) === path.resolve(rootDir) ? "core" : "project",
      resolutionSource: discovered.source,
    };
  }

  if (group === "help") {
    return {
      projectFacing: true,
      forwardedArgs: parsed.forwardedArgs,
      targetRoot: invocationCwd,
      targetKind: "workspace",
      resolutionSource: "cwd-unresolved",
    };
  }

  return {
    projectFacing: true,
    forwardedArgs: parsed.forwardedArgs,
    targetRoot: null,
    targetKind: "unresolved",
    resolutionSource: "cwd-unresolved",
    error:
      "Project context required; run from a project root or use --project <path>.",
  };
}

function resolveExecution() {
  const target = resolveExecutionTarget(rawArgs);

  if (!target.targetRoot) {
    const commandLabel = target.forwardedArgs?.join(" ") || rawArgs.join(" ") || "(none)";
    console.error("zcl target resolution: BLOCKED");
    console.error(`command: ${commandLabel}`);
    console.error(`reason: ${target.error || "Project context is unresolved."}`);
    console.error("action: run from a governed project root or pass --project <path>.");
    process.exit(1);
  }

  if (isDevTsMode) {
    return {
      mode: "dev-ts",
      command: ["--import", "tsx", sourceGateway, ...target.forwardedArgs],
      entryPath: sourceGateway,
      target,
    };
  }

  if (!existsSync(distGateway)) {
    if (target.forwardedArgs[0] === "preflight") {
      console.log("Z-MOS Preflight Report");
      console.log("");
      console.log("Status: BLOCKING");
      console.log("");
      console.log("Checks");
      console.log("- dist-integrity [BLOCKING]");
      console.log("  code: dist-missing");
      console.log("  message: dist/cli/gateway.js is missing");
      console.log("  likely cause: Operational build artifact is not available.");
      console.log("  action: Run npm run ops:build and rerun ops:preflight.");
      console.log("");
      console.log("Execution Result");
      console.log("- Command: preflight");
      console.log("- Execution Status: blocked");
      console.log("- Result Class: blocked-preflight");
      console.log("- Trace Expectation: optional-by-design");
      console.log("- Trace Result: not-emitted-blocked-before-logic");
      console.log("- Reason: dist/cli/gateway.js is missing");
      console.log("- Next Action: Run npm run ops:build and rerun ops:preflight.");
      process.exit(1);
    }

    console.error(
      "zcl startup error [dist-missing]: dist not found — run build before using zcl",
    );
    console.error(
      "likely cause: compiled operational artifact dist/cli/gateway.js is missing",
    );
    console.error("next action: run npm run build, then retry command");
    process.exit(1);
  }

  try {
    accessSync(distGateway, constants.R_OK);
  } catch {
    console.error(
      "zcl startup error [dist-missing]: dist gateway path is not readable",
    );
    console.error("likely cause: invalid dist artifact or file permissions");
    console.error("next action: rebuild dist and verify file permissions");
    process.exit(1);
  }

  return {
    mode: "ops-dist",
    command: [distGateway, ...target.forwardedArgs],
    entryPath: distGateway,
    target,
  };
}

const execution = resolveExecution();
console.error(`zcl startup: mode=${execution.mode}`);
console.error(`zcl startup: entry=${execution.entryPath}`);
console.error(`zcl startup: target=${execution.target.targetKind}:${execution.target.targetRoot}`);
console.error(`zcl startup: target-source=${execution.target.resolutionSource}`);

const child = spawn(process.execPath, execution.command, {
  stdio: ["inherit", "pipe", "pipe"],
  cwd: execution.target.targetRoot,
  env: {
    ...process.env,
    ZMOS_CORE_ROOT: rootDir,
    ZMOS_INVOCATION_CWD: invocationCwd,
    ZMOS_EXEC_TARGET_ROOT: execution.target.targetRoot,
    ZMOS_EXEC_TARGET_KIND: execution.target.targetKind,
    ZMOS_EXEC_RESOLUTION_SOURCE: execution.target.resolutionSource,
  },
});

let capturedStderr = "";
let capturedStdout = "";

child.stdout?.on("data", (chunk) => {
  const value = chunk.toString();
  capturedStdout += value;
  process.stdout.write(value);
});

child.stderr?.on("data", (chunk) => {
  const value = chunk.toString();
  capturedStderr += value;
  process.stderr.write(value);
});

child.on("close", (code) => {
  const exitCode = code ?? 1;
  if (exitCode !== 0) {
    if (
      execution.target.forwardedArgs[0] === "preflight" &&
      capturedStdout.includes("Z-MOS Preflight Report")
    ) {
      process.exit(exitCode);
    }
    if (capturedStdout.includes("Execution Result")) {
      process.exit(exitCode);
    }

    const failure = classifyStartupFailure(`${capturedStderr}\n${capturedStdout}`);
    console.error(`zcl startup classifier: ${failure.code}`);
    console.error(`likely cause: ${failure.likelyCause}`);
    console.error(`next action: ${failure.nextAction}`);
  }
  process.exit(exitCode);
});
