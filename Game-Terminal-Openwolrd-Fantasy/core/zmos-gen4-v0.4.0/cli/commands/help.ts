import { promises as fs } from "node:fs";
import * as path from "node:path";

type HelpEntry = {
  key: string;
  command: string;
  purpose: string;
  usage: string[];
  category: "core" | "data" | "tls" | "help" | "other";
  family:
    | "doctor"
    | "start"
    | "migrate"
    | "preflight"
    | "init"
    | "status"
    | "core"
    | "doc"
    | "workflow"
    | "trace"
    | "context"
    | "lane"
    | "budget"
    | "load-data"
    | "tls"
    | "ai"
    | "help";
};

const HELP_ENTRIES: HelpEntry[] = [
  {
    key: "doctor",
    command: "zcl doctor",
    purpose: "Check system health and readiness",
    usage: ["zcl doctor", "zcl doctor --project <path>"],
    category: "core",
    family: "doctor",
  },
  {
    key: "start",
    command: "zcl start",
    purpose: "Initialize execution environment",
    usage: ["zcl start"],
    category: "core",
    family: "start",
  },
  {
    key: "migrate",
    command: "zcl migrate",
    purpose: "Perform system migration (supports dry-run)",
    usage: [
      "zcl migrate --from v0.2.x --to evo1.0 --dry-run",
      "zcl migrate --from v0.2.x --to evo1.0 [--force] [--apply-rewrite-safe]",
    ],
    category: "core",
    family: "migrate",
  },
  {
    key: "preflight",
    command: "zcl preflight",
    purpose: "Run startup preflight checks",
    usage: ["zcl preflight"],
    category: "other",
    family: "preflight",
  },
  {
    key: "init",
    command: "zcl init",
    purpose: "Bootstrap canonical runtime state",
    usage: ["zcl init"],
    category: "other",
    family: "init",
  },
  {
    key: "status",
    command: "zcl status",
    purpose: "Show runtime status summary",
    usage: ["zcl status", "zcl status --project <path>"],
    category: "other",
    family: "status",
  },
  {
    key: "core",
    command: "zcl core <subcommand>",
    purpose: "Core baseline doctor/clean/restore commands",
    usage: [
      "zcl core doctor",
      "zcl core clean [--dry-run]",
      "zcl core restore [--dry-run]",
    ],
    category: "other",
    family: "core",
  },
  {
    key: "document",
    command: "zcl doc:*",
    purpose: "Document governance checks",
    usage: [
      "zcl doc:check",
      "zcl doc:index [--type=<type>] [--phase=<phase>] [--status=<status>]",
      "zcl doc:doctor",
    ],
    category: "other",
    family: "doc",
  },
  {
    key: "workflow",
    command: "zcl workflow <subcommand>",
    purpose: "Run governed workflows",
    usage: [
      "zcl workflow list",
      "zcl workflow runtime-check",
      "zcl workflow advisory-check",
    ],
    category: "other",
    family: "workflow",
  },
  {
    key: "trace",
    command: "zcl trace verify",
    purpose: "Verify trace integrity",
    usage: ["zcl trace verify [--json]"],
    category: "other",
    family: "trace",
  },
  {
    key: "context",
    command: "zcl context <subcommand>",
    purpose: "Manage task context cache state",
    usage: [
      "zcl context init --task-id <id> [--force]",
      "zcl context show --task-id <id>",
      "zcl context update --task-id <id> --patch <json>",
      "zcl context invalidate --task-id <id> --reason <taxonomy>",
    ],
    category: "other",
    family: "context",
  },
  {
    key: "lane",
    command: "zcl lane <subcommand>",
    purpose: "Manage worker lane ownership and locks",
    usage: [
      "zcl lane claim --task-id <id> --lane <lane> --actor <id>",
      "zcl lane release --task-id <id> --actor <id>",
      "zcl lane lock-path --task-id <id> --lane <lane> --actor <id> --path <glob>",
      "zcl lane lock-artifact --task-id <id> --lane <lane> --actor <id> --artifact <id>",
      "zcl lane handoff --task-id <id> --to-lane <lane> --actor <id> --summary <text>",
      "zcl lane ack --task-id <id> --actor <id>",
    ],
    category: "other",
    family: "lane",
  },
  {
    key: "budget",
    command: "zcl budget <subcommand>",
    purpose: "Evaluate and enforce token budget prompt profiles",
    usage: [
      "zcl budget evaluate --task-id <id> --risk <low|medium|high> --mode <full|compact|unknown> --estimated-input <n>",
      "zcl budget profile --task-id <id> --profile <compact|balanced|full>",
      "zcl budget status --task-id <id>",
    ],
    category: "other",
    family: "budget",
  },
  {
    key: "load-data-new-room-prompt",
    command: "zcl load-data --type new-room-prompt",
    purpose: "Generate new room prompt",
    usage: [
      "zcl load-data --type new-room-prompt",
      "zcl load-data --type new-room-prompt --project .",
    ],
    category: "data",
    family: "load-data",
  },
  {
    key: "load-data-zmos-usage-prompt",
    command: "zcl load-data --type zmos-usage-prompt",
    purpose: "Generate Z-MOS usage prompt for AI teams",
    usage: [
      "zcl load-data --type zmos-usage-prompt",
      "zcl load-data --type zmos-usage-prompt --project .",
      "zcl load-data ai2ai --project .",
      "zcl load-data --type zmos-usage-prompt --mode compact",
    ],
    category: "data",
    family: "load-data",
  },
  {
    key: "load-data-team-onboarding",
    command: "zcl load-data --type team-onboarding",
    purpose: "Generate two-layer onboarding prompt (global + project)",
    usage: [
      "zcl load-data --type team-onboarding --project .",
      "zcl load-data onboarding --project <path>",
    ],
    category: "data",
    family: "load-data",
  },
  {
    key: "tls-install",
    command: "zcl tls install",
    purpose: "Install template system",
    usage: [
      "zcl tls install --source <path> --type <type> --name <name> [--dry-run] [--force]",
    ],
    category: "tls",
    family: "tls",
  },
  {
    key: "tls-update",
    command: "zcl tls update",
    purpose: "Update template system",
    usage: ["zcl tls update --name <name> --source <path> [--dry-run] [--force]"],
    category: "tls",
    family: "tls",
  },
  {
    key: "tls-validate",
    command: "zcl tls validate",
    purpose: "Validate template integrity",
    usage: ["zcl tls validate <name>"],
    category: "tls",
    family: "tls",
  },
  {
    key: "tls-other",
    command: "zcl tls <subcommand>",
    purpose: "Additional TLS operations",
    usage: [
      "zcl tls create --template <path> --config <file> --output <dir>",
      "zcl tls list [--type=<type>] [--status=<status>] [--json]",
      "zcl tls show <name>",
      "zcl tls sync",
      "zcl tls uninstall <name> [--dry-run] [--force]",
    ],
    category: "other",
    family: "tls",
  },
  {
    key: "ai",
    command: "zcl ai <subcommand>",
    purpose: "AI advisory commands",
    usage: ["zcl ai analyze", "zcl ai summarize", "zcl ai review"],
    category: "other",
    family: "ai",
  },
  {
    key: "help",
    command: "zcl help",
    purpose: "Show all available commands",
    usage: ["zcl help", "zcl help <command>", "zcl help --sync-check"],
    category: "help",
    family: "help",
  },
];

const SUMMARY_FAMILY_COVERAGE = new Set([
  "doctor",
  "start",
  "migrate",
  "load-data",
  "tls",
  "help",
  "preflight",
  "init",
  "status",
  "core",
  "doc",
  "workflow",
  "trace",
  "context",
  "lane",
  "budget",
  "ai",
]);

type ExecutionTargetContext = {
  kind: string;
  root: string;
  source: string;
};

function readExecutionTargetContext(): ExecutionTargetContext {
  return {
    kind: process.env.ZMOS_EXEC_TARGET_KIND || "not enough evidence",
    root: process.env.ZMOS_EXEC_TARGET_ROOT || process.cwd(),
    source: process.env.ZMOS_EXEC_RESOLUTION_SOURCE || "not enough evidence",
  };
}

function printSummary(): void {
  const target = readExecutionTargetContext();
  const lines = [
    "Z-MOS Command Line Interface (ZCL)",
    "Available Commands",
    "",
    "Execution Target Context",
    `- kind: ${target.kind}`,
    `- root: ${target.root}`,
    `- source: ${target.source}`,
    "",
    "Core Commands",
    "- zcl doctor",
    "  -> Check system health and readiness",
    "- zcl start",
    "  -> Initialize execution environment",
    "- zcl migrate",
    "  -> Perform system migration (supports dry-run)",
    "",
    "Data Commands",
    "- zcl load-data --type new-room-prompt",
    "  -> Generate new room prompt",
    "- zcl load-data --type zmos-usage-prompt",
    "  -> Generate Z-MOS usage prompt for AI teams",
    "- zcl load-data ai2ai",
    "  -> Generate compact AI2AI governance prompt",
    "",
    "TLS Commands",
    "- zcl tls install",
    "  -> Install template system",
    "- zcl tls update",
    "  -> Update template system",
    "- zcl tls validate",
    "  -> Validate template integrity",
    "",
    "Help Command",
    "- zcl help",
    "  -> Show all available commands",
    "- zcl help <command>",
    "  -> Show detailed usage",
    "",
    "Additional Commands",
    "- zcl preflight | zcl init | zcl status",
    "- zcl core doctor|clean|restore",
    "- zcl doc:check | zcl doc:index | zcl doc:doctor",
    "- zcl workflow list|runtime-check|advisory-check",
    "- zcl trace verify",
    "- zcl context init|show|update|invalidate",
    "- zcl lane claim|release|lock-path|lock-artifact|handoff|ack",
    "- zcl budget evaluate|profile|status",
    "- zcl tls create|list|show|sync|uninstall",
    "- zcl ai analyze|summarize|review",
    "",
    "Usage Notes",
    "- All commands follow Z-MOS lifecycle rules.",
    "- Mutation requires precheck (zcl doctor).",
    "- Do not manually modify .z-mos/.",
    "- Some commands are read-only (help, load-data).",
  ];

  console.log(lines.join("\n"));
}

function normalizeTopic(rawTopic: string): string {
  const value = rawTopic.trim().toLowerCase();
  if (value === "load-data" || value === "data") {
    return "load-data-zmos-usage-prompt";
  }
  if (value === "tls") {
    return "tls-install";
  }
  if (value === "doc") {
    return "document";
  }
  return value;
}

function printDetail(topic: string): void {
  const key = normalizeTopic(topic);
  const match = HELP_ENTRIES.find((entry) => entry.key === key || entry.command === key);
  if (!match) {
    console.log(`Unknown command help topic: ${topic}`);
    console.log("Run 'zcl help' to view all available commands.");
    process.exitCode = 1;
    return;
  }

  const target = readExecutionTargetContext();
  const lines = [
    "Z-MOS Command Line Interface (ZCL)",
    "Command Detail",
    "",
    `Command: ${match.command}`,
    `Purpose: ${match.purpose}`,
    "Usage:",
    ...match.usage.map((usage) => `- ${usage}`),
    "",
    "Execution Target Context:",
    `- kind: ${target.kind}`,
    `- root: ${target.root}`,
    `- source: ${target.source}`,
    "",
    "Read-Only Note:",
    "- Help command is read-only and does not mutate runtime state.",
  ];

  console.log(lines.join("\n"));
}

function normalizeGatewayGroup(rawGroup: string): string {
  if (rawGroup.startsWith("doc:")) {
    return "doc";
  }
  if (rawGroup === "doc") {
    return "doc";
  }
  if (rawGroup === "load-data") {
    return "load-data";
  }
  if (rawGroup === "tls") {
    return "tls";
  }
  if (rawGroup === "workflow") {
    return "workflow";
  }
  if (rawGroup === "trace") {
    return "trace";
  }
  if (rawGroup === "ai") {
    return "ai";
  }
  return rawGroup;
}

async function extractGatewayFamilies(): Promise<Set<string>> {
  const coreRoot = process.env.ZMOS_CORE_ROOT || process.cwd();
  const gatewayPath = path.join(coreRoot, "cli", "gateway.ts");
  const raw = await fs.readFile(gatewayPath, "utf8");

  const matches = raw.matchAll(/group\s*(?:===|!==)\s*"([^"]+)"/gu);
  const families = new Set<string>();
  for (const match of matches) {
    const group = match[1];
    if (!group) {
      continue;
    }
    families.add(normalizeGatewayGroup(group));
  }

  return families;
}

function collectHelpFamilies(): Set<string> {
  return new Set(HELP_ENTRIES.map((entry) => entry.family));
}

function setDiff(left: Set<string>, right: Set<string>): string[] {
  return Array.from(left).filter((item) => !right.has(item)).sort((a, b) => a.localeCompare(b));
}

async function runSyncCheck(): Promise<void> {
  const gatewayFamilies = await extractGatewayFamilies();
  const helpFamilies = collectHelpFamilies();

  const missingInHelp = setDiff(gatewayFamilies, helpFamilies);
  const extraInHelp = setDiff(helpFamilies, gatewayFamilies);
  const missingInSummary = setDiff(gatewayFamilies, SUMMARY_FAMILY_COVERAGE);

  const detailTopicInvalid = HELP_ENTRIES.filter(
    (entry) => !gatewayFamilies.has(entry.family) && entry.family !== "help",
  )
    .map((entry) => `${entry.key} -> ${entry.family}`)
    .sort((a, b) => a.localeCompare(b));

  const hasMismatch =
    missingInHelp.length > 0 ||
    extraInHelp.length > 0 ||
    missingInSummary.length > 0 ||
    detailTopicInvalid.length > 0;

  const lines = [
    "Z-MOS Help Sync Check",
    "",
    `- gateway families: ${Array.from(gatewayFamilies).sort((a, b) => a.localeCompare(b)).join(", ")}`,
    `- help families: ${Array.from(helpFamilies).sort((a, b) => a.localeCompare(b)).join(", ")}`,
    `- missing in help: ${missingInHelp.length > 0 ? missingInHelp.join(", ") : "(none)"}`,
    `- extra in help: ${extraInHelp.length > 0 ? extraInHelp.join(", ") : "(none)"}`,
    `- top-level summary missing families: ${missingInSummary.length > 0 ? missingInSummary.join(", ") : "(none)"}`,
    `- detail topic invalid mappings: ${detailTopicInvalid.length > 0 ? detailTopicInvalid.join(" | ") : "(none)"}`,
    "",
    `Result: ${hasMismatch ? "FAIL" : "PASS"}`,
  ];

  console.log(lines.join("\n"));
  if (hasMismatch) {
    process.exitCode = 1;
  }
}

export async function runHelpCommand(argv: string[]): Promise<void> {
  const [topic] = argv;

  if (!topic) {
    printSummary();
    return;
  }

  if (topic === "--sync-check" || topic === "sync-check") {
    await runSyncCheck();
    return;
  }

  printDetail(topic);
}
