import { runGovernedAiTask } from "./_governed-run.js";

const SMOKE_PAYLOAD = {
  task: "system-check",
  goal: "Confirm Z-MOS AI integration is operational",
  input: "Verify that the AI client can receive a structured task and return a valid response.",
  constraints: ["respond in one sentence", "no markdown", "no filler"],
};

export async function runAiTestCommand(): Promise<void> {
  await runGovernedAiTask("zcl ai test", SMOKE_PAYLOAD);
}
