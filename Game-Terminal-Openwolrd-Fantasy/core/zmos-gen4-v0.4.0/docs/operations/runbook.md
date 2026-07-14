# Runbook — Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"

## Standard Startup Sequence

1. Validate schemas.
2. Build truth contract.
3. Run preflight.
4. Inspect status and drift signals.
5. Execute target command only when verdict is safe.

## Commands

```bash
zcl schema validate
zcl truth build
zcl preflight
zcl status
zcl start
```

## Incident Handling

1. If verdict is `STOP-AND-REPAIR`, stop execution immediately.
2. Capture drift reason and contract hash.
3. Repair source of mismatch (commit, environment, schema, or scope).
4. Re-run schema, truth build, preflight, and status.

## Recovery Checklist

- Truth contract exists and schema-valid
- Drift level is 0 or acceptable for current phase
- Scope guard is explicit and non-empty for strict mode
- Verify suite passes before merge
