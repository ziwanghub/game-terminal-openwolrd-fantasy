import { spawnSync, SpawnSyncOptions } from "node:child_process";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import type { SdkCommandResult } from "../../types/sdk-command-result.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Resolve Z-MOS root dynamically to handle monorepos and linked dependencies
const ZMOS_CORE_ROOT = process.env.ZMOS_CORE_ROOT || path.resolve(__dirname, "..", "..", "..");

export function runZclCommand(
  args: string[],
  workspaceDir: string,
  timeoutMs: number = 30000,
): SdkCommandResult {
  const zclPath = path.join(ZMOS_CORE_ROOT, "bin", "zcl.js");
  
  const options: SpawnSyncOptions = {
    cwd: workspaceDir,
    env: { ...process.env },
    timeout: timeoutMs,
    encoding: "utf8",
  };

  try {
    const result = spawnSync(process.execPath, [zclPath, ...args], options);

    if (result.error) {
      // Typically an OS-level error (e.g. timeout or EACCES)
      return {
        success: false,
        exitCode: result.status ?? 1,
        output: result.stdout?.toString() || "",
        error: result.error.message,
      };
    }

    return {
      success: result.status === 0,
      exitCode: result.status ?? 1,
      output: result.stdout?.toString() || "",
      error: result.stderr?.toString() || undefined,
    };
  } catch (err) {
    return {
      success: false,
      exitCode: 1,
      output: "",
      error: err instanceof Error ? err.message : String(err),
    };
  }
}
