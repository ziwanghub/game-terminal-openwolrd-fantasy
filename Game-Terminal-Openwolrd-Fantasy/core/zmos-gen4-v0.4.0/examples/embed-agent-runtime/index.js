import { stabilizeWorkspace } from "zmos-core/sdk/index.js";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function runAgentLoop() {
  console.log("AI Agent initialized...");
  
  for (let step = 1; step <= 3; step++) {
    console.log(`\n--- Agent Step ${step} ---`);
    
    // Before executing any commands or making mutations, the agent asks Z-MOS to stabilize the environment
    console.log("Requesting Z-MOS stabilization...");
    const stable = stabilizeWorkspace({ workspaceDir: __dirname });
    
    if (!stable.success) {
      console.log("Z-MOS rejected stabilization. Agent must wait or abort.");
      console.log(stable.output);
      break;
    }
    
    console.log("Environment is stable. Executing logic...");
    // Agent executes logic here...
    console.log("Logic executed successfully.");
  }
}

runAgentLoop();
