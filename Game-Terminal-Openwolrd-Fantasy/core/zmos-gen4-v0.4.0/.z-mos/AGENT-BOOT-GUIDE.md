# Z-MOS Agent Boot Guide

**Version:** Z-MOS v1.5.0-p0
**Updated:** 2026-04-17
**Audience:** AI agents (Claude, Gemini, Cursor, etc.) operating in a Z-MOS governed project

---

## Read This First

You are operating inside a **Z-MOS v1.5.0-p0** governed project.
Z-MOS provides three layers:

| Layer | Purpose |
|-------|---------|
| **Governance** | Enforces safe mutation, workflow policy, document standards |
| **Operational Memory** | Tracks your current task state, git sync, and handoff context |
| **Coordination** | Enables deterministic handoffs between agents and sessions |

**The canonical entrypoint is:** `.z-mos/entrypoint.json`
Read this file first if you are loading context manually.

---

## Start Here

```sh
# 1. Boot context (run this first, every session)
zcl start

# 2. Check system health
zcl doctor

# 3. Check your working state integrity
zcl verify worktree
```

`zcl start` will tell you:
- Current phase, gate, next safe action
- Whether memory is drifted from Git HEAD
- Whether any blockers exist

---

## Canonical State — What to Read / What to Write

### Read from:
| File | What it contains |
|------|-----------------|
| `.z-mos/entrypoint.json` | System entrypoints — read first |
| `.z-mos/state/project-state.json` | Current phase, active gate, task status |
| `.z-mos/handoff/latest.json` | Next safe action, scope files, resume flag |
| `.z-mos/reports/latest.json` | Latest report output |

### Write via CLI (never edit JSON files directly):
```sh
# Update operational state
zcl state update --phase "Phase X" --task "Task Name"

# Write handoff with scope declaration
zcl handoff write --next-action "what to do next" \
  --scope "cli/commands/scope.ts,core/git.ts" \
  --safe-to-resume true

# Write a report
zcl report [options]
```

---

## zcl Command Quick Reference

```sh
zcl start                            # Boot context — run first
zcl doctor                           # Full system diagnostic
zcl status                           # Compact status summary
zcl verify worktree                  # Git sync + handoff + scope validation
zcl validate scope                   # Scope drift check only
zcl state update --phase X --task Y  # Stamp operational state
zcl handoff write --next-action "..." --scope "a.ts,b.ts"
zcl handoff validate                 # Validate handoff schema
zcl context build --mode=minimal     # Build minimal AI context
zcl trace verify                     # Verify trace integrity
zcl hooks install                    # Install pre-commit hook (optional)
```

---

## Reporting Standards

| What | Canonical? |
|------|-----------|
| `.z-mos/state/project-state.json` | ✅ CANONICAL — machine-readable |
| `.z-mos/handoff/latest.json` | ✅ CANONICAL — canonical handoff source |
| `.z-mos/trace/runtime-trace.jsonl` | ✅ CANONICAL — append-only audit trail |
| Markdown session notes | ⚠️ COMPATIBILITY ONLY — not parsed by system |
| Conversational summaries | ⚠️ COMPATIBILITY ONLY — for human readers |

**Rule:** Always write state and handoff via CLI commands, not by editing JSON directly.
**Rule:** Markdown notes are acceptable for human readability but are not the source of truth.

---

## Before Handing Off

Run this before ending your session or passing to another agent:

```sh
# 1. Verify worktree is clean
zcl verify worktree

# 2. Stamp current state
zcl state update --phase "Current Phase" --task "Last completed task"

# 3. Write handoff with scope
zcl handoff write \
  --next-action "What the next agent should do" \
  --scope "files,you,touched.ts" \
  --safe-to-resume true
```

---

## If You See Drift Warnings

`zcl start` or `zcl verify worktree` warns about Git drift:

```sh
# Re-sync state to current HEAD
zcl state update

# Re-sync handoff to current HEAD
zcl handoff write --next-action "your next action"
```

If scope drift is detected:
```sh
# Review which files are outside scope
zcl validate scope

# Update scope in handoff if the extra files are intentional
zcl handoff write --next-action "..." --scope "all,files,including,new,ones.ts"
```

---

## Z-MOS is Warning-First

Z-MOS produces warnings, not hard blocks, for scope drift and sync issues.
You can proceed with caution — but you should understand why the warning exists
before continuing. Ignoring drift warnings repeatedly leads to context corruption.
