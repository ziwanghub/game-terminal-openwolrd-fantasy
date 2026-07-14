import { promises as fs } from "node:fs";
import * as path from "node:path";
import { getTraceFilePath, appendTraceRecord } from "../../trace/writer.js";

async function pathExists(p: string) {
  try { await fs.access(p); return true; } catch { return false; }
}

async function writeIfNotExists(p: string, content: string, force: boolean) {
  if (await pathExists(p) && !force) {
    console.log(`Skipping existing file: ${p} (use --force to overwrite)`);
    return false;
  }
  await fs.mkdir(path.dirname(p), { recursive: true });
  await fs.writeFile(p, content, "utf8");
  console.log(`Initialized: ${p}`);
  return true;
}

export async function runMemoryInitCommand(args: string[]): Promise<void> {
  const force = args.includes("--force");
  const initAll = args.length === 0 || (!args.includes("state") && !args.includes("handoff"));
  const initState = initAll || args.includes("state");
  const initHandoff = initAll || args.includes("handoff");

  const cwd = process.cwd();
  let initializedSomething = false;

  // Repair legacy session path in entrypoint.json if found
  const entrypointPath = path.join(cwd, ".z-mos/entrypoint.json");
  if (await pathExists(entrypointPath)) {
    try {
      const raw = await fs.readFile(entrypointPath, "utf8");
      const parsed = JSON.parse(raw);
      if (
        parsed &&
        parsed.runtime_state_paths &&
        parsed.runtime_state_paths.session === ".z-mos/state/session.json"
      ) {
        parsed.runtime_state_paths.session = ".z-mos/state/runtime-state.json";
        await fs.writeFile(entrypointPath, JSON.stringify(parsed, null, 2), "utf8");
        console.log("Repaired entrypoint.json: updated legacy session path to runtime-state.json");
        initializedSomething = true;
      }
    } catch {
      // ignore malformed entrypoint file for repair
    }
  }

  if (initAll) {
    const entrypointObj = {
      schema_version: "1.3.2",
      generated_at: new Date().toISOString(),
      standard_path: "docs/standards/ZMOS-COMMUNICATION-STANDARD.md",
      runtime_state_paths: {
        manifest: ".z-mos/zmos-manifest.json",
        session: ".z-mos/state/runtime-state.json",
        project_state: ".z-mos/state/project-state.json"
      },
      policy_paths: {
        workflow_policy: ".z-mos/workflow-policy.json",
        readiness_policy: ".z-mos/readiness-policy.json"
      },
      latest_artifacts: {
        latest_handoff: ".z-mos/intent.card.json",
        latest_report: ".z-mos/reports/latest.json",
        latest_advisory_bundle: ".z-mos/advisory/latest.json"
      },
      trace_path: ".z-mos/trace/runtime-trace.jsonl",
      rehydration_order: [
        "runtime_state_paths.manifest",
        "runtime_state_paths.project_state",
        "latest_artifacts.latest_handoff"
      ]
    };
    if (await writeIfNotExists(entrypointPath, JSON.stringify(entrypointObj, null, 2), force)) {
      initializedSomething = true;
    }

    const readinessPolicyPath = path.join(cwd, ".z-mos/readiness-policy.json");
    const readinessPolicyObj = {
      version: "1.0.0",
      defaultProfile: "standard",
      profiles: {
        standard: {
          description: "Controlled rollout mode: pass with explicitly budgeted warnings.",
          allowlistedPreflightWarnings: [
            "runtime-lock-health",
            "document-schema"
          ],
          allowDoctorWarning: true,
          allowStartWarning: true
        },
        strict: {
          description: "Hard production mode: zero-warning only.",
          allowlistedPreflightWarnings: [
            "worktree-discipline",
            "phase3-5state-code",
            "phase3-5state-runtime",
            "phase3-5state-environment",
            "phase3-5state-data-config",
            "phase3-5state-assets-schema",
            "document-structure"
          ],
          allowDoctorWarning: true,
          allowStartWarning: true
        }
      }
    };
    if (await writeIfNotExists(readinessPolicyPath, JSON.stringify(readinessPolicyObj, null, 2), force)) {
      initializedSomething = true;
    }
  }

  if (initState) {
    const statePath = path.join(cwd, ".z-mos/state/project-state.json");
    const stateObj = {
      schema_version: "1.3.2",
      current_phase: "unknown",
      active_gate: "standard",
      next_safe_action: "initiate system",
      current_working_blocker: null,
      last_updated: new Date().toISOString(),
      updated_by_task: "system",
      staleness_threshold_hours: 24,
      auto_stale_at: new Date(Date.now() + 24*60*60*1000).toISOString()
    };
    if (await writeIfNotExists(statePath, JSON.stringify(stateObj, null, 2), force)) {
      initializedSomething = true;
    }

    const sessionPath = path.join(cwd, ".z-mos/state/runtime-state.json");
    const sessionObj = {
      workspace: path.basename(cwd),
      framework: "Z-MOS",
      sessionState: "bootstrap",
      activeCommand: null,
      lastReport: null
    };
    if (await writeIfNotExists(sessionPath, JSON.stringify(sessionObj, null, 2), force)) {
      initializedSomething = true;
    }
  }

  if (initHandoff) {
    const handoffPath = path.join(cwd, ".z-mos/intent.card.json");
    const handoffObj = {
      schema_version: "3.0.0-agent",
      intent: {
        objective: "Define task objective",
        strategy: "Document chosen implementation path",
        risk_acknowledgement: "None"
      },
      system: {
        scope_files: [],
        required_tests: ["node ./scripts/verify/verify.mjs core"],
        stop_conditions: ["schema validation fail", "critical drift detected"],
        rollback_plan: "Revert to previous known-good commit and re-run verify:core",
        truth_snapshot_ref: ".z-mos/truth.contract.json",
        allowed_hosts: ["localhost"],
        allowed_databases: ["zmos_local_dev"]
      },
      agent: {
        allowed_tools: ["functions.exec_command", "functions.apply_patch"],
        allowed_actions: ["read", "write", "test", "command"],
        max_steps: 50,
        termination_conditions: ["attempted out-of-scope mutation"],
        enforcement: "hard-block"
      }
    };
    if (await writeIfNotExists(handoffPath, JSON.stringify(handoffObj, null, 2), force)) {
      initializedSomething = true;
    }
  }

  if (initializedSomething) {
    const tracePath = await getTraceFilePath();
    await appendTraceRecord({
      command: "zcl memory init",
      status: "success",
      actor: "system",
      details: { action: "initialized missing memory artifacts" }
    });
  }

  console.log("Memory initialization sequence complete.");
}
