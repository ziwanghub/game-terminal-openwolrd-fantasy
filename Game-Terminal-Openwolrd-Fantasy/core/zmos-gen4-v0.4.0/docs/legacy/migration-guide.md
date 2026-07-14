# Migration Guide — Z-MOS v1.5 to v3.0.0 "Purity"

## Migration Goal

Move from advisory governance to enforced, truth-first governance without breaking active operations.

## Scope of Change

- Version/branding: `v3.0.0 "Purity"`
- Core state model: Pure truth-first
- Runtime authority model:
  - canonical runtime authority = `.z-mos/truth.contract.json`
  - canonical execution intent = `.z-mos/intent.card.json`
  - legacy compatibility artifacts (session, project-state, handoff) permanently removed
- Enforcement behavior: fail-closed in critical conditions
- Documentation: v2 taxonomy and operational runbooks

## Recommended Migration Phases

1. Foundation
- Lock schemas
- Validate schema command in CI
- Confirm verify suite baseline

2. Core Enforcement Safety
- Scope guard strict fail-closed
- Bind regression tests into verify suite

3. Truth Engine Adoption
- Atomic write + backup for truth contract
- `zcl truth build` operational and verified
- Integrate truth read paths in start/status

4. Consistency and Preflight
- Truth-legacy drift detection
- 5-state preflight checks

5. Final Enforcement
- Truth-first authoritative mode
- Drift escalation policy
- Hard block on critical drift conditions

## Legacy Handling Rules

- Legacy read paths and fallback compatibility have been permanently removed.
- The system is now 100% Pure Truth-First.

## Cutover Checklist

- `zcl --version` returns `v3.0.0 "Purity"`
- `zcl schema validate` passes
- `zcl truth build` succeeds and writes valid contract
- `zcl preflight` runs with expected signals
- `zcl status` reports truth-first mode
- Verify suite passes 100%

## Rollback Guidance

- Roll back by release boundary, not by partial file revert.
- Preserve truth backups and trace history.
- Re-run full verification before re-enabling protected operations.
