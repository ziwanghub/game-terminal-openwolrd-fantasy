import { loadDataPrompt, type LoadDataMode, type LoadDataType } from "../../core/load-data.js";

type LoadDataArgs = {
  type: LoadDataType;
  mode: LoadDataMode;
  projectPath?: string;
};

function parseLoadDataArgs(argv: string[]): LoadDataArgs | null {
  let type = "";
  let mode: LoadDataMode = "full";
  let projectPath: string | undefined;

  // 1. Process explicit flags
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];

    if (arg === "--type" && argv[i + 1]) {
      type = argv[++i] || "";
      continue;
    }
    if (arg.startsWith("--type=")) {
      type = arg.split("=")[1] || "";
      continue;
    }

    if (arg === "--mode" && argv[i + 1]) {
      const rawMode = argv[++i] || "";
      if (rawMode === "full" || rawMode === "compact") {
        mode = rawMode;
      } else {
        return null;
      }
      continue;
    }
    if (arg.startsWith("--mode=")) {
      const rawMode = arg.split("=")[1] || "";
      if (rawMode === "full" || rawMode === "compact") {
        mode = rawMode;
      } else {
        return null;
      }
      continue;
    }

    if (arg === "--project" && argv[i + 1]) {
      projectPath = argv[++i] || undefined;
      continue;
    }
    if (arg.startsWith("--project=")) {
      projectPath = arg.split("=")[1] || undefined;
      continue;
    }
  }

  // 2. Process positional arguments (if type is still empty)
  if (!type) {
    for (const arg of argv) {
      if (!arg.startsWith("-")) {
        if (arg === "zmos" || arg === "master") {
          type = "zmos-master";
          break;
        }
        if (arg === "usage") {
          type = "zmos-usage-prompt";
          break;
        }
        if (arg === "ai2ai") {
          type = "zmos-usage-prompt";
          mode = "compact";
          break;
        }
        if (arg === "new-room") {
          type = "new-room-prompt";
          break;
        }
        if (arg === "team-onboarding" || arg === "onboarding") {
          type = "team-onboarding";
          break;
        }
      }
    }
  }

  // 3. Apply default if still empty
  if (!type) {
    type = "zmos-master";
  }

  if (
    type !== "new-room-prompt" &&
    type !== "zmos-usage-prompt" &&
    type !== "zmos-master" &&
    type !== "team-onboarding"
  ) {
    return null;
  }

  return {
    type: type as LoadDataType,
    mode,
    projectPath,
  };
}

function printUsage(): void {
  console.error(
    [
      "Usage:",
      "  zcl load-data [zmos|usage|new-room|ai2ai] [--project <path>] [--mode full|compact]",
      "  zcl load-data --type zmos-master [--mode full|compact]",
      "  zcl load-data --type team-onboarding [--project <path>]",
      "",
      "Shorthands:",
      "  zcl load-data        -> Defaults to zmos-master",
      "  zcl load-data zmos   -> Shorthand for zmos-master",
      "  zcl load-data usage  -> Shorthand for zmos-usage-prompt",
      "  zcl load-data ai2ai  -> Shorthand for zmos-usage-prompt --mode compact",
      "  zcl load-data onboarding -> Shorthand for team-onboarding",
      "",
      "Examples:",
      "  zcl load-data",
      "  zcl load-data zmos --project .",
      "",
      "Notes:",
      "  - This command is read-only.",
      "  - No trace write, no state mutation.",
    ].join("\n"),
  );
}

export async function runLoadDataCommand(argv: string[]): Promise<void> {
  const parsed = parseLoadDataArgs(argv);
  if (!parsed) {
    printUsage();
    process.exitCode = 1;
    return;
  }

  const prompt = await loadDataPrompt({
    type: parsed.type,
    mode: parsed.mode,
    projectPath: parsed.projectPath,
  });

  console.log(prompt);
}
