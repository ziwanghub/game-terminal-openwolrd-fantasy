# Z-MOS FUNCTIONAL UI/UX STANDARD v1
(NO DESIGN, ONLY BEHAVIOR)

## 1) Purpose
- Define functional UI behavior standards, not visual styling.
- Keep user interaction aligned with system contracts and governance rules.
- Reduce operational risk from inconsistent UI behavior.

## 2) Why This Standard Exists
Z-MOS currently governs contracts, runtime behavior, and execution safety strongly at logic level. Without a functional UI behavior standard:
- behavior can drift between pages and projects
- user-induced errors can increase
- contract violations can happen through incorrect UI assumptions
- validation and audit become harder because UI decisions are inconsistent

UI is part of the execution layer. It must be governed similarly to backend behavior for safety and predictability.

This standard prevents:
- invalid input passing silently
- silent failure paths
- misleading UI states that hide blocked/error outcomes

This standard ensures:
- predictable user interaction outcomes
- safer system usage
- consistency with backend governance semantics

## 3) Scope
Applies to all UI layers in Z-MOS-governed projects.

In scope:
- input behavior
- validation behavior
- system state handling
- error handling
- UI-layer security behavior

Out of scope:
- visual theme/styling design systems
- branding/art direction choices

## 4) Core Principles (UI Version of Z-MOS)
1. Fail-closed UI by default.
2. No silent failure.
3. Contract-first interaction behavior.
4. No implicit behavior.
5. Explicit user feedback for state transitions.

## 5) Functional Standards

### A) Input/Form Standard
1. Required fields must be explicit and visibly indicated.
2. Validation timing:
- immediate validation for basic format/safety
- submit-time validation for full contract checks
3. Error message rules:
- specific, actionable, and tied to field/state
- do not mask contract errors as generic success/failure
4. Input safety:
- sanitize/normalize UI input before submission
- never assume backend will infer missing critical values

### B) Filter/Search Standard
1. Filter state must be visible and reversible.
2. Empty-state result must be explicit (no fake stale data).
3. Provide clear reset behavior for filter/search inputs.

### C) System State Standard
Every critical view must define and render:
1. Loading state
2. Success state
3. Error state
4. Empty state

State transitions must be visible; UI must not silently remain stale.

### D) Auth/Security UI Standard
1. Permission outcomes must be explicit (`blocked`, denied, forbidden paths).
2. UI must follow fail-closed behavior when auth/session status is uncertain.
3. Session/token invalid states must route safely and clearly.
4. UI must not expose privileged actions before permission confirmation.

### E) Action Safety
1. Destructive actions require explicit confirmation.
2. Double-submit prevention is mandatory for mutation actions.
3. In-flight actions must show pending state and prevent duplicate triggers.

### F) API/Contract UI Rule
1. UI must not assume undocumented response shapes.
2. UI must map to contract-defined fields and semantics.
3. No silent fallback when API contract fields are missing/invalid.
4. Prefer deterministic branching from contract signals over free-text parsing.

### G) Consistency Rule
1. Same action class should behave consistently across pages.
2. Same failure class should present equivalent guidance across modules.
3. Shared interaction patterns should be reused rather than redefined ad hoc.

## 6) SA Review Quick Check
Use these 5 questions:
1. Does UI behavior align with current contract semantics?
2. Are loading/success/error/empty states explicit and complete?
3. Is fail-closed behavior preserved for auth/permission uncertainty?
4. Are destructive and repeat actions guarded safely?
5. Does any page introduce implicit/fallback/silent behavior?

If any answer is "no", status should be ADJUST or REJECT.

## 7) Usage
### Codex (Implementation)
- Apply this as behavior constraints for UI build tasks.
- Do not introduce implicit behavior outside contract/governance rules.

### Antigravity (Validation)
- Validate page flows against these functional behavior rules.
- Report violations as governance findings, not styling feedback.

### SA (Decision)
- Use this standard as review baseline for UI behavior approval.
- Enforce fail-closed/no-silent-failure/no-implicit behavior gates.

## 8) Version
v1 (initial release)
