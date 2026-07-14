import { verifyWorkspace } from "zmos-core/sdk/index.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// In a monorepo, Z-MOS core root is the monorepo root, but scripts might run in packages/
const MONOREPO_ROOT = path.resolve(__dirname, "..");

async function main() {
  console.log("Running Monorepo deployment script...");
  
  // We can pass the monorepo root to the Z-MOS SDK
  const result = verifyWorkspace({ workspaceDir: MONOREPO_ROOT, strict: true });
  
  if (!result.success) {
    console.error("Monorepo failed governance checks. Deployment aborted.");
    console.error(result.output);
    process.exit(1);
  }

  console.log("Monorepo governance check passed! Proceeding to deploy...");
}

main();
