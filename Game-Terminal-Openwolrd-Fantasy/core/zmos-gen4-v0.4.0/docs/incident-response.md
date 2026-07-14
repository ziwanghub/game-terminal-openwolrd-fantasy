# Incident Response — Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"

## Trigger

Use this runbook when system verdict is:

- `STOP_AND_REPAIR`
- `CRITICAL_DRIFT_HARD_BLOCK`
- non-zero exit caused by truth, scope, preflight, or environment enforcement

## Immediate Actions

1. Stop further protected operations.
2. Capture current output from `zcl status` and `zcl preflight`.
3. Record `contract_hash`, `drift_level`, and `reason`.
4. Open incident record in team workflow.

## Triage Matrix

- Commit mismatch:
  - Verify repository HEAD and expected commit.
  - Rebuild truth contract after sync.
- Environment mismatch:
  - Verify target environment settings and forbidden host policy.
  - Correct environment, then rerun preflight.
- Invalid truth schema:
  - Run `zcl schema validate`.
  - Rebuild contract via `zcl truth build` only.
- Scope enforcement failure:
  - Review strict mode allow-list.
  - Add explicit scope and rerun guard.

## Recovery Sequence

```bash
zcl schema validate
zcl truth build
zcl preflight
zcl status
```

Proceed only when verdict returns to safe state for current phase policy.

## Post-Incident Requirements

- Add trace evidence reference.
- Document root cause and corrective action.
- Add regression test if issue came from missing guard in verify suite.
