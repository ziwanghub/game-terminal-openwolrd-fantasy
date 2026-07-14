# Truth Contract Specification — Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"

## Purpose

`truth.contract.json` is the authoritative machine state for Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial".
All truth-first decisions must read from this contract when schema-valid.

## Required High-Level Fields

- `contract_version`
- `generated_at`
- `contract_hash`
- `code_ref`
- `runtime_ref`
- `env_ref`
- `data_ref`
- `asset_ref`
- `gate_state`
- `confidence`
- `unknowns`
- `verdict`

## Field Intent

- `code_ref`: identifies branch and commit used by current execution context
- `runtime_ref`: identifies process/runtime identity used to run enforcement logic
- `env_ref`: identifies target environment and config fingerprint
- `data_ref`: identifies data/schema state used by the system
- `asset_ref`: identifies artifacts and schema-related assets
- `gate_state`: current gate and eligibility for next step
- `confidence`: confidence score and evaluation basis
- `unknowns`: unresolved evidence items
- `verdict`: system decision (`SAFE_TO_CONTINUE`, `CONTINUE_WITH_RISK`, `STOP_AND_REPAIR`)

## Write Requirements

- Must be written only through atomic write flow.
- Must validate against schema before final rename.
- Must create timestamped backup for previous contract.
- Direct write to `truth.contract.json` is forbidden.

## Validation Requirements

1. Schema validation must pass.
2. `contract_hash` must match canonical serialized content.
3. `generated_at` must be present and parseable.
4. `verdict` must be one of allowed enum values.

## Operational Rules

- If contract exists and is valid: use as authoritative source.
- If contract is missing/invalid: follow configured fallback policy for current phase.
- In final enforcement, invalid truth contract is a block condition.
