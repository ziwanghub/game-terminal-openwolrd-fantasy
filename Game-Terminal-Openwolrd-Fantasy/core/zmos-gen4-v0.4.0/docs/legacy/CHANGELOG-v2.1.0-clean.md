# Z-MOS v3.0.0 "Purity"

## Summary

- Final canonicalization sprint completed.
- Truth-first runtime path hardened.
- Legacy runtime bridges reduced for session/handoff migration.
- Production readiness strict profile returns GREEN.
- CI sequential enforcement and branch-protection governance documented.
- Documentation authority model aligned to truth-first runtime semantics.

## Key Changes

- Canonical consistency module renamed to `core/truth-consistency.ts`.
- `state-integrity.ts` now validates `truth.contract.json` as primary canonical state.
- `zcl init` no longer generates `session.json`.
- Added regression test `Core K — Session Fallback Optional Under Truth-First`.
- Strict readiness policy updated to enforce GREEN classification under approved warning policy.
- Added `.github/workflows/verify-strict.yml` as dedicated sequential verification job.
- Added branch protection guide and required-merge gate visibility in README/docs.
- Aligned docs terminology: canonical runtime authority, canonical execution intent, and non-authoritative compatibility artifact.

## Verification

- `node ./scripts/verify/verify.mjs core` = PASS
- `npm run verify:production-readiness:strict` = PASS (GREEN)
- `node ./bin/zcl.js --version` = `v3.0.0 "Purity"`

## Release Closure Notes

- Baseline status document: `docs/v3.0.0 "Purity"-status.md`
- Required merge gate: `verify-strict` (sequential only, no matrix parallelization)
- Branch governance setup guide: `docs/branch-protection-guide.md`
