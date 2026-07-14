# Z-MOS DEVELOPMENT STANDARD

## Scope
This document defines the baseline engineering standard for projects built on Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial".

## Project Structure Standard
- Keep core code under stable top-level domains: `sdk/`, `core/`, `cli/`, `scripts/`, `tests/`, `docs/`.
- Put integration examples under `examples/`.
- Keep governance/runtime artifacts in `.z-mos/` but treat them as environment state, not product source.
- Keep version constants centralized in `sdk/version.ts`.

## Directory Structure for New Projects
- Recommended application workspace layout:
  - `project/` for product-level docs and deployment artifacts.
  - `app/` for product application code (features, UI/API adapters).
  - `core/` for stable domain/runtime logic.
  - `tests/` for integration and acceptance coverage.
  - `.z-mos/` for runtime state/contracts generated during execution.
- Keep Z-MOS SDK/runtime logic isolated from app feature code to avoid governance bypass.

## GitHub Flow & Branching Strategy
- `main` is always releasable.
- Use short-lived feature/fix branches from `main`.
- Open PRs to `main` with CI passing before merge.
- Use squash or clean linear history, and avoid force-push on shared branches.

## How to Fork / Duplicate this Template
1. Fork repository on GitHub.
2. Clone your fork locally.
3. Update project identity (`README.md`, `package.json`, docs names if needed).
4. Run `npm ci` then `npm test`.
5. Verify CI workflow is enabled in your fork.
6. Start feature work from a new branch.

## Z-MOS Core Usage
- All agent execution paths must go through `runWithIntent()`.
- `intent.card.json` defines allowed scope, tools, actions, and enforcement rules.
- `truth.contract.json` represents runtime truth state and must be validated before execution.
- If truth or intent checks fail, enforce hard-block and do not execute handler logic.

## Commit Convention
- Use Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `ci:`.
- Keep commits atomic and scoped to one concern.
- Use imperative subject line and include body bullets for non-trivial changes.

## Testing & CI Standard
- Local baseline:
  - `npm ci`
  - `npm test`
- CI baseline (stable minimum):
  - install dependencies
  - show tested version
  - run `npm test`
- Keep `verify:all` for controlled/local verification unless CI environment requirements are fully deterministic.

## What Should Be Ignored
Ignore runtime/state artifacts from `.z-mos/` including:
- `.z-mos/truth.contract.json`
- `.z-mos/trace/`
- `.z-mos/advisory/`
- `.z-mos/state/`
- backup and generated runtime files

Do not commit volatile state files unless explicitly required for a reproducible test fixture.

## Agent Workspace Rule
- Agents must operate only inside the assigned target workspace.
- Agents must not read, modify, or execute against the original Z-MOS source repository unless explicitly authorized.
- Treat template/source repository as protected baseline; implementation work must happen in a copied/forked project workspace.
- Any cross-workspace access requires explicit intent scope and operator approval.
