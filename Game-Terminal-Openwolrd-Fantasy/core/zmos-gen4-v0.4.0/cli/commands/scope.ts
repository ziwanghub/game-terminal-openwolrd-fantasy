import { validateScopePure } from "../../core/worktree.js";

export async function runScopeValidateCommand(): Promise<void> {
  const result = await validateScopePure();

  if (result.status === "WARN_NO_SCOPE") {
    console.warn("[WARN] No canonical scope_files found in .z-mos/intent.card.json");
    console.warn("Recommendation:\n  regenerate handoff with --scope");
    process.exitCode = 0;
    return;
  }

  if (result.status === "WARN_DRIFT") {
    console.warn("[WARN] Scope drift detected\n");
    console.warn("Expected scope:");
    result.expectedScope.forEach(f => console.warn(`- ${f}`));
    console.warn("\nChanged files:");
    result.changedFiles.forEach(f => console.warn(`- ${f}`));
    console.warn("\nOutside scope:");
    result.outsideScope.forEach(f => console.warn(`- ${f}`));
    process.exitCode = 0;
    return;
  }

  console.log("[PASS] Scope validation clean");
  console.log("Expected scope:");
  result.expectedScope.forEach(f => console.log(`- ${f}`));
  console.log("\nChanged files:");
  if (result.changedFiles.length === 0) {
    console.log("- (none)");
  } else {
    result.changedFiles.forEach(f => console.log(`- ${f}`));
  }
  process.exitCode = 0;
}
