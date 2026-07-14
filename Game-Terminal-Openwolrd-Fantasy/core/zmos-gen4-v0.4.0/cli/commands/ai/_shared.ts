import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import * as path from "node:path";

const ROOT_DIR = process.cwd();
const CONTEXT_DIR = path.join(ROOT_DIR, "ai", "ollama", "context");
const REPORTS_DIR = path.join(ROOT_DIR, "ai", "ollama", "reports");

const CONTEXT_FILES = [
  "project-map.md",
  "workspace-summary.md",
  "zmos-framework-goal.md",
] as const;

const DEFAULT_MODEL = process.env.OLLAMA_MODEL || "llama3.1:8b";
const DEFAULT_TIMEOUT_MS = 60_000;
const EXECUTION_TIMEOUT_MS = parseTimeoutMs(process.env.OLLAMA_TIMEOUT_MS);
const RUNTIME_GOVERNED_RULES = [
  "use evidence-first reasoning",
  "use only the provided governed context",
  "keep the response advisory only",
  'if context is insufficient, respond exactly: "not enough evidence"',
];

export type ContextEntry = {
  fileName: string;
  filePath: string;
  content: string;
};

export type GovernedContext = {
  contextEntries: ContextEntry[];
};

export type AdvisoryCommandConfig = {
  commandName: string;
  purpose: string;
  tasks: string[];
  outputSections: string[];
};

export type PromptBuildInput = AdvisoryCommandConfig & GovernedContext;

export type OllamaResponse = {
  stdout: string;
  stderr: string;
  model: string;
};

type ExecFileErrorShape = Error & {
  code?: number | string;
  signal?: NodeJS.Signals | string;
  killed?: boolean;
  stdout?: string;
  stderr?: string;
};

export type AdvisoryReportInput = {
  commandName: string;
  purpose: string;
  prompt: string;
  response: OllamaResponse;
  contextEntries: ContextEntry[];
};

export type AdvisoryCommandResult = {
  reportPath: string;
  model: string;
  stdout: string;
};

function formatTaskLines(tasks: string[]): string {
  return tasks.map((task) => `- ${task}`).join("\n");
}

function formatOutputSections(sections: string[]): string {
  return sections.map((section) => `- ${section}`).join("\n");
}

function buildReportName(commandName: string): string {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `${commandName}-${stamp}.md`;
}

function parseTimeoutMs(rawValue: string | undefined): number {
  const parsed = Number.parseInt(rawValue || "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_TIMEOUT_MS;
}

function findContextEntry(
  contextEntries: ContextEntry[],
  fileName: string,
): ContextEntry | undefined {
  return contextEntries.find((entry) => entry.fileName === fileName);
}

function buildRuntimeContextDigest(contextEntries: ContextEntry[]): string {
  const projectMap = findContextEntry(contextEntries, "project-map.md");
  const workspaceSummary = findContextEntry(
    contextEntries,
    "workspace-summary.md",
  );
  const frameworkGoal = findContextEntry(
    contextEntries,
    "zmos-framework-goal.md",
  );

  const digestLines = [
    "Repository identity:",
    "- repository name: zmos-core",
    "- framework: Z-MOS",
    "",
    "Top-level structure summary:",
    "- ai/: governed Ollama workspace",
    "- bin/: intended executable entrypoints",
    "- cli/: command and gateway layer",
    "- contracts/: intended schemas and contracts",
    "- core/: intended runtime and bootstrap logic",
    "- docs/: architecture and planning documentation",
    "- governance/: intended governance logic",
    "- scripts/: intended support scripts",
    "- tests/: intended automated tests",
    "- trace/: intended trace and evidence layer",
    "",
    "Implementation status summary:",
    "- repository scaffold exists",
    "- governed Ollama workspace exists under ai/ollama/",
    "- AI command layer exists in TypeScript source",
    "- most core runtime areas remain scaffold-only",
    "- no full AI runtime integration is complete yet",
    "",
    "Framework goal summary:",
    "- Z-MOS is a governance-first AI work environment",
    "- AI work should remain bounded, evidence-first, and advisory",
  ];

  if (!projectMap || !workspaceSummary || !frameworkGoal) {
    digestLines.push(
      "",
      'If any required summary detail is uncertain, respond exactly: "not enough evidence"',
    );
  }

  return digestLines.join("\n");
}

export async function loadGovernedContext(): Promise<GovernedContext> {
  const contextEntries = await Promise.all(
    CONTEXT_FILES.map(async (fileName): Promise<ContextEntry> => {
      const filePath = path.join(CONTEXT_DIR, fileName);
      const content = await fs.readFile(filePath, "utf8");
      return { fileName, filePath, content };
    }),
  );

  return { contextEntries };
}

export function buildPrompt({
  commandName,
  purpose,
  tasks,
  outputSections,
  contextEntries,
}: PromptBuildInput): string {
  const contextBlock =
    commandName === "analyze"
      ? buildRuntimeContextDigest(contextEntries)
      : contextEntries
          .map(
            ({ fileName, content }) =>
              `===== ai/ollama/context/${fileName} =====\n${content.trim()}`,
          )
          .join("\n\n");

  return [
    "You are Ollama operating under Z-MOS governance.",
    "",
    `Command: ${commandName}`,
    `Purpose: ${purpose}`,
    "",
    "Read only the curated context files included below.",
    "Do not use any other repository files, hidden assumptions, prior memory, or external knowledge.",
    "",
    "Tasks:",
    formatTaskLines(tasks),
    "",
    "Rules:",
    formatTaskLines(RUNTIME_GOVERNED_RULES),
    "- do not suggest direct file modification as if already performed",
    "",
    "Output format:",
    formatOutputSections(outputSections),
    "",
    commandName === "analyze"
      ? "Governed runtime summary:"
      : "Governed context:",
    contextBlock,
    "",
  ].join("\n");
}

export async function runOllamaPrompt(prompt: string): Promise<OllamaResponse> {
  return await new Promise<OllamaResponse>((resolve) => {
    const child = spawn("ollama", ["run", DEFAULT_MODEL], {
      cwd: ROOT_DIR,
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let settled = false;

    const timer = setTimeout(() => {
      if (!settled) {
        child.kill("SIGTERM");
      }
    }, EXECUTION_TIMEOUT_MS);

    const finalize = (response: OllamaResponse): void => {
      if (settled) {
        return;
      }

      settled = true;
      clearTimeout(timer);
      resolve(response);
    };

    child.stdout.on("data", (chunk: Buffer | string) => {
      stdout += chunk.toString();
    });

    child.stderr.on("data", (chunk: Buffer | string) => {
      stderr += chunk.toString();
    });

    child.on("error", (error: Error) => {
      const execError = error as ExecFileErrorShape;
      finalize({
        stdout: stdout.trim(),
        stderr: [
          `ollama execution failed for model ${DEFAULT_MODEL} | ${execError.message}`,
          stderr.trim(),
        ]
          .filter(Boolean)
          .join("\n"),
        model: DEFAULT_MODEL,
      });
    });

    child.on("close", (code, signal) => {
      const normalizedStdout = stdout.trim();
      const normalizedStderr = stderr.trim();

      if (code === 0) {
        finalize({
          stdout: normalizedStdout,
          stderr: normalizedStderr,
          model: DEFAULT_MODEL,
        });
        return;
      }

      const timeoutSummary =
        signal === "SIGTERM"
          ? `timeout=${EXECUTION_TIMEOUT_MS}ms`
          : "";
      const exitSummary = [
        `ollama execution failed for model ${DEFAULT_MODEL}`,
        code !== null ? `code=${String(code)}` : "",
        signal ? `signal=${signal}` : "",
        timeoutSummary,
      ]
        .filter(Boolean)
        .join(" | ");

      finalize({
        stdout: normalizedStdout,
        stderr: [exitSummary, normalizedStderr].filter(Boolean).join("\n"),
        model: DEFAULT_MODEL,
      });
    });

    child.stdin.write(prompt);
    child.stdin.end();
  });
}

export async function writeAdvisoryReport({
  commandName,
  purpose,
  prompt,
  response,
  contextEntries,
}: AdvisoryReportInput): Promise<string> {
  const reportPath = path.join(REPORTS_DIR, buildReportName(commandName));
  const contextList = contextEntries
    .map(({ fileName }) => `- ai/ollama/context/${fileName}`)
    .join("\n");

  const report = [
    `# ${commandName} Advisory Report`,
    "",
    "## Metadata",
    "",
    `- Command: \`${commandName}\``,
    `- Model: \`${response.model}\``,
    `- Purpose: ${purpose}`,
    `- Created At: ${new Date().toISOString()}`,
    "",
    "## Governed Context",
    "",
    contextList,
    "",
    "## Prompt",
    "",
    "```text",
    prompt.trim(),
    "```",
    "",
    "## Ollama Response",
    "",
    response.stdout || "not enough evidence",
    "",
    "## stderr",
    "",
    response.stderr || "(empty)",
    "",
  ].join("\n");

  await fs.writeFile(reportPath, report, "utf8");
  return reportPath;
}

export async function executeAdvisoryCommand(
  config: AdvisoryCommandConfig,
): Promise<AdvisoryCommandResult> {
  const { contextEntries } = await loadGovernedContext();
  const prompt = buildPrompt({
    ...config,
    contextEntries,
  });
  const response = await runOllamaPrompt(prompt);
  const reportPath = await writeAdvisoryReport({
    commandName: config.commandName,
    purpose: config.purpose,
    prompt,
    response,
    contextEntries,
  });

  return {
    reportPath,
    model: response.model,
    stdout: response.stdout,
  };
}
