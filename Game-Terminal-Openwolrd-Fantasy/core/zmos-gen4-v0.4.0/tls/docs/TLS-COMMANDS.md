# TLS CLI Commands (Phase 1)
**Namespace:** `zcl tls ...`  
**Scope:** Safe inspection, validation, sync reporting, and controlled library mutations

---

## Commands

### `zcl tls create --template <path> --config <file> --output <dir>`
Project generation command. Existing behavior preserved.

### `zcl tls install --source <path> --type <type> --name <name> [--dry-run] [--force]`
Install a template source directory into TLS library destination:
- destination: `tls/templates/<type>/<name>` (`bundle` stored under `bundles`)
- validates source structure and template manifest before install
- refuses overwrite by default
- `--force` allows overwrite
- updates `tls/registry/template-registry.json` only after filesystem install succeeds
- `--dry-run` reports planned actions without mutation

### `zcl tls update --name <name> --source <path> [--dry-run] [--force]`
Controlled template evolution command (not equivalent to `install --force`):
- requires target template to already exist in TLS
- validates source structure before mutation
- enforces identity compatibility (`name`, `type`) with existing template
- enforces version transition rules:
  - downgrade: blocked
  - major update: requires `--force`
  - same-major update: allowed
- dry-run reports:
  - files to replace
  - version transition
  - registry impact
- apply mode:
  - replaces template files
  - updates registry metadata
  - logs update trace (old/new version, change type, source path)
  - applies rollback on failure

### `zcl tls list [--type=<type>] [--status=<status>] [--json]`
List templates discovered from filesystem under `tls/templates/**/template.json`.

Output fields:
- `name`
- `type`
- `version`
- `status`
- `path`

### `zcl tls show <name>`
Show `template.json` details for a template resolved by:
- manifest `name`
- template folder name
- relative template path

### `zcl tls validate <name>`
Validate one template using:
- manifest contract checks
- template schema required-field checks (when schema is readable)
- required file structure checks
- type-to-folder policy checks

### `zcl tls sync`
Safe drift report between:
- filesystem templates (`tls/templates/**/template.json`)
- `tls/registry/template-registry.json`

Reports:
- missing in registry (should add)
- missing on filesystem (registry stale)
- mismatched entries (should update)

Mutation flags (`--apply`, `--write`) are intentionally rejected in Phase 1.

### `zcl tls uninstall <name> [--dry-run] [--force]`
Uninstall a template from TLS library:
- validates safe path inside `tls/templates`
- blocks protected roots (`tls/`, `tls/templates/`, `tls/modules/`)
- blocks uninstall when live usage evidence exists (`customer_live_status=live|feedback-loop`)
- removes template directory and cleans registry entry when present
