import { promises as fs } from "node:fs";
import * as path from "node:path";
import { FULL_VERSION } from "../../sdk/version.js";

export async function runTraceSummaryCommand(): Promise<void> {
  const tracePath = path.join(process.cwd(), ".z-mos/trace/runtime-trace.jsonl");
  try {
    const data = await fs.readFile(tracePath, "utf8");
    const lines = data.split("\n").filter(l => l.trim().length > 0);
    
    if (lines.length === 0) {
      console.log(`[Z-MOS ${FULL_VERSION} TRACE SUMMARY] No trace records found.`);
      return;
    }

    const records = lines.map(l => JSON.parse(l));
    const recent = records.slice(-10);
    const latest = records[records.length - 1];

    let latestGate = "unknown";
    if (latest.details?.gateId) latestGate = latest.details.gateId;
    else if (latest.command) latestGate = latest.command;

    const errors = records.filter((r: any) => r.result_class === "failure" || r.result_class === "error").slice(-5);
    const lastHealthy = records.filter((r: any) => r.result_class === "success").pop();

    console.log("===================================================");
    console.log(`Z-MOS ${FULL_VERSION} [Trace Summary]`);
    console.log("===================================================");
    console.log(`latest_status: ${latest.result_class}`);
    console.log(`latest_gate/task: ${latestGate}`);
    console.log(`recent_failures: ${errors.length > 0 ? errors.length : 'none'}`);
    
    if (errors.length > 0) {
      console.log(`top_errors:`);
      errors.forEach((err: any) => {
         const msg = err.details?.gateId ? `Gate ${err.details.gateId} failed` : err.command;
         console.log(`  - ${msg} (${err.timestamp})`);
      });
    }

    console.log(`trace_file: ${tracePath}`);
    if (lastHealthy) {
      console.log(`last_healthy_record: ${lastHealthy.timestamp}`);
    }
    console.log("===================================================");

  } catch (error) {
    console.error(`Failed to summarize trace: ${error instanceof Error ? error.message : String(error)}`);
  }
}
