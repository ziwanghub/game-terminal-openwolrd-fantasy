# Living Truth Transition Protocol

- Document Code: `ADD-GEN4-003`
- Version: `0.2`
- Status: Draft - Under Review
- Basis: RD-GEN4-001 v0.3, ADD-GEN4-001 v0.2, ADD-GEN4-002 v0.2

---

## 1. Purpose of Living Truth Transition

The Living Truth Transition Protocol defines how Z-MOS v4.0 "Sovereignty" manages evolution of the Living Canonical Truth. The protocol ensures the truth may evolve, but only through controlled, trace-backed, authority-approved transitions. Uncontrolled mutation is prohibited and the truth contract must always remain auditable and verifiable.

---

## 2. Transition Request Flow

The protocol defines an architectural flow for truth transitions.

- `proposed transition`: A candidate change to the living truth is declared with explicit intent.
- `intent authorization`: Human-authorized intent validates the purpose and scope of the proposed transition.
- `authority review`: The proposed transition is reviewed by the relevant root or delegated authority.
- `trace evidence collection`: Supporting evidence is collected and linked to the transition request.
- `approval/rejection`: The authority either approves or rejects the transition based on governance rules.
- `signed transition publication`: Approved transitions are published as signed truth artifacts.
- `federation propagation`: The signed transition is propagated to federation participants for verification.

This flow is architecture-level only and does not specify executable protocol details.

---

## 3. Signed Transition Format & Requirements

The signed transition artifact includes governance metadata that defines the transition's authority and continuity.

| Field | Purpose | Governance Meaning |
|---|---|---|
| `transition_id` | Unique identifier for the transition request | Prevents ambiguity and supports traceability. |
| `previous_truth_ref` | Reference to the current canonical truth version | Anchors the transition to the approved prior state. |
| `proposed_truth_ref` | Reference to the proposed new truth version | Defines the exact candidate truth state under consideration. |
| `issuer_authority` | Authority signing the transition | Identifies who is authorizing the change. |
| `approval_scope` | Scope of the transition approval | Delimits what aspects of truth may evolve. |
| `trace_evidence_ref` | Link to trace evidence supporting the transition | Connects the transition to audit records and supporting justification. |
| `signed_timestamp` | Time when the transition was authorized | Records when the authority approved the change. |
| `rollback_ref` | Reference to an authorized rollback path if required | Defines how the transition may be safely reverted if needed. |

Each element carries governance meaning and ensures the transition is explicit, authorized, and auditable.

---

## Transition Rejection Handling

Rejected transitions must never mutate canonical truth state.

- Rejection due to invalid authority: If the signing authority is unverified or unauthorized, the transition is rejected.
- Rejection due to missing trace evidence: If required evidence is absent or incomplete, the transition is rejected.
- Rejection due to lineage discontinuity: If the proposed transition breaks truth ancestry or creates orphan state, it is rejected.
- Rejection due to federation conflict: If federation participants identify conflicting truth states or trust mismatch, the transition is rejected.
- Rejection quarantine semantics: Rejected transitions may place the submitting node or transition candidate into quarantine until the issue is resolved.
- Fail-closed rejection handling: Any failed validation results in a fail-closed outcome and no change to canonical truth.

---

## 4. Truth Lineage Model

The Truth Lineage Model ensures continuity and verifiability of canonical truth.

- Immutable lineage: Every truth version is part of an unbroken ancestry chain.
- Ancestry chain: Each transition references its predecessor and preserves lineage continuity.
- Signed transitions: Each step in the lineage is authorized by a signed transition artifact.
- Lineage continuity: No orphan truth state is permitted.
- Verifiable truth ancestry: Participants can validate the chain from current truth back to authorized origins.

---

## 5. Rollback Protocol

Rollback is a controlled mechanism for returning to a prior authorized truth state.

- Authorized rollback only: Rollback may occur only with explicit authority approval.
- Rollback trace evidence: Rollback actions must be backed by trace records.
- Rollback lineage continuity: Rollback preserves a continuous lineage by referencing the prior authorized state.
- Rollback quarantine handling: Nodes may enter quarantine until rollback validation completes.
- Rollback approval gates: Rollback must pass the same authority and verification gates as forward transitions.

---

## 6. Drift Detection & Quarantine Rules

This section defines how unauthorized or inconsistent truth state is handled.

- Unauthorized truth mutation: Any truth state lacking signed transition evidence is invalid.
- Lineage discontinuity: Missing ancestry or orphaned truth state triggers drift detection.
- Invalid signature: Signature failures are treated as evidence of drift.
- Stale truth: Outdated truth versions are recognized as stale and must not remain authoritative.
- Federation divergence: Conflicting truth states across nodes indicate federation drift.

Quarantine semantics and isolation requirements:

- Quarantine semantics: Nodes with drift or invalid truth state are isolated from federation actions.
- Isolation requirements: Quarantined nodes may not participate in truth sync or authority validation.
- Recovery prerequisites: Nodes must restore valid truth lineage and evidence before returning to active federation participation.

---

## 7. Verification & Approval Gates

The protocol establishes governance gates for truth transitions.

- Human-authorized intent is required for every transition.
- Root or delegated authority validation is required before approval.
- Trace-backed verification is required for evidence and lineage.
- Fail-closed transition rejection is the default for invalid or unverified transitions.
- Federation verification gate ensures participating nodes agree on the signed transition and lineage.

---

## 8. Security Invariants

- Human-Authorized Evolution
- No Hidden Authority
- Fail-Closed Truth Validation
- Trace-Backed Truth Mutation
- No Self-Authorized Truth Rewrite

These invariants are central to the Living Truth Transition Protocol.

---

## 9. Alignment

- Aligns with RD-GEN4-001 v0.3 by preserving living canonical truth, explicit authority ownership, immutable trace, and bounded adaptive governance.
- Aligns with ADD-GEN4-001 v0.2 by supporting node identity, authority inheritance visibility, trust boundary isolation, lifecycle semantics, and verification requirements.
- Aligns with ADD-GEN4-002 v0.2 by integrating trust envelope semantics, federation scope constraints, and fail-closed envelope verification.

---

## 8. Security Invariants

- Human-Authorized Evolution
- No Hidden Authority
- Fail-Closed Truth Validation
- Trace-Backed Truth Mutation
- No Self-Authorized Truth Rewrite

These invariants are central to the Living Truth Transition Protocol.

---

## 9. Definition of Done

This document is complete when:

- Transition lifecycle is defined.
- Lineage continuity is defined.
- Rollback semantics are explicit.
- Rejection handling is explicit.
- Quarantine semantics are defined.
- Verification gates are defined.
- Human-Authorized Evolution is preserved.
- No implementation logic or pseudocode is present.

---

## 10. Alignment

- Aligns with RD-GEN4-001 v0.3 by preserving living canonical truth, explicit authority ownership, immutable trace, and bounded adaptive governance.
- Aligns with ADD-GEN4-001 v0.2 by supporting node identity, authority inheritance visibility, trust boundary isolation, lifecycle semantics, and verification requirements.
- Aligns with ADD-GEN4-002 v0.2 by integrating trust envelope semantics, federation scope constraints, and fail-closed envelope verification.

---

## Notes

This specification is architecture-focused and does not include implementation details. It is intended for review and iterative refinement during Phase 0.
