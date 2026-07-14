# Phase 1 GEN4 Constraints

- Document Code: `PHASE1-GEN4-CONSTRAINTS`
- Version: `0.1`
- Status: Phase 1 Controlled Core Constraint Definition
- Purpose: Define the Phase 1 controlled core implementation boundaries for Z-MOS Gen 4 and prevent scope expansion beyond a local deterministic governance foundation.

## 1. Purpose

Phase 1 is a Local deterministic governance core foundation.

This phase is explicitly not a full distributed federation runtime.
Phase 1 work is limited to local core types, validators, transition rules, and deterministic validation behavior.

## 2. Allowed Scope

The following implementation elements are permitted in Phase 1:

- core types
- local validators
- deterministic transition rules
- fixture-based tests
- static validation
- side-effect-free logic

## 3. Forbidden Scope

Phase 1 must not introduce any of the following:

- networking
- distributed sync
- consensus
- adaptive governance runtime
- runtime mutation
- `.z-mos/` mutation
- CLI federation command
- background daemon
- cross-node communication
- self-modifying truth

## 4. Required Invariants

Phase 1 must preserve these non-negotiable invariants:

- Truth-First Authority
- Zero Hidden Authority
- Fail-Closed Validation
- Explicit Authority Ownership
- Human-Authorized Evolution
- No Self-Authorized Privilege Escalation
- Immutable Evidence

## 5. Current Phase 1 Completed Work

Phase 1 has completed the following work items:

- GEN4-P1-001
- GEN4-P1-002
- GEN4-P1-003
- GEN4-P1-004
- GEN4-P1-005
- GEN4-P1-006

## 6. Phase 1 Exit Criteria

Phase 1 controlled core stage may be exited only when:

- validators are complete
- fixture tests pass
- constraints are documented
- no forbidden scope is introduced
- build/test pass
- review gate passes

## 7. Next Gate

This document is a precursor to:

- `P1-GATE-001 — Phase 1 Controlled Core Review Gate`
