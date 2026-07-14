import { spawnSync } from "node:child_process";
import * as path from "node:path";

export type MacroStep = {
  label: string;
  command: string[];
};

export async function runMacroSequence(name: string, steps: MacroStep[]): Promise<void> {
  console.log(`\n[Z-MOS MACRO] Starting: ${name}\n`);
  let totalTime = 0;

  const zclPath = path.join(process.env.ZMOS_CORE_ROOT || process.cwd(), "bin", "zcl.js");

  for (let i = 0; i < steps.length; i++) {
    const step = steps[i];
    console.log(`[STEP ${i + 1}/${steps.length}] Running: zcl ${step.command.join(" ")}`);
    const start = Date.now();

    const result = spawnSync(process.execPath, [zclPath, ...step.command], {
      stdio: "inherit",
      env: process.env,
    });

    const elapsed = Date.now() - start;
    totalTime += elapsed;

    if (result.status !== 0) {
      console.log(`\n[STEP ${i + 1}/${steps.length}] ❌ FAILED in ${elapsed}ms`);
      console.log(`[Z-MOS MACRO] ${name} ABORTED.\n`);
      process.exit(1);
    } else {
      console.log(`\n[STEP ${i + 1}/${steps.length}] ✅ PASS (${elapsed}ms)\n`);
    }
  }

  console.log(`[Z-MOS MACRO] ${name} COMPLETED SUCCESSFULLY in ${totalTime}ms.\n`);
}
