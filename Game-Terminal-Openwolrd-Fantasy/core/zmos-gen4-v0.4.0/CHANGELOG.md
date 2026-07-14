# Changelog

## v3.0.0 "Purity"

- **SDK Readiness**: Transformed Z-MOS into an embeddable governance runtime by introducing a Thin Governance Access Layer (`sdk/index.ts`).
- **Stable Runtime APIs**: Added `bootstrapWorkspace`, `verifyWorkspace`, and `stabilizeWorkspace` for secure integration via `child_process.spawnSync`.
- **Public Type Contracts**: Introduced fully typed Formal Interfaces for `TruthContract`, `IntentCard`, and `TraceRecord`.
- **Trace Scaling**: Implemented Atomic Trace Rotation and Segmented Verification with stream hashing (`O(1)` memory) for infinite scale audit integrity.
- **User Guide**: Published a comprehensive User Guide covering CLI and SDK usage.
## v3.0.0 "Purity"

- **Architectural Purification**: Completed the transition to a 100% Pure Truth-First Enforcement Runtime.
- **Removed Legacy Dependencies**: Permanently deleted all code, runtime paths, and dual-reads related to `session.json`, `project-state.json`, and `handoff/latest.json`.
- **Core CLI Cleanup**: Removed legacy probing from `zcl start` and `zcl status`; completely deleted the `zcl handoff` command.
- **Verification Integrity**: Removed Core K (Session Fallback) tests and aligned the verification suite to strict, truth-first constraints.
- **Docs Alignment**: Updated migration guide and architecture docs to strictly prohibit legacy fallback.
## v3.0.0 "Purity"

- Finalized Pure Truth-First enforcement baseline.
- Removed residual runtime legacy references for `session.json` and `handoff/latest` in core runtime scopes.
- Canonical consistency migrated to `core/truth-consistency.ts`.
- Added truth runtime snapshot path (`core/truth-runtime.ts`) for readiness/workflow integration.
- `state-integrity.ts` now treats `truth.contract.json` as primary canonical source with controlled fallback semantics.
- `zcl init` no longer generates legacy session artifact.
- `verify:core` passes (11/11).
- `verify:production-readiness --profile=strict` returns GREEN.
- Version baseline set to `v3.0.0 "Purity"`.
