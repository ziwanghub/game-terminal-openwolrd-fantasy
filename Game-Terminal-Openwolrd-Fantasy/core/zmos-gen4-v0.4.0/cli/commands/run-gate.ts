import { loadRunProfile, executeRunProfile } from "../../core/run-profile.js";
import { writeTraceRecord } from "../../core/trace-writer.js";
import { FULL_VERSION } from "../../sdk/version.js";

export async function runRunGateCommand(args: string[]): Promise<void> {
  const [gateId] = args;
  if (!gateId) {
    throw new Error("Usage: zcl run-gate <gate_id>");
  }

  console.log(`[Z-MOS ${FULL_VERSION}] Executing run profile: ${gateId}...`);
  try {
    const profile = await loadRunProfile(gateId);
    
    console.log(`- Gate ID: ${gateId}`);
    console.log(`- Workdir: ${profile.workdir || '.'}`);
    console.log(`- Timeout: ${profile.timeout_ms || 30000} ms`);
    console.log(`- Command: ${profile.command}`);
    if (profile.stop_conditions && profile.stop_conditions.length > 0) {
      console.log(`- Stop Conditions (Advisory): ${profile.stop_conditions.join(', ')}`);
    }
    
    const { passed, output } = await executeRunProfile(profile);
    
    await writeTraceRecord({
      command: `zcl run-gate ${gateId}`,
      status: passed ? "success" : "failed",
      actor: "system",
      details: {
        gateId,
        passed,
        nextAction: passed ? profile.next_action : "Investigate failure and retry."
      }
    });

    console.log("===================================================");
    if (passed) {
      console.log(`[PASS] Gate ${gateId} executed successfully.`);
      console.log(`[ACTION REQUIRED] Next: ${profile.next_action}`);
    } else {
      console.log(`[FAIL] Gate ${gateId} failed.`);
      console.log(`[OUTPUT SUMMARY]\n${output.slice(-500)}`);
      console.log(`[ACTION REQUIRED] Investigate failure and retry.`);
    }
    console.log("===================================================");

    if (!passed) {
      process.exitCode = 1;
    }
  } catch (error) {
    console.error(`Error: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  }
}
