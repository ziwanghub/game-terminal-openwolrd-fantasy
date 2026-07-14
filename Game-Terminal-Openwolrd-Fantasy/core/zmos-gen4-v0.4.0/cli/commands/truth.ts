import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import * as path from "node:path";
import { getGitContext } from "../../core/git.js";
import { writeTruthContractAtomic } from "../../core/truth-store.js";

type TruthContractPayload = {
  schema_version: string;
  generated_at: string;
  code_ref: {
    commit: string;
    branch: string;
  };
  runtime_ref: {
    platform: string;
    process: string;
  };
  env_ref: {
    target_host: string;
    target_env: string;
    config_hash: string;
  };
  data_ref: {
    source: string;
    schema_hash: string;
  };
  asset_ref: {
    bundle_hash: string;
    cache_hash: string;
  };
  gate_state: {
    active_gate: string;
    required_checks: string[];
  };
  confidence: number;
  unknowns: string[];
  verdict: "SAFE_TO_CONTINUE" | "BLOCKED" | "STALE" | "CONFLICTED" | "UNKNOWN";
};

function sha256(input: string): string {
  return createHash("sha256").update(input).digest("hex");
}

async function hashFileOrFallback(filePath: string, fallbackSeed: string): Promise<string> {
  try {
    const raw = await fs.readFile(filePath, "utf8");
    return sha256(raw);
  } catch {
    return sha256(fallbackSeed);
  }
}

function summarizeUnknowns(unknowns: string[]): string {
  return unknowns.length === 0 ? "none" : unknowns.join(", ");
}

export async function runTruthBuildCommand(): Promise<void> {
  const root = process.cwd();
  const git = getGitContext();
  const now = new Date();
  const unknowns: string[] = [];

  const commit = git.commit ?? "not-enough-evidence";
  const branch = git.branch ?? "not-enough-evidence";
  if (!git.commit) unknowns.push("git.commit");
  if (!git.branch) unknowns.push("git.branch");

  const nodeEnv = process.env.NODE_ENV || "development";
  const host = os.hostname() || "unknown-host";

  const schemaPath = path.join(root, ".z-mos", "schemas", "truth.contract.schema.json");
  const lockPath = path.join(root, "package-lock.json");
  const distGateway = path.join(root, "dist", "cli", "gateway.js");

  const schemaHash = await hashFileOrFallback(schemaPath, "schema-missing");
  const bundleHash = await hashFileOrFallback(lockPath, "lock-missing");
  const cacheHash = await hashFileOrFallback(distGateway, "dist-missing");
  const configHash = sha256(
    JSON.stringify({
      node_env: nodeEnv,
      cwd: root,
      platform: process.platform,
      arch: process.arch,
    }),
  );

  const payload: TruthContractPayload = {
    schema_version: "2.0.0",
    generated_at: now.toISOString(),
    code_ref: {
      commit,
      branch,
    },
    runtime_ref: {
      platform: `${process.platform}-${process.arch}`,
      process: "zcl truth build",
    },
    env_ref: {
      target_host: host,
      target_env: nodeEnv,
      config_hash: configHash,
    },
    data_ref: {
      source: "workspace-local",
      schema_hash: schemaHash,
    },
    asset_ref: {
      bundle_hash: bundleHash,
      cache_hash: cacheHash,
    },
    gate_state: {
      active_gate: "standard",
      required_checks: ["schema-validate", "preflight", "scope-guard"],
    },
    confidence: unknowns.length === 0 ? 0.98 : 0.7,
    unknowns,
    verdict: unknowns.length === 0 ? "SAFE_TO_CONTINUE" : "UNKNOWN",
  };

  const result = await writeTruthContractAtomic(payload);

  console.log("Z-MOS TRUTH BUILD");
  console.log("----------------");
  console.log(`truth_path: ${result.truthPath}`);
  console.log(`backup_path: ${result.backupPath ?? "(none)"}`);
  console.log(`contract_hash: ${result.contractHash}`);
  console.log(`unknowns: ${summarizeUnknowns(unknowns)}`);
  console.log(`verdict: ${payload.verdict}`);
}

