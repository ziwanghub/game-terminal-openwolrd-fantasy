# Phase 3B Controlled Internal Usage Preparation

- Document Code: `PHASE3B-IMPL-008`
- Version: `0.1`
- Status: Draft
- Date: `2026-05-29`
- Basis:
  - `docs/roadmap/PHASE3B-PLAN-001-LOCAL-RUNTIME-HARDENING-PLAN-0.1.md`
  - `docs/roadmap/PHASE3A-IMPL-009-LOCAL-KERNEL-INTEGRATION-GATE-0.1.md`
  - `core/gen4/local-kernel/**`
  - `tests/gen4/local-kernel.*.test.ts`
  - `tests/gen4/fixtures/local-kernel.fixtures.ts`

## 1. Purpose

Prepare controlled internal usage assessment for Z-MOS Gen4 local sovereign kernel before any broader trial.

This document is preparation-only and local-only. It does not authorize production deployment, federation runtime implementation, networking, or distributed synchronization.

## 2. Entry Basis

Current authorized posture:

- `Phase 3A Local Sovereign Kernel = PASS`
- `Phase 3B Local Runtime Hardening = ACTIVE`
- `Federation Runtime Implementation = NOT APPROVED`
- `Networking/Distributed Sync = FORBIDDEN`
- `Production Deployment = NOT APPROVED`

Current local-kernel readiness summary:

- local intent model and validation
- trust envelope enforcement
- fail-closed decision outcomes (`accepted`, `rejected`, `quarantined`)
- append-only trace
- deterministic replay
- local evidence package
- deterministic recovery diagnostics
- fixture/scenario helpers
- static no-network boundary guard

## 3. Usage Boundaries

Controlled usage boundaries:

- local-only execution scope
- in-memory or local-file-only diagnostic artifacts
- mock/non-destructive action posture only
- diagnostic-first usage posture
- no external side effects
- no production workflows
- no networking
- no federation runtime
- no distributed sync

## 4. Allowed Internal Usage Cases

Candidate A: Local workflow validation

- allowed scope:
  - local intent submission and validation
  - mock action execution only
  - accepted/rejected/quarantined observation
- expected outputs:
  - decision + trace + replay + evidence + recovery diagnostic

Candidate B: Local trace/replay audit exercise

- allowed scope:
  - local trace review
  - deterministic replay/recovery diagnostics
  - evidence inspection for mismatch/corruption investigation
- expected outputs:
  - reproducible replay summaries and blocked/failed recovery diagnostics when appropriate

Candidate C: Local governance enforcement simulation

- allowed scope:
  - reject/quarantine path validation
  - fail-closed behavior verification under fixtures
- expected outputs:
  - explicit error/invariant visibility and no implicit pass paths

## 5. Forbidden Usage Cases

Forbidden during controlled internal usage:

- networking or external API calls
- federation runtime behavior
- distributed sync/consensus behavior
- cross-process federation runtime
- autonomous/adaptive runtime behavior
- production deployment or production workflow coupling
- real infrastructure/customer system control
- real external side-effect execution

## 6. Operator Checklist

Operator checks:

- can accepted/rejected/quarantined results be understood quickly?
- can rejection reason be identified via error/invariant references?
- can trace/replay/evidence be inspected without code changes?
- can blocked recovery state be identified with clear reason?
- is fail-closed friction manageable for normal local workflows?

## 7. Developer Checklist

Developer checks:

- setup time for local scenario run is acceptable
- fixture builders are predictable and easy to use
- scenario helpers reduce repetitive setup
- debugging path for reject/quarantine/mismatch is clear
- tests remain readable and maintainable
- local-kernel API boundary is clear
- no-network/non-federated boundary is clear and enforceable

## 8. Failure Handling Procedure

Controlled failure handling procedure:

1. stop at fail-closed decision output (`rejected`/`quarantined` or blocked/failed diagnostic)
2. capture decision, trace, replay, evidence, recovery artifacts
3. classify failure category:
   - input/intent validation
   - trust/scope enforcement
   - trace/replay integrity
   - evidence/recovery alignment
4. document operator/developer interpretation difficulty
5. prohibit repair attempts that mutate trace/history
6. escalate only as local hardening feedback item

## 9. Trace / Replay Review Procedure

Review sequence:

1. verify trace exists for accepted/rejected/quarantined outcomes
2. verify trace sequence monotonicity and append-only posture
3. replay identical trace and compare deterministic output
4. verify replay error handling on malformed/gapped/duplicate conditions
5. record replay usefulness score for investigation workflow

## 10. Evidence Package Review Procedure

Review sequence:

1. verify evidence package generation after replay
2. verify status semantics (`complete`/`incomplete`/`failed`)
3. verify count and ID alignment with trace/replay
4. verify error/invariant aggregation readability
5. record whether evidence object helps or hinders debugging

## 11. Recovery Diagnostic Review Procedure

Review sequence:

1. run deterministic recovery diagnostic from trace+replay+evidence
2. verify status semantics (`recoverable`/`blocked`/`failed`)
3. verify diagnostic codes and reason visibility
4. verify `RECOVERY_REPAIR_PROHIBITED` posture remains explicit
5. confirm no implicit release/escalation paths

## 12. Governance Overhead Evaluation Criteria

Evaluate:

- fail-closed governance adds practical safety or only ceremony
- trace/evidence/recovery payloads are readable enough for internal users
- error/invariant codes are actionable
- governance review steps are proportionate to local runtime value
- development throughput impact remains acceptable

## 13. Developer Usability Evaluation Criteria

Evaluate:

- onboarding friction for new internal engineer
- average setup/diagnosis time
- helper/fixture completeness for common local scenarios
- debugging clarity for rejection/quarantine/mismatch cases
- number of bypass attempts caused by tooling friction

## 14. Trial Success Criteria

Controlled internal usage trial is successful when:

- local-only boundary is preserved throughout trial
- operators understand decision outcomes and failure reasons
- developers can run and debug scenarios reliably
- trace/replay/evidence/recovery artifacts improve diagnosis
- governance overhead is acceptable
- no bypass behavior is needed to complete normal local workflows

## 15. Exit Criteria

Exit criteria for closing PHASE3B-IMPL-008:

- operator checklist completed with acceptable results
- developer checklist completed with acceptable results
- feedback metrics captured and reviewed
- no boundary violations detected
- no production/federation/network usage attempted
- unresolved high-friction failures are either fixed or clearly queued for hardening follow-up

## 16. Final Determination

- `PHASE3B-IMPL-008 Controlled Internal Usage Preparation = READY`
- `Controlled Internal Usage = AUTHORIZED (LOCAL-ONLY, NON-PRODUCTION)`
- `Federation Runtime Implementation = NOT APPROVED`
- `Networking/Distributed Sync = FORBIDDEN`
- `Production Deployment = NOT APPROVED`

Recommended transition after controlled usage completion:

- proceed to `PHASE3B-GATE-001 — Local Runtime Hardening Review`

## 17. Authorization Statement

This document prepares controlled internal usage assessment only and does not authorize federation runtime implementation.
