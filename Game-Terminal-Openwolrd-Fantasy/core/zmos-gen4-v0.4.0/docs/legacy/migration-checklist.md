# Migration Checklist — v1.5 to v3.0.0 "Purity"

## Foundation

- [ ] `zcl --version` returns `v3.0.0 "Purity"`
- [ ] `zcl schema validate` is enabled in CI
- [ ] locked schemas exist in `.z-mos/schemas/`

## Core Safety

- [ ] Scope guard strict mode is fail-closed
- [ ] Empty allow-list in strict mode fails
- [ ] Scope guard regression test is in verify suite

## Truth Engine

- [ ] Atomic write strategy is active
- [ ] Backup files are created on contract update
- [ ] `zcl truth build` writes via atomic path only

## Integration

- [ ] `start` and `status` read truth-first
- [ ] Dual-read fallback behavior is controlled
- [ ] Truth-legacy drift signal is visible

## Enforcement

- [ ] Preflight 5-state verification is active
- [ ] Drift escalation policy (L0/L1/L2) is active
- [ ] Hard block policy triggers on critical drift

## Release Readiness

- [ ] `verify.mjs` core suite passes 100%
- [ ] Documentation migrated to v2.0 taxonomy
- [ ] Incident runbook is available and reviewed
