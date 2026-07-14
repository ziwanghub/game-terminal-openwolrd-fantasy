# Z-MOS SDK Overview

The Z-MOS SDK provides a **Thin Governance Access Layer** that allows external projects, agents, and tooling pipelines to securely embed the Z-MOS Enforcer Engine.

## Core Philosophy

1. **Host Safety First**: The SDK operates via `child_process.spawnSync` to ensure that Z-MOS's aggressive `process.exit()` enforcement semantics never accidentally terminate the host application.
2. **No New Authority**: The SDK is strictly an *interface*. It cannot bypass, rewrite, or override the canonical runtime authority (`truth.contract.json`) or intent (`intent.card.json`).
3. **Formal Types**: Fully typed Public Type Contracts (`sdk/types`) give developers discoverable and safe representations of all internal governance concepts.

## Available APIs

- `bootstrapWorkspace`: Syncs and prepares the Z-MOS environment safely.
- `verifyWorkspace`: Executes preflight and strict readiness checks.
- `stabilizeWorkspace`: Pauses and recovers the runtime before critical mutation.
- `statusWorkspace`, `recoverWorkspace`: Convenience wrappers for diagnostic operations.
