export type TruthVerdict = "SAFE_TO_CONTINUE" | "PROCEED_WITH_CAUTION" | "STOP_AND_REPAIR";

export interface TruthContract {
  schema_version: string;
  generated_at: string;
  code_ref: {
    commit: string;
    branch: string;
  };
  runtime_ref: {
    platform: string;
    process: string;
  };
  env_ref: {
    target_host: string;
    target_env: string;
    config_hash: string;
  };
  data_ref: {
    source: string;
    schema_hash: string;
  };
  asset_ref: {
    bundle_hash: string;
    cache_hash: string;
  };
  gate_state: {
    active_gate: string;
    required_checks: string[];
  };
  confidence: number;
  unknowns: string[];
  verdict: TruthVerdict;
}
