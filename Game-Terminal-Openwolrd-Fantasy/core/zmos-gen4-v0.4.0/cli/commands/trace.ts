import { verifyTraceIntegrity } from "../../core/trace-verifier.js";
import { getTraceFilePath } from "../../core/trace-writer.js";

export async function runTraceVerifyCommand(jsonFormat: boolean): Promise<void> {
  const tracePath = await getTraceFilePath();
  const result = await verifyTraceIntegrity(tracePath);

  if (jsonFormat) {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log(`Trace Integrity Verification:`);
    console.log(`  - Status: ${result.status}`);
    console.log(`  - Checked Entries: ${result.checked_entries}`);
    if (result.enforcement_start_sequence !== null) {
      console.log(`  - Enforcement Start Sequence: ${result.enforcement_start_sequence}`);
    }
    if (result.tampered_at_sequence !== null) {
      console.log(`  - Tampered At Sequence: ${result.tampered_at_sequence}`);
    }
    console.log(`  - Verified At: ${result.verified_at}`);
  }

  if (result.status === "valid") {
    process.exitCode = 0;
  } else if (result.status === "tampered") {
    process.exitCode = 1;
  } else if (result.status === "error") {
    process.exitCode = 2;
  }
}
