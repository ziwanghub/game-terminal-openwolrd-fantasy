# TLS Extraction Flow — Project to Template
**Version:** 1.0
**System:** Z-MOS v1.4.0

---

## Purpose

This document defines how to extract a reusable template from a completed project.

Extraction transforms:
```
Project (client-specific, stateful)  →  Template (generic, stateless)
```

---

## Extraction Steps

### Step 1 — Remove Client Data
Remove all client-specific information:
- Client names, contact info, addresses
- Real bookings, transactions, customer records
- Any PII (Personally Identifiable Information)

Replace with placeholder/example data in `config.default.json`.

### Step 2 — Remove Secrets
Remove all environment-specific secrets:
- API keys (LINE, Firebase, Stripe, etc.)
- Service account JSON files
- `.env` file contents
- OAuth tokens or credentials

Verify: `grep -r "sk_" "AIza" "PRIVATE_KEY"` returns zero matches.

### Step 3 — Normalize Config
Create `config.default.json` with:
- Generic shop name (e.g., "Sample Spa")
- Placeholder branding (neutral colors)
- Example services with sample pricing
- All features set to package-appropriate defaults

Config must pass `config.schema.json` validation.

### Step 4 — Isolate Reusable Logic
Move reusable source code to `src/`:
- Component code (React/Vue/etc.)
- Styling (CSS/Tailwind)
- Utility functions
- Page layouts

Exclude:
- Project-specific hooks or integrations
- Hardcoded paths or URLs
- Environment-specific Firebase config

### Step 5 — Create template.json
Create the template manifest with:
- `name`: unique kebab-case identifier
- `version`: start at `1.0.0`
- `type`: landing / booking / admin / member / bundle
- `status`: `tested` or `proven` (based on evidence)
- `created_from_project`: reference to origin project
- All required fields per `template.schema.json`

### Step 6 — Assign Status
| Condition | Status |
|-----------|--------|
| Built but only tested in dev | `tested` |
| Used with 1 real client, QA passed | `proven` |
| Used with ≥2 clients, no P1 issues | `stable` |

### Step 7 — Register in Registry
Add entry to `template-registry.json`:
```json
{
  "name": "landing-premium-spa",
  "version": "1.0.0",
  "type": "landing",
  "status": "proven",
  "path": "templates/landing/premium-spa-v1",
  "compatible_with": ["booking-standard-v1"]
}
```

---

## Extraction Checklist

```
□ All client data removed
□ All secrets removed
□ config.default.json created and passes schema
□ template.json created and passes schema
□ Source code isolated in src/
□ README.md written
□ preview.png captured
□ Status correctly assigned
□ Registered in template-registry.json
□ No P1 bugs remain
```

---

## Who Can Extract

Extraction should be performed by the agent(s) who built the original project, as they have the most context on what is client-specific vs. reusable.

Extraction is a **TIER 2** operation (async approval required).
