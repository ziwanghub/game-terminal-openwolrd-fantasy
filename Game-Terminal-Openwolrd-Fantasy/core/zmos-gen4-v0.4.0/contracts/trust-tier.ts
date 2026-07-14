// Trust Tier definitions for Z-MOS governed execution.
//
// Tiers define the level of autonomy and mutation authority granted to an AI task.
// Each tier is strictly more permissive than the one below it.
// The workflow policy assigns a minimum required tier per workflow.
//
// TIER_0 — Diagnostic only. No AI invocation. Read-only runtime evidence.
// TIER_1 — Advisory AI. Read + summarize. No state mutation.
// TIER_2 — Bounded task execution. Structured tasks with defined allowed-tasks list. No mutation.
// TIER_3 — Full task execution. Code tasks, artifact writes. Still no direct state mutation.
//
// Runtime enforcement: runGovernedAiTask checks the payload task against the
// tier ceiling defined in the workflow policy entry.

export type TrustTier = "TIER_0" | "TIER_1" | "TIER_2" | "TIER_3";

export const TRUST_TIER_ORDER: TrustTier[] = ["TIER_0", "TIER_1", "TIER_2", "TIER_3"];

// Returns true if `actual` meets or exceeds `required`.
export function tierSatisfies(actual: TrustTier, required: TrustTier): boolean {
  return TRUST_TIER_ORDER.indexOf(actual) >= TRUST_TIER_ORDER.indexOf(required);
}

// Maps task names to the minimum Trust Tier required to execute them.
export const TASK_TIER_REQUIREMENTS: Record<string, TrustTier> = {
  "system-check": "TIER_2",
  "code-task": "TIER_3",
};

// Returns the minimum tier required to run a given task.
// Unknown tasks default to TIER_3 (most restrictive unknown).
export function getRequiredTierForTask(task: string): TrustTier {
  return TASK_TIER_REQUIREMENTS[task] ?? "TIER_3";
}
