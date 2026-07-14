# Architecture Overview — Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"

## System Goal

Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial" prevents unsafe agent execution by enforcing Truth-First, Fail-Closed governance.

## Core Components

- `sdk/version.ts`: single source of truth for version constants
- `sdk/runtime/run-with-intent.ts`: primary execution gate for agents
- `.z-mos/intent.card.json`: execution boundary authority (`3.0.1-agent`)
- `.z-mos/truth.contract.json`: runtime truth authority
- `.z-mos/trace/runtime-trace.jsonl`: append-only execution audit trace

## Enforcement Flow (SDK-Centered)

1. Agent requests execution through `runWithIntent()`.
2. Runtime loads and validates truth + intent authority.
3. Hard-block checks are evaluated.
4. If all checks pass, handler executes.
5. Result + trace are returned for auditability.

## Hard-Block Behavior

Execution is blocked when:
- truth verdict is not `SAFE_TO_CONTINUE`
- action/tool is outside allow-list
- target path is outside declared intent scope
- authority files are missing or invalid

## Governance Modes

- Default mode: fail-closed hard-block
- Warning paths are diagnostic only and never bypass hard-block criteria
