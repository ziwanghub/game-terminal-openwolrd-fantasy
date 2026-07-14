export type AgentActionType = "read" | "write" | "test" | "command";

export interface AgentAction {
  action: AgentActionType;
  tool: string;
  targetPaths?: string[];
  metadata?: Record<string, unknown>;
}

export interface AgentContext {
  sessionId: string;
  agentName: string;
}
