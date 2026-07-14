export type TraceActor = "human" | "system" | "ollama" | "codex";

export type TraceExecutionStatus = "success" | "warning" | "blocked" | "failed";

export type TraceResultClass =
  | "success"
  | "warning-execution"
  | "blocked-preflight"
  | "blocked-canonical-integrity"
  | "blocked-policy"
  | "failed-runtime";

export type TraceGateStatus = "healthy" | "warning" | "blocking" | "not-evaluated";

export type TracePolicyStatus = "healthy" | "warning" | "blocking" | "not-applicable";

export type TraceExpectation = "required-if-business-logic" | "optional-by-design";

export type TraceResult =
  | "emitted"
  | "not-emitted-by-design"
  | "not-emitted-blocked-before-logic"
  | "not-emitted-due-failure"
  | "not-enough-evidence";

export type TraceEnvironment = {
  platform: string;
  arch: string;
};

export type TraceRecordContract = {
  timestamp: string;
  command: string;
  execution_status: TraceExecutionStatus;
  result_class: TraceResultClass;
  preflight_status: TraceGateStatus;
  canonical_status: TraceGateStatus;
  policy_status: TracePolicyStatus;
  trace_expectation: TraceExpectation;
  trace_result: TraceResult;
  environment: TraceEnvironment;
  actor: TraceActor;
  repository: string;
  framework: string;
  node_id?: string;
  node_role?: string;
  details: Record<string, unknown>;
  sequence?: number;
  previous_hash?: string;
  current_hash?: string;
};
