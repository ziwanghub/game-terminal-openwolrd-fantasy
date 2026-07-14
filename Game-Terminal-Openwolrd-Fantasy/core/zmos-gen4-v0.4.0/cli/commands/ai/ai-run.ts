import { readFile } from "node:fs/promises";
import { runGovernedAiTask, type AiTaskPayload, type AiRunMode } from "./_governed-run.js";

const KNOWN_PAYLOAD_KEYS = new Set(["task", "goal", "input", "constraints"]);

const DEFAULT_PAYLOAD: AiTaskPayload = {
  task: "code-task",
  goal: "Perform a governed AI code task",
  input: "Describe the target code task in the payload file passed via --payload <path>.",
  constraints: ["be concise", "no markdown", "output plain text only"],
};

function assertRuntimePayloadShape(raw: unknown, payloadPath: string): AiTaskPayload {
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    throw new Error(`PAYLOAD_FAIL: ${payloadPath} must be a JSON object`);
  }

  const obj = raw as Record<string, unknown>;

  const unknownKeys = Object.keys(obj).filter((k) => !KNOWN_PAYLOAD_KEYS.has(k));
  if (unknownKeys.length > 0) {
    throw new Error(
      `PAYLOAD_FAIL: unknown fields in payload: ${unknownKeys.join(", ")}. Allowed: ${[...KNOWN_PAYLOAD_KEYS].join(", ")}`,
    );
  }

  if (typeof obj.task !== "string" || obj.task.trim() === "")
    throw new Error("PAYLOAD_FAIL: task must be a non-empty string");
  if (typeof obj.goal !== "string" || obj.goal.trim() === "")
    throw new Error("PAYLOAD_FAIL: goal must be a non-empty string");
  if (typeof obj.input !== "string" || obj.input.trim() === "")
    throw new Error("PAYLOAD_FAIL: input must be a non-empty string");
  if (
    !Array.isArray(obj.constraints) ||
    obj.constraints.length === 0 ||
    obj.constraints.some((c) => typeof c !== "string" || c.trim() === "")
  )
    throw new Error("PAYLOAD_FAIL: constraints must be an array of non-empty strings");

  return obj as unknown as AiTaskPayload;
}

// Precedence: --describe > --dry-run > execute (default)
function resolveMode(args: string[]): AiRunMode {
  if (args.includes("--describe")) return "describe";
  if (args.includes("--dry-run")) return "dry-run";
  return "execute";
}

function getFlagValue(args: string[], flag: string): string | undefined {
  const idx = args.indexOf(flag);
  if (idx === -1) return undefined;
  const value = args[idx + 1];
  return value && !value.startsWith("--") ? value : undefined;
}

function getAllFlagValues(args: string[], flag: string): string[] {
  const values: string[] = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === flag && i + 1 < args.length && !args[i + 1].startsWith("--")) {
      values.push(args[i + 1]);
    }
  }
  return values;
}

function buildInlinePayload(args: string[]): AiTaskPayload | null {
  const task = getFlagValue(args, "--task");
  const goal = getFlagValue(args, "--goal");
  const input = getFlagValue(args, "--input");
  const constraints = getAllFlagValues(args, "--constraint");

  if (!task && !goal && !input && constraints.length === 0) return null;

  if (!task) throw new Error("PAYLOAD_FAIL: --task is required for inline payload");
  if (!goal) throw new Error("PAYLOAD_FAIL: --goal is required for inline payload");
  if (!input) throw new Error("PAYLOAD_FAIL: --input is required for inline payload");
  if (constraints.length === 0)
    throw new Error("PAYLOAD_FAIL: at least one --constraint is required for inline payload");

  return { task, goal, input, constraints };
}

export async function runAiRunCommand(args: string[]): Promise<void> {
  const mode = resolveMode(args);
  const payloadFlagIndex = args.indexOf("--payload");
  let payload: AiTaskPayload = DEFAULT_PAYLOAD;
  let payloadPath: string | undefined;

  if (payloadFlagIndex !== -1) {
    // --payload <file> takes precedence over inline flags
    payloadPath = args[payloadFlagIndex + 1];
    if (!payloadPath) throw new Error("Usage: zcl ai run --payload <path>");
    const raw = await readFile(payloadPath, "utf8");
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      throw new Error(`PAYLOAD_FAIL: ${payloadPath} is not valid JSON`);
    }
    payload = assertRuntimePayloadShape(parsed, payloadPath);
  } else {
    // Try inline flags: --task --goal --input --constraint (repeatable)
    const inlinePayload = buildInlinePayload(args);
    if (inlinePayload) {
      payload = inlinePayload;
    }
  }

  await runGovernedAiTask("zcl ai run", payload, payloadPath, mode);
}
