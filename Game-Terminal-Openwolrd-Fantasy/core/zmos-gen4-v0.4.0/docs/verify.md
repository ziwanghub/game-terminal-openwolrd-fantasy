# Verification Rules

This document defines execution rules for verification in Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial".

## Mandatory Rule: Sequential Strict Readiness

`npm run verify:production-readiness:strict` must run in sequential mode only.

Do not run it in parallel with commands that mutate truth/canonical state, including:

- `zcl truth build`
- drift test flows that intentionally alter truth evidence
- `zcl runtime clear-stale-locks`

## CI Guidance

- Use a dedicated job for `verify:production-readiness:strict`.
- Do not include this strict job in matrix parallelization with mutation-capable checks.
- Keep strict readiness after build/typecheck and before release promotion.

## Team Debug Procedure

If strict readiness fails:

1. Re-run `npm run verify:production-readiness:strict` alone (sequential).
2. Run `zcl doctor` and inspect blocking items.
3. If canonical/truth drift is detected, run `zcl truth build` and re-run strict readiness.

## Notes

This rule prevents false RED results caused by concurrent mutation of canonical runtime evidence.

## Trace Segmented Verification

When `zcl trace verify` or `npm run verify:core` is executed:
- The `trace-verifier` uses stream-based (`node:fs` + `readline`) logic to parse and verify the `runtime-trace.jsonl` memory limits.
- Archived segments are verified using `.meta.json` checkpoints to ensure rapid `O(N)` verification time and `O(1)` memory overhead, securely connecting the SHA-256 chain across rotating files.
