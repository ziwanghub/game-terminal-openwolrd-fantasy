# Intent Card Specification — Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"

## Purpose

`intent.card.json` is the canonical execution intent contract for Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial".

This contract is Agent-First. Every AI agent action must be authorized by intent boundaries before execution begins.

---

## Authority Position

| File | Role |
|------|------|
| `.z-mos/truth.contract.json` | Canonical runtime authority (machine state) |
| `.z-mos/intent.card.json` | Canonical execution intent (agent authorization boundary) |

The truth contract answers whether execution is currently safe.
The intent card answers what the agent is allowed to do.

---

## Schema Structure

```json
{
  "schema_version": "3.0.0-agent",
  "intent": {
    "objective": "<string>",
    "strategy": "<string>",
    "risk_acknowledgement": "<string>"
  },
  "system": {
    "scope_files": ["<glob or path>"],
    "required_tests": ["<command string>"],
    "stop_conditions": ["<string>"],
    "rollback_plan": "<string>",
    "truth_snapshot_ref": "<path to truth.contract.json>"
  },
  "agent": {
    "allowed_tools": ["<tool-id>"],
    "allowed_actions": ["<action-id>"],
    "max_steps": 20,
    "termination_conditions": ["<string>"],
    "enforcement": "hard-block"
  }
}
```

---

## Field Semantics

### `schema_version`

- Type: `string`
- Required: yes
- Value: must be `"3.0.0-agent"`

### `intent` block

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `objective` | string | yes | Task goal the agent is expected to complete |
| `strategy` | string | yes | Chosen implementation path |
| `risk_acknowledgement` | string | yes | Accepted execution risk (use `"None"` when no risk) |

### `system` block

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scope_files` | string[] | yes | Paths/globs the agent is allowed to mutate |
| `required_tests` | string[] | yes | Commands that must pass before completion |
| `stop_conditions` | string[] | yes | Conditions that require immediate stop/escalation |
| `rollback_plan` | string | yes | Explicit rollback instruction |
| `truth_snapshot_ref` | string | yes | Bound truth snapshot used for drift checks |

### `agent` block

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `allowed_tools` | string[] | yes | Approved tools the agent may invoke |
| `allowed_actions` | string[] | yes | Approved action classes (e.g. `read`, `write`, `test`) |
| `max_steps` | number | yes | Maximum governed execution steps |
| `termination_conditions` | string[] | yes | Additional deterministic termination triggers |
| `enforcement` | string | yes | Must be `"hard-block"` |

---

## Hard-Block Enforcement

Z-MOS must block execution immediately when any condition below is true:

1. truth contract is missing/invalid
2. truth verdict is not `SAFE_TO_CONTINUE`
3. requested action is outside `allowed_actions`
4. requested tool is outside `allowed_tools`
5. target mutations fall outside `scope_files`
6. step count exceeds `max_steps`
7. any `termination_conditions` or `stop_conditions` is triggered

No audit-only fallback is allowed in this profile.

---

## Lifecycle

1. `zcl intent init [--force]` creates `.z-mos/intent.card.json`
2. intent payload is finalized with task objective/strategy/risk
3. system boundaries are declared (`scope_files`, tests, stop conditions)
4. agent boundaries are declared (`allowed_tools`, `allowed_actions`, `max_steps`, `termination_conditions`)
5. `zcl schema validate` must pass
6. governed execution may begin

---

## Validation Rules

1. `schema_version` must be `"3.0.0-agent"`
2. `intent.objective` must be non-empty
3. `intent.strategy` must be non-empty
4. `system.rollback_plan` must be non-empty
5. `system.truth_snapshot_ref` must point to `.z-mos/truth.contract.json` or an equivalent valid truth path
6. `agent.enforcement` must equal `"hard-block"`
7. `agent.max_steps` must be integer >= 1
8. `allowed_tools`, `allowed_actions`, `termination_conditions` must be arrays

---

## Truth-First Semantics

```
truth.contract.verdict = STOP_AND_REPAIR
  -> execution blocked before intent evaluation

truth.contract.verdict = SAFE_TO_CONTINUE
  -> intent + system + agent boundaries evaluated
  -> any violation = hard-block
```

---

## Example (Agent Task)

```json
{
  "schema_version": "3.0.0-agent",
  "intent": {
    "objective": "Implement runWithIntent() for Node SDK",
    "strategy": "Add runtime guard pipeline and enforce tool/action boundaries before handler execution",
    "risk_acknowledgement": "Low"
  },
  "system": {
    "scope_files": [
      "sdk/**",
      "docs/intent-card-spec.md"
    ],
    "required_tests": [
      "npm test",
      "node ./scripts/verify/verify.mjs core"
    ],
    "stop_conditions": [
      "schema validation fail",
      "critical drift detected"
    ],
    "rollback_plan": "Revert affected files and re-run required tests",
    "truth_snapshot_ref": ".z-mos/truth.contract.json"
  },
  "agent": {
    "allowed_tools": [
      "functions.exec_command",
      "functions.apply_patch"
    ],
    "allowed_actions": [
      "read",
      "write",
      "test"
    ],
    "max_steps": 40,
    "termination_conditions": [
      "attempted out-of-scope mutation",
      "second consecutive verification failure"
    ],
    "enforcement": "hard-block"
  }
}
```

---

## Related Documents

- [`docs/truth-contract-spec.md`](./truth-contract-spec.md)
- [`docs/commands.md`](./commands.md)
- [`docs/architecture/data-flow.md`](./architecture/data-flow.md)
