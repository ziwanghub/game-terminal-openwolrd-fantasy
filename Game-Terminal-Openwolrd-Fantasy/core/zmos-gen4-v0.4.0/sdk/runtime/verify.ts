import { runZclCommand } from "./shared/run-zcl-command.js";
import type { SdkCommandResult } from "../types/sdk-command-result.js";

export interface VerifyOptions {
  workspaceDir: string;
  timeoutMs?: number;
  strict?: boolean;
}

/**
 * Verifies the Z-MOS workspace by executing preflight or strict readiness checks.
 * 
 * @param options configuration for verification
 * @returns the command result containing output and exit code
 */
export function verifyWorkspace(options: VerifyOptions): SdkCommandResult {
  if (options.strict) {
    // If strict mode is requested, run the full verification matrix
    // Usually this is done via npm script, but we can expose the verifier via bin
    return runZclCommand(["preflight"], options.workspaceDir, options.timeoutMs);
  }
  return runZclCommand(["preflight"], options.workspaceDir, options.timeoutMs);
}

/**
 * Checks the operational status and verdicts.
 */
export function statusWorkspace(options: Omit<VerifyOptions, "strict">): SdkCommandResult {
  return runZclCommand(["status"], options.workspaceDir, options.timeoutMs);
}
