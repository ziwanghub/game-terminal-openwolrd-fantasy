# Embedding Guide

This guide explains how to install and embed the Z-MOS SDK within an external Node.js project or AI Agent Runtime.

## 1. Installation

You can link or install `zmos-core` locally:
```bash
npm install zmos-core@file:../path/to/zmos-core
```

## 2. Basic Initialization

Import the SDK from the index and invoke `bootstrapWorkspace`:

```javascript
import { bootstrapWorkspace, verifyWorkspace } from "zmos-core/sdk/index.js";

const result = bootstrapWorkspace({ workspaceDir: process.cwd() });
if (!result.success) {
  console.error("Z-MOS initialization failed!", result.error);
  process.exit(1);
}
```

## 3. Strict Verification

Before your external project performs a critical operation (like a production deployment), wrap it with `verifyWorkspace`:

```javascript
const verify = verifyWorkspace({ workspaceDir: process.cwd(), strict: true });
if (!verify.success) {
  console.error("Governance block: Cannot deploy.");
  console.error(verify.output);
  process.exit(1);
}

// Proceed with deployment...
```

See the `/examples` folder in the `zmos-core` repository for complete boilerplate implementations.
