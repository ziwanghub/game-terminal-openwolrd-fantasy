import { evaluateReadiness } from "./readiness.js";
import { evaluateFullL7Criteria } from "./l7-criteria.js";

export async function getGovernanceRuntimeStatus() {
  const [readiness, l7] = await Promise.all([
    evaluateReadiness(),
    evaluateFullL7Criteria(),
  ]);

  return {
    ...readiness,
    l7,
  };
}
