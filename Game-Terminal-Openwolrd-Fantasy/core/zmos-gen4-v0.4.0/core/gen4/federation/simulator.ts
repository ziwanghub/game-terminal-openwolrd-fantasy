import type {
  FederationSimulationEvent,
  FederationSimulationState,
  FederationSimulationResult,
  FederationSimulationErrorDetail,
  FederationConsensusView,
  FederationLineageView,
} from "./types.js";
import type { MembershipState } from "../membership/types.js";
import {
  validateFederationNodeRef,
  validateFederationNodeParticipation,
  validateTrustEnvelopeCompatibility,
  validateLineageCompatibility,
} from "./validator.js";
import {
  FederationSimulationValidationError,
  FEDERATION_SIMULATION_ERROR_CODES,
} from "./errors.js";

function sortEvents(events: readonly FederationSimulationEvent[]): FederationSimulationEvent[] {
  return [...events].sort((left, right) => left.event_id.localeCompare(right.event_id));
}

function buildConsensusView(
  state: FederationSimulationState,
  quarantinedNodeIds: Set<string>,
  trustCompatibleNodeIds: Set<string>,
  membershipStatus: Record<string, MembershipState>,
): FederationConsensusView {
  return {
    federation_id: state.federation_id,
    active_node_ids: state.nodes
      .filter((node) => node.active && !quarantinedNodeIds.has(node.node_id))
      .map((node) => node.node_id),
    quarantined_node_ids: Array.from(quarantinedNodeIds).sort(),
    revoked_node_ids: state.nodes
      .filter((node) => node.membership_state === "revoked" || membershipStatus[node.node_id] === "revoked")
      .map((node) => node.node_id)
      .sort(),
    membership_status: membershipStatus,
    trust_compatible_node_ids: Array.from(trustCompatibleNodeIds).sort(),
  };
}

function buildLineageView(
  acceptedLineageReference: string,
  incompatibleNodes: Set<string>,
  details: FederationLineageView["details"],
): FederationLineageView {
  return {
    accepted_lineage_reference: acceptedLineageReference,
    incompatible_node_ids: Array.from(incompatibleNodes).sort(),
    mismatched_lineage: incompatibleNodes.size > 0,
    details,
  };
}

export function simulateFederationEvents(
  state: FederationSimulationState,
  events: readonly FederationSimulationEvent[],
): FederationSimulationResult {
  const sortedEvents = sortEvents(events);
  const errors: FederationSimulationErrorDetail[] = [];
  const quarantinedNodeIds = new Set<string>();
  const trustCompatibleNodeIds = new Set<string>();
  const membershipStatus: Record<string, MembershipState> = {};
  const lineageDetails: {
    node_id: string;
    expected_lineage_reference: string;
    actual_lineage_reference: string;
  }[] = [];
  const acceptedLineageReference = state.nodes.length > 0 ? state.nodes[0].lineage_reference : "";

  state.nodes.forEach((node) => {
    membershipStatus[node.node_id] = node.membership_state;
  });

  for (const event of sortedEvents) {
    const nodeId = event.node_ref.node_id;

    try {
      validateFederationNodeRef(event.node_ref);

      switch (event.event_type) {
        case "join-request": {
          validateFederationNodeParticipation(event.node_ref);
          if (event.node_ref.membership_state !== "joining") {
            throw new FederationSimulationValidationError(
              FEDERATION_SIMULATION_ERROR_CODES.INVALID_NODE_PARTICIPATION,
              "Join request must originate from a node in joining state.",
            );
          }
          break;
        }
        case "trust-validation": {
          validateTrustEnvelopeCompatibility(event.node_ref, event.trust_envelope);
          trustCompatibleNodeIds.add(nodeId);
          break;
        }
        case "lineage-validation": {
          try {
            validateLineageCompatibility(event.node_ref, event.expected_lineage_reference);
          } catch (error) {
            if (error instanceof FederationSimulationValidationError) {
              quarantinedNodeIds.add(nodeId);
              lineageDetails.push({
                node_id: nodeId,
                expected_lineage_reference: event.expected_lineage_reference,
                actual_lineage_reference: event.actual_lineage_reference,
              });
              throw error;
            }
            throw error;
          }
          break;
        }
        case "membership-update": {
          membershipStatus[nodeId] = event.membership_state;
          if (event.membership_state === "revoked" || event.membership_state === "left") {
            quarantinedNodeIds.add(nodeId);
          }
          break;
        }
        case "quarantine": {
          quarantinedNodeIds.add(nodeId);
          break;
        }
        case "audit": {
          if (event.node_ref.membership_state === "revoked" || event.node_ref.membership_state === "left") {
            quarantinedNodeIds.add(nodeId);
          }
          if (!event.node_ref.active) {
            quarantinedNodeIds.add(nodeId);
          }
          break;
        }
        default:
          throw new FederationSimulationValidationError(
            FEDERATION_SIMULATION_ERROR_CODES.MALFORMED_NODE_REF,
            `Unsupported event type: ${(event as FederationSimulationEvent).event_type}.`,
          );
      }
    } catch (error) {
      if (error instanceof FederationSimulationValidationError) {
        quarantinedNodeIds.add(nodeId);
        errors.push({
          node_id: nodeId,
          code: error.code,
          message: error.message,
          event_id: event.event_id,
        });
      } else {
        throw error;
      }
    }
  }

  const consensus_view = buildConsensusView(state, quarantinedNodeIds, trustCompatibleNodeIds, membershipStatus);
  const lineage_view = buildLineageView(acceptedLineageReference, new Set(lineageDetails.map((detail) => detail.node_id)), lineageDetails);

  return {
    success: errors.length === 0,
    federation_id: state.federation_id,
    events: sortedEvents,
    errors,
    consensus_view,
    lineage_view,
  };
}
