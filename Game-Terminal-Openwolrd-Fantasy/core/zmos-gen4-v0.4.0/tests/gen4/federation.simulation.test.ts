import test from "node:test";
import assert from "node:assert/strict";
import { simulateFederationEvents } from "../../core/gen4/federation/simulator.ts";
import { FederationSimulationValidationError } from "../../core/gen4/federation/errors.ts";
import {
  buildValidFederationSimulationState,
  buildValidJoinRequestEvent,
  buildValidTrustValidationEvent,
  buildInvalidTrustValidationEvent,
  buildLineageMismatchEvent,
  buildRevokedMembershipEvent,
  buildStaleStateAuditEvent,
  buildUnsortedEvents,
} from "./fixtures/federation.fixtures.ts";

test("simulateFederationEvents processes a successful join simulation deterministically", () => {
  const state = buildValidFederationSimulationState();
  const events = [buildValidJoinRequestEvent(), buildValidTrustValidationEvent()];

  const result = simulateFederationEvents(state, events);

  assert.equal(result.success, true);
  assert.deepEqual(result.errors, []);
  assert.ok(result.consensus_view.active_node_ids.includes("node-001"));
  assert.ok(result.consensus_view.trust_compatible_node_ids.includes("node-001"));
});

test("simulateFederationEvents rejects an incompatible trust envelope and quarantines the node", () => {
  const state = buildValidFederationSimulationState();
  const events = [buildInvalidTrustValidationEvent()];

  const result = simulateFederationEvents(state, events);

  assert.equal(result.success, false);
  assert.equal(result.errors.length, 1);
  assert.equal(result.errors[0].code, "TRUST_ENVELOPE_INCOMPATIBLE");
  assert.ok(result.consensus_view.quarantined_node_ids.includes("node-001"));
});

test("simulateFederationEvents quarantines nodes with lineage mismatch", () => {
  const state = buildValidFederationSimulationState();
  const events = [buildLineageMismatchEvent()];

  const result = simulateFederationEvents(state, events);

  assert.equal(result.success, false);
  assert.equal(result.lineage_view.mismatched_lineage, true);
  assert.ok(result.lineage_view.incompatible_node_ids.includes("node-001"));
  assert.ok(result.consensus_view.quarantined_node_ids.includes("node-001"));
});

test("simulateFederationEvents quarantines revoked membership state", () => {
  const state = buildValidFederationSimulationState();
  const events = [buildRevokedMembershipEvent()];

  const result = simulateFederationEvents(state, events);

  assert.equal(result.success, true);
  assert.ok(result.consensus_view.quarantined_node_ids.includes("node-001"));
  assert.ok(result.consensus_view.revoked_node_ids.includes("node-001"));
});

test("simulateFederationEvents detects stale federation state during audit", () => {
  const state = buildValidFederationSimulationState();
  const events = [buildStaleStateAuditEvent()];

  const result = simulateFederationEvents(state, events);

  assert.equal(result.success, true);
  assert.ok(result.consensus_view.quarantined_node_ids.includes("node-001"));
});

test("simulateFederationEvents orders events deterministically by event_id", () => {
  const state = buildValidFederationSimulationState();
  const events = buildUnsortedEvents();

  const result = simulateFederationEvents(state, events);

  assert.deepEqual(result.events.map((event) => event.event_id), ["event-001", "event-002", "event-003"]);
});
