import { spawnSync } from "node:child_process";
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const POLICY_PATH = path.join(ROOT_DIR, ".z-mos", "readiness-policy.json");
const NODE_IDENTITY_PATH = path.join(ROOT_DIR, ".z-mos", "node.json");
const PROJECT_STATE_PATH = path.join(ROOT_DIR, ".z-mos", "state", "project-state.json");
const STRICT_LOCK_PATH = path.join(ROOT_DIR, ".z-mos", "runtime", "locks", "verify-strict.lock");

function run(cmd, args, env = {}) {
  const result = spawnSync(cmd, args, {
    cwd: ROOT_DIR,
    encoding: "utf8",
    env: { ...process.env, ...env },
    shell: true,
  });
  return {
    cmd: [cmd, ...args].join(" "),
    code: result.status ?? 1,
    output: `${result.stdout || ""}${result.stderr || ""}`,
  };
}

function assertPass(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function parseProfileArg() {
  const profileArg = process.argv.find((arg) => arg.startsWith("--profile="));
  if (profileArg) {
    return profileArg.split("=")[1]?.trim() || null;
  }
  return null;
}

function loadReadinessPolicy() {
  const raw = readFileSync(POLICY_PATH, "utf8");
  const parsed = JSON.parse(raw);
  if (
    typeof parsed !== "object" ||
    parsed === null ||
    typeof parsed.defaultProfile !== "string" ||
    typeof parsed.profiles !== "object" ||
    parsed.profiles === null
  ) {
    throw new Error(`invalid readiness policy at ${POLICY_PATH}`);
  }
  return parsed;
}

function extractPreflightWarningChecks(output) {
  const warnings = [];
  const lines = output.split("\n");
  for (const line of lines) {
    const match = line.match(/^- (.+) \[WARNING\]$/);
    if (match) warnings.push(match[1]);
  }
  return warnings;
}

function hasDoctorWarning(output) {
  return output.includes("Overall Status: warning");
}

function hasStartWarning(output) {
  return (
    output.includes("Final Entry Verdict: CONTINUE-WITH-CAUTION") ||
    output.includes("- Execution Status: warning")
  );
}

function classifyResult(warningsCount) {
  if (warningsCount === 0) {
    return "GREEN";
  }
  return "AMBER";
}


function acquireStrictLock() {
  mkdirSync(path.dirname(STRICT_LOCK_PATH), { recursive: true });
  let fd = -1;
  try {
    fd = openSync(STRICT_LOCK_PATH, "wx");
    writeFileSync(STRICT_LOCK_PATH, `${process.pid}\n`);
  } catch {
    throw new Error(
      `verify-strict is already running or lock is stale at ${STRICT_LOCK_PATH}. Run sequentially and clear lock if needed.`,
    );
  } finally {
    if (fd >= 0) closeSync(fd);
  }

  return () => {
    try {
      unlinkSync(STRICT_LOCK_PATH);
    } catch {
      // no-op on cleanup if lock was already removed
    }
  };
}

function stabilizeCanonicalTruth() {
  const truthBuild = run("node", ["./bin/zcl.js", "truth", "build"]);
  assertPass(
    truthBuild.code === 0 && truthBuild.output.includes("verdict: SAFE_TO_CONTINUE"),
    `truth build stabilization failed\n${truthBuild.output}`,
  );

  const schemaValidate = run("node", ["./bin/zcl.js", "schema", "validate"]);
  assertPass(schemaValidate.code === 0, `schema validate failed after truth build\n${schemaValidate.output}`);

  const lockCleanup = run("node", ["./bin/zcl.js", "runtime", "clear-stale-locks"]);
  assertPass(lockCleanup.code === 0, `runtime clear-stale-locks failed\n${lockCleanup.output}`);
}

function ensureNodeIdentitySeed() {
  if (existsSync(NODE_IDENTITY_PATH)) {
    return;
  }
  mkdirSync(path.dirname(NODE_IDENTITY_PATH), { recursive: true });
  writeFileSync(
    NODE_IDENTITY_PATH,
    `${JSON.stringify(
      {
        node_id: "pc-ai-node",
        node_role: "execution-node",
        runtime: "nodejs-local",
        capabilities: ["cli-execution", "diagnostics", "ai-advisory"],
      },
      null,
      2,
    )}\n`,
  );
}


function ensureProjectStateSeed() {
  if (existsSync(PROJECT_STATE_PATH)) {
    return;
  }
  mkdirSync(path.dirname(PROJECT_STATE_PATH), { recursive: true });
  writeFileSync(
    PROJECT_STATE_PATH,
    `${JSON.stringify(
      {
        schema_version: "1.3.2",
        current_phase: "v2.0.0-enforcer Enforcer Baseline",
        active_gate: "standard",
        next_safe_action: "embed into target project",
        current_working_blocker: null,
        last_updated: "2026-04-28T07:00:00.000Z",
        updated_by_task: "VERIFY-STRICT-BOOTSTRAP",
        staleness_threshold_hours: 720,
        auto_stale_at: "2026-05-17T10:00:00.000Z",
        synchronized_commit_hash: null,
        synchronized_branch: null,
        synchronized_at: null,
      },
      null,
      2,
    )}\n`,
  );
}

async function main() {
  const releaseLock = acquireStrictLock();
  try {
  const checks = [];
  const warningLedger = [];
  const policy = loadReadinessPolicy();
  const requestedProfile = parseProfileArg() || process.env.ZMOS_READINESS_PROFILE || policy.defaultProfile;
  const profile = policy.profiles[requestedProfile];

  if (!profile) {
    throw new Error(
      `unknown readiness profile "${requestedProfile}". Available: ${Object.keys(policy.profiles).join(", ")}`,
    );
  }

  const typecheck = run("npm", ["run", "typecheck"]);
  assertPass(typecheck.code === 0, `typecheck failed\n${typecheck.output}`);
  checks.push("typecheck");

  const build = run("npm", ["run", "build"]);
  assertPass(build.code === 0, `build failed\n${build.output}`);
  checks.push("build");

  const init = run("node", ["./bin/zcl.js", "init"]);
  assertPass(init.code === 0, `init failed\n${init.output}`);
  checks.push("init-bootstrap");

  const coverage = run("node", ["./bin/zcl.js", "workflow", "coverage-check"]);
  assertPass(
    coverage.code === 0 && coverage.output.includes("status: HEALTHY"),
    `workflow coverage check failed\n${coverage.output}`,
  );
  checks.push("workflow-coverage-check");

  stabilizeCanonicalTruth();
  checks.push("truth-build-stabilization");
  checks.push("schema-validate-post-stabilization");
  checks.push("runtime clear-stale-locks");
  ensureNodeIdentitySeed();
  ensureProjectStateSeed();
  checks.push("node-identity-seed");
  checks.push("project-state-seed");

  const advisoryExternal = run("node", ["./bin/zcl.js", "workflow", "advisory-check"], {
    AI_PROVIDER: "external-code-agent",
  });
  assertPass(
    advisoryExternal.code === 0 &&
      advisoryExternal.output.includes("bundle generated: mode=external-code-agent"),
    `advisory external mode failed\n${advisoryExternal.output}`,
  );
  checks.push("workflow-advisory-check external-code-agent");

  const advisoryNone = run("node", ["./bin/zcl.js", "workflow", "advisory-check"], {
    AI_PROVIDER: "none",
  });
  assertPass(
    advisoryNone.code === 0 &&
      advisoryNone.output.includes("bundle generated: mode=local-deterministic"),
    `advisory deterministic mode failed\n${advisoryNone.output}`,
  );
  checks.push("workflow-advisory-check none");

  const aiTestExternal = run("node", ["./bin/zcl.js", "ai", "test"], {
    AI_PROVIDER: "external-code-agent",
  });
  assertPass(
    aiTestExternal.code === 0 &&
      aiTestExternal.output.includes("EXECUTION_MODE: bundle-export") &&
      aiTestExternal.output.includes("BUNDLE_PATH:"),
    `ai test external provider failed\n${aiTestExternal.output}`,
  );
  checks.push("ai-test external-code-agent");

  const aiTestNone = run("node", ["./bin/zcl.js", "ai", "test"], {
    AI_PROVIDER: "none",
  });
  assertPass(
    aiTestNone.code === 0 &&
      aiTestNone.output.includes("AI_PROVIDER=none; governance checks passed; execution skipped by design."),
    `ai test deterministic fallback failed\n${aiTestNone.output}`,
  );
  checks.push("ai-test none");

  stabilizeCanonicalTruth();
  checks.push("truth-build-restabilization");
  checks.push("schema-validate-restabilization");
  checks.push("runtime clear-stale-locks-restabilization");

  const preflight = run("node", ["./bin/zcl.js", "preflight"]);
  assertPass(preflight.code === 0, `preflight failed\n${preflight.output}`);
  assertPass(
    !preflight.output.includes("Status: BLOCKING"),
    `preflight returned BLOCKING\n${preflight.output}`,
  );
  const preflightWarnings = extractPreflightWarningChecks(preflight.output);
  const allowedPreflightWarnings = new Set(profile.allowlistedPreflightWarnings || []);
  if (process.platform === "linux") {
    allowedPreflightWarnings.add("environment-consistency");
  }
  const unexpectedPreflightWarnings = preflightWarnings.filter(
    (name) => !allowedPreflightWarnings.has(name),
  );
  assertPass(
    unexpectedPreflightWarnings.length === 0,
    `unexpected preflight warnings: ${unexpectedPreflightWarnings.join(", ")}\n${preflight.output}`,
  );
  preflightWarnings
    .filter((warning) => !allowedPreflightWarnings.has(warning))
    .forEach((warning) => warningLedger.push(`preflight:${warning}`));
  checks.push("preflight");

  const doctor = run("node", ["./bin/zcl.js", "doctor"]);
  assertPass(doctor.code === 0, `doctor failed\n${doctor.output}`);
  assertPass(
    !doctor.output.includes("Overall Status: blocking"),
    `doctor returned blocking\n${doctor.output}`,
  );
  if (hasDoctorWarning(doctor.output)) {
    assertPass(profile.allowDoctorWarning === true, `doctor warning is not allowed in profile=${requestedProfile}`);
  }
  checks.push("doctor");

  const start = run("node", ["./bin/zcl.js", "start"]);
  assertPass(start.code === 0, `start failed\n${start.output}`);
  assertPass(
    !start.output.includes("Final Entry Verdict: STOP-AND-REPAIR"),
    `start returned stop-and-repair\n${start.output}`,
  );
  if (hasStartWarning(start.output)) {
    assertPass(profile.allowStartWarning === true, `start warning is not allowed in profile=${requestedProfile}`);
  }
  checks.push("start");

  const classification = classifyResult(warningLedger.length);
  const gateResult = classification === "GREEN" ? "PASS" : "PASS-WITH-WARNINGS";
  const summary = [
    `ZMOS_PRODUCTION_READINESS: ${gateResult}`,
    `READINESS_CLASSIFICATION: ${classification}`,
    `PROFILE: ${requestedProfile}`,
    "",
    `Checks executed (${checks.length}):`,
    ...checks.map((name) => `- ${name}`),
    "",
    `Warning Budget Used (${warningLedger.length}):`,
    ...(warningLedger.length > 0 ? warningLedger.map((entry) => `- ${entry}`) : ["- (none)"]),
    "",
    `Warning Budget Allowed (${requestedProfile}):`,
    `- preflight: ${(profile.allowlistedPreflightWarnings || []).join(", ") || "(none)"}`,
    `- doctor: ${profile.allowDoctorWarning ? "allowed" : "not-allowed"}`,
    `- start: ${profile.allowStartWarning ? "allowed" : "not-allowed"}`,
  ];
  console.log(summary.join("\n"));
  } finally {
    releaseLock();
  }
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error("ZMOS_PRODUCTION_READINESS: FAIL");
  console.error("READINESS_CLASSIFICATION: RED");
  console.error(message);
  process.exit(1);
});
