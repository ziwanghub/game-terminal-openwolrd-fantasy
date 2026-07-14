import { promises as fs } from "node:fs";
import * as path from "node:path";
import { getTraceFilePath, appendTraceRecord } from "../../trace/writer.js";

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

export async function runReportCommand(args: string[]): Promise<void> {
  const parsed = parseArgs(args);
  const reportPath = path.join(process.cwd(), ".z-mos/reports/latest.json");
  
  const report = {
    schema_version: "1.3.2",
    generated_at: new Date().toISOString(),
    task: parsed["task"] || "unknown",
    mode: parsed["mode"] || "execution",
    status: parsed["status"] || "PASS",
    what_done: parsed["what-done"] || "unknown",
    evidence: parsed["evidence"] || "none",
    gaps: parsed["gaps"] || "none",
    risks: parsed["risks"] || "none"
  };
  
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2), "utf8");
  
  const tracePath = await getTraceFilePath();
  await appendTraceRecord({
    command: "zcl report",
    status: "success",
    actor: "system",
    details: { action: "Report generated", task: report.task, status: report.status }
  });

  console.log(`Z-MOS Report written consistently: Status [${report.status}]`);
}
