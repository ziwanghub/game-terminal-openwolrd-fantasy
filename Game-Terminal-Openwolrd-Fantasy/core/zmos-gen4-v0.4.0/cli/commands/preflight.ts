import { runPreflightChecks } from "../../core/preflight.js";
import { renderCommandExecutionResult } from "../../core/execution-contract.js";

function toDisplayStatus(status: "healthy" | "warning" | "blocking"): string {
  if (status === "healthy") {
    return "HEALTHY";
  }
  if (status === "warning") {
    return "WARNING";
  }
  return "BLOCKING";
}

export async function runPreflightCommand(argv: string[] = []): Promise<void> {
  const allowMissingCanonical =
    process.env.ZMOS_PREFLIGHT_ALLOW_CANONICAL_MISSING === "1";
  const executionMode =
    process.env.ZMOS_PREFLIGHT_EXEC_MODE === "dev-ts" ? "dev-ts" : "ops-dist";
  let intendedCommand = "";
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--check-command" && argv[i + 1]) {
      intendedCommand = argv[++i] || "";
    } else if (arg?.startsWith("--check-command=")) {
      intendedCommand = arg.split("=")[1] || "";
    }
  }

  const report = await runPreflightChecks({
    allowMissingCanonical,
    executionMode,
    intendedCommand,
  });
  const lines = [
    "Z-MOS Preflight Report",
    "",
    `Status: ${toDisplayStatus(report.status)}`,
    "",
    "Checks",
  ];

  for (const check of report.checks) {
    lines.push(
      `- ${check.name} [${toDisplayStatus(check.status)}]`,
      `  code: ${check.code}`,
      `  message: ${check.message}`,
      `  likely cause: ${check.likelyCause}`,
      `  action: ${check.action}`,
    );
  }

  const firstBlocking = report.checks.find((check) => check.status === "blocking");
  const firstWarning = report.checks.find((check) => check.status === "warning");
  const resultBlock =
    report.status === "blocking"
      ? renderCommandExecutionResult({
          command: "preflight",
          status: "blocked",
          resultClass: "blocked-preflight",
          reason: firstBlocking?.message || "Preflight blocking condition detected.",
          traceExpectation: "optional-by-design",
          traceResult: "not-emitted-by-design",
          nextAction:
            firstBlocking?.action ||
            "Resolve preflight blockers before running downstream commands.",
        })
      : report.status === "warning"
        ? renderCommandExecutionResult({
            command: "preflight",
            status: "warning",
            resultClass: "warning-execution",
            warningReason: firstWarning?.message || "Preflight warning detected.",
            traceExpectation: "optional-by-design",
            traceResult: "not-emitted-by-design",
            nextAction:
              firstWarning?.action || "Review warnings before proceeding.",
          })
        : renderCommandExecutionResult({
            command: "preflight",
            status: "success",
            resultClass: "success",
            traceExpectation: "optional-by-design",
            traceResult: "not-emitted-by-design",
          });
  lines.push("", resultBlock);

  console.log(lines.join("\n"));

  if (report.status === "blocking") {
    process.exitCode = 1;
  }
}
