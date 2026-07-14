import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { runWithIntent } from "../../sdk/runtime/run-with-intent.ts";
import { SCHEMA_VERSION_AGENT, VERSION } from "../../sdk/version.ts";

function buildIntent(overrides?: Partial<any>) {
  return {
    schema_version: SCHEMA_VERSION_AGENT,
    intent: {
      objective: "test objective",
      strategy: "test strategy",
      risk_acknowledgement: "None",
    },
    system: {
      scope_files: ["sdk/runtime/run-with-intent.ts", "docs/intent-card-spec.md"],
      required_tests: [],
      stop_conditions: [],
      rollback_plan: "revert",
      truth_snapshot_ref: ".z-mos/truth.contract.json",
    },
    agent: {
      allowed_tools: ["functions.apply_patch"],
      allowed_actions: ["write", "read"],
      max_steps: 5,
      termination_conditions: [],
      enforcement: "hard-block",
    },
    ...overrides,
  };
}

function buildTruth(verdict: "SAFE_TO_CONTINUE" | "STOP_AND_REPAIR" | "PROCEED_WITH_CAUTION") {
  return {
    schema_version: VERSION,
    generated_at: new Date().toISOString(),
    verdict,
  };
}

async function createWorkspace(intent: any, truth: any) {
  const root = await mkdtemp(path.join(tmpdir(), "zmos-run-with-intent-"));
  const zmosDir = path.join(root, ".z-mos");
  await mkdir(zmosDir, { recursive: true });
  await writeFile(path.join(zmosDir, "intent.card.json"), JSON.stringify(intent, null, 2));
  await writeFile(path.join(zmosDir, "truth.contract.json"), JSON.stringify(truth, null, 2));
  return root;
}

test("runWithIntent happy path allows execution", async () => {
  const workspaceDir = await createWorkspace(buildIntent(), buildTruth("SAFE_TO_CONTINUE"));
  try {
    let executed = false;
    const result = await runWithIntent({
      workspaceDir,
      action: {
        action: "write",
        tool: "functions.apply_patch",
        targetPaths: ["sdk/runtime/run-with-intent.ts"],
      },
      agentContext: {
        sessionId: "s1",
        agentName: "codex",
      },
      handler: async ({ agentContext }) => {
        executed = true;
        return `ok:${agentContext?.agentName}`;
      },
    });

    assert.equal(result.blocked, false);
    assert.equal(result.success, true);
    assert.equal(result.decision, "ALLOW");
    assert.equal(result.data, "ok:codex");
    assert.equal(executed, true);
  } finally {
    await rm(workspaceDir, { recursive: true, force: true });
  }
});

test("runWithIntent blocks when truth verdict is not SAFE_TO_CONTINUE", async () => {
  const workspaceDir = await createWorkspace(buildIntent(), buildTruth("STOP_AND_REPAIR"));
  try {
    let executed = false;
    const result = await runWithIntent({
      workspaceDir,
      action: {
        action: "write",
        tool: "functions.apply_patch",
        targetPaths: ["sdk/runtime/run-with-intent.ts"],
      },
      handler: async () => {
        executed = true;
        return "should-not-run";
      },
    });

    assert.equal(result.blocked, true);
    assert.equal(result.reason, "TRUTH_VERDICT_BLOCKED");
    assert.equal(executed, false);
  } finally {
    await rm(workspaceDir, { recursive: true, force: true });
  }
});

test("runWithIntent blocks disallowed tool/action", async () => {
  const workspaceDir = await createWorkspace(buildIntent(), buildTruth("SAFE_TO_CONTINUE"));
  try {
    let executed = false;
    const result = await runWithIntent({
      workspaceDir,
      action: {
        action: "command",
        tool: "functions.exec_command",
        targetPaths: ["sdk/runtime/run-with-intent.ts"],
      },
      handler: async () => {
        executed = true;
        return "should-not-run";
      },
    });

    assert.equal(result.blocked, true);
    assert.ok(result.reason === "TOOL_NOT_ALLOWED" || result.reason === "ACTION_NOT_ALLOWED");
    assert.equal(executed, false);
  } finally {
    await rm(workspaceDir, { recursive: true, force: true });
  }
});

test("runWithIntent blocks scope violation", async () => {
  const workspaceDir = await createWorkspace(buildIntent(), buildTruth("SAFE_TO_CONTINUE"));
  try {
    let executed = false;
    const result = await runWithIntent({
      workspaceDir,
      action: {
        action: "write",
        tool: "functions.apply_patch",
        targetPaths: ["core/forbidden.ts"],
      },
      handler: async () => {
        executed = true;
        return "should-not-run";
      },
    });

    assert.equal(result.blocked, true);
    assert.equal(result.reason, "SCOPE_VIOLATION");
    assert.equal(executed, false);
  } finally {
    await rm(workspaceDir, { recursive: true, force: true });
  }
});
