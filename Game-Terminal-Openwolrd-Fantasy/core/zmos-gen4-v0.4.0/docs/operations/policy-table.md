# Policy Table — Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"

## Drift Policy

| Drift Level | Condition | System Behavior | Verdict |
|---|---|---|---|
| 0 (SAFE) | Truth and legacy are consistent | Continue | `PASS` |
| 1 (WARNING) | Non-critical mismatch (for example phase drift) | Warn only | `CONTINUE` |
| 2 (CRITICAL) | Commit mismatch or environment mismatch | Soft/Hard block by phase | `CONTINUE-WITH-RISK` or `STOP-AND-REPAIR` |

## Hard Block Conditions

| Condition | Action | Exit Behavior |
|---|---|---|
| `commit_sha` mismatch | Block start path | non-zero exit |
| Environment mismatch (for example prod vs dev) | Block protected operations | non-zero exit |
| Invalid `truth.contract.json` schema | Block truth-first execution | non-zero exit |

## Required Gates

| Gate | Requirement |
|---|---|
| Schema Gate | `zcl schema validate` must pass |
| Truth Gate | `zcl truth build` must produce valid contract |
| Preflight Gate | 5-state verification must run |
| Scope Gate | strict mode must fail-closed on empty allow-list |
