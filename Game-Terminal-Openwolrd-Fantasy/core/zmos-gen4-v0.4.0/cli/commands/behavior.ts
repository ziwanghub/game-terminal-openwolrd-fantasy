import { promises as fs, existsSync } from "node:fs";
import * as path from "node:path";
import { getTraceFilePath, getLastHashedTrace } from "../../core/trace-writer.js";

const BEHAVIOR_DIR = path.join(process.cwd(), ".z-mos", "behavior", "decisions");

type RiskLevel = "low" | "medium" | "high";
type RecordStatus = "active" | "superseded";

type BehaviorArgs = {
  context: string;
  decision: string;
  reason: string;
  risk: RiskLevel;
  traceRef: string;
  status: RecordStatus;
  autoFill: boolean;
  blefEnabled: boolean;
  blefBaseline: string;
  blefLogic: string;
  blefEvidence: string;
  blefFreeze: string;
};

function parseBehaviorArgs(argv: string[]): BehaviorArgs | null {
  const args: BehaviorArgs = {
    context: "",
    decision: "",
    reason: "",
    risk: "low",
    traceRef: "",
    status: "active",
    autoFill: false,
    blefEnabled: false,
    blefBaseline: "",
    blefLogic: "",
    blefEvidence: "",
    blefFreeze: "",
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--auto-fill") {
      args.autoFill = true;
      continue;
    }
    if (arg === "--blef") {
      args.blefEnabled = true;
      continue;
    }
    
    // Parse key-value flags (--flag <value>)
    if (arg.startsWith("--") && !arg.includes("=") && i + 1 < argv.length && !argv[i + 1]?.startsWith("--")) {
      const key = arg.replace("--", "");
      const val = argv[++i];
      if (val !== undefined) {
        if (key === "context") args.context = val;
        if (key === "decision") args.decision = val;
        if (key === "reason") args.reason = val;
        if (key === "risk" && ["low", "medium", "high"].includes(val)) args.risk = val as RiskLevel;
        if (key === "trace-ref") args.traceRef = val;
        if (key === "status" && ["active", "superseded"].includes(val)) args.status = val as RecordStatus;
        if (key === "blef-baseline") args.blefBaseline = val;
        if (key === "blef-logic") args.blefLogic = val;
        if (key === "blef-evidence") args.blefEvidence = val;
        if (key === "blef-freeze") args.blefFreeze = val;
      }
      continue;
    }
    
    // Parse key=value flags (--flag=value)
    if (arg.startsWith("--") && arg.includes("=")) {
      const [k, v] = arg.split("=");
      const key = k?.replace("--", "");
      if (key && v) {
        if (key === "context") args.context = v;
        if (key === "decision") args.decision = v;
        if (key === "reason") args.reason = v;
        if (key === "risk" && ["low", "medium", "high"].includes(v)) args.risk = v as RiskLevel;
        if (key === "trace-ref") args.traceRef = v;
        if (key === "status" && ["active", "superseded"].includes(v)) args.status = v as RecordStatus;
        if (key === "blef-baseline") args.blefBaseline = v;
        if (key === "blef-logic") args.blefLogic = v;
        if (key === "blef-evidence") args.blefEvidence = v;
        if (key === "blef-freeze") args.blefFreeze = v;
      }
      continue;
    }
  }

  return args;
}

function printUsage(): void {
  console.error(
    [
      "Usage:",
      "  zcl behavior record --context <text> --decision <text> --reason <text> --risk <low|medium|high> --trace-ref <sequence-N> [--status active|superseded] [--auto-fill] [--blef --blef-baseline <text> --blef-logic <text> --blef-evidence <text> --blef-freeze <text>]",
      "",
      "Notes:",
      "  - use --auto-fill to pull the latest trace_ref automatically.",
      "  - decision and reason cannot be auto-filled to prevent fake reasoning.",
      "  - add --blef to persist Baseline/Logic/Evidence/Freeze decision factors.",
    ].join("\n"),
  );
}

export async function runBehaviorRecordCommand(argv: string[]): Promise<void> {
  const parsed = parseBehaviorArgs(argv);
  if (!parsed) {
    printUsage();
    process.exitCode = 1;
    return;
  }

  if (parsed.autoFill) {
    if (!parsed.traceRef) {
      try {
        const tracePath = await getTraceFilePath();
        const lastTrace = await getLastHashedTrace(tracePath);
        parsed.traceRef = lastTrace?.sequence ? `sequence-${lastTrace.sequence}` : "sequence-0";
      } catch {
        parsed.traceRef = "sequence-0";
      }
    }
  }

  if (!parsed.context || !parsed.decision || !parsed.reason || !parsed.traceRef) {
    console.error("zcl check failed: --context, --decision, --reason, and --trace-ref are required (or use --auto-fill).");
    process.exitCode = 1;
    return;
  }
  if (parsed.blefEnabled) {
    if (!parsed.blefBaseline || !parsed.blefLogic || !parsed.blefEvidence || !parsed.blefFreeze) {
      console.error(
        "zcl check failed: --blef requires --blef-baseline, --blef-logic, --blef-evidence, and --blef-freeze.",
      );
      process.exitCode = 1;
      return;
    }
  }

  const dateObj = new Date();
  const timestamp = dateObj.toISOString();
  // Safe collision ID format: e.g. BIL-20260328T033000-abcd
  const idTimestamp = timestamp.replace(/[-:]/g, "").split(".")[0];
  const shortSuffix = Math.random().toString(36).substring(2, 6);
  const id = `BIL-${idTimestamp}-${shortSuffix}`;

  const record = {
    id,
    timestamp,
    agent: "Antigravity",
    context: parsed.context,
    decision: parsed.decision,
    reason: parsed.reason,
    risk: parsed.risk,
    trace_ref: parsed.traceRef,
    status: parsed.status,
    superseded_by: null,
    record_format: parsed.blefEnabled ? "BIL+BLEF-v1" : "BIL-v1",
    ...(parsed.blefEnabled
      ? {
          blef: {
            baseline: parsed.blefBaseline,
            logic: parsed.blefLogic,
            evidence: parsed.blefEvidence,
            freeze: parsed.blefFreeze,
          },
        }
      : {}),
  };

  if (!existsSync(BEHAVIOR_DIR)) {
    await fs.mkdir(BEHAVIOR_DIR, { recursive: true });
  }

  const filepath = path.join(BEHAVIOR_DIR, `${id}.json`);
  await fs.writeFile(filepath, JSON.stringify(record, null, 2), "utf8");
  console.log(`Behavior record created: ${filepath}`);
}
