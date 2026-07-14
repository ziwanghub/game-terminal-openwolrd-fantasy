import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { runWithIntent } from "../sdk/index.js";

async function createDemoWorkspace(): Promise<string> {
  const workspaceDir = await mkdtemp(path.join(tmpdir(), "zmos-example-"));
  const zmosDir = path.join(workspaceDir, ".z-mos");
  await mkdir(zmosDir, { recursive: true });

  const intentCard = {
    schema_version: "3.0.0-agent",
    intent: {
      objective: "Demo governed execution",
      strategy: "Allow one safe write action in declared scope",
      risk_acknowledgement: "None",
    },
    system: {
      scope_files: ["sdk/runtime/run-with-intent.ts"],
      required_tests: [],
      stop_conditions: [],
      rollback_plan: "No-op for demo",
      truth_snapshot_ref: ".z-mos/truth.contract.json",
      allowed_hosts: ["localhost"],
      allowed_databases: ["zmos_local_dev"],
    },
    agent: {
      allowed_tools: ["functions.apply_patch"],
      allowed_actions: ["write"],
      max_steps: 3,
      termination_conditions: [],
      enforcement: "hard-block",
    },
  };

  const truthContract = {
    schema_version: "3.0.0",
    generated_at: new Date().toISOString(),
    verdict: "SAFE_TO_CONTINUE",
  };

  await writeFile(path.join(zmosDir, "intent.card.json"), JSON.stringify(intentCard, null, 2));
  await writeFile(path.join(zmosDir, "truth.contract.json"), JSON.stringify(truthContract, null, 2));
  return workspaceDir;
}

async function main() {
  const workspaceDir = await createDemoWorkspace();

  try {
    const result = await runWithIntent({
      workspaceDir,
      action: {
        action: "write",
        tool: "functions.apply_patch",
        targetPaths: ["sdk/runtime/run-with-intent.ts"],
        metadata: { triggeredConditions: [] },
      },
      agentContext: {
        sessionId: "session-001",
        agentName: "codex",
      },
      stepIndex: 1,
      maxRuntimeMs: 10_000,
      handler: async ({ agentContext, action }) => ({
        message: "governed action executed",
        action: action.action,
        tool: action.tool,
        agent: agentContext?.agentName ?? "unknown",
      }),
    });

    if (result.blocked) {
      console.error("Execution blocked by governance.");
      console.error(result.reason, result.error);
      process.exit(1);
    }

    console.log("Execution allowed.");
    console.log(result.data);
  } finally {
    await rm(workspaceDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error("runWithIntent example failed:", error);
  process.exit(1);
});
