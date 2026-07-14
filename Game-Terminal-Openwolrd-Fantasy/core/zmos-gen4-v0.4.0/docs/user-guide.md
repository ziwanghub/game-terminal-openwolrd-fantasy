# Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial" — User Guide

Welcome to **Z-MOS Gen4 v0.4.0 "Gen4 Controlled Trial"**, the definitive Pure Truth-First Governance Runtime. This release strips away all legacy compatibility mechanisms to deliver a hardened, deterministic, and embeddable architecture for AI development.

---

## 1. Truth-First Principles (Inherited from Purity v3.x)

Gen4 v0.4.0 keeps three uncompromising architectural constraints inherited from legacy Purity v3.x:

1. **Pure Truth-First Authority**: The system's decisions are exclusively governed by `.z-mos/truth.contract.json` (canonical runtime context) and `.z-mos/intent.card.json` (human-driven intent). There are no fallback systems, dual-reads, or legacy session artifacts.
2. **Infinite Scale Audit**: The `runtime-trace.jsonl` utilizes segmented hash checkpoints and atomic file rotation to enable indefinite scaling without dropping records or blowing up memory usage.
3. **Embeddable Thin Governance**: Z-MOS operates strictly as a Thin Governance Access Layer (`zmos-core/sdk`), guaranteeing that host project processes are never hijacked or killed abruptly by unexpected `process.exit()` signals.

---

## 2. Installation & Initialization

You can install Z-MOS within an existing project or initialize a new workspace.

### Installing the CLI and Core:
```bash
npm install -g zmos-core  # For global CLI usage
npm install --save-dev zmos-core  # For local workspace embedding
```

### Initializing the Workspace:
```bash
zcl init
```
This generates the core `.z-mos` folder structure. 

---

## 3. Working with the CLI (zcl)

The CLI acts as the primary operational gateway. It strictly evaluates truth evidence before allowing mutations.

### Recommended Macro Operations

Z-MOS incorporates safe macros that chain essential verifications together:

- **`zcl sync`**: Perfect for beginning a work session. Rebuilds the truth contract, validates the schema, clears stale locks, and runs a full preflight verification.
- **`zcl stabilize`**: Use this immediately before undertaking a critical mutation (e.g., executing a complex feature rollout). It locks the runtime to ensure environmental determinism.
- **`zcl recover`**: If an AI agent loop crashes or a lock is left stale, this macro safely forces the removal of stale lock files and reconstructs the truth evidence from scratch.

### Checking Health
- **`zcl doctor`**: Runs a full diagnostic, covering trace integrity, truth schemas, and drift signals.

---

## 4. Working with the SDK (TypeScript)

For projects that require embedded governance (like AI Agents, monorepo deployment scripts, or CI systems), Z-MOS provides a completely stable, type-safe API.

### Bootstrapping
```typescript
import { bootstrapWorkspace, verifyWorkspace } from "zmos-core/sdk/index.js";

// Initialize the environment securely without risking host termination
const boot = bootstrapWorkspace({ workspaceDir: process.cwd() });
if (!boot.success) {
  console.error("Z-MOS initialization failed:", boot.error);
}
```

### Strict Verification Gates
```typescript
// Enforce strict preflight and drift checks
const verify = verifyWorkspace({ workspaceDir: process.cwd(), strict: true });
if (!verify.success) {
  console.error("Governance blocked execution:", verify.output);
  process.exit(1); // The host process decides when to exit, not Z-MOS.
}
```

---

## 5. Understanding the `.z-mos` Structure

The core repository of runtime memory lives within `.z-mos`. In Gen4 v0.4.0, this structure remains strictly governed:

- **`truth.contract.json`**: The sole machine-readable snapshot of runtime authority.
- **`intent.card.json`**: The explicit, human-authorized boundaries for the current mission.
- **`zmos-manifest.json`**: Project identity and policy envelope.
- **`workflow-policy.json`**: Defines the workflow execution gates and required schemas.
- **`trace/runtime-trace.jsonl`**: The active audit log containing operational and mutation trace records.
- **`trace/archive/`**: The storage directory for rotated trace segments and `.meta.json` checkpoints ensuring continuous SHA-256 integrity.

---

*Z-MOS guarantees deterministic predictability once a project is synchronized with the Gen4 truth-first baseline.*
