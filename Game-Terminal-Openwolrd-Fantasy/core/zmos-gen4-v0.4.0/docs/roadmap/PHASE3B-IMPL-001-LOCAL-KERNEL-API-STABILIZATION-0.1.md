# Phase 3B IMPL-001 Local Kernel API Stabilization

- Version: `0.1`
- Status: Draft
- Date: `2026-05-29`
- Scope: `core/gen4/local-kernel/**`, `core/gen4/index.ts`, `tests/gen4/local-kernel.*.test.ts`

## API Surface Map

Public API (`core/gen4/local-kernel/index.ts`):

- `runLocalIntent`
- `createLocalTraceWriter`
- `replayLocalTraceRecords`
- `buildLocalEvidencePackage`
- `LOCAL_KERNEL_ERROR_CODES`
- `LocalKernelValidationError`
- public types:
  - `LocalIntent`
  - `LocalDecisionResult`
  - `LocalDecisionStatus`
  - `LocalInvariantViolation`
  - `LocalHarnessOptions`
  - `LocalTraceRecord`
  - `LocalTraceWriter`
  - `LocalReplayResult`
  - `LocalReplayStatus`
  - `LocalEvidencePackage`
  - `LocalEvidencePackageStatus`

Internal-only API (not re-exported from barrel):

- `validateLocalIntent` (`harness.ts`)
- `createLocalDecisionResult` (`decision.ts`)

## Public/Internal Export Review

- local-kernel barrel now exports explicit public contracts instead of wildcard export.
- `validateLocalIntent` and `createLocalDecisionResult` remain available for direct module tests, but are treated as internal helpers.
- Gen4 root export remains unchanged and still exposes `LocalKernel` namespace only.

## Compatibility Review Summary

- No runtime behavior changes introduced.
- Existing tests continue to validate full local path:
  - intent -> trust enforcement -> decision -> trace -> replay -> evidence.
- Public API posture is now clearer and less prone to accidental coupling.

## Readonly Return Posture Notes

- Current runtime immutability is strongest on evidence package (deep-freeze).
- Decision/trace/replay return immutability hardening is deferred to `PHASE3B-IMPL-002`.

## Invariant Error Structure Notes

- Structured error model remains centralized in `LOCAL_KERNEL_ERROR_CODES`.
- Replay/evidence contracts remain deterministic and fail-closed.
