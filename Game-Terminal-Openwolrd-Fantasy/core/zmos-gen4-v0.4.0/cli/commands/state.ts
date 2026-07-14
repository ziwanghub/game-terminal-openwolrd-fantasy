import { promises as fs } from "node:fs";
import * as path from "node:path";
import { getTraceFilePath, appendTraceRecord } from "../../trace/writer.js";
import { getGitContext } from "../../core/git.js";

function parseArgs(args: string[]): Record<string, string> {
  const result: Record<string, string> = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith("--")) {
      const key = args[i].replace(/^--/, "");
      if (i + 1 < args.length && !args[i+1].startsWith("--")) {
        result[key] = args[i+1];
        i++;
      } else {
        result[key] = "true";
      }
    }
  }
  return result;
}

export async function runStateUpdateCommand(args: string[]): Promise<void> {
  const parsed = parseArgs(args);
  const statePath = path.join(process.cwd(), ".z-mos/state/project-state.json");
  
  let stateStr = "";
  try {
    stateStr = await fs.readFile(statePath, "utf8");
  } catch (err) {
    console.error(`error: ${statePath} not found.`);
    process.exitCode = 1;
    return;
  }
  const state = JSON.parse(stateStr);
  
  if (parsed["phase"]) state.current_phase = parsed["phase"];
  if (parsed["next-action"]) state.next_safe_action = parsed["next-action"];
  if (parsed["blocker"]) state.current_working_blocker = parsed["blocker"] === "none" ? null : parsed["blocker"];
  
  const now = new Date();
  state.last_updated = now.toISOString();
  state.updated_by_task = parsed["task"] || "system";
  
  const git = getGitContext();
  state.synchronized_commit_hash = git.commit;
  state.synchronized_branch = git.branch;
  state.synchronized_at = now.toISOString();

  if (state.staleness_threshold_hours) {
    const staleTime = new Date(now.getTime() + state.staleness_threshold_hours * 60 * 60 * 1000);
    state.auto_stale_at = staleTime.toISOString();
  }
  
  await fs.writeFile(statePath, JSON.stringify(state, null, 2), "utf8");
  
  const tracePath = await getTraceFilePath();
  await appendTraceRecord({
    command: "zcl state update",
    status: "success",
    actor: "system",
    details: {
      action: "Project state updated safely",
      phase: state.current_phase,
      next_action: state.next_safe_action
    }
  });

  console.log(`Z-MOS Project State updated. Phase: ${state.current_phase}`);
}
