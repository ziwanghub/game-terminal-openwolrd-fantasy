export type IntentValidationIssueCode =
  | "INTENT_FILE_MISSING"
  | "INTENT_JSON_INVALID"
  | "INTENT_SCHEMA_VERSION_AGENT_INVALID"
  | "INTENT_SHAPE_INVALID"
  | "INTENT_FIELD_INVALID";

export interface IntentValidationIssue {
  code: IntentValidationIssueCode;
  message: string;
  path?: string;
}

export interface IntentValidationResult {
  valid: boolean;
  issues: IntentValidationIssue[];
}
