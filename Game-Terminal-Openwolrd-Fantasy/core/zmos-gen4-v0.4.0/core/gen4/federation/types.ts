import type { MembershipAuthorityRef, MembershipScopeRef, MembershipState, MembershipVerificationStatus } from "../membership/types.js";
import type { TrustEnvelope } from "../trust-envelope/index.js";

export type FederationNodeRef = {
  node_id: string;
  node_namespace: string;
  node_role: "sovereign" | "observer" | "auditor" | "validator" | "participant";
  federation_membership_id: string;
  membership_state: MembershipState;
  verification_status: MembershipVerificationStatus;
  authority_owner_ref: MembershipAuthorityRef;
  trust_envelope_id: string;
  lineage_reference: string;
  scope_ref: MembershipScopeRef;
  active: boolean;
};

export type FederationSimulationEvent =
  | {
      event_id: string;
      event_type: "join-request";
      node_ref: FederationNodeRef;
      initiated_at: string;
    }
  | {
      event_id: string;
      event_type: "trust-validation";
      node_ref: FederationNodeRef;
      trust_envelope: TrustEnvelope;
      initiated_at: string;
    }
  | {
      event_id: string;
      event_type: "lineage-validation";
      node_ref: FederationNodeRef;
      expected_lineage_reference: string;
      actual_lineage_reference: string;
      initiated_at: string;
    }
  | {
      event_id: string;
      event_type: "membership-update";
      node_ref: FederationNodeRef;
      membership_state: MembershipState;
      initiated_at: string;
    }
  | {
      event_id: string;
      event_type: "quarantine";
      node_ref: FederationNodeRef;
      reason: string;
      initiated_at: string;
    }
  | {
      event_id: string;
      event_type: "audit";
      node_ref: FederationNodeRef;
      initiated_at: string;
    };

export type FederationConsensusView = {
  federation_id: string;
  active_node_ids: readonly string[];
  quarantined_node_ids: readonly string[];
  revoked_node_ids: readonly string[];
  membership_status: Record<string, MembershipState>;
  trust_compatible_node_ids: readonly string[];
};

export type FederationLineageView = {
  accepted_lineage_reference: string;
  incompatible_node_ids: readonly string[];
  mismatched_lineage: boolean;
  details: readonly {
    node_id: string;
    expected_lineage_reference: string;
    actual_lineage_reference: string;
  }[];
};

export type FederationSimulationState = {
  federation_id: string;
  nodes: readonly FederationNodeRef[];
};

export type FederationSimulationErrorDetail = {
  node_id: string;
  code: string;
  message: string;
  event_id?: string;
};

export type FederationSimulationResult = {
  success: boolean;
  federation_id: string;
  events: readonly FederationSimulationEvent[];
  errors: readonly FederationSimulationErrorDetail[];
  consensus_view: FederationConsensusView;
  lineage_view: FederationLineageView;
};
