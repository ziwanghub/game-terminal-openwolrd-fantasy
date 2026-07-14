# Introduction — Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"

## What Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial" Is

Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial" is a deterministic governance engine that moves the system from advisory behavior to strict enforcement.

## Core Principles

- Single Source of Truth (`truth.contract.json`)
- Fail-Closed behavior (unknown state means stop)
- Minimal human input via `intent.card.json`
- Verifiable execution trace via `trace-integrity.jsonl`

## Authority Model (Current)

- `.z-mos/truth.contract.json` = canonical runtime authority
- `.z-mos/intent.card.json` = canonical execution intent

## Enforcement Model

Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial" validates scope, environment, and gate dependencies before allowing protected operations.
