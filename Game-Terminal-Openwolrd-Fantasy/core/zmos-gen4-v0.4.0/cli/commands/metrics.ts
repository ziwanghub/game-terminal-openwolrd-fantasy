import { promises as fs, existsSync } from "node:fs";
import * as path from "node:path";

const METRICS_DIR = path.join(process.cwd(), ".z-mos", "metrics");
const METRICS_FILE = path.join(METRICS_DIR, "token-baseline.jsonl");

type MetricsArgs = {
  task: string;
  type: string;
  size: number;
};

function parseMetricsArgs(argv: string[]): MetricsArgs | null {
  const args: MetricsArgs = {
    task: "",
    type: "",
    size: 0,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    
    if (arg.startsWith("--") && !arg.includes("=") && i + 1 < argv.length && !argv[i + 1]?.startsWith("--")) {
      const key = arg.replace("--", "");
      const val = argv[++i];
      if (val !== undefined) {
        if (key === "task") args.task = val;
        if (key === "type" && ["L1", "L2", "L3"].includes(val)) args.type = val;
        if (key === "size") args.size = parseInt(val, 10);
      }
      continue;
    }
    
    if (arg.startsWith("--") && arg.includes("=")) {
      const [k, v] = arg.split("=");
      const key = k?.replace("--", "");
      if (key && v) {
        if (key === "task") args.task = v;
        if (key === "type" && ["L1", "L2", "L3"].includes(v)) args.type = v;
        if (key === "size") args.size = parseInt(v, 10);
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
      "  zcl metrics record --task <text> --type <L1|L2|L3> --size <number>",
    ].join("\n"),
  );
}

export async function runMetricsRecordCommand(argv: string[]): Promise<void> {
  const parsed = parseMetricsArgs(argv);
  if (!parsed || !parsed.task || !parsed.type || !parsed.size || isNaN(parsed.size)) {
    printUsage();
    process.exitCode = 1;
    return;
  }

  const record = {
    timestamp: new Date().toISOString(),
    task: parsed.task,
    type: parsed.type,
    size: parsed.size,
  };

  if (!existsSync(METRICS_DIR)) {
    await fs.mkdir(METRICS_DIR, { recursive: true });
  }

  const line = `${JSON.stringify(record)}\n`;
  await fs.appendFile(METRICS_FILE, line, { encoding: "utf8" });
  console.log(`Metrics recorded to ${METRICS_FILE}`);
}
