import { promises as fs } from "node:fs";
import * as path from "node:path";

export async function runNextCommand(): Promise<void> {
  let projectState: any = null;
  let handoffState: any = null;
  
  try {
    projectState = JSON.parse(await fs.readFile(path.join(process.cwd(), ".z-mos/state/project-state.json"), "utf8"));
  } catch {}
  try {
    handoffState = JSON.parse(await fs.readFile(path.join(process.cwd(), ".z-mos/intent.card.json"), "utf8"));
  } catch {}

  const phase = projectState?.current_phase || handoffState?.current_phase || "unknown";
  const gate = projectState?.active_gate || "unknown";
  const runProfile = gate !== "unknown" ? gate : "standard";
  const blocked = projectState?.current_working_blocker ? true : false;
  
  let output;
  if (blocked) {
    output = {
      next_task: "Repair blocking issues",
      exact_command: "zcl doctor",
      why: `System is blocked: ${projectState?.current_working_blocker}`,
      warnings: ["Do not mutate logic files until doctor is clear."]
    };
  } else {
    output = {
      next_task: handoffState?.next_safe_action || projectState?.next_safe_action || "Continue execution",
      exact_command: `zcl run-gate ${runProfile}`,
      why: `Gate '${runProfile}' is the active gate for phase '${phase}'.`,
      warnings: []
    };
  }

  console.log(JSON.stringify(output, null, 2));
}
