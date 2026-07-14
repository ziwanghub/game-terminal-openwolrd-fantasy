# Phase 3A Local Sovereign Kernel Execution Roadmap

- Version: `0.1`
- Status: Draft
- Date: `2026-05-28`
- Basis:
  - `docs/roadmap/PHASE2-GEN4-CONSOLIDATION-PLAN-0.1.md`
  - `docs/roadmap/PHASE3A-GEN4-LOCAL-KERNEL-PLAN-0.1.md`
  - `docs/roadmap/PHASE3A-GEN4-IMPLEMENTATION-TASKS-0.1.md`
  - `docs/roadmap/GEN4-P1-009-0.1.md`
  - `core/gen4/**`
  - `tests/gen4/**`

## 1. Purpose of Phase 3A Execution Roadmap

Define the actionable execution roadmap for Phase 3A local-only sovereign kernel implementation preparation.

This roadmap merges Phase 2 pullback decisions with immediate local executable preparation.

## 2. Current Strategic Decision

Current strategic decision:

- `Phase 2 Governance Baseline = SUFFICIENT`
- `Phase 2 RD Depth = OVER-EXTENDED`
- `Recursive RD/GATE Expansion = FROZEN`
- `Phase 3A Local-Only Implementation Prep = ACTIVE`
- `Federation Runtime Implementation = NOT APPROVED`
- `Networking/Distributed Sync = FORBIDDEN`

## 3. Keep / Pause / Merge Direction

Keep:

- keep Phase 1 core as implementation foundation
- keep local-only scope
- keep fail-closed and anti-drift invariants
- keep no federation/network/sync boundary

Pause:

- pause new recursive Phase 2 RD/GATE expansion
- pause `RD-GEN4-P2-024+`
- pause new closure/attribution/transition semantic refinements
- pause all work outside local-only implementation scope

Merge:

- merge Phase 2 consolidation plan and Phase 3A local kernel plan into one execution roadmap
- use this roadmap as team-facing source for immediate implementation prep
- keep existing RD/GATE artifacts as archive/supporting rationale

## 4. Phase 3A Local-Only Boundary

Allowed scope only:

- local sovereign node execution harness
- local intent model
- trust envelope enforcement in execution path
- local fail-closed decision model
- append-only trace writer
- deterministic replay
- local quarantine/rejection result model
- local invariant tests

Forbidden scope:

- networking
- HTTP/RPC/socket behavior
- federation transport
- distributed sync
- consensus
- cross-process federation runtime
- adaptive governance runtime
- autonomous AI decision layer
- production deployment
- external side-effect execution

## 5. First 3 Implementation-Prep Workstreams

Workstream 1 — Freeze Local Kernel Boundary + Invariants + Threat Model

- define local-only kernel boundary
- define invariant list
- define threat assumptions
- define forbidden scope
- define boundary review checklist

Output:

- local kernel boundary spec v0.1

Workstream 2 — Create Local Kernel Skeleton

- define local execution harness skeleton
- define local scheduler or execution entry point
- define local storage/trace abstraction
- enforce zero-network surface
- enforce no external call policy

Output:

- local skeleton ready for validator integration

Workstream 3 — Migrate / Validate Phase 1 Core Into Skeleton

- integrate existing trust-envelope validator path
- integrate existing membership/federation local validation where safe
- preserve all existing tests
- add regression tests for local execution path
- verify no networking imports or runtime federation behavior

Output:

- at least one existing Phase 1/Gen4 subsystem runs in Phase 3A skeleton under tests

## 6. Two-Week KPIs

Two-week KPIs:

1. unified execution roadmap approved
2. local kernel boundary spec v0.1 frozen and reviewed
3. at least one Phase 1/Gen4 subsystem runs inside Phase 3A skeleton
4. all existing Gen4 tests still pass
5. new local kernel boundary tests pass
6. no external calls or networking imports introduced
7. at least one fail-closed execution path is observable under test
8. trace output exists for both accepted and rejected local decisions

## 7. Local Kernel Boundary Enforcement

Boundary enforcement requirements:

- explicit zero-network surface check
- no HTTP/RPC/socket imports
- no distributed runtime behavior
- no external side effects
- no CLI mutation command expansion
- no hidden authority path
- no implicit trust path

## 8. Phase 1 Core Migration / Validation Strategy

Current module areas:

- `core/gen4/trust-envelope`
- `core/gen4/membership`
- `core/gen4/federation`
- `core/gen4/sovereign-node`

Migration strategy:

- reuse existing validators where available
- do not rewrite stable validators unnecessarily
- wrap existing validators into local execution path
- use tests to reveal mismatch between documents and executable behavior

## 9. Test & Regression Strategy

Required test coverage:

- local intent accepted path
- local intent rejected path
- missing human authorization reference rejection
- invalid trust envelope rejection
- scope mismatch rejection
- rejected action emits trace
- accepted action emits trace
- deterministic replay
- zero-network import/surface check
- existing Gen4 tests remain green

## 10. Risks & Mitigations

Risks:

- Phase 2 documentation expansion consumes team time
- local-only boundary drift
- implicit networking/sync assumptions
- consolidation stalls without owner/deadline
- validator-doc mismatch
- developer confusion from too many RD/GATE docs

Mitigations:

- freeze recursive RD/GATE expansion
- appoint roadmap/consolidation owner
- set short deadline for consolidation
- prefer tests over new governance abstractions
- make local kernel skeleton the next proof target

## 11. Acceptance Criteria

Roadmap acceptance criteria:

- roadmap approved
- recursive RD/GATE expansion paused
- local-only boundary accepted
- first 3 workstreams defined
- 2-week KPIs accepted
- forbidden scope explicit
- Phase 3A implementation prep can begin
- federation runtime remains not approved

## 12. Final Determination

Final determination:

- `Next Best Move = CONSOLIDATE + START LOCAL KERNEL`
- `Phase 3A Local-Only Implementation Prep = ACTIVE`
- `Recursive RD/GATE Expansion = FROZEN`
- `Federation Runtime Implementation = NOT APPROVED`
- `Networking/Distributed Sync = FORBIDDEN`

## 13. Authorization Statement

This document defines Phase 3A local-only execution roadmap posture only and does not authorize federation runtime implementation.
