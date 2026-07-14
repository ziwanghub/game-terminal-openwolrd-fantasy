import { promises as fs } from "node:fs";
import * as path from "node:path";

import { getManifestPath, readManifest } from "../core/manifest.js";
import { getNodePath, loadNodeIdentity } from "../core/node.js";
import { getTraceFilePath } from "../trace/writer.js";
import { readTruthRuntimeSnapshot } from "../core/truth-runtime.js";

export type ReadinessLevel =
  | "bootstrap"
  | "manifest-active"
  | "trace-active"
  | "advisory-operational"
  | "governance-runtime-v1";

export type ReadinessSignals = {
  manifestAvailable: boolean;
  truthAvailable: boolean;
  traceAvailable: boolean;
  contractsPresent: boolean;
  aiCliOperational: boolean;
  nodeIdentityActive: boolean;
};

const AI_CLI_OPERATIONAL_STATES = new Set([
  "operational-advisory",
  "provider-agnostic-governance",
]);

export type GovernanceReadiness = {
  level: ReadinessLevel;
  signals: ReadinessSignals;
  activeCapabilities: string[];
};

async function pathExists(targetPath: string): Promise<boolean> {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function areContractsPresent(rootDir: string): Promise<boolean> {
  const contractPaths = [
    path.join(rootDir, "contracts", "manifest.ts"),
    path.join(rootDir, "contracts", "trace.ts"),
  ];

  const states = await Promise.all(contractPaths.map((filePath) => pathExists(filePath)));
  return states.every(Boolean);
}

function resolveReadinessLevel(signals: ReadinessSignals): ReadinessLevel {
  if (
    signals.manifestAvailable &&
    signals.truthAvailable &&
    signals.traceAvailable &&
    signals.contractsPresent &&
    signals.aiCliOperational &&
    signals.nodeIdentityActive
  ) {
    return "governance-runtime-v1";
  }

  if (
    signals.manifestAvailable &&
    signals.truthAvailable &&
    signals.traceAvailable &&
    signals.aiCliOperational
  ) {
    return "advisory-operational";
  }

  if (signals.manifestAvailable && signals.truthAvailable && signals.traceAvailable) {
    return "trace-active";
  }

  if (signals.manifestAvailable && signals.truthAvailable) {
    return "manifest-active";
  }

  return "bootstrap";
}

function buildActiveCapabilities(signals: ReadinessSignals): string[] {
  const capabilities: string[] = [];

  if (signals.manifestAvailable) {
    capabilities.push("manifest-runtime-state");
  }

  if (signals.truthAvailable) {
    capabilities.push("truth-runtime-state");
  }

  if (signals.traceAvailable) {
    capabilities.push("append-only-trace");
  }

  if (signals.contractsPresent) {
    capabilities.push("contracts-and-validation");
  }

  if (signals.aiCliOperational) {
    capabilities.push("ai-cli-advisory");
  }

  if (signals.nodeIdentityActive) {
    capabilities.push("node-identity-active");
  }

  return capabilities;
}

export async function evaluateReadiness(): Promise<GovernanceReadiness> {
  const rootDir = process.cwd();
  const manifest = await readManifest();
  const truthSnapshot = await readTruthRuntimeSnapshot();
  const node = await loadNodeIdentity();

  const [
    manifestAvailable,
    truthAvailable,
    traceAvailable,
    contractsPresent,
    nodeIdentityPathExists,
  ] =
    await Promise.all([
      pathExists(getManifestPath()),
      Promise.resolve(truthSnapshot.truthAvailable),
      pathExists(await getTraceFilePath()),
      areContractsPresent(rootDir),
      pathExists(getNodePath()),
    ]);

  const aiCliOperational = AI_CLI_OPERATIONAL_STATES.has(manifest.status.aiCli);
  const nodeIdentityActive =
    nodeIdentityPathExists &&
    node.node_id.trim().length > 0 &&
    node.node_role.trim().length > 0;
  const signals: ReadinessSignals = {
    manifestAvailable,
    truthAvailable,
    traceAvailable,
    contractsPresent,
    aiCliOperational,
    nodeIdentityActive,
  };

  return {
    level: resolveReadinessLevel(signals),
    signals,
    activeCapabilities: buildActiveCapabilities(signals),
  };
}
