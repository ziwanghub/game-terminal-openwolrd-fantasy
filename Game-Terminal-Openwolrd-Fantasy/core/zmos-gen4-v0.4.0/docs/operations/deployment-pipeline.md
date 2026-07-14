# Z-MOS Continuous Deployment & Quality Pipeline Standard

**Status:** ACTIVE  
**Version:** v1.0.0  
**Effective Date:** 2026-05-30  
**Audience:** Human Operators, Lead Developers, AI Development Agents  

---

## 1. Rationale & Core Principle

In software engineering, **initial development represents only 20% of the lifecycle cost, while maintenance and operations under active production load represent 80%.** Anyone can build and ship an MVP quickly, but preserving system integrity, performance, and correctness in the long run is the true engineering challenge.

For systems under continuous active use (e.g., active CRUD operations, live marketing pixel loads, automated ad integration, and rolling updates), any untested mutation can lead to immediate financial and reputational damage. 

To eliminate regression risks and ensure sustainable delivery, this project enforces a mandatory **Three-Stage Quality Pipeline** for all code changes.

---

## 2. The Three-Stage Pipeline

```
[ STAGE 1: Local Z-MOS ] ➔ [ STAGE 2: GitHub CI/CD Gate ] ➔ [ STAGE 3: Production Smoke Test ]
```

### Stage 1: Local Development with Z-MOS Governance
*   **Purpose:** Enforce guardrails and capture intention before any change leaves the developer's computer.
*   **Rules:**
    1.  All developers and AI Agents must boot Z-MOS context via `zcl start` at the beginning of each session.
    2.  For any mutation, the AI Agent must stay within the declared file path limits defined in `zmos-manifest.json` under `scope.mutation.allowedPaths`.
    3.  All risky changes require a Behavior Intelligence Log (BIL) entry justifying the decision, recorded via `zcl behavior record`.
    4.  Before committing and pushing, the strict verification script must pass locally:
        ```bash
        npm run verify:production-readiness:strict
        ```

### Stage 2: GitHub CI/CD Gate
*   **Purpose:** Establish a centralized, non-bypassable checkpoint to block unauthorized, out-of-scope, or corrupted code from merging.
*   **Rules:**
    1.  No developer or AI Agent may push directly to `main` or `develop`. All changes must go through a Pull Request (PR).
    2.  GitHub Actions will run the strict verification pipeline (`verify-strict` workflow).
    3.  The CI pipeline executes:
        ```bash
        # 1. Verify trace log hash integrity
        node ./bin/zcl.js trace verify
        
        # 2. Run system doctor diagnostics
        node ./bin/zcl.js doctor
        
        # 3. Execute project test suites
        npm run verify:core
        ```
    4.  If any check fails (e.g., drift detected, broken trace chain, or test failures), the PR is blocked automatically.

### Stage 3: Deployment & Active Smoke Testing
*   **Purpose:** Confirm that the live environment (database connections, environment variables, external API integrations, ad pixels) functions correctly post-deployment.
*   **Rules:**
    1.  **Staging Deploy & Test:** Deploy the PR to a staging sandbox (a mirror of production connected to safe mock databases). Run automated user flows (using Playwright or Cypress) simulating:
        *   User login and session validation.
        *   Basic CRUD flows (Create, Read, Update, Delete) on core tables.
        *   Third-party tracking scripts and marketing ad pixels verification.
    2.  **Production Deploy:** Once staging tests pass, deploy to production.
    3.  **Production Smoke Check:** Execute a rapid, read-only smoke check on the live environment using a dedicated test account to confirm active connectivity.

---

## 3. Incident & Rollback Protocol

If a failure occurs or a smoke test fails:
1.  **Immediate Revert:** Immediately revert `main` to the last known-good commit.
2.  **State Stability:** Run the recovery macro:
    ```bash
    zcl recover
    ```
3.  **Audit the Trace:** Inspect the append-only `runtime-trace.jsonl` to locate the exact change and BIL reasoning that introduced the failure. Do not re-attempt execution until the root cause has been documented and resolved.
