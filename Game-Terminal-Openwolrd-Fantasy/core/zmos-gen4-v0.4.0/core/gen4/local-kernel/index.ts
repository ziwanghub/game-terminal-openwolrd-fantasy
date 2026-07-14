export type {
  LocalDecisionResult,
  LocalDecisionStatus,
  LocalEvidencePackage,
  LocalEvidencePackageStatus,
  LocalHarnessOptions,
  LocalIntent,
  LocalInvariantViolation,
  LocalReplayResult,
  LocalReplayStatus,
  LocalRecoveryDiagnostic,
  LocalRecoveryStatus,
  LocalTraceRecord,
  LocalTraceWriter,
} from "./types.js";

export { LOCAL_KERNEL_ERROR_CODES, LocalKernelValidationError } from "./errors.js";

// Public runtime entrypoints.
export { runLocalIntent } from "./harness.js";
export { createLocalTraceWriter } from "./trace.js";
export { replayLocalTraceRecords } from "./replay.js";
export { buildLocalEvidencePackage } from "./evidence.js";
export { diagnoseLocalTraceRecovery } from "./recovery.js";
export {
  appendLocalTraceRecordToFile,
  isLocalTracePersistenceFailure,
  loadLocalTraceRecordsFromFile,
  LOCAL_TRACE_PERSISTENCE_ERROR_CODES,
} from "./trace-persistence.js";
export type {
  LocalTracePersistenceLoadResult,
  LocalTracePersistenceWriteResult,
} from "./trace-persistence.js";

// Internal helpers intentionally not re-exported from this barrel:
// - validateLocalIntent
// - createLocalDecisionResult
