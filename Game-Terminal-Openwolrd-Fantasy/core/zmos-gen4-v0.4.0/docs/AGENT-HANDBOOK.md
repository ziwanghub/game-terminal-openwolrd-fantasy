# AGENT-HANDBOOK.md
Mandatory quick-start handbook for every AI Agent in this repository.

## Project Context
- Project: `zmos-gen4-v0.4.0`
- Runtime: `ZMOS Gen4 v0.4.0 "Controlled Trial"`
- Phase: `PHASE 5 — AGENT-GOVERNANCE-001`
- Authorities: `.z-mos/truth.contract.json` + `.z-mos/intent.card.json`
- Version source of truth: `sdk/version.ts`

## Current Status
- `runWithIntent()` is delivered, exported, and integration-tested on Gen4 local runtime baseline.
- Hard-block governance is active.

## Non-Negotiable Rules
1. Validate truth + intent before any mutation.
2. ทุกการกระทำต้องผ่าน `runWithIntent()`.
3. Never bypass hard-block conditions.
4. Mutate only files in active intent scope.
5. Stop immediately on truth/intent conflict.
6. Provide verification evidence before completion claims.

## Standard Start Response (New Agent)
`ZMOS Gen4 v0.4.0 Controlled Trial — AGENT-HANDBOOK LOADED. PHASE 5 ACTIVE.`

## Required Reading
- `docs/AGENT-HANDBOOK.md`
- `docs/COMMUNICATION-STANDARD.md`
- `docs/intent-card-spec.md`
- `docs/roadmap/ZMOS-GEN4-STATUS-0.4.0.md`
- `sdk/types/intent-card-v3.0.1.ts`
