# COMMUNICATION-STANDARD.md
Standard communication protocol for AI Agents under Z-MOS governance.
Canonical version constants are defined in `sdk/version.ts`.

## Communication Priority
`REQUIRED REPORT` > `DECISION REPORT` > `STATUS REPORT`

## Command Families
- `REQUIRED REPORT`: full structured delivery with all requested sections.
- `DECISION REPORT`: key technical/policy decision, rationale, and impact.
- `STATUS REPORT`: progress snapshot and current execution state.

## Standard Report Structure
1. `WHAT_DONE`
2. `CURRENT STATUS`
3. `VALIDATION / EVIDENCE`
4. `RISKS / LIMITATIONS`
5. `NEXT ACTION`

## Status & Decision Keywords
- Status: `APPROVED`, `IN PROGRESS`, `COMPLETED`, `DELIVERED`, `READY FOR REVIEW`, `BLOCKED`, `NEEDS REVISION`
- Decision: `ALLOW`, `HARD-BLOCK`, `GO`, `NO-GO`, `ESCALATE`, `DEFER`

## REQUIRED REPORT Example
```text
REQUIRED REPORT — SDK UPDATE
WHAT_DONE: Added runWithIntent export in sdk/index.ts
CURRENT STATUS: DELIVERED
VALIDATION / EVIDENCE: integration tests pass (4/4)
RISKS / LIMITATIONS: none critical
NEXT ACTION: proceed to documentation sync
```

## Escalation Protocol (Fail-Closed)
- `STATUS: BLOCKED`
- `REASON: <explicit violated rule>`
- `EVIDENCE: <file/field/command output>`
- `NEXT SAFE ACTION: <safe recovery step>`
- If evidence is missing: `not enough evidence to conclude`

Cross-reference: follow operational entry rules in `docs/AGENT-HANDBOOK.md`.

## Host & Database Access Protocol

### 1) Mandatory Scope Declaration
- Every host/database access must be explicitly declared in `intent.card.json`.
- Intent card must include both `allowed_hosts` and `allowed_databases`.

### 2) Required Fields in `intent.card.json`
```json
"system": {
  "allowed_hosts": ["api.staging.example.com", "localhost"],
  "allowed_databases": ["zmos_staging", "zmos_local_dev"]
}
```

### 3) Communication Rule
- Before connecting to any host/database or running related commands, agent must issue a `DECISION REPORT` first.
- The report must explicitly list impacted hosts and databases every time.

### 4) Hard-Block Condition
- If `allowed_hosts` or `allowed_databases` is missing, or target access is outside declared lists -> `HARD-BLOCK` immediately.
- No default values and no inferred/guessed targets are allowed.

### 5) Example Report
```text
DECISION REPORT — DATABASE ACCESS
DECISION: ALLOW (pending scope check)
TARGET HOSTS: api.staging.example.com
TARGET DATABASES: zmos_staging
RATIONALE: Required for migration-read verification in approved staging scope.
VALIDATION: target host/database found in intent.card.json system.allowed_hosts/system.allowed_databases
```
