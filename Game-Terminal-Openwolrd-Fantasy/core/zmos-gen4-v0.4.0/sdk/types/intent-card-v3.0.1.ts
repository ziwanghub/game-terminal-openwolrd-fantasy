import { SCHEMA_VERSION_AGENT } from "../version.js";

export interface IntentCardV300Agent {
  schema_version: typeof SCHEMA_VERSION_AGENT;
  intent: IntentCardIntentBlock;
  system: IntentCardSystemBlock;
  agent: IntentCardAgentBlock;
}

export interface IntentCardIntentBlock {
  objective: string;
  strategy: string;
  risk_acknowledgement: string;
}

export interface IntentCardSystemBlock {
  scope_files: string[];
  required_tests: string[];
  stop_conditions: string[];
  rollback_plan: string;
  truth_snapshot_ref: string;
}

export interface IntentCardAgentBlock {
  allowed_tools: string[];
  allowed_actions: string[];
  max_steps: number;
  termination_conditions: string[];
  enforcement: "hard-block";
}
