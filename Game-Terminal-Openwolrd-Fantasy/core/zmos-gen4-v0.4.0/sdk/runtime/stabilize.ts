import { runZclCommand } from "./shared/run-zcl-command.js";
import type { SdkCommandResult } from "../types/sdk-command-result.js";

export interface StabilizeOptions {
  workspaceDir: string;
  timeoutMs?: number;
}

/**
 * Stabilizes the Z-MOS workspace runtime before critical execution.
 * 
 * @param options configuration for stabilizing the workspace
 * @returns the command result containing output and exit code
 */
export function stabilizeWorkspace(options: StabilizeOptions): SdkCommandResult {
  return runZclCommand(["stabilize"], options.workspaceDir, options.timeoutMs);
}

/**
 * Recovers the workspace from interrupted or stale states.
 */
export function recoverWorkspace(options: StabilizeOptions): SdkCommandResult {
  return runZclCommand(["recover"], options.workspaceDir, options.timeoutMs);
}
