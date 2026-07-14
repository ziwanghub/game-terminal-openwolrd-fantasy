import type { AgentAction, AgentContext } from "./agent-action.js";
import type { IntentCardV300Agent } from "./intent-card-v3.0.1.js";
import type { TruthContract } from "./truth-contract.js";

export type GovernanceDecision = "ALLOW" | "BLOCK";

export type GovernanceBlockReason =
  | "INTENT_LOAD_FAILED"
  | "INTENT_VALIDATION_FAILED"
  | "TRUTH_LOAD_FAILED"
  | "TRUTH_VERDICT_BLOCKED"
  | "TOOL_NOT_ALLOWED"
  | "ACTION_NOT_ALLOWED"
  | "SCOPE_VIOLATION"
  | "STEP_LIMIT_EXCEEDED"
  | "STOP_CONDITION_TRIGGERED"
  | "TERMINATION_CONDITION_TRIGGERED"
  | "UNKNOWN_ERROR";

export interface RunWithIntentOptions<TContext = unknown, TResult = unknown> {
  workspaceDir: string;
  action: AgentAction;
  handler: (ctx: RunWithIntentExecutionContext<TContext>) => Promise<TResult> | TResult;
  intentPath?: string;
  truthPath?: string;
  stepIndex?: number;
  maxRuntimeMs?: number;
  context?: TContext;
  agentContext?: AgentContext;
}

export interface RunWithIntentExecutionContext<TContext = unknown> {
  workspaceDir: string;
  context?: TContext;
  action: AgentAction;
  intentCard: IntentCardV300Agent;
  truthContract: TruthContract;
  agentContext?: AgentContext;
}

export interface RunWithIntentResult<TResult = unknown> {
  success: boolean;
  blocked: boolean;
  exitCode: number;
  decision: GovernanceDecision;
  reason?: GovernanceBlockReason;
  data?: TResult;
  trace: RunWithIntentTraceEvent[];
  intentSummary?: {
    schema_version: string;
    max_steps: number;
    enforcement: "hard-block";
  };
  truthSummary?: {
    verdict?: TruthContract["verdict"];
    generated_at?: string;
  };
  error?: string;
}

export interface RunWithIntentTraceEvent {
  step: string;
  action: string;
  decision: GovernanceDecision;
  reason?: string;
  blocked_by?: GovernanceBlockReason;
  timestamp: string;
  details?: Record<string, unknown>;
}
