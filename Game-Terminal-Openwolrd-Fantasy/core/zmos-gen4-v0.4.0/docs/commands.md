# Commands Reference — Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"

Z-MOS CLI (`zcl`) provides the operational interface for the Enforcer Engine. All commands execute within the governance and enforcement policies defined by the system.

## Core Lifecycle & Context

- `zcl start`: Boot context and memory status. Evaluates the truth contract and determines if execution is safe.
- `zcl status`: Show current truth mode, drift status, verdict, and contract hash.
- `zcl doctor`: Full system diagnostic, including canonical integrity, trace health, and policy alignment.
- `zcl init`: Initialize a new Z-MOS workspace structure.
- `zcl next`: Suggest the next safe action based on current state.
- `zcl help [<command>]`: Show usage information.

## Macro Operations (Orchestration)

- `zcl sync`: Sync and prepare the system end-to-end (`truth build` → `schema validate` → `clear-stale-locks` → `preflight`).
- `zcl recover`: Recover system from interrupted or stale states (`clear-stale-locks` → `schema validate` → `truth build` → `doctor`).
- `zcl stabilize`: Stabilize runtime before critical work (`truth build` → `schema validate` → `clear-stale-locks` → `doctor`).

## Truth & Enforcement

- `zcl truth build`: Build or rebuild the `truth.contract.json` using an atomic write strategy and schema validation.
- `zcl preflight [--check-command=<cmd>]`: Run the 5-state verification checks (code, runtime, env, data, asset).
- `zcl schema validate`: Validate all Z-MOS internal schemas and configurations. Fail on invalid.
- `zcl intent init [--force]`: Generate a new `intent.card.json` template and bind it to the current truth snapshot.

## Operational State & Memory

- `zcl state update --phase <phase> --next-action <action> --blocker <none>`: Stamp the operational project state.
- `zcl state init [--force]`: Initialize project state.
- `zcl handoff write --safe-to-resume <true|false> --next-action <action>`: Write a handoff packet (Legacy, transitioning to intent card).
- `zcl handoff validate`: Validate current handoff packet.
- `zcl handoff init [--force]`: Initialize handoff state.
- `zcl memory init [--force]`: Initialize the complete memory structure.

## Trace & Audit

- `zcl trace verify [--json]`: Verify the append-only integrity of the runtime trace (SHA-256 chain).
- `zcl trace query [--status <status>] [--command <cmd>] [--result-class <class>] [--last <n>] [--since <date>] [--json]`: Query trace records.
- `zcl trace summary`: Display an aggregated summary of recent trace activity.
- `zcl behavior record`: Record specific behavioral decisions into the trace log.
- `zcl metrics record`: Record execution or operational metrics.

## Scope & Worktree

- `zcl verify worktree`: Verify git synchronization and scope drift.
- `zcl validate scope`: Validate current changes against the scope guard policy.
- `zcl scope guard`: Explicitly execute the scope guard evaluation (strict/advisory).

## Governance & Workflows

- `zcl workflow list`: List all supported workflows defined in the policy.
- `zcl workflow coverage-check`: Check if the workflow policy covers all required system workflows.
- `zcl workflow runtime-check`: Execute runtime policy validation.
- `zcl workflow advisory-check`: Execute advisory policy validation.
- `zcl run-gate <gate_id>`: Run a specific execution gate and its required checks.

## Lane & Coordination

- `zcl lane claim --task-id <id> --lane <lane> --actor <id>`: Claim an operational lane.
- `zcl lane release --task-id <id> --actor <id>`: Release a claimed lane.
- `zcl lane lock-path --task-id <id> --lane <lane> --actor <id> --path <glob>`: Lock a specific path for mutation.
- `zcl lane lock-artifact --task-id <id> --lane <lane> --actor <id> --artifact <id>`: Lock an artifact.
- `zcl lane handoff --task-id <id> --to-lane <lane> --actor <id> --summary <text>`: Handoff a lane to another actor.
- `zcl lane ack --task-id <id> --actor <id>`: Acknowledge a lane handoff.

## Context & Budget

- `zcl context init / show / update / invalidate`: Manage AI task context boundaries.
- `zcl budget evaluate / profile / status`: Manage and track execution token/cost budgets.

## Template Lifecycle System (TLS)

- `zcl tls create / install / update / list / show / validate / sync / uninstall`: Manage standardized templates and boilerplates.

## Document Governance

- `zcl doc:check`: Verify document schema, naming, and structural integrity.
- `zcl doc:index [--type=<type>]`: Generate a structured index of documentation.
- `zcl doc:doctor`: Full diagnostic of the documentation subsystem.

## AI Integration

- `zcl ai test / run / status`: Execute or test AI-driven runs within governed boundaries.
- `zcl ai context build`: Build minimal or full AI context bundles for external agents.

## Core Operations

- `zcl core doctor`: Deep diagnostic of the Z-MOS core engine itself.
- `zcl core clean / restore`: Manage internal engine state.
- `zcl runtime lock-status / clear-stale-locks`: Manage runtime execution locks.
- `zcl load-data`: Load structured context bundles.
- `zcl migrate`: Migrate from legacy Z-MOS versions.
- `zcl report`: Generate standardized operational reports.
- `zcl hooks install`: Install Z-MOS git hooks.

---

## Exit Codes

All `zcl` commands adhere to standard POSIX exit semantics combined with Z-MOS fail-closed principles:

- `0`: Success / Safe to continue. The operation passed all governance checks.
- `1` (or non-zero): Blocked, invalid, drift detected, or verification failure. Execution must halt.

## Enforcement Behavior

In v0.4.0 "Gen4 Controlled Trial", commands are bound by the **Truth-First** enforcement model:

1. Operations that mutate state or evaluate conditions will first read `.z-mos/truth.contract.json`.
2. If the truth contract verdict is `STOP_AND_REPAIR`, commands will exit non-zero immediately.
3. Bypassing CLI commands to manually edit state files circumvents trace logging and will result in integrity verification failures (`zcl trace verify`).
