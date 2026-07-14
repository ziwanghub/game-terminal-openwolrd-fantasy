# TLS Overview — Template Library System
**Version:** 1.0
**System:** Z-MOS v1.4.0

---

## What is TLS?

TLS (Template Library System) is Z-MOS's **blueprint storage** for proven, reusable system components.

TLS stores templates and modules that have been:
- Built in real projects
- Validated through QA
- Stripped of client-specific data
- Made reusable for future deployments

## TLS is NOT:

- ❌ Not a project workspace
- ❌ Not a code dump
- ❌ Not a place for client data or secrets
- ❌ Not for experimental/unproven code

## Structure

```
tls/
├── templates/       ← Proven UI/page blueprints
│   ├── landing/     ← Landing page templates
│   ├── booking/     ← Booking system templates
│   ├── admin/       ← Admin dashboard templates
│   ├── member/      ← Member area templates
│   └── bundles/     ← Pre-combined template sets
│
├── modules/         ← Reusable logic modules
│   ├── auth/        ← Authentication (LINE OAuth, etc.)
│   ├── payments/    ← Payment processing
│   ├── notifications/ ← LINE messaging, email
│   └── scheduling/  ← Appointment scheduling
│
├── registry/        ← Governance index/catalog of templates & modules (current phase)
│   ├── template-registry.json
│   └── module-registry.json
│
├── schemas/         ← Validation schemas
│   ├── template.schema.json  ← Template manifest validation
│   ├── module.schema.json    ← Module manifest validation
│   └── config.schema.json    ← Client config validation
│
└── docs/            ← TLS documentation
    ├── TLS-OVERVIEW.md
    ├── TLS-RULES.md
    └── TLS-EXTRACTION.md
```

## Template Standard

Every template directory must contain:

```
template-name/
├── template.json        ← Manifest (REQUIRED — must pass schema validation)
├── config.default.json  ← Default config values
├── README.md            ← Usage documentation
├── preview.png          ← Visual preview
└── src/                 ← Reusable source code (canonical)
```

Legacy compatibility:
- `app/` is temporarily allowed for extracted legacy templates during transition
- New/updated template standards should use `src/`

## Status Lifecycle

```
draft → tested → proven → stable → deployable → deprecated
```

| Status | Meaning |
|--------|---------|
| draft | Design only, not yet built |
| tested | Built and tested in dev |
| proven | Used with real client, QA passed |
| stable | Used in ≥2 projects, battle-tested |
| deployable | Ready for `zcl tls create` auto-create flow |
| deprecated | Superseded, do not use for new projects |

## Category Canonical Mapping

- Canonical template type enum: `landing | booking | admin | member | bundle`
- Canonical folder mapping: type `bundle` is stored under `tls/templates/bundles/`

## How TLS Connects to Z-MOS

```
TLS (blueprints)  →  copy to project  →  project .z-mos/ (runtime)
                  ↑                    ↓
           never modified         config overlay applied
```

TLS provides the blueprint. The project provides the runtime state and client config.
