import { bootstrapWorkspace, verifyWorkspace } from "zmos-core/sdk/index.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
  console.log("Starting Node Project...");
  
  // 1. Boot the environment
  const bootResult = bootstrapWorkspace({ workspaceDir: __dirname });
  if (!bootResult.success) {
    console.error("Z-MOS Bootstrap failed:", bootResult.error || bootResult.output);
    process.exit(1);
  }
  
  // 2. Enforce strict verification before doing anything critical
  const verifyResult = verifyWorkspace({ workspaceDir: __dirname, strict: true });
  if (!verifyResult.success) {
    console.error("Z-MOS Verification failed. Governance rules blocked execution.");
    console.error(verifyResult.output);
    process.exit(1);
  }

  console.log("Z-MOS verification passed! Running application logic...");
}

main();
