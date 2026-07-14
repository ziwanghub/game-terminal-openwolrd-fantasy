import { promises as fs } from "node:fs";
import * as path from "node:path";
import { exec } from "node:child_process";
import { promisify } from "node:util";

const execAsync = promisify(exec);

export interface RunProfileConfig {
  gate_id: string;
  env: Record<string, string>;
  command: string;
  expected_assertions: string[];
  next_action: string;
  workdir?: string;
  timeout_ms?: number;
  stop_conditions?: string[];
}

export async function loadRunProfile(gateId: string): Promise<RunProfileConfig> {
  const profilePath = path.join(process.cwd(), `.z-mos/run-profiles/${gateId}.json`);
  try {
    const data = await fs.readFile(profilePath, "utf8");
    return JSON.parse(data) as RunProfileConfig;
  } catch (error) {
    throw new Error(`Failed to load run profile for gate '${gateId}': ${error instanceof Error ? error.message : error}`);
  }
}

export async function executeRunProfile(profile: RunProfileConfig): Promise<{ passed: boolean; output: string }> {
  const env = { ...process.env, ...profile.env };
  const workdir = profile.workdir || ".";
  const timeoutMs = profile.timeout_ms || 30000;
  
  const targetDir = path.resolve(process.cwd(), workdir);

  try {
    const stat = await fs.stat(targetDir);
    if (!stat.isDirectory()) {
      return { passed: false, output: `Run profile workdir does not exist: ${workdir}` };
    }
  } catch {
    return { passed: false, output: `Run profile workdir does not exist: ${workdir}` };
  }

  try {
    const { stdout, stderr } = await execAsync(profile.command, { 
      env, 
      cwd: targetDir, 
      timeout: timeoutMs,
      killSignal: 'SIGTERM'
    });
    const output = `${stdout}\n${stderr}`;
    
    let passed = true;
    for (const assertion of profile.expected_assertions) {
      if (!output.includes(assertion)) {
        passed = false;
        break;
      }
    }
    return { passed, output };
  } catch (error: any) {
    if (error.killed && error.signal === 'SIGTERM') {
      return { passed: false, output: `Run profile command timed out after ${timeoutMs} ms` };
    }
    return { passed: false, output: error instanceof Error ? error.message : String(error) };
  }
}
