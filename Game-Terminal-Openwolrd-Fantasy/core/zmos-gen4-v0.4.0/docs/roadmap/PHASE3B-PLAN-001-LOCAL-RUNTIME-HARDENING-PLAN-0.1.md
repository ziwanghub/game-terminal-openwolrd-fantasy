# Phase 3B Local Runtime Hardening Plan

- Version: `0.1`
- Status: Draft
- Date: `2026-05-29`
- Basis:
  - `docs/roadmap/PHASE3A-IMPL-009-LOCAL-KERNEL-INTEGRATION-GATE-0.1.md`
  - `docs/roadmap/PHASE3A-GEN4-EXECUTION-ROADMAP-0.1.md`
  - `docs/roadmap/PHASE3A-GEN4-IMPLEMENTATION-TASKS-0.1.md`
  - `core/gen4/local-kernel/**`
  - `tests/gen4/local-kernel.*.test.ts`
  - existing Gen4 tests

## 1. Purpose of Phase 3B Local Runtime Hardening

Define the Phase 3B local-only hardening plan that evolves the Phase 3A working local kernel into a more stable local runtime foundation.

This phase is planning-only, governance-constrained, and non-authorizing.

## 2. Phase 3B Entry Basis

- `Phase 3A Local Sovereign Kernel = PASS`
- `Phase 3B Local Runtime Hardening = RECOMMENDED`
- `Federation Runtime Implementation = NOT APPROVED`
- `Networking/Distributed Sync = FORBIDDEN`

## 3. Phase 3B Boundary Model

Phase 3B boundaries:

- local-only runtime
- mock or controlled local-only execution
- fail-closed behavior
- deterministic trace/replay/evidence posture
- no networking
- no federation runtime
- no distributed sync
- no adaptive governance runtime
- no autonomous AI decision layer
- no production deployment

Boundary intent:

- strengthen local reliability and usability before any pre-federation consideration

## 4. Hardening Workstream A — API / Interface Stabilization

Tasks:

- review public exports in `core/gen4/local-kernel/index.ts`
- stabilize naming and type contracts for intent/decision/trace/replay/evidence
- document internal-only vs public API surfaces
- reduce accidental cross-module coupling
- preserve compatibility with existing local-kernel and Gen4 tests

Deliverable:

- local-kernel API surface map v0.1 (public/internal classification)

## 5. Hardening Workstream B — Stronger Readonly Typing

Tasks:

- strengthen readonly typings for returned decision/trace/replay/evidence objects
- reduce mutation risk via stricter compile-time guarantees
- preserve runtime immutability behavior already present
- add compile-time readonly validation tests/checks where feasible

Deliverable:

- readonly contract hardening checklist + type updates

## 6. Hardening Workstream C — Local Trace Persistence Experiment

Tasks:

- design and test a bounded append-only local file trace experiment
- support deterministic load + replay from local file input
- keep scope local-only and experimental
- avoid database introduction
- avoid network/sync/background service behavior
- avoid production durability guarantees at this stage

Deliverable:

- local trace persistence experiment report with constraints and findings

## 7. Hardening Workstream D — Deterministic Recovery / Replay Hardening

Tasks:

- harden replay recovery flow from local trace sources
- improve replay mismatch diagnostics
- improve failed replay handling clarity
- define corrupted trace diagnostic behavior
- produce deterministic recovery summary format
- explicitly prohibit automatic state repair

Deliverable:

- recovery/replay hardening scenarios and expected fail-closed outputs

## 8. Hardening Workstream E — Developer Ergonomics & Fixture Builders

Tasks:

- provide local intent fixture builders
- provide trust-envelope fixture adapters/builders for local-kernel usage
- add scenario runner helpers for common local flows
- add replay/evidence inspection helpers
- improve test utilities for onboarding speed
- reduce developer friction while preserving fail-closed semantics

Deliverable:

- local-kernel developer test utility pack v0.1

## 9. Hardening Workstream F — Static No-Network Boundary Enforcement

Tasks:

- strengthen current string-based scans with static import boundary checks
- preserve existing forbidden import list
- evaluate lightweight lint/static policy checks feasible in CI
- define CI-friendly no-network guard execution
- keep guard low-overhead and deterministic

Deliverable:

- static no-network guard strategy and CI integration plan

## 10. Hardening Workstream G — Local Recovery Scenarios

Tasks:

- define rejected-intent recovery visibility scenarios
- define quarantine inspection scenarios
- define replay mismatch investigation scenarios
- define corrupted trace diagnostic failure scenarios
- define evidence package incomplete/failed review scenarios
- keep all recovery scenarios local-only and diagnostic-only

Deliverable:

- local recovery scenario matrix with expected fail-closed outcomes

## 11. Hardening Workstream H — Controlled Internal Usage Preparation

Tasks:

- identify one to two safe internal local-only usage cases
- define strict usage constraints and safety boundaries
- define operator/developer feedback checklist
- assess governance overhead in real local workflows
- assess developer usability and debugging clarity
- validate practical usability of fail-closed behavior

Constraint:

- this is controlled internal usage preparation only, not production deployment

Deliverable:

- controlled internal usage readiness checklist v0.1

## 12. Explicitly Forbidden Scope

Forbidden in Phase 3B:

- networking
- HTTP/RPC/socket behavior
- federation transport
- distributed sync
- consensus
- cross-process federation runtime
- adaptive governance runtime
- autonomous AI behavior
- production deployment
- database-backed distributed persistence
- background daemon
- real external side-effect execution

## 13. Phase 3B Acceptance Criteria

Phase 3B planning acceptance criteria:

- existing Gen4 tests remain green
- Phase 3A local-kernel tests remain green
- local API/interface surface is documented
- readonly typing is improved or explicitly reviewed with action list
- local trace persistence experiment is scoped with guardrails
- deterministic recovery/replay hardening tests are planned
- developer fixture/helper strategy is defined
- static no-network boundary strategy is defined
- controlled internal usage criteria are defined
- no federation/networking behavior is approved

## 14. Phase 3B Exit Review Questions

- Is the local kernel usable by another engineer?
- Is trace/replay useful for debugging real local scenarios?
- Is fail-closed behavior operationally practical for internal users?
- Is governance overhead acceptable in daily usage?
- Are local recovery diagnostics sufficient?
- Are boundary guards strong enough for continued local hardening?
- Is persistence still local-only and safe?
- Should Phase 4 pre-federation research begin, or should local hardening continue?

## 15. Final Determination

- `Phase 3B Local Runtime Hardening = PLANNED`
- `Federation Runtime Implementation = NOT APPROVED`
- `Networking/Distributed Sync = FORBIDDEN`
- `Production Deployment = NOT APPROVED`
- `Next Best Move = LOCAL HARDENING BEFORE FEDERATION`

## 16. Authorization Statement

This document defines Phase 3B local runtime hardening planning only and does not authorize federation runtime implementation.
