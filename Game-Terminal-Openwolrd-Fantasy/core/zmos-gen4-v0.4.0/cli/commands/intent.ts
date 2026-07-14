import { promises as fs } from "node:fs";
import * as path from "node:path";

type IntentInitOptions = {
  force: boolean;
};

function parseArgs(args: string[]): IntentInitOptions {
  return {
    force: args.includes("--force"),
  };
}

function buildDefaultIntentCard() {
  return {
    schema_version: "3.0.0-agent",
    intent: {
      objective: "Define task objective",
      strategy: "Document chosen implementation path",
      risk_acknowledgement: "None",
    },
    system: {
      scope_files: [],
      required_tests: ["node ./scripts/verify/verify.mjs core"],
      stop_conditions: ["schema validation fail", "critical drift detected"],
      rollback_plan: "Revert to previous known-good commit and re-run verify:core",
      truth_snapshot_ref: ".z-mos/truth.contract.json",
      allowed_hosts: ["localhost"],
      allowed_databases: ["zmos_local_dev"],
    },
    agent: {
      allowed_tools: ["functions.exec_command", "functions.apply_patch"],
      allowed_actions: ["read", "write", "test", "command"],
      max_steps: 50,
      termination_conditions: ["attempted out-of-scope mutation"],
      enforcement: "hard-block",
    },
  };
}

export async function runIntentInitCommand(args: string[]): Promise<void> {
  const options = parseArgs(args);
  const intentPath = path.join(process.cwd(), ".z-mos", "intent.card.json");

  try {
    await fs.access(intentPath);
    if (!options.force) {
      console.log(`Skipping existing file: ${intentPath} (use --force to overwrite)`);
      return;
    }
  } catch {
    // File does not exist. Continue.
  }

  await fs.mkdir(path.dirname(intentPath), { recursive: true });
  const payload = buildDefaultIntentCard();
  await fs.writeFile(intentPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  console.log(`Initialized: ${intentPath}`);
}
