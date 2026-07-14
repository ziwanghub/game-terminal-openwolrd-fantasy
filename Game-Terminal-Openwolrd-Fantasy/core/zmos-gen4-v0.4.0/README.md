# zmos-core

**ZMOS Gen4 v0.4.0 "Controlled Trial Foundation"** — Local Sovereign Runtime

`zmos-core` is the canonical engine for Z-MOS, a governance-driven AI development framework that provides evidence-first execution, deterministic memory-bound state, and traceable agent coordination.

---

## What Z-MOS Is

Z-MOS is a file-native operational layer for AI-assisted development. It sits between the human operator and AI agents, enforcing:

- **Governance** — mutation control, workflow policy, scope validation
- **Operational Memory** — truth-first runtime state, intent capture, compatibility artifacts
- **Coordination** — deterministic task execution with traceable governance decisions

Z-MOS is model-agnostic. It works with any AI agent that can read files and run CLI commands.

---

## What Is Canonical

| File | Role |
|------|------|
| `.z-mos/truth.contract.json` | **Canonical runtime authority** |
| `.z-mos/intent.card.json` | **Canonical execution intent** |
| `.z-mos/trace/runtime-trace.jsonl` | Append-only audit trail |
| `.z-mos/zmos-manifest.json` | System identity and policy envelope |

**Always write state via CLI, never by editing JSON directly.**

After Sprint 4, runtime governance is **Pure Truth-First**. Legacy compatibility artifacts have been permanently removed.

## Operational Memory

- Primary runtime authority: `.z-mos/truth.contract.json`
- Primary task intent source: `.z-mos/intent.card.json`
- Supplemental state files may exist under `.z-mos/state/`, but governance decisions are resolved from truth-first authority.

---

## How to Start

```sh
# 1. Sync and prepare environment (Macro)
zcl sync

# 2. Boot context — run every session
zcl start

# 3. Check system health
zcl doctor
```

## Macro Operations (UX Friction Reduction)

To reduce operational complexity, Z-MOS provides macro commands that safely orchestrate multiple core operations:

- `zcl sync`: Prepares the system end-to-end (`truth build` → `schema validate` → `clear-stale-locks` → `preflight`).
- `zcl recover`: Recovers the system from drift or interrupted states (`clear-stale-locks` → `schema validate` → `truth build` → `doctor`).
- `zcl stabilize`: Stabilizes the runtime before critical execution (`truth build` → `schema validate` → `clear-stale-locks` → `doctor`).
# 3. Verify worktree integrity
zcl verify worktree
```

---

## Required Verification Gate

[![verify-strict](https://github.com/ziwanghub/zmos-core-v1.4.0/actions/workflows/verify-strict.yml/badge.svg)](https://github.com/ziwanghub/zmos-core-v1.4.0/actions/workflows/verify-strict.yml)

`verify-strict` is the required gate before merge.

- Run strict verification in sequential mode only.
- Do not run it in parallel with truth/canonical mutation commands.
- Do not use matrix parallelization for strict readiness execution.

Run locally before pushing:

```bash
npm run verify:core
npm run verify:production-readiness:strict
```

If strict readiness fails, rerun the same commands sequentially before debugging deeper.

---

## Branch Protection & Merge Rules

Branch protection is required to enforce `verify-strict` at merge time.

- Configure protected branches for `main` (and `develop` if used).
- Require PR-based merges, approvals, up-to-date branches, and required checks.
- Set `verify-strict` as a required status check.

See:
- [Branch Protection Guide](docs/branch-protection-guide.md)
- [Continuous Deployment & Quality Pipeline Standard](docs/operations/deployment-pipeline.md)

---

## Key CLI Commands

```sh
zcl start                            # Boot context + memory status
zcl doctor                           # Full system diagnostic
zcl status                           # Compact status summary
zcl verify worktree                  # Git sync + scope drift check
zcl state update --phase X --task Y  # Stamp operational state
zcl trace verify                     # Verify append-only integrity
zcl context build --mode=minimal     # Build AI context bundle
```

---

## How It Fits Into a Real Project

Embed `zmos-core` as a governance layer inside an existing project:

1. Copy `.z-mos/` directory into the target project root
2. Run `zcl init` to verify structure
3. Configure `zmos-manifest.json` for the target project
4. Use `zcl start` and maintain `truth.contract`/`intent.card` as operational authority

Z-MOS adds governance — it does not replace your build system, framework, or test infrastructure.

---

## Repository Structure

| Path | Contents |
|------|----------|
| `bin/` | CLI entrypoint (`zcl`) |
| `cli/` | Command implementations |
| `core/` | Runtime helpers (git, state, trace) |
| `contracts/` | Shared schema and contract definitions |
| `governance/` | Readiness, workflow policy engines |
| `tls/` | Template Lifecycle System |
| `docs/` | Changelogs, roadmap, standards |
| `trace/` | Trace schema and integrity logic |
| `.z-mos/` | Live operational memory (state, handoff, trace) |

---

## Version

**Current:** v0.4.0 "Gen4 Controlled Trial" — Local Runtime Hardening Milestone
**Lifecycle:** stabilized-p0 · ready for project embedding

## Release Posture

- Controlled Internal Trial: **AUTHORIZED**
- Production Deployment: **NOT APPROVED**
- Federation Runtime Implementation: **NOT APPROVED**
- Networking / Distributed Sync: **FORBIDDEN**

See legacy changelog and roadmap files in `docs/` for historical context.
