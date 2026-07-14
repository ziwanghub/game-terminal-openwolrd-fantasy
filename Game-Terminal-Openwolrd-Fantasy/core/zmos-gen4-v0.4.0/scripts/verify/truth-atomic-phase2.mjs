import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, unlinkSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const ZMOS_DIR = path.join(ROOT_DIR, ".z-mos");
const TRUTH_PATH = path.join(ZMOS_DIR, "truth.contract.json");

async function main() {
  const moduleUrl = pathToFileURL(path.join(ROOT_DIR, "dist", "core", "truth-store.js")).href;
  const { writeTruthContractAtomic } = await import(moduleUrl);

  const original = {
    schema_version: "2.0.0",
    generated_at: "2026-05-06T00:00:00.000Z",
    code_ref: { commit: "abc123", branch: "main" },
    runtime_ref: { platform: "node", process: "zcl" },
    env_ref: { target_host: "localhost", target_env: "dev", config_hash: "cfg1" },
    data_ref: { source: "local", schema_hash: "sch1" },
    asset_ref: { bundle_hash: "bun1", cache_hash: "cac1" },
    gate_state: { active_gate: "standard", required_checks: ["preflight"] },
    confidence: 1,
    unknowns: [],
    verdict: "SAFE_TO_CONTINUE",
  };

  const replacement = {
    ...original,
    code_ref: { commit: "def456", branch: "develop" },
    generated_at: "2026-05-06T00:05:00.000Z",
  };

  const hadOriginalTruth = existsSync(TRUTH_PATH);
  const originalTruthRaw = hadOriginalTruth ? readFileSync(TRUTH_PATH, "utf8") : null;
  writeFileSync(TRUTH_PATH, `${JSON.stringify(original, null, 2)}\n`, "utf8");

  const before = readFileSync(TRUTH_PATH, "utf8");
  let failureThrown = false;
  try {
    await writeTruthContractAtomic(replacement, {
      simulateFailureAfterBackup: true,
      now: new Date("2026-05-06T00:06:00.000Z"),
    });
  } catch {
    failureThrown = true;
  }

  assert.equal(failureThrown, true, "simulated failure should throw");
  const afterFailure = readFileSync(TRUTH_PATH, "utf8");
  assert.equal(afterFailure, before, "truth.contract.json must remain unchanged after failure");

  const backupExpected = path.join(ZMOS_DIR, "truth.backup.2026-05-06T00-06-00-000Z.json");
  assert.equal(existsSync(backupExpected), true, "backup must be created before replacement");

  const successResult = await writeTruthContractAtomic(replacement, {
    now: new Date("2026-05-06T00:07:00.000Z"),
  });
  assert.equal(successResult.truthPath, TRUTH_PATH);
  assert.ok(typeof successResult.contractHash === "string" && successResult.contractHash.length > 0);

  const finalContent = JSON.parse(readFileSync(TRUTH_PATH, "utf8"));
  assert.equal(finalContent.code_ref.commit, "def456");

  const backupFiles = readdirSync(ZMOS_DIR).filter((entry) => entry.startsWith("truth.backup."));
  assert.ok(backupFiles.length >= 2, "backup should be created on every replacement");

  for (const backup of backupFiles) {
    const backupPath = path.join(ZMOS_DIR, backup);
    const backupRaw = readFileSync(backupPath, "utf8");
    if (backupRaw.includes("\"schema_version\": \"2.0.0\"")) {
      unlinkSync(backupPath);
    }
  }

  if (hadOriginalTruth && originalTruthRaw !== null) {
    writeFileSync(TRUTH_PATH, originalTruthRaw, "utf8");
  } else if (existsSync(TRUTH_PATH)) {
    unlinkSync(TRUTH_PATH);
  }

  console.log("truth-atomic-phase2: PASS");
}

main();
