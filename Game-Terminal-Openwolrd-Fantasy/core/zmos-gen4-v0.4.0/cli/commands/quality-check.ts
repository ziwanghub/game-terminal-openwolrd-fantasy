import { promises as fs } from "node:fs";
import * as path from "node:path";
import { validateScopeGuard } from "../../core/scope-guard.js";

export async function runQualityCheckCommand(): Promise<void> {
  let overallStatus: "PASS" | "WARN" | "FAIL" = "PASS";
  const violations: string[] = [];

  // 1. Check Scope Guard
  const scopeResult = await validateScopeGuard();
  if (scopeResult.status !== "PASS") {
    overallStatus = scopeResult.status === "FAIL" ? "FAIL" : "WARN";
    violations.push(`[SCOPE] ${scopeResult.violations.length} scope violations detected.`);
  }

  // 2. Check Handoff Quality Block
  try {
    const handoffPath = path.join(process.cwd(), ".z-mos/intent.card.json");
    const rawHandoff = await fs.readFile(handoffPath, "utf8");
    const handoff = JSON.parse(rawHandoff);

    if (!handoff.quality) {
      overallStatus = "WARN";
      violations.push("[HANDOFF] Missing top-level 'quality' block.");
    } else {
      const q = handoff.quality;
      if (!Array.isArray(q.allowed_scope)) violations.push("[HANDOFF] quality.allowed_scope missing or invalid.");
      if (!Array.isArray(q.do_not_touch)) violations.push("[HANDOFF] quality.do_not_touch missing or invalid.");
      if (!Array.isArray(q.known_risks)) violations.push("[HANDOFF] quality.known_risks missing or invalid.");
      if (!Array.isArray(q.required_tests)) violations.push("[HANDOFF] quality.required_tests missing or invalid.");
      if (!Array.isArray(q.stop_conditions)) violations.push("[HANDOFF] quality.stop_conditions missing or invalid.");
      
      if (violations.some(v => v.startsWith("[HANDOFF]"))) {
        overallStatus = "WARN";
      }
    }
  } catch {
    overallStatus = "WARN";
    violations.push("[HANDOFF] Could not read or parse latest.json");
  }

  // 3. Check Run Profiles
  try {
    const profilesDir = path.join(process.cwd(), ".z-mos/run-profiles");
    const files = await fs.readdir(profilesDir);
    const jsonFiles = files.filter(f => f.endsWith(".json"));

    for (const file of jsonFiles) {
      const p = path.join(profilesDir, file);
      const raw = await fs.readFile(p, "utf8");
      const profile = JSON.parse(raw);
      
      if (!profile.workdir) violations.push(`[PROFILE] ${file} missing 'workdir'`);
      if (!profile.timeout_ms) violations.push(`[PROFILE] ${file} missing 'timeout_ms'`);
      if (!Array.isArray(profile.stop_conditions)) violations.push(`[PROFILE] ${file} missing 'stop_conditions'`);
    }

    if (violations.some(v => v.startsWith("[PROFILE]"))) {
      overallStatus = "WARN";
    }
  } catch {
    overallStatus = "WARN";
    violations.push("[PROFILE] Could not read run-profiles directory.");
  }

  // Output
  console.log(`[${overallStatus}] Quality Check`);
  if (violations.length > 0) {
    console.log("Violations Summary:");
    violations.forEach(v => console.log(`- ${v}`));
  } else {
    console.log("All quality checks passed.");
  }

  if (violations.length > 0) {
    console.log("\nRecommended Action:");
    console.log("Update the affected contracts or configurations to comply with the quality standards.");
  }

  if (overallStatus === "FAIL") {
    process.exitCode = 1;
  }
}
