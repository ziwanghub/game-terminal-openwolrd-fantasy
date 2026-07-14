export type GovernanceVerdict = "SAFE_TO_CONTINUE" | "PROCEED_WITH_CAUTION" | "STOP_AND_REPAIR";

export type ExecutionStatus = "success" | "warning" | "blocked" | "failed";

export type GateStatus = "healthy" | "warning" | "blocking" | "not-evaluated";

export type PolicyStatus = "healthy" | "warning" | "blocking" | "not-applicable";
