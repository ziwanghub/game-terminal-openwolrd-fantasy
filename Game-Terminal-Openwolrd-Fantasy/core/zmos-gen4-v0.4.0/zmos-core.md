# zmos-core.md — Z-MOS v2.0.0-enforcer Protocol
**Version:** v2.0.0-enforcer (Enforcer Engine)
**Type:** Reusable Core System Protocol
**Last Updated:** 2026-04-16

---

## 1. What Z-MOS EVO Is

Z-MOS v2.0.0-enforcer is the **reusable core engine** that powers Z-MOS governed projects.

It provides:
- CLI runtime (`zcl`)
- Execution loop enforcement
- Trace integrity (SHA-256 hash chain)
- Governance protocol (trust tiers, task identity, QA)
- Workflow policy enforcement
- Session entry gate

EVO is a **system core**, not a project instance.

## 2. What Z-MOS EVO Is Not

- ❌ Not a customer project
- ❌ Not a project template (no customer data, no project-specific state)
- ❌ Not a deployment target
- ❌ Does not carry project runtime memory (`.z-mos/state/`, `.z-mos/trace/`)

Project-specific runtime memory (session state, trace logs, manifest, node identity) belongs inside the **project's own `.z-mos/` directory**, never inside EVO itself.

---

## 3. Session Entry Rule

**Source:** v0.2.x runtime

Every AI agent must establish current state before any work:

```
zcl start
```

Session entry is **READ-ONLY**. Do not mutate canonical state during entry.

Wait for verdict before proceeding:
- **SAFE-TO-CONTINUE** → Proceed with bounded scope
- **CONTINUE-WITH-CAUTION** → List all warnings before any action
- **STOP-AND-REPAIR** → Stop. Report blockers. No changes.

---

## 4. Execution Loop

**Source:** v0.2.x runtime

Every change must complete this full loop:

```
Preflight → Execute → Validate → Verify → Document
```

1. **Preflight:** `zcl preflight` — If blocking → do not execute
2. **Execute:** The intended command or change
3. **Validate:** Check immediate output
4. **Verify:** `zcl trace verify` — If fails → loop is incomplete
5. **Document:** Decision, evidence, remaining risk classified

### Hard Stops
1. Preflight blocking → do not execute any downstream commands
2. Canonical integrity blocking → stop all mutation, recover first
3. Verification fails → loop is incomplete, do not proceed

### Definition of Done
A task is complete only when ALL four are true:
- Execution succeeded
- Verification passed
- Documents updated
- Remaining risk explicitly classified

Missing any one = not done.

---

## 5. Governance Layer

**Source:** v0.3.5 governance

### Trust Tiers
| Tier | Mode | Description |
|------|------|-------------|
| TIER 0 | AUTO | ทำได้เลย (UI/style only) |
| TIER 1 | SELF-APPROVE | ทำ + report หลังเสร็จ |
| TIER 2 | ASYNC | แจ้งก่อน execute ไม่ต้องรอ |
| TIER 3 | MUST APPROVE | รอ approval เสมอ |

### Task Identity Verification
Before executing any task:
1. Read the `Agent:` field in task header
2. Compare with your own name
3. If match → execute
4. If mismatch → stop immediately, report mismatch

### File Ownership
Each agent owns specific paths. Cross-agent commits require diff review.
See: [docs/governance/ownership-matrix.md](docs/governance/ownership-matrix.md)

### Credentials Protocol
No secrets in chat, prompt, log, or commit — ever.
If leaked → rotate immediately.
See: [docs/governance/credentials-protocol.md](docs/governance/credentials-protocol.md)

---

## 6. Communication Standard

**Source:** v0.3.5 governance

Canonical source of truth:
- [docs/standards/ZMOS-COMMUNICATION-STANDARD.md](docs/standards/ZMOS-COMMUNICATION-STANDARD.md)

EVO must follow this 7-system communication model:
1. Unified Task Brief Format
2. Task Identity Verification
3. Standard Report Format (mandatory 5-line header)
4. Suggestion Protocol (separate, approval-required)
5. `@zmos-status` Convention
6. Emergency Protocol
7. Audit Protocol

Minimum non-negotiable rules:
- Every report must include the required 5-line header.
- Task identity verification is mandatory before execution.
- Suggestions must not be self-executed.
- Emergency reporting must preserve handoff continuity.

---

## 7. QA Standard

**Source:** v0.3.5 governance

QA is a Quality Gate, not just testing.
3-layer audit: UI/UX → Project Structure → Console/Network.
QA can block release if Blocking Criteria are met.

See: [docs/qa/qa-standard-v1.md](docs/qa/qa-standard-v1.md)

---

## 7.5. Template Library System (TLS)

**TLS is the single source of truth** for all product-level logic:
- Template definitions (landing, booking, admin, member, bundle)
- Feature control model (dual flag: visible + enabled)
- Config structure (shop-config.json schema)
- Package model (basic / pro / premium)

### Rules
- Z-MOS must use TLS as the source of truth for templates, config, and packages
- ห้าม bypass TLS — template/config/package ต้องอ้างอิง TLS เท่านั้น
- ห้ามเก็บ product logic ใน zmos-core.md — ใช้ TLS docs แทน

### TLS Documentation
- [TLS-OVERVIEW.md](tls/docs/TLS-OVERVIEW.md) — System overview
- [TLS-TEMPLATE-MODEL.md](tls/docs/TLS-TEMPLATE-MODEL.md) — Template layers & lifecycle
- [TLS-FEATURE-CONTROL.md](tls/docs/TLS-FEATURE-CONTROL.md) — Dual flag system
- [TLS-CONFIG-SYSTEM.md](tls/docs/TLS-CONFIG-SYSTEM.md) — Config structure & validation
- [TLS-PACKAGE-MODEL.md](tls/docs/TLS-PACKAGE-MODEL.md) — Package tiers & activation
- [TLS-RULES.md](tls/docs/TLS-RULES.md) — Admission, usage & category rules
- [TLS-EXTRACTION.md](tls/docs/TLS-EXTRACTION.md) — Project → Template extraction

---

## 7.6. TLS Promotion Governance

**Source:** ZMOS-TLS-PROMOTION-POLICY-001

การนำ code จาก Project เข้าสู่ TLS หรือการเลื่อนระดับความน่าเชื่อถือของ Template ต้องเป็นไปตามมาตรฐานกลาง:
- **Sanitization First**: ห้ามนำ code เข้า TLS โดยไม่ผ่านการ Extraction (ลบ Client Data/Secrets)
- **Measurable Promotion**: การเลื่อนระดับสถานะ (Promotion) ต้องอิงตามหลักฐานเชิงประจักษ์ (e.g., ใช้งานจริงกับลูกค้า 1 รายเพื่อเป็น `proven`)
- **Decoupled Lifecycle**: การแก้ไขใน Project ไม่ถือเป็นการแก้ไข Template อัตโนมัติ — ทุกการเปลี่ยนแปลงใน TLS ต้องผ่านการ Validate ใหม่

รายละเอียดนโยบายและขั้นตอน:
- [TLS-PROMOTION-POLICY.md](tls/docs/TLS-PROMOTION-POLICY.md) — หลักการและกฎการเลื่อนระดับ
- [TLS-STATUS-LIFECYCLE.md](tls/docs/TLS-STATUS-LIFECYCLE.md) — นิยามสถานะและเงื่อนไขรายขั้นตอน

---

## 8. Enforcement and Trace Rule

**Source:** v0.2.x runtime (Patch 1 + 1a)

### Trace Integrity
- Every trace entry includes `sequence`, `previous_hash`, `current_hash`
- Hash algorithm: SHA-256 via `node:crypto`
- Hash input: `sequence|timestamp|canonicalized_payload|previous_hash`
- Genesis: sequence = 1, previous_hash = "GENESIS"
- Legacy entries (pre-hash) are skipped by verifier

### Verification Command
```
zcl trace verify [--json]
```

Exit codes:
| Code | Status | Meaning |
|------|--------|---------|
| 0 | valid | Hash chain intact |
| 1 | tampered | Readable entry but hash mismatch |
| 2 | error | Parse failure / IO error / operational failure |

### Trace Verify is mandatory as an integrity step where applicable.

### Workflow Policy Enforcement
- `governance/workflow-policy.ts` loads `.z-mos/workflow-policy.json`
- Mutation and delegation are disallowed by default
- Only whitelisted workflows execute

---

## 9. Runtime State Rule

### Canonical State (Project-level, NOT in EVO)
```
.z-mos/state/runtime-state.json  ← Generated session state (helper/advisory only)
.z-mos/state/trace-integrity.json ← Verification results
.z-mos/trace/runtime-trace.jsonl  ← Append-only trace log
.z-mos/zmos-manifest.json        ← Project identity
.z-mos/node.json                 ← Node identity
.z-mos/workflow-policy.json      ← Workflow governance rules
```

> [!NOTE]
> `.z-mos/state/runtime-state.json` serves exclusively as a generated helper/advisory state.
> The canonical runtime authority resides entirely in `.z-mos/truth.contract.json`, and the canonical execution intent resides in `.z-mos/intent.card.json`.

Do not modify canonical state without authorization.
EVO itself does **not** carry any of these files.

---

## 10. Project Boundary Rule

### EVO ↔ Project Separation
```
zmos-core-evo1.0/     ← Core system (reusable, stateless)
  ├── bin/cli/core/…  ← Engine code
  └── docs/           ← Governance protocol

project-xyz/          ← Project instance (stateful)
  ├── .z-mos/         ← Project runtime memory
  └── src/            ← Project source code
```

- EVO provides the engine
- Project provides the runtime state (`.z-mos/`)
- EVO must never contain project-specific memory
- Project connects to EVO's engine at runtime

---

## Core Principle

> Do not trust memory. Trust current system state.
