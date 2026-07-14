import { verifyWorktree } from "../../core/worktree.js";

export async function runVerifyWorktreeCommand(): Promise<void> {
  const rt = await verifyWorktree();

  console.log("Z-MOS Worktree Verification\n");

  const syncStr = rt.sync.status === "PASS" ? "clean" : "desynced";
  const handoffStr = rt.handoff.valid ? "valid" : "invalid/stale";
  let scopeStr = "clean";
  if (rt.scope.status === "WARN_NO_SCOPE") scopeStr = "no-scope";
  if (rt.scope.status === "WARN_DRIFT") scopeStr = "outside-scope files detected";

  if (rt.status === "PASS") {
    console.log("[PASS] Worktree verification clean");
    console.log(`- git/state sync: ${syncStr}`);
    console.log(`- handoff: ${handoffStr}`);
    console.log(`- scope: ${scopeStr}`);
    process.exitCode = 0;
    return;
  }

  console.warn("[WARN] Worktree verification found issues");
  console.warn(`- git/state sync: ${syncStr}`);
  console.warn(`- handoff: ${handoffStr}`);
  console.warn(`- scope: ${scopeStr}`);
  
  console.warn("\nRecommendation:");
  if (rt.sync.status !== "PASS") console.warn("  zcl state update");
  if (!rt.handoff.valid) console.warn("  zcl handoff write");
  if (rt.scope.status !== "PASS") console.warn("  zcl validate scope");

  process.exitCode = 0;
}
