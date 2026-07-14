import type {
  DelegatedAuthorityRef,
  FederationScope,
  IssuerAuthorityRef,
  TrustEnvelope,
  TrustEnvelopeLifecycleState,
  TrustEnvelopeSignatureMetadata,
  TrustVerificationPolicy,
} from "./types.js";
import {
  TrustEnvelopeValidationError,
  TRUST_ENVELOPE_ERROR_CODES,
} from "./errors.js";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertNonEmptyString(
  value: unknown,
  label: string,
  code: string = TRUST_ENVELOPE_ERROR_CODES.EMPTY_AUTHORITY_OWNER,
): asserts value is string {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new TrustEnvelopeValidationError(
      code,
      `${label} must be a non-empty string.`,
    );
  }
}

function assertIsoDate(value: unknown, label: string): asserts value is string {
  assertNonEmptyString(value, label);
  if (Number.isNaN(Date.parse(value))) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MALFORMED_TRUST_REFERENCE,
      `${label} must be a valid ISO 8601 date string.`,
    );
  }
}

function assertAllowedLifecycleState(value: unknown): asserts value is TrustEnvelopeLifecycleState {
  const allowed = ["draft", "issued", "active", "suspended", "revoked", "expired"] as const;
  if (typeof value !== "string" || !allowed.includes(value as TrustEnvelopeLifecycleState)) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_LIFECYCLE_STATE,
      `Invalid lifecycle state: ${String(value)}.`,
    );
  }
}

function assertAuthorityType(value: unknown): asserts value is "root-authority" | "delegated-authority" {
  if (value !== "root-authority" && value !== "delegated-authority") {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.HIDDEN_AUTHORITY,
      `Authority type must be explicit and cannot be hidden.`,
    );
  }
}

function validateIssuerAuthorityRef(value: unknown, path: string): IssuerAuthorityRef {
  if (!isRecord(value)) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MISSING_ISSUER_AUTHORITY,
      `${path} must be an object.`,
    );
  }

  assertNonEmptyString(value.authority_owner_id, `${path}.authority_owner_id`);
  assertNonEmptyString(value.authority_namespace, `${path}.authority_namespace`);
  assertAuthorityType(value.authority_type);

  if (value.explicit_ownership !== true) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.EMPTY_AUTHORITY_OWNER,
      `${path}.explicit_ownership must be true.`,
    );
  }

  assertIsoDate(value.authorized_at, `${path}.authorized_at`);
  assertNonEmptyString(value.human_authorization_ref, `${path}.human_authorization_ref`);

  return value as IssuerAuthorityRef;
}

function validateFederationScope(value: unknown, path: string): FederationScope {
  if (!isRecord(value)) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_FEDERATION_SCOPE,
      `${path} must be an object.`,
    );
  }

  assertNonEmptyString(value.federation_id, `${path}.federation_id`);

  if (!Array.isArray(value.permitted_actions) || value.permitted_actions.length === 0) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_FEDERATION_SCOPE,
      `${path}.permitted_actions must be a non-empty array.`,
    );
  }

  if (!Array.isArray(value.permitted_resources) || value.permitted_resources.length === 0) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_FEDERATION_SCOPE,
      `${path}.permitted_resources must be a non-empty array.`,
    );
  }

  if (value.escalation_policy !== "authority-approved" && value.escalation_policy !== "none") {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_FEDERATION_SCOPE,
      `${path}.escalation_policy must be authority-approved or none.`,
    );
  }

  assertNonEmptyString(value.scope_description, `${path}.scope_description`);

  return value as FederationScope;
}

function validateTrustVerificationPolicy(value: unknown, path: string): TrustVerificationPolicy {
  if (!isRecord(value)) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MISSING_VERIFICATION_POLICY,
      `${path} must be an object.`,
    );
  }

  if (value.verification_mode !== "fail-closed") {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MISSING_VERIFICATION_POLICY,
      `${path}.verification_mode must be fail-closed.`,
    );
  }

  if (value.require_human_authorization !== true) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MISSING_VERIFICATION_POLICY,
      `${path}.require_human_authorization must be true.`,
    );
  }

  if (typeof value.allow_delegated_authority !== "boolean") {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MISSING_VERIFICATION_POLICY,
      `${path}.allow_delegated_authority must be a boolean.`,
    );
  }

  if (!Array.isArray(value.required_authority_types) || value.required_authority_types.length === 0) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MISSING_VERIFICATION_POLICY,
      `${path}.required_authority_types must include explicit authority types.`,
    );
  }

  for (const authorityType of value.required_authority_types) {
    assertAuthorityType(authorityType);
  }

  if (value.allow_delegated_authority === false && (value.required_authority_types as string[]).includes("delegated-authority")) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MISSING_VERIFICATION_POLICY,
      `${path}.required_authority_types cannot include delegated-authority when allow_delegated_authority is false.`,
    );
  }

  const acceptedScope = validateFederationScope(value.accepted_scope, `${path}.accepted_scope`);

  if (value.accepted_truth_lineage_reference !== undefined) {
    assertNonEmptyString(
      value.accepted_truth_lineage_reference,
      `${path}.accepted_truth_lineage_reference`,
      TRUST_ENVELOPE_ERROR_CODES.INVALID_ACCEPTED_TRUTH_LINEAGE_REFERENCE,
    );
  }

  return {
    verification_mode: "fail-closed",
    required_authority_types: value.required_authority_types as ["root-authority" | "delegated-authority", ...Array<"root-authority" | "delegated-authority">],
    require_human_authorization: true,
    allow_delegated_authority: value.allow_delegated_authority,
    accepted_scope: acceptedScope,
    accepted_truth_lineage_reference: value.accepted_truth_lineage_reference,
  };
}

function validateDelegatedAuthorityRef(value: unknown, path: string): DelegatedAuthorityRef {
  if (!isRecord(value)) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_DELEGATION_CHAIN,
      `${path} must be an object.`,
    );
  }

  assertNonEmptyString(value.delegate_id, `${path}.delegate_id`);
  assertNonEmptyString(value.delegate_namespace, `${path}.delegate_namespace`);

  if (value.delegate_type !== "delegated-authority") {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_DELEGATION_CHAIN,
      `${path}.delegate_type must be delegated-authority.`,
    );
  }

  if (value.explicit_ownership !== true) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_DELEGATION_CHAIN,
      `${path}.explicit_ownership must be true.`,
    );
  }

  const delegatedBy = validateIssuerAuthorityRef(value.delegated_by, `${path}.delegated_by`);
  assertIsoDate(value.delegated_at, `${path}.delegated_at`);
  assertIsoDate(value.expires_at, `${path}.expires_at`);

  if (value.delegation_policy !== "restricted" && value.delegation_policy !== "scoped" && value.delegation_policy !== "none") {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_DELEGATION_CHAIN,
      `${path}.delegation_policy must be restricted, scoped, or none.`,
    );
  }

  if (value.delegation_policy === "restricted" && (!Array.isArray(value.authorized_scopes) || value.authorized_scopes.length === 0)) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_DELEGATION_CHAIN,
      `${path}.authorized_scopes must be a non-empty array when delegation_policy is restricted.`,
    );
  }

  assertNonEmptyString(value.human_authorization_ref, `${path}.human_authorization_ref`);

  if (delegatedBy.authority_owner_id === value.delegate_id) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.SELF_AUTHORIZED_ESCALATION,
      `${path} cannot delegate to itself.`,
    );
  }

  const authorizedScopes = Array.isArray(value.authorized_scopes)
    ? value.authorized_scopes.map((scope, index) => validateFederationScope(scope, `${path}.authorized_scopes[${index}]`))
    : [];

  return {
    delegate_id: value.delegate_id,
    delegate_namespace: value.delegate_namespace,
    delegate_type: "delegated-authority",
    explicit_ownership: true,
    delegated_by: delegatedBy,
    delegated_at: value.delegated_at,
    expires_at: value.expires_at,
    delegation_policy: value.delegation_policy,
    authorized_scopes: authorizedScopes,
    human_authorization_ref: value.human_authorization_ref,
  };
}

function validateSignatureMetadata(value: unknown, path: string): TrustEnvelopeSignatureMetadata {
  if (!isRecord(value)) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_SIGNATURE_METADATA,
      `${path} must be an object.`,
    );
  }

  assertNonEmptyString(value.signature_id, `${path}.signature_id`);
  assertIsoDate(value.signed_at, `${path}.signed_at`);
  assertNonEmptyString(value.signature_reference, `${path}.signature_reference`);

  if (value.signature_scheme !== "placeholder") {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_SIGNATURE_METADATA,
      `${path}.signature_scheme must be placeholder.`,
    );
  }

  const signerAuthority = validateIssuerAuthorityRef(value.signer_authority, `${path}.signer_authority`);
  const verificationPolicy = validateTrustVerificationPolicy(value.verification_policy, `${path}.verification_policy`);

  return {
    signature_id: value.signature_id,
    signed_at: value.signed_at,
    signer_authority: signerAuthority,
    signature_scheme: "placeholder",
    signature_reference: value.signature_reference,
    verification_policy: verificationPolicy,
  };
}

function validateRevocationRef(value: unknown, path: string): void {
  if (!isRecord(value)) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MALFORMED_TRUST_REFERENCE,
      `${path} must be an object.`,
    );
  }

  assertNonEmptyString(value.revocation_id, `${path}.revocation_id`);
  assertIsoDate(value.revoked_at, `${path}.revoked_at`);
  assertNonEmptyString(value.revocation_reason, `${path}.revocation_reason`);
  assertNonEmptyString(value.trace_reference, `${path}.trace_reference`);

  if (!isRecord(value.revoked_by)) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MALFORMED_TRUST_REFERENCE,
      `${path}.revoked_by must be an object.`,
    );
  }

  validateIssuerAuthorityRef(value.revoked_by, `${path}.revoked_by`);
}

function assertValidValidityRange(validFrom: string, validUntil: string): void {
  const from = Date.parse(validFrom);
  const until = Date.parse(validUntil);
  if (from > until) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_FEDERATION_SCOPE,
      `valid_from must be before or equal to valid_until.`,
    );
  }

  if (until < Date.now()) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.STALE_ENVELOPE,
      `The trust envelope is stale or expired.`,
    );
  }
}

function assertDelegationScopeContainsEnvelopeScope(
  delegatedAuthority: DelegatedAuthorityRef,
  envelopeScope: FederationScope,
): void {
  if (delegatedAuthority.delegation_policy === "none") {
    return;
  }

  const matches = delegatedAuthority.authorized_scopes.some((scope) => {
    return (
      scope.federation_id === envelopeScope.federation_id &&
      scope.escalation_policy === envelopeScope.escalation_policy &&
      envelopeScope.permitted_actions.every((action) => scope.permitted_actions.includes(action)) &&
      envelopeScope.permitted_resources.every((resource) => scope.permitted_resources.includes(resource))
    );
  });

  if (!matches) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.INVALID_DELEGATION_CHAIN,
      `Delegated authority scope must contain or match the envelope federation scope.`,
    );
  }
}

export function validateTrustEnvelope(envelope: unknown): TrustEnvelope {
  if (!isRecord(envelope)) {
    throw new TrustEnvelopeValidationError(
      TRUST_ENVELOPE_ERROR_CODES.MALFORMED_TRUST_REFERENCE,
      "TrustEnvelope must be an object.",
    );
  }

  assertNonEmptyString(envelope.trust_envelope_id, "trust_envelope_id");
  assertNonEmptyString(envelope.version, "version");
  assertAllowedLifecycleState(envelope.lifecycle_state);

  const issuer = validateIssuerAuthorityRef(envelope.issuer, "issuer");
  const federationScope = validateFederationScope(envelope.federation_scope, "federation_scope");
  const verificationPolicy = validateTrustVerificationPolicy(envelope.verification_policy, "verification_policy");
  const signature = validateSignatureMetadata(envelope.signature, "signature");

  assertIsoDate(envelope.issued_at, "issued_at");
  assertIsoDate(envelope.valid_from, "valid_from");
  assertIsoDate(envelope.valid_until, "valid_until");
  assertValidValidityRange(envelope.valid_from, envelope.valid_until);
  assertNonEmptyString(envelope.human_authorization_ref, "human_authorization_ref");

  let delegatedAuthority: DelegatedAuthorityRef | undefined;
  if (envelope.delegated_authority !== undefined) {
    delegatedAuthority = validateDelegatedAuthorityRef(envelope.delegated_authority, "delegated_authority");
    assertDelegationScopeContainsEnvelopeScope(delegatedAuthority, federationScope);
  }

  if (envelope.lifecycle_state === "revoked") {
    if (envelope.revocation_ref === undefined) {
      throw new TrustEnvelopeValidationError(
        TRUST_ENVELOPE_ERROR_CODES.MALFORMED_TRUST_REFERENCE,
        "revocation_ref is required when lifecycle_state is revoked.",
      );
    }
    validateRevocationRef(envelope.revocation_ref, "revocation_ref");
  }

  return {
    trust_envelope_id: envelope.trust_envelope_id,
    version: envelope.version,
    lifecycle_state: envelope.lifecycle_state,
    issuer,
    delegated_authority: delegatedAuthority,
    federation_scope: federationScope,
    verification_policy: verificationPolicy,
    revocation_ref: envelope.revocation_ref as any,
    signature,
    issued_at: envelope.issued_at,
    valid_from: envelope.valid_from,
    valid_until: envelope.valid_until,
    human_authorization_ref: envelope.human_authorization_ref,
  };
}
