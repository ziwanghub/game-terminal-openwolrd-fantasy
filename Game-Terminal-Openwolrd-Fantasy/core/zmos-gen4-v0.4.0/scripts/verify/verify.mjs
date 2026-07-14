import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, writeFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const DIST_GATEWAY = path.join(ROOT_DIR, "dist", "cli", "gateway.js");
const MANIFEST_PATH = path.join(ROOT_DIR, ".z-mos", "zmos-manifest.json");
const POLICY_PATH = path.join(ROOT_DIR, ".z-mos", "workflow-policy.json");
const TRACE_PATH = path.join(ROOT_DIR, ".z-mos", "trace", "runtime-trace.jsonl");
const TRUTH_CONTRACT_PATH = path.join(ROOT_DIR, ".z-mos", "truth.contract.json");

const DOCS_ROOT = path.join(ROOT_DIR, "docs", "zmos");
const DOCS_DUPLICATE_PATH = path.join(
  DOCS_ROOT,
  "knowledge",
  "ZMOS-RUNLOG-CORE-V020-2026-999-VERIFY-DUPLICATE-ID.md",
);

const mode = process.argv[2] || "all";
const allowedModes = new Set(["smoke", "core", "trace", "docs", "all"]);

if (!allowedModes.has(mode)) {
  console.error(`verify: unknown mode "${mode}"`);
  console.error("allowed modes: smoke | core | trace | all");
  process.exit(1);
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: ROOT_DIR,
    encoding: "utf8",
    env: { ...process.env, ...(options.env || {}) },
    shell: true,
  });

  return {
    command: [command, ...args].join(" "),
    code: result.status ?? 1,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
    output: `${result.stdout || ""}${result.stderr || ""}`,
  };
}

function commandExists(relativePath) {
  return existsSync(path.join(ROOT_DIR, relativePath));
}

function ensureParent(filePath) {
  mkdirSync(path.dirname(filePath), { recursive: true });
}

function bootstrapRequiredPaths() {
  const requiredDirs = [
    path.join(ROOT_DIR, ".z-mos"),
    path.join(ROOT_DIR, ".z-mos", "trace"),
    path.join(ROOT_DIR, ".z-mos", "trace", "archive"),
  ];

  for (const dirPath of requiredDirs) {
    if (!existsSync(dirPath)) {
      mkdirSync(dirPath, { recursive: true });
      console.log(`Created missing directory: ${path.relative(ROOT_DIR, dirPath)}`);
    }
  }

  if (!existsSync(TRACE_PATH)) {
    writeFileSync(TRACE_PATH, "");
    console.log(`Created missing file: ${path.relative(ROOT_DIR, TRACE_PATH)}`);
  }
}

function ensureTraceArtifacts() {
  bootstrapRequiredPaths();
}

async function withFileBackup(filePath, callback) {
  const fileExists = existsSync(filePath);
  const backup = fileExists ? readFileSync(filePath) : null;
  try {
    return await callback();
  } finally {
    if (fileExists && backup) {
      writeFileSync(filePath, backup);
    } else if (!fileExists && existsSync(filePath)) {
      rmSync(filePath, { force: true });
    }
  }
}

async function withPathBackup(targetPath, callback) {
  const exists = existsSync(targetPath);
  const backupPath = `${targetPath}.verify-bak`;
  if (exists) {
    renameSync(targetPath, backupPath);
  }
  try {
    return await callback();
  } finally {
    if (existsSync(targetPath)) {
      rmSync(targetPath, { recursive: true, force: true });
    }
    if (exists && existsSync(backupPath)) {
      renameSync(backupPath, targetPath);
    }
  }
}

async function withRenamedFile(filePath, tempSuffix, callback) {
  const tempPath = `${filePath}.${tempSuffix}`;
  const fileExists = existsSync(filePath);
  if (fileExists) {
    renameSync(filePath, tempPath);
  }
  try {
    return await callback();
  } finally {
    if (fileExists && existsSync(tempPath)) {
      renameSync(tempPath, filePath);
    }
  }
}

async function withTempFile(filePath, content, callback) {
  ensureParent(filePath);
  const existed = existsSync(filePath);
  const backup = existed ? readFileSync(filePath) : null;
  writeFileSync(filePath, content);
  try {
    return await callback();
  } finally {
    if (existed && backup) {
      writeFileSync(filePath, backup);
    } else if (existsSync(filePath)) {
      rmSync(filePath, { force: true });
    }
  }
}

function addResult(results, entry) {
  results.push(entry);
}

function containsAll(text, patterns) {
  return patterns.every((pattern) => text.includes(pattern));
}

async function runSmokeSuite(results) {
  const scope = "smoke";

  {
    const build = run("npm", ["run", "ops:build"]);
    const verifyDist = run("npm", ["run", "ops:verify-dist"]);
    const status = run("node", ["./bin/zcl.js", "status"]);
    const pass =
      build.code === 0 &&
      verifyDist.code === 0 &&
      status.code === 0 &&
      containsAll(status.output, ["zcl startup: mode=ops-dist", "\"verdict\""]);

    addResult(results, {
      testName: "Smoke 1 — Build + Dist Path",
      scope,
      pass,
      failureReason: pass ? "" : "build/dist/startup contract did not meet expectation",
      commandExecuted: `${build.command} ; ${verifyDist.command} ; ${status.command}`,
      expectedOutcome: "build and dist verify pass, status starts in ops-dist path",
      actualOutcome: pass ? "ops-dist startup confirmed" : status.output || verifyDist.output || build.output,
      recommendedNextAction: pass ? "none" : "run ops:build, verify dist path, and inspect startup output",
      warning: false,
    });
  }

  {
    ensureParent(TRACE_PATH);
    const pass = await withFileBackup(TRACE_PATH, () => {
      writeFileSync(TRACE_PATH, "");
      const preflight = run("npm", ["run", "ops:preflight"]);
      return (
        preflight.code === 0 &&
        !preflight.output.includes("Status: BLOCKING") &&
        preflight.output.includes("document-schema")
      );
    });
    addResult(results, {
      testName: "Smoke 2 — Preflight Healthy",
      scope,
      pass,
      failureReason: pass ? "" : "preflight returned blocking status under controlled smoke conditions",
      commandExecuted: "npm run ops:preflight",
      expectedOutcome: "Status is non-blocking (healthy/warning) with document checks visible",
      actualOutcome: pass ? "preflight non-blocking confirmed" : run("npm", ["run", "ops:preflight"]).output,
      recommendedNextAction: pass ? "none" : "repair blocking/warning preflight checks and retest",
      warning: false,
    });
  }

  {
    const init = run("npm", ["run", "ops:init"]);
    const pass = init.code === 0 && containsAll(init.output, ["Z-MOS Init Report", "Execution Result"]);
    addResult(results, {
      testName: "Smoke 3 — Init Path",
      scope,
      pass,
      failureReason: pass ? "" : "ops:init did not complete",
      commandExecuted: init.command,
      expectedOutcome: "init succeeds with governed execution result",
      actualOutcome: pass ? "init path succeeded" : init.output,
      recommendedNextAction: pass ? "none" : "repair preflight/canonical blockers, then rerun ops:init",
      warning: false,
    });
  }

  {
    const status = run("npm", ["run", "ops:status"]);
    const pass =
      status.code === 0 &&
      containsAll(status.output, ["zcl startup: mode=ops-dist", "\"verdict\""]);
    addResult(results, {
      testName: "Smoke 4 — Status Path",
      scope,
      pass,
      failureReason: pass ? "" : "ops:status did not return governed runtime status",
      commandExecuted: status.command,
      expectedOutcome: "status succeeds and returns governed execution result",
      actualOutcome: pass ? "status path succeeded" : status.output,
      recommendedNextAction: pass ? "none" : "inspect status/preflight output and recover blocking state",
      warning: status.output.includes("Execution Status: warning"),
    });
  }

  {
    const doctor = run("npm", ["run", "ops:doctor"]);
    const pass =
      doctor.code === 0 &&
      containsAll(doctor.output, ["Z-MOS Doctor Report", "Execution Result", "trace validation status"]);
    addResult(results, {
      testName: "Smoke 5 — Doctor Path",
      scope,
      pass,
      failureReason: pass ? "" : "ops:doctor did not return diagnostics report",
      commandExecuted: doctor.command,
      expectedOutcome: "doctor succeeds and reports trace/canonical/governance diagnostics",
      actualOutcome: pass ? "doctor path succeeded" : doctor.output,
      recommendedNextAction: pass ? "none" : "repair diagnostics blockers and rerun ops:doctor",
      warning: doctor.output.includes("Overall Status: warning"),
    });
  }

  {
    const workflow = run("node", ["./bin/zcl.js", "workflow", "runtime-check"]);
    const pass =
      workflow.code === 0 &&
      containsAll(workflow.output, ["Workflow: runtime-check", "Execution Result"]);
    addResult(results, {
      testName: "Smoke 6 — Workflow Runtime Path",
      scope,
      pass,
      failureReason: pass ? "" : "workflow runtime-check did not execute as governed workflow",
      commandExecuted: workflow.command,
      expectedOutcome: "runtime-check executes under healthy policy state",
      actualOutcome: pass ? "workflow runtime-check executed" : workflow.output,
      recommendedNextAction: pass ? "none" : "inspect workflow policy and runtime diagnostics, then retry",
      warning: workflow.output.includes("Execution Status: warning"),
    });
  }
}

async function runCoreSuite(results) {
  const scope = "core";

  {
    const status = run("node", ["./bin/zcl.js", "status"]);
    const pass = status.code === 0 && status.output.includes("zcl startup: mode=ops-dist");
    addResult(results, {
      testName: "Core A — Startup Contract",
      scope,
      pass,
      failureReason: pass ? "" : "ops command did not start in ops-dist mode",
      commandExecuted: status.command,
      expectedOutcome: "startup contract uses dist path",
      actualOutcome: pass ? "ops-dist startup confirmed" : status.output,
      recommendedNextAction: pass ? "none" : "run ops:verify-dist and repair startup path",
      warning: false,
    });
  }

  {
    const pass = await withRenamedFile(DIST_GATEWAY, "verify-bak", () => {
      const status = run("node", ["./bin/zcl.js", "status"]);
      return status.code !== 0 && status.output.includes("dist not found");
    });
    addResult(results, {
      testName: "Core B — Preflight Blocking Contract (dist missing)",
      scope,
      pass,
      failureReason: pass ? "" : "dist-missing block was not detected correctly",
      commandExecuted: "node ./bin/zcl.js status (with dist temporarily missing)",
      expectedOutcome: "non-zero + explicit dist-missing failure",
      actualOutcome: pass ? "dist-missing block detected" : "dist-missing handling mismatch",
      recommendedNextAction: pass ? "none" : "fix startup/preflight dist blocker handling",
      warning: false,
    });
  }

  {
    const pass = await withFileBackup(MANIFEST_PATH, () => {
      writeFileSync(MANIFEST_PATH, "{invalid-json");
      const status = run("node", ["./bin/zcl.js", "start"]);
      return (
        status.code !== 0 &&
        status.output.includes("blocked: true") &&
        status.output.includes("blocking issues")
      );
    });
    addResult(results, {
      testName: "Core C — Canonical Integrity Contract",
      scope,
      pass,
      failureReason: pass ? "" : "canonical corruption did not block correctly",
      commandExecuted: "node ./bin/zcl.js start (with malformed manifest)",
      expectedOutcome: "blocked canonical result with explicit reason",
      actualOutcome: pass ? "canonical block detected" : "canonical block not detected as expected",
      recommendedNextAction: pass ? "none" : "enforce canonical integrity blocking path",
      warning: false,
    });
  }

  {
    if (!existsSync(POLICY_PATH)) {
      addResult(results, {
        testName: "Core D — Governance Workflow Contract",
        scope,
        pass: false,
        failureReason: "workflow-policy.json is missing",
        commandExecuted: "node ./bin/zcl.js workflow advisory-check (policy advisory disabled)",
        expectedOutcome: "blocked-policy with non-zero result",
        actualOutcome: "policy file missing before governance test",
        recommendedNextAction: "restore .z-mos/workflow-policy.json and rerun verification",
        warning: false,
      });
      return;
    }

    const pass = await withFileBackup(POLICY_PATH, () => {
      const truthBuild = run("node", ["./bin/zcl.js", "truth", "build"]);
      if (truthBuild.code !== 0) {
        return false;
      }
      const policy = JSON.parse(readFileSync(POLICY_PATH, "utf8"));
      const advisory = policy.workflows.find((workflow) => workflow.workflowName === "advisory-check");
      if (!advisory) {
        return false;
      }
      advisory.advisoryAiAllowed = false;
      writeFileSync(POLICY_PATH, `${JSON.stringify(policy, null, 2)}\n`);
      const command = run("node", ["./bin/zcl.js", "workflow", "advisory-check"]);
      return (
        command.code !== 0 &&
        (command.output.includes("Result Class: blocked-policy") ||
          command.output.includes("Execution Status: blocked"))
      );
    });

    addResult(results, {
      testName: "Core D — Governance Workflow Contract",
      scope,
      pass,
      failureReason: pass ? "" : "workflow governance block did not report blocked-policy",
      commandExecuted: "node ./bin/zcl.js workflow advisory-check (policy advisory disabled)",
      expectedOutcome: "blocked-policy with non-zero result",
      actualOutcome: pass ? "policy block detected and classified" : "governance block classification mismatch",
      recommendedNextAction: pass ? "none" : "repair workflow policy enforcement path",
      warning: false,
    });
  }

  {
    const validatorModule = await import(pathToFileURL(path.join(ROOT_DIR, "dist", "core", "trace-validator.js")).href);
    const report = await validatorModule.validateTraceFile({ maxLines: 120 });
    const pass = report.status !== "corrupted";
    addResult(results, {
      testName: "Core E — Trace Contract Baseline",
      scope,
      pass,
      failureReason: pass ? "" : "trace validator reported corrupted baseline",
      commandExecuted: "validateTraceFile(maxLines=120)",
      expectedOutcome: "trace baseline not corrupted",
      actualOutcome: `status=${report.status}, issues=${report.issues.length}`,
      recommendedNextAction: pass ? "none" : "repair trace corruption before proceeding",
      warning: report.status === "warning",
    });
  }

  {
    const guardRegression = run("node", ["./scripts/verify/scope-guard-phase1.mjs"]);
    const pass =
      guardRegression.code === 0 &&
      guardRegression.output.includes("scope-guard-phase1: PASS");
    addResult(results, {
      testName: "Core F — Scope Guard Fail-Closed Regression",
      scope,
      pass,
      failureReason: pass ? "" : "scope-guard fail-closed regression test failed",
      commandExecuted: guardRegression.command,
      expectedOutcome: "strict + empty allow-list is rejected (fail-closed)",
      actualOutcome: pass ? "fail-closed behavior verified" : guardRegression.output,
      recommendedNextAction: pass ? "none" : "repair scope-guard strict fail-closed logic",
      warning: false,
    });
  }

  {
    const truthBuild = run("node", ["./bin/zcl.js", "truth", "build"]);
    const truthPath = path.join(ROOT_DIR, ".z-mos", "truth.contract.json");
    const schemaValidate = run("node", ["./bin/zcl.js", "schema", "validate"]);

    const pass =
      truthBuild.code === 0 &&
      existsSync(truthPath) &&
      schemaValidate.code === 0 &&
      schemaValidate.output.includes(".z-mos/truth.contract.json   PASS");

    addResult(results, {
      testName: "Core G — Truth Build Contract",
      scope,
      pass,
      failureReason: pass ? "" : "truth build contract failed (build/create/schema)",
      commandExecuted: `${truthBuild.command} ; ${schemaValidate.command}`,
      expectedOutcome: "truth contract is built and passes schema validation",
      actualOutcome: pass
        ? "truth build succeeded and schema validation passed"
        : `${truthBuild.output}\n${schemaValidate.output}`,
      recommendedNextAction: pass ? "none" : "repair truth build pipeline and atomic write path",
      warning: false,
    });
  }

  {
    const pass = await withFileBackup(TRUTH_CONTRACT_PATH, () => {
      const truth = JSON.parse(readFileSync(TRUTH_CONTRACT_PATH, "utf8"));
      truth.code_ref.commit = "verify-hard-block-commit-mismatch";
      writeFileSync(TRUTH_CONTRACT_PATH, `${JSON.stringify(truth, null, 2)}\n`);
      const start = run("node", ["./bin/zcl.js", "start"]);
      const status = run("node", ["./bin/zcl.js", "status"]);
      return (
        start.code !== 0 &&
        start.output.includes("verdict: STOP-AND-REPAIR") &&
        start.output.includes("drift_policy_reason: CRITICAL_DRIFT_HARD_BLOCK") &&
        status.output.includes("\"blocked\": true") &&
        status.output.includes("\"reason\": \"CRITICAL_DRIFT_HARD_BLOCK\"")
      );
    });
    addResult(results, {
      testName: "Core H — Hard Block Commit Drift",
      scope,
      pass,
      failureReason: pass ? "" : "commit mismatch did not trigger hard block policy",
      commandExecuted: "node ./bin/zcl.js start/status (with temporary truth commit mismatch)",
      expectedOutcome: "critical commit drift causes STOP-AND-REPAIR and blocked status",
      actualOutcome: pass ? "hard block on commit mismatch verified" : "hard block behavior mismatch",
      recommendedNextAction: pass ? "none" : "repair commit drift hard-block escalation path",
      warning: false,
    });
  }

  {
    const pass = await withFileBackup(TRUTH_CONTRACT_PATH, () => {
      const truth = JSON.parse(readFileSync(TRUTH_CONTRACT_PATH, "utf8"));
      truth.env_ref.target_env = "production";
      writeFileSync(TRUTH_CONTRACT_PATH, `${JSON.stringify(truth, null, 2)}\n`);
      const strictEnv = { NODE_ENV: "development" };
      const start = run("node", ["./bin/zcl.js", "start"], { env: strictEnv });
      const status = run("node", ["./bin/zcl.js", "status"], { env: strictEnv });
      return (
        start.code !== 0 &&
        start.output.includes("verdict: STOP-AND-REPAIR") &&
        start.output.includes("drift_policy_reason: CRITICAL_DRIFT_HARD_BLOCK") &&
        status.output.includes("\"blocked\": true") &&
        status.output.includes("\"reason\": \"CRITICAL_DRIFT_HARD_BLOCK\"")
      );
    });
    addResult(results, {
      testName: "Core I — Hard Block Environment Drift",
      scope,
      pass,
      failureReason: pass ? "" : "environment mismatch did not trigger hard block policy",
      commandExecuted:
        "NODE_ENV=development node ./bin/zcl.js start/status (with temporary truth environment mismatch)",
      expectedOutcome: "critical environment drift causes STOP-AND-REPAIR and blocked status",
      actualOutcome: pass ? "hard block on environment mismatch verified" : "hard block behavior mismatch",
      recommendedNextAction: pass ? "none" : "repair environment drift hard-block escalation path",
      warning: false,
    });
  }

  {
    const pass = await withFileBackup(TRUTH_CONTRACT_PATH, () => {
      const baselineBuild = run("node", ["./bin/zcl.js", "truth", "build"]);
      if (baselineBuild.code !== 0) {
        return false;
      }
      const truth = JSON.parse(readFileSync(TRUTH_CONTRACT_PATH, "utf8"));
      truth.code_ref.commit = "verify-hard-block-recovery-mismatch";
      truth.code_ref.commit_sha = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef";
      writeFileSync(TRUTH_CONTRACT_PATH, `${JSON.stringify(truth, null, 2)}\n`);

      const blockedStart = run("node", ["./bin/zcl.js", "start"]);
      const recoverTruth = run("node", ["./bin/zcl.js", "truth", "build"]);
      const recoveredStart = run("node", ["./bin/zcl.js", "start"]);
      const schemaValidate = run("node", ["./bin/zcl.js", "schema", "validate"]);

      return (
        blockedStart.code !== 0 &&
        (blockedStart.output.includes("verdict: STOP-AND-REPAIR") ||
          blockedStart.output.includes("Execution Status: blocked")) &&
        recoverTruth.code === 0 &&
        (recoveredStart.code === 0 || recoveredStart.code === 1) &&
        !recoveredStart.output.includes("verdict: STOP-AND-REPAIR") &&
        schemaValidate.code === 0
      );
    });

    addResult(results, {
      testName: "Core J — E2E Drift Block and Recovery",
      scope,
      pass,
      failureReason: pass ? "" : "critical drift block/recovery flow failed end-to-end",
      commandExecuted:
        "node ./bin/zcl.js start ; node ./bin/zcl.js truth build ; node ./bin/zcl.js start ; node ./bin/zcl.js schema validate",
      expectedOutcome:
        "critical commit drift hard-blocks first, then truth build recovers to SAFE_TO_CONTINUE with schema-valid state",
      actualOutcome: pass
        ? "hard block and recovery flow verified"
        : "e2e drift block/recovery behavior mismatch",
      recommendedNextAction: pass ? "none" : "repair hard-block escalation or truth recovery path",
      warning: false,
    });
  }


}

async function runTraceSuite(results) {
  const scope = "trace";
  ensureTraceArtifacts();
  const validatorModule = await import(pathToFileURL(path.join(ROOT_DIR, "dist", "core", "trace-validator.js")).href);
  const writerModule = await import(pathToFileURL(path.join(ROOT_DIR, "dist", "core", "trace-writer.js")).href);
  const traceArchiveDir = path.join(path.dirname(TRACE_PATH), "archive");
  const traceIntegrityStatePath = path.join(ROOT_DIR, ".z-mos", "state", "trace-integrity.json");

  {
    const report = await validatorModule.validateTraceFile({ maxLines: 100 });
    const pass = report.status !== "corrupted";
    addResult(results, {
      testName: "Trace 1 — Validator Baseline",
      scope,
      pass,
      failureReason: pass ? "" : "trace baseline corrupted",
      commandExecuted: "validateTraceFile(maxLines=100)",
      expectedOutcome: "healthy or warning (non-corrupted) baseline",
      actualOutcome: `status=${report.status}, issues=${report.issues.length}`,
      recommendedNextAction: pass ? "none" : "repair trace file corruption",
      warning: report.status === "warning",
    });
  }

  {
    const pass = await withFileBackup(TRACE_PATH, () => {
      writeFileSync(TRACE_PATH, `${readFileSync(TRACE_PATH, "utf8")}{"broken":true\n`);
      const report = run("node", ["./bin/zcl.js", "doctor"]);
      return report.output.includes("trace validation status — blocking: status=corrupted");
    });
    addResult(results, {
      testName: "Trace 2 — Corruption Detection",
      scope,
      pass,
      failureReason: pass ? "" : "doctor did not detect corrupted trace",
      commandExecuted: "node ./bin/zcl.js doctor (with temporary broken trace line)",
      expectedOutcome: "doctor reports trace validation corrupted",
      actualOutcome: pass ? "corruption detected in doctor output" : "corruption not surfaced as expected",
      recommendedNextAction: pass ? "none" : "repair doctor trace diagnostics path",
      warning: false,
    });
  }

  {
    const pass = await withFileBackup(TRACE_PATH, async () => {
        const first = await writerModule.writeCanonicalTraceRecord({
          command: "verify-trace-mismatch-success",
          actor: "system",
          execution_status: "success",
          result_class: "success",
          preflight_status: "healthy",
          canonical_status: "healthy",
          policy_status: "not-applicable",
          trace_expectation: "required-if-business-logic",
          trace_result: "not-emitted-due-failure",
        });

        const second = await writerModule.writeCanonicalTraceRecord({
          command: "verify-trace-mismatch-blocked",
          actor: "system",
          execution_status: "blocked",
          result_class: "blocked-preflight",
          preflight_status: "blocking",
          canonical_status: "not-evaluated",
          policy_status: "not-applicable",
          trace_expectation: "required-if-business-logic",
          trace_result: "emitted",
        });

        if (!first.ok || !second.ok) {
          return false;
        }

        const report = await validatorModule.validateTraceFile({ maxLines: 20 });
        return (
          report.status === "warning" &&
          report.completeness.emittedExpectedButMissing > 0 &&
          report.completeness.blockedButEmitted > 0
        );
    });

    addResult(results, {
      testName: "Trace 3 — Completeness Mismatch Detection",
      scope,
      pass,
      failureReason: pass ? "" : "trace completeness mismatch not detected",
      commandExecuted: "writeCanonicalTraceRecord(...) x2 + validateTraceFile(maxLines=20)",
      expectedOutcome: "warning with mismatch counters > 0",
      actualOutcome: pass
        ? "completeness mismatch detected as warning"
        : "mismatch counters not detected as expected",
      recommendedNextAction: pass ? "none" : "repair trace completeness validator logic",
      warning: false,
    });
  }

  {
    const result = await writerModule.writeCanonicalTraceRecord({
      command: "verify-trace-schema-invalid",
      actor: "system",
      execution_status: "invalid",
      result_class: "success",
      preflight_status: "healthy",
      canonical_status: "healthy",
      policy_status: "not-applicable",
      trace_expectation: "required-if-business-logic",
      trace_result: "emitted",
    });
    const pass = result.ok === false && typeof result.error === "string";
    addResult(results, {
      testName: "Trace 4 — Schema Violation Rejection",
      scope,
      pass,
      failureReason: pass ? "" : "invalid trace schema was accepted unexpectedly",
      commandExecuted: "writeCanonicalTraceRecord(invalid execution_status)",
      expectedOutcome: "write rejected with schema error",
      actualOutcome: JSON.stringify(result),
      recommendedNextAction: pass ? "none" : "enforce strict schema guard before append",
      warning: false,
    });
  }

  {
    const pass = await withPathBackup(traceArchiveDir, async () =>
      withPathBackup(traceIntegrityStatePath, async () =>
        withFileBackup(TRACE_PATH, async () => {
          process.env.ZMOS_TRACE_ROTATION_LIMIT = "5";
          for (let i = 0; i < 7; i++) {
            await writerModule.writeCanonicalTraceRecord({
              command: `verify-trace-rotation-${i}`,
              actor: "system",
              execution_status: "success",
              result_class: "success",
              preflight_status: "healthy",
              canonical_status: "healthy",
              policy_status: "not-applicable",
              trace_expectation: "required-if-business-logic",
              trace_result: "emitted",
            });
          }

          const verifierModule = await import(
            pathToFileURL(path.join(ROOT_DIR, "dist", "core", "trace-verifier.js")).href
          );
          const result = await verifierModule.verifyTraceIntegrity(TRACE_PATH);
          return result.status === "valid" && result.checked_entries >= 7;
        }),
      ),
    );

    addResult(results, {
      testName: "Trace 5 — Trace Rotation Preserves Hash Chain",
      scope,
      pass,
      failureReason: pass ? "" : "trace rotation broke hash continuity",
      commandExecuted: "write 7 records with ROTATION_LIMIT=5 + verifyTraceIntegrity",
      expectedOutcome: "valid status across segments",
      actualOutcome: pass ? "valid integrity" : "tampered or error",
      recommendedNextAction: pass ? "none" : "fix rotation segment hash or continuity chain",
      warning: false,
    });
  }

  {
    const pass = await withPathBackup(traceArchiveDir, async () =>
      withPathBackup(traceIntegrityStatePath, async () =>
        withFileBackup(TRACE_PATH, async () => {
          process.env.ZMOS_TRACE_ROTATION_LIMIT = "3";
          for (let i = 0; i < 5; i++) {
            await writerModule.writeCanonicalTraceRecord({
              command: `verify-trace-continuity-${i}`,
              actor: "system",
              execution_status: "success",
              result_class: "success",
              preflight_status: "healthy",
              canonical_status: "healthy",
              policy_status: "not-applicable",
              trace_expectation: "required-if-business-logic",
              trace_result: "emitted",
            });
          }

          const archiveDir = path.join(path.dirname(TRACE_PATH), "archive");
          const files = readdirSync(archiveDir);
          const metaFiles = files.filter(f => f.endsWith(".meta.json"));
          if (metaFiles.length > 0) {
            const metaPath = path.join(archiveDir, metaFiles[0]);
            const content = readFileSync(metaPath, "utf8");
            const meta = JSON.parse(content);
            meta.segment_hash = "corrupted_hash";
            writeFileSync(metaPath, JSON.stringify(meta), "utf8");
          }

          const verifierModule = await import(
            pathToFileURL(path.join(ROOT_DIR, "dist", "core", "trace-verifier.js")).href
          );
          const result = await verifierModule.verifyTraceIntegrity(TRACE_PATH);
          return result.status === "tampered";
        }),
      ),
    );

    addResult(results, {
      testName: "Trace 6 — Corrupted Segment Fails Verification",
      scope,
      pass,
      failureReason: pass ? "" : "tampered archive segment was not detected",
      commandExecuted: "corrupt segment_hash in archive + verifyTraceIntegrity",
      expectedOutcome: "tampered status",
      actualOutcome: pass ? "tampered detected" : "invalid verification",
      recommendedNextAction: pass ? "none" : "fix segmented verification checks",
      warning: false,
    });
  }
}

async function runDocsSuite(results) {
  const scope = "docs";

  {
    const check = run("node", ["./bin/zcl.js", "doc:check"]);
    const pass = check.code === 0 && !check.output.includes("Execution Status: blocked");
    addResult(results, {
      testName: "Docs 1 — Schema + Naming Baseline",
      scope,
      pass,
      failureReason: pass ? "" : "doc:check reported blocking findings",
      commandExecuted: check.command,
      expectedOutcome: "doc:check has no blocking status",
      actualOutcome: pass ? "doc baseline is non-blocking" : check.output,
      recommendedNextAction: pass ? "none" : "fix document schema/naming/duplicate blockers",
      warning: check.output.includes("Execution Status: warning"),
    });
  }

  {
    const index = run("node", ["./bin/zcl.js", "doc:index", "--type=playbook"]);
    const pass = index.code === 0 && index.output.includes("Z-MOS Document Index");
    addResult(results, {
      testName: "Docs 2 — Index Minimal Structure",
      scope,
      pass,
      failureReason: pass ? "" : "doc:index failed or minimal structure missing",
      commandExecuted: index.command,
      expectedOutcome: "doc:index returns structured listing",
      actualOutcome: pass ? "doc index returned structured output" : index.output,
      recommendedNextAction: pass ? "none" : "repair document index command and docs structure",
      warning: index.output.includes("Execution Status: warning"),
    });
  }

  {
    const duplicateTemplate = `---
document_id: DOC-CORE-V020-2026-001
document_type: runlog
project_code: CORE
phase: V020
version: v1.0.1
status: active
created_at: 2026-03-19T21:40:00+07:00
updated_at: 2026-03-19T21:40:00+07:00
---

# Duplicate ID Probe
`;

    const duplicateA = DOCS_DUPLICATE_PATH;
    const duplicateB = DOCS_DUPLICATE_PATH.replace("-DUPLICATE-ID.md", "-DUPLICATE-ID-B.md");
    const pass = await withTempFile(duplicateA, duplicateTemplate, async () => {
      return await withTempFile(duplicateB, duplicateTemplate, () => {
        const check = run("node", ["./bin/zcl.js", "doc:check"]);
        return check.code !== 0 && check.output.includes("Duplicate document_id");
      });
    });

    addResult(results, {
      testName: "Docs 3 — Duplicate ID Detection",
      scope,
      pass,
      failureReason: pass ? "" : "duplicate document_id was not detected",
      commandExecuted: "node ./bin/zcl.js doc:check (with temporary duplicate document_id)",
      expectedOutcome: "doc:check returns non-zero with duplicate-id finding",
      actualOutcome: pass ? "duplicate id detection works" : "duplicate id detection mismatch",
      recommendedNextAction: pass ? "none" : "repair document index duplicate-id detection",
      warning: false,
    });
  }

  {
    const preflight = run("npm", ["run", "ops:preflight"]);
    const pass =
      preflight.code === 0 &&
      preflight.output.includes("document-structure") &&
      preflight.output.includes("document-schema") &&
      preflight.output.includes("document-naming");
    addResult(results, {
      testName: "Docs 4 — Preflight Integration",
      scope,
      pass,
      failureReason: pass ? "" : "preflight does not surface document governance checks",
      commandExecuted: preflight.command,
      expectedOutcome: "preflight includes document-structure/schema/naming checks",
      actualOutcome: pass ? "document checks visible in preflight output" : preflight.output,
      recommendedNextAction: pass ? "none" : "integrate document checks into preflight",
      warning: preflight.output.includes("Status: WARNING"),
    });
  }
}

function summarize(results, selectedMode) {
  const failed = results.filter((item) => !item.pass);
  const warnings = results.filter((item) => item.pass && item.warning);

  let confidence = "core-unverified";
  if (failed.length > 0) {
    confidence = "core-unverified";
  } else if (selectedMode === "smoke") {
    confidence = warnings.length > 0 ? "verification-warning" : "core-smoke-pass";
  } else if (selectedMode === "all") {
    confidence = warnings.length > 0 ? "verification-warning" : "core-verified";
  } else {
    confidence = warnings.length > 0 ? "verification-warning" : "core-smoke-pass";
  }

  return {
    mode: selectedMode,
    environment: `${process.platform}-${process.arch}`,
    totals: {
      total: results.length,
      pass: results.length - failed.length,
      fail: failed.length,
      warning: warnings.length,
    },
    confidence,
    results,
  };
}

function printSummary(summary) {
  console.log("ZMOS WS-G Verification Report");
  console.log(`Mode: ${summary.mode}`);
  console.log(`Environment: ${summary.environment}`);
  console.log(
    `Totals: total=${summary.totals.total} pass=${summary.totals.pass} fail=${summary.totals.fail} warning=${summary.totals.warning}`,
  );
  console.log(`Confidence: ${summary.confidence}`);
  console.log("");
  console.log(JSON.stringify(summary, null, 2));
}

async function main() {
  const results = [];
  bootstrapRequiredPaths();

  if (!commandExists("bin/zcl.js")) {
    console.error("verify: workspace does not look like zmos-core root (bin/zcl.js missing)");
    process.exit(1);
  }

  const build = run("npm", ["run", "ops:build"]);
  if (build.code !== 0) {
    addResult(results, {
      testName: "Bootstrap Build Gate",
      scope: "bootstrap",
      pass: false,
      failureReason: "ops build failed",
      commandExecuted: build.command,
      expectedOutcome: "build succeeds before verification",
      actualOutcome: build.output,
      recommendedNextAction: "repair build and rerun verification",
      warning: false,
    });
    const summary = summarize(results, mode);
    printSummary(summary);
    process.exit(1);
  }

  if (mode === "smoke" || mode === "all") {
    await runSmokeSuite(results);
  }
  if (mode === "core" || mode === "all") {
    await runCoreSuite(results);
  }
  if (mode === "trace" || mode === "all") {
    await runTraceSuite(results);
  }
  if (mode === "docs" || mode === "all") {
    await runDocsSuite(results);
  }

  const summary = summarize(results, mode);
  printSummary(summary);

  if (summary.totals.fail > 0) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error("verify: unexpected runtime failure");
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
