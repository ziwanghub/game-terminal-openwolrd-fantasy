import { validateScopeGuard } from "../../core/scope-guard.js";

export async function runScopeGuardCommand(): Promise<void> {
  const result = await validateScopeGuard();

  if (!result.configLoaded) {
    console.log("[WARN] Scope guard config not found at .z-mos/quality/scope-guard.json");
    return;
  }

  if (result.status === "PASS") {
    console.log("[PASS] Scope guard clean");
    return;
  }

  console.log(`[${result.status}] Protected scope touched or allowed scope violated`);
  
  if (result.violations.length > 0) {
    console.log("Violations:");
    result.violations.forEach((v) => {
      console.log(`- ${v.file}`);
      console.log(`  Reason: ${v.reason}`);
    });
  }

  console.log("\nRecommended Action:");
  console.log("Review changes. Revert out-of-scope files if this was unintentional.");

  if (result.status === "FAIL") {
    process.exitCode = 1;
  }
}
