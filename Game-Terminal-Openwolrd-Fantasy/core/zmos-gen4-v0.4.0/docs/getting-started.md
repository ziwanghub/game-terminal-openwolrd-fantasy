# Getting Started — Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"

## Prerequisites

- Node.js runtime installed
- Project dependencies installed
- Repository initialized with `.z-mos/` v2.0 structure

## Quick Start

The fastest way to safely initialize and verify your runtime environment is to use the synchronization macro:

```bash
zcl sync
```

This macro orchestrates:
1. `zcl truth build`
2. `zcl schema validate`
3. `zcl runtime clear-stale-locks`
4. `zcl preflight`

To recover from an interrupted or stale state:

```bash
zcl recover
```

To stabilize your runtime before critical work:

```bash
zcl stabilize
```

## Expected Outcome

The system should run in truth-first mode with clear verdict output, displaying execution steps sequentially via the macro orchestrator.

## Runtime Authority Notes

- Runtime decisions are derived from `.z-mos/truth.contract.json` (canonical runtime authority).
- Task intent is derived from `.z-mos/intent.card.json` (canonical execution intent).
