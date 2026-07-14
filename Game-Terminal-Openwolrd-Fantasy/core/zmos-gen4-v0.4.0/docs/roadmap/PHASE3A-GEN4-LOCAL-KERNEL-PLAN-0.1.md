# Phase 3A Local Sovereign Kernel Plan

- Document Code: `PHASE3A-GEN4-LOCAL-KERNEL-PLAN`
- Version: `0.1`
- Status: Draft
- Date: `2026-05-28`
- Basis:
  - `PHASE2-GEN4-CONSOLIDATION-PLAN-0.1.md`
  - `GEN4-P1-009-0.1.md`
  - `core/gen4/**`
  - `tests/gen4/**`

## 1. Purpose of Phase 3A Local Sovereign Kernel

Define the smallest safe implementation-entry scope for ZMOS Gen4 that proves sovereignty enforcement in executable local-only form.

This plan shifts priority from governance recursion to executable invariant validation while preserving fail-closed and anti-drift discipline.

## 2. Phase 3A Boundary Model

Phase 3A boundaries:

- local-only
- fail-closed
- anti-drift
- non-federated runtime execution
- non-networked
- non-adaptive
- non-autonomous

Boundary clarifications:

- federation runtime implementation remains not approved
- networking/distributed sync remains forbidden
- runtime execution scope is strictly single-node local kernel validation

## 3. Minimum Useful Sovereign Kernel Definition

Minimum useful kernel is a single local node execution path that can:

1. receive local intent
2. load or construct trust envelope context
3. enforce authority and scope constraints
4. reject invalid intent fail-closed
5. emit append-only trace for accepted and rejected outcomes
6. replay trace deterministically to same result

Why this is sufficient now:

- it validates sovereignty kernel behavior with executable evidence before any federation expansion

## 4. Local Sovereign Execution Path

Planned local execution path:

1. intake local intent payload
2. resolve local authority context and trust envelope metadata
3. run local validators (authority/scope/membership/trust constraints)
4. produce decision (accept or reject) under fail-closed rules
5. emit structured local trace event
6. update local evidence package state model for audit/replay

Execution priority:

- ugly-but-working local runtime is acceptable
- executable enforcement is higher priority than additional recursive governance abstraction

## 5. Trust Envelope Enforcement Requirements

Trust envelope enforcement in Phase 3A must include:

- authority ownership presence and explicitness checks
- human authorization reference requirement checks
- scope-bound action/resource checks
- invalid/stale/revoked trust fail-closed checks
- no hidden authority source acceptance

Requirement outcome:

- trust envelope semantics must be directly observable in local execution outcomes and trace evidence

## 6. Fail-Closed Execution Requirements

Fail-closed requirements:

- missing authority or authorization evidence -> reject
- invalid trust envelope linkage -> reject
- out-of-scope intent -> reject
- unresolved verification ambiguity -> reject
- reject path must still emit trace evidence

Execution discipline:

- no implicit pass path
- no silent escalation path
- no best-effort partial acceptance path

## 7. Immutable Trace & Replay Requirements

Trace requirements:

- append-only trace writer for all decisions
- trace entries for accepted and rejected actions
- explicit references to authority/trust/intent/evidence context
- deterministic replay over trace stream

Replay requirements:

- identical trace input must produce identical replay outcome
- replay mismatch is treated as fail-closed diagnostic failure

## 8. Required Invariants To Encode In Code

Required invariants for immediate encoding in code/tests:

- no hidden authority
- no self-delegation
- intent scope must remain within trust envelope allowed scope
- missing human authorization reference must fail closed
- invalid/stale/revoked trust must fail closed
- trace must be append-only
- rejected actions must emit trace evidence
- replay must be deterministic

## 9. Explicitly Forbidden Scope

Forbidden in Phase 3A:

- networking
- federation transport
- multi-node synchronization
- consensus
- distributed runtime behavior
- adaptive governance runtime
- autonomous AI decision layer
- production runtime deployment

Global posture:

- `Federation Runtime Implementation = NOT APPROVED`
- `Networking/Distributed Sync = FORBIDDEN`

## 10. Initial Validation & Test Strategy

Initial validation strategy:

- add local execution harness tests for accept/reject path
- add invariant-focused fixture tests for authority/scope/trust failures
- add trace emission tests for both success and failure decisions
- add deterministic replay tests across mixed accepted/rejected traces
- keep existing Phase 1/Gen4 validator and simulation tests green

Definition of useful progress:

- local kernel path runs end-to-end under test
- fail-closed behavior is observable and repeatable
- replay determinism is test-proven

## 11. Risks & Engineering Concerns

- under-specified integration edges between validators and local harness
- potential mismatch between governance semantics and executable behavior
- trace model adjustment may be required after first executable iteration
- local kernel may reveal simplification opportunities in current governance language

Why this is still the right move:

- implementation feedback is now more valuable than additional recursive governance documents
- executable proof reduces paper-architecture risk

## 12. Phase 3A Entry Criteria

Phase 3A entry criteria:

- Phase 2 consolidation posture accepted
- recursive RD/GATE expansion frozen
- local-only boundaries and forbidden scope explicitly accepted
- invariant list approved for immediate code/test encoding
- team alignment on non-networked, non-federated execution focus

## 13. Final Determination

Final determination:

- `Phase 3A Local-Only Implementation Prep = RECOMMENDED`
- `Federation Runtime Implementation = NOT APPROVED`
- `Networking/Distributed Sync = FORBIDDEN`

Execution direction:

- begin local kernel implementation preparation immediately
- defer any federation runtime expansion until local kernel proof is complete

## 14. Authorization Statement

This document defines local-only sovereign kernel preparation posture only and does not authorize federation runtime implementation.
