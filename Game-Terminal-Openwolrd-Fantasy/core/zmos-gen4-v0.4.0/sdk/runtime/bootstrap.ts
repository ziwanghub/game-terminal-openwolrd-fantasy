import { runZclCommand } from "./shared/run-zcl-command.js";
import type { SdkCommandResult } from "../types/sdk-command-result.js";

export interface BootstrapOptions {
  workspaceDir: string;
  timeoutMs?: number;
  mode?: "sync" | "start";
}

/**
 * Bootstraps the Z-MOS workspace by executing the truth-first initialization sequence.
 * 
 * @param options configuration for bootstrapping the workspace
 * @returns the command result containing output and exit code
 */
export function bootstrapWorkspace(options: BootstrapOptions): SdkCommandResult {
  const mode = options.mode || "sync";
  return runZclCommand([mode], options.workspaceDir, options.timeoutMs);
}
