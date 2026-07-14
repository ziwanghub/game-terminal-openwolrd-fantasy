import { runAiTestCommand } from "./commands/ai/ai-test.js";
import { runAiRunCommand } from "./commands/ai/ai-run.js";
import { runAiStatusCommand } from "./commands/ai/ai-status.js";
import { runContextBuildCommand } from "./commands/ai/context-build.js";
import { runPreflightCommand } from "./commands/preflight.js";
import { runScopeValidateCommand } from "./commands/scope.js";
import { runScopeGuardCommand } from "./commands/scope-guard.js";
import { runSchemaValidateCommand } from "./commands/schema-validate.js";
import { runQualityCheckCommand } from "./commands/quality-check.js";
import { runVerifyWorktreeCommand } from "./commands/verify-worktree.js";
import { runHooksInstallCommand } from "./commands/hooks.js";
import { runDoctorCommand } from "./commands/doctor.js";
import {
  isContextSubcommand,
  runContextCommand,
} from "./commands/context.js";
import { isBudgetSubcommand, runBudgetCommand } from "./commands/budget.js";
import { isLaneSubcommand, runLaneCommand } from "./commands/lane.js";
import {
  runCoreCleanCommand,
  runCoreDoctorCommand,
  runCoreRestoreCommand,
} from "./commands/core.js";
import { runStartCommand } from "./commands/start.js";
import {
  runDocCheckCommand,
  runDocDoctorCommand,
  runDocIndexCommand,
} from "./commands/document.js";
import { runInitCommand } from "./commands/init.js";
import { runHelpCommand } from "./commands/help.js";
import { runLoadDataCommand } from "./commands/load-data.js";
import { runMigrateCommand } from "./commands/migrate.js";
import { runStatusCommand } from "./commands/status.js";
import { runNextCommand } from "./commands/next.js";
import { runReportCommand } from "./commands/report.js";
import { runStateUpdateCommand } from "./commands/state.js";
import { runMemoryInitCommand } from "./commands/memory.js";
import { runTraceVerifyCommand } from "./commands/trace.js";
import { runTraceQueryCommand } from "./commands/trace-query.js";
import { runBehaviorRecordCommand } from "./commands/behavior.js";
import { runMetricsRecordCommand } from "./commands/metrics.js";
import {
  runTlsCreateCommand,
  runTlsInstallCommand,
  runTlsListCommand,
  runTlsShowCommand,
  runTlsSyncCommand,
  runTlsUninstallCommand,
  runTlsUpdateCommand,
  runTlsValidateCommand,
} from "./commands/tls.js";
import {
  runWorkflowCommand,
  runWorkflowCoverageCheckCommand,
  runWorkflowListCommand,
} from "./commands/workflow.js";
import { runRuntimeLockStatusCommand, runRuntimeClearStaleLocksCommand } from "./commands/runtime.js";
import { runRunGateCommand } from "./commands/run-gate.js";
import { runTraceSummaryCommand } from "./commands/trace-summary.js";
import { runSyncCommand } from "./commands/sync.js";
import { runRecoverCommand } from "./commands/recover.js";
import { runStabilizeCommand } from "./commands/stabilize.js";
import { runTruthBuildCommand } from "./commands/truth.js";
import { runIntentInitCommand } from "./commands/intent.js";
import type { WorkflowName } from "../contracts/workflow.js";
import { assertSupportedWorkflowName } from "../core/workflow.js";
import { FULL_VERSION } from "../sdk/version.js";

type AiSubcommand = "test";

type CommandHandler = () => Promise<void>;

const AI_HANDLERS: Record<AiSubcommand, CommandHandler> = {
  test: runAiTestCommand,
};

function printUsage(): void {
  console.error(
    [
      "Usage:",
      "  zcl start",
      "  zcl preflight [--check-command=<cmd>]",
      "  zcl init",
      "  zcl help [<command>]",
      "  zcl load-data --type new-room-prompt [--project <path>] [--mode full|compact]",
      "  zcl load-data --type zmos-usage-prompt [--project <path>] [--mode full|compact]",
      "  zcl load-data --type team-onboarding [--project <path>]",
      "  zcl migrate --from v0.2.x --to evo1.0 [--project <path>] [--dry-run] [--force] [--apply-rewrite-safe]",
      "  zcl status",
      "  zcl next",
      "  zcl status --project <path>",
      "  zcl doctor",
      "  zcl doctor --project <path>",
      "  zcl report --status <PASS|FAIL> --task <task> --what-done <detail>",
      "  zcl state update --phase <phase> --next-action <action> --blocker <none>",
      "  zcl state init [--force]",
      "  zcl memory init [--force]",
      "  zcl context init --task-id <id> [--force]",
      "  zcl context show --task-id <id>",
      "  zcl context update --task-id <id> --patch <json>",
      "  zcl context invalidate --task-id <id> --reason <taxonomy>",
      "  zcl lane claim --task-id <id> --lane <lane> --actor <id>",
      "  zcl lane release --task-id <id> --actor <id>",
      "  zcl lane lock-path --task-id <id> --lane <lane> --actor <id> --path <glob>",
      "  zcl lane lock-artifact --task-id <id> --lane <lane> --actor <id> --artifact <id>",
      "  zcl lane handoff --task-id <id> --to-lane <lane> --actor <id> --summary <text>",
      "  zcl lane ack --task-id <id> --actor <id>",
      "  zcl budget evaluate --task-id <id> --risk <low|medium|high> --mode <full|compact|unknown> --estimated-input <n>",
      "  zcl budget profile --task-id <id> --profile <compact|balanced|full>",
      "  zcl budget status --task-id <id>",
      "  zcl core doctor",
      "  zcl core clean [--dry-run]",
      "  zcl core restore [--dry-run]",
      "  zcl doc:check",
      "  zcl doc:index [--type=<type>] [--phase=<phase>] [--status=<status>]",
      "  zcl doc:doctor",
      "  zcl workflow list",
      "  zcl workflow coverage-check",
      "  zcl workflow runtime-check",
      "  zcl workflow advisory-check",
      "  zcl runtime lock-status",
      "  zcl runtime clear-stale-locks",
      "  zcl run-gate <gate_id>",
      "  zcl trace verify [--json]",
      "  zcl trace query [--status <status>] [--command <cmd>] [--result-class <class>] [--last <n>] [--since <date>] [--json]",
      "  zcl trace summary",
      "  zcl tls create --template <path> --config <file> --output <dir>",
      "  zcl tls install --source <path> --type <type> --name <name> [--dry-run] [--force]",
      "  zcl tls update --name <name> --source <path> [--dry-run] [--force]",
      "  zcl tls list [--type=<type>] [--status=<status>] [--json]",
      "  zcl tls show <name>",
      "  zcl tls validate <name>",
      "  zcl tls sync",
      "  zcl tls uninstall <name> [--dry-run] [--force]",
      "  zcl schema validate",
      "  zcl truth build",
      "  zcl intent init [--force]",
      "  zcl sync",
      "  zcl recover",
      "  zcl stabilize",
      "  zcl behavior record --context <text> --decision <text> --reason <text> --risk <low|medium|high> --trace-ref <sequence-N> [--auto-fill] [--blef ...]",
      "  zcl metrics record --task <text> --type <L1|L2|L3> --size <number>",
      "  zcl ai test",
      "  zcl ai run --payload <file.json> [--dry-run] [--describe]",
      "  zcl ai run --task <task> --goal <goal> --input <input> --constraint <c> [--constraint <c>...] [--dry-run] [--describe]",
      "  zcl ai context build",
      "  zcl ai status",
    ].join("\n"),
  );
}

function resolveHandler(argv: string[]): CommandHandler | null {
  const [group, subcommand, ...rest] = argv;

  if (group === "doc:check") {
    return runDocCheckCommand;
  }

  if (group === "doc:index") {
    const args = subcommand ? [subcommand, ...rest] : rest;
    return () => runDocIndexCommand(args);
  }

  if (group === "doc:doctor") {
    return runDocDoctorCommand;
  }

  if (group === "status" && !subcommand) {
    return runStatusCommand;
  }

  if (group === "next" && !subcommand) {
    return runNextCommand;
  }

  if (group === "report") {
    return () => runReportCommand(argv.slice(1));
  }

  if (group === "state" && subcommand === "update") {
    return () => runStateUpdateCommand(rest);
  }

  if (group === "state" && subcommand === "init") {
    return () => runMemoryInitCommand(["state", ...rest]);
  }

  if (group === "validate" && subcommand === "scope") {
    return () => runScopeValidateCommand();
  }

  if (group === "scope" && subcommand === "guard") {
    return () => runScopeGuardCommand();
  }

  if (group === "schema" && subcommand === "validate") {
    return () => runSchemaValidateCommand();
  }

  if (group === "truth" && subcommand === "build") {
    return () => runTruthBuildCommand();
  }

  if (group === "intent" && subcommand === "init") {
    return () => runIntentInitCommand(rest);
  }

  if (group === "quality" && subcommand === "check") {
    return () => runQualityCheckCommand();
  }

  if (group === "verify" && subcommand === "worktree") {
    return () => runVerifyWorktreeCommand();
  }

  if (group === "hooks" && subcommand === "install") {
    return () => runHooksInstallCommand();
  }

  if (group === "memory" && subcommand === "init") {
    return () => runMemoryInitCommand(rest);
  }

  if (group === "start" && !subcommand) {
    return runStartCommand;
  }

  if (group === "preflight") {
    const args = subcommand ? [subcommand, ...rest] : rest;
    return () => runPreflightCommand(args);
  }

  if (group === "init" && !subcommand) {
    return runInitCommand;
  }

  if (group === "help") {
    const args = subcommand ? [subcommand, ...rest] : rest;
    return () => runHelpCommand(args);
  }

  if (group === "load-data") {
    const args = subcommand ? [subcommand, ...rest] : rest;
    return () => runLoadDataCommand(args);
  }

  if (group === "migrate") {
    const args = subcommand ? [subcommand, ...rest] : rest;
    return () => runMigrateCommand(args);
  }

  if (group === "doctor" && !subcommand) {
    return runDoctorCommand;
  }

  if (group === "context" && subcommand && isContextSubcommand(subcommand)) {
    return () => runContextCommand(subcommand, rest);
  }

  if (group === "lane" && subcommand && isLaneSubcommand(subcommand)) {
    return () => runLaneCommand(subcommand, rest);
  }

  if (group === "budget" && subcommand && isBudgetSubcommand(subcommand)) {
    return () => runBudgetCommand(subcommand, rest);
  }

  if (group === "core" && subcommand === "doctor") {
    return runCoreDoctorCommand;
  }

  if (group === "core" && subcommand === "clean") {
    return () => runCoreCleanCommand(rest);
  }

  if (group === "core" && subcommand === "restore") {
    return () => runCoreRestoreCommand(rest);
  }

  if (group === "doc" && subcommand === "check") {
    return runDocCheckCommand;
  }

  if (group === "doc" && subcommand === "index") {
    return () => runDocIndexCommand(rest);
  }

  if (group === "doc" && subcommand === "doctor") {
    return runDocDoctorCommand;
  }

  if (group === "workflow" && subcommand) {
    if (subcommand === "list") {
      return runWorkflowListCommand;
    }
    if (subcommand === "coverage-check") {
      return runWorkflowCoverageCheckCommand;
    }

    const workflowName = assertSupportedWorkflowName(subcommand);
    if (workflowName) {
      return () => runWorkflowCommand(workflowName as WorkflowName);
    }
  }

  if (group === "runtime" && subcommand === "lock-status") {
    return runRuntimeLockStatusCommand;
  }

  if (group === "runtime" && subcommand === "clear-stale-locks") {
    return runRuntimeClearStaleLocksCommand;
  }

  if (group === "trace" && subcommand === "verify") {
    return () => runTraceVerifyCommand(rest.includes("--json"));
  }

  if (group === "trace" && subcommand === "query") {
    return () => runTraceQueryCommand(rest);
  }

  if (group === "trace" && subcommand === "summary") {
    return runTraceSummaryCommand;
  }

  if (group === "sync") {
    return runSyncCommand;
  }

  if (group === "recover") {
    return runRecoverCommand;
  }

  if (group === "stabilize") {
    return runStabilizeCommand;
  }

  if (group === "run-gate") {
    const args = subcommand ? [subcommand, ...rest] : rest;
    return () => runRunGateCommand(args);
  }

  if (group === "behavior" && subcommand === "record") {
    return () => runBehaviorRecordCommand(rest);
  }

  if (group === "metrics" && subcommand === "record") {
    return () => runMetricsRecordCommand(rest);
  }

  if (group === "tls" && subcommand === "create") {
    return () => runTlsCreateCommand(rest);
  }

  if (group === "tls" && subcommand === "install") {
    return () => runTlsInstallCommand(rest);
  }

  if (group === "tls" && subcommand === "update") {
    return () => runTlsUpdateCommand(rest);
  }

  if (group === "tls" && subcommand === "list") {
    return () => runTlsListCommand(rest);
  }

  if (group === "tls" && subcommand === "show") {
    return () => {
      const [name] = rest;
      if (!name) {
        throw new Error("Usage: zcl tls show <name>");
      }
      return runTlsShowCommand(name);
    };
  }

  if (group === "tls" && subcommand === "validate") {
    return () => {
      const [name] = rest;
      if (!name) {
        throw new Error("Usage: zcl tls validate <name>");
      }
      return runTlsValidateCommand(name);
    };
  }

  if (group === "tls" && subcommand === "sync") {
    return () => runTlsSyncCommand(rest);
  }

  if (group === "tls" && subcommand === "uninstall") {
    return () => runTlsUninstallCommand(rest);
  }

  if (group !== "ai" || !subcommand) {
    return null;
  }

  if (subcommand === "run") {
    return () => runAiRunCommand(rest);
  }

  if (subcommand === "status") {
    return runAiStatusCommand;
  }

  if (subcommand === "context" && rest[0] === "build") {
    return () => runContextBuildCommand(rest.slice(1));
  }

  if (subcommand in AI_HANDLERS) {
    return AI_HANDLERS[subcommand as AiSubcommand];
  }

  return null;
}

async function main(): Promise<void> {
  const argv = process.argv.slice(2);
  if (
    argv.length === 1 &&
    (argv[0] === "--version" || argv[0] === "-v" || argv[0] === "version")
  ) {
    console.log(FULL_VERSION);
    return;
  }

  const handler = resolveHandler(argv);

  if (!handler) {
    printUsage();
    process.exitCode = 1;
    return;
  }

  try {
    await handler();
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown CLI execution error";
    console.error(`zcl error: ${message}`);
    process.exitCode = 1;
  }
}

await main();
