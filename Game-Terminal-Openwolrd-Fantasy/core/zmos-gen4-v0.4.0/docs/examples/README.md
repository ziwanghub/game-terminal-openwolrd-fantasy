# Examples Guide — Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"

This guide explains how to use templates in `docs/examples/` for onboarding and operations.

## Files in This Folder

- `truth.contract.json` — reference structure for truth contract payload
- `incident-report-template.md` — incident documentation template for block events
- `migration-checklist.md` — migration execution checklist from v1.5 to v2.0

## How to Use Each Template

### 1) `truth.contract.json`

Use as a structural reference when validating required fields and field intent.

Recommended workflow:

1. Run `zcl schema validate` first.
2. Run `zcl truth build` to generate real contract from runtime state.
3. Compare generated output against this example for readability and field completeness.

Do not copy this example directly into production state files.

### 2) `incident-report-template.md`

Use this template every time a hard block or critical drift event is triggered.

Recommended workflow:

1. Capture command, verdict, reason, and contract hash immediately.
2. Attach `zcl status` and `zcl preflight` evidence.
3. Record root cause and corrective actions.
4. Close incident only after recovery checklist is fully complete.

### 3) `migration-checklist.md`

Use as a gate-by-gate migration tracker during v1.5 to v2.0 transition.

Recommended workflow:

1. Complete sections in order: Foundation → Core Safety → Truth Engine → Integration → Enforcement → Release Readiness.
2. Require explicit sign-off per section.
3. Keep checklist as an artifact in migration PR or release ticket.

## Cautions

- Example files are templates, not authoritative runtime state.
- Always treat schema files and live command outputs as source of truth.
- If command behavior and template differ, update template immediately.
- Never bypass atomic truth write path by manual edits to `truth.contract.json`.

## Best Practices

- Version templates with the same cadence as enforcement policy changes.
- Link incident reports to trace evidence and commit SHA.
- Add new examples when introducing new block conditions or gate rules.
- Review examples in every release readiness checkpoint.
