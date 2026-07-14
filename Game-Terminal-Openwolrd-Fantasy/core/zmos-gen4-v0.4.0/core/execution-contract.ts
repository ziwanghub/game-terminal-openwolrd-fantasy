export type GovernedCommandName =
  | "start"
  | "preflight"
  | "init"
  | "load-data"
  | "migrate"
  | "status"
  | "doctor"
  | "core-doctor"
  | "core-clean"
  | "core-restore"
  | "doc-check"
  | "doc-index"
  | "doc-doctor"
  | "workflow-list"
  | "workflow-coverage-check"
  | "workflow-runtime-check"
  | "workflow-advisory-check"
  | "ai-test"
  | "ai-run";

export type ExecutionStatus = "success" | "warning" | "blocked" | "failed";

export type ExecutionResultClass =
  | "success"
  | "warning-execution"
  | "blocked-preflight"
  | "blocked-canonical-integrity"
  | "blocked-policy"
  | "failed-runtime";

export type TraceExpectation =
  | "required-if-business-logic"
  | "optional-by-design";

export type TraceResult =
  | "emitted"
  | "not-emitted-by-design"
  | "not-emitted-blocked-before-logic"
  | "not-emitted-due-failure"
  | "not-enough-evidence";

export type CommandExecutionResult = {
  command: GovernedCommandName;
  status: ExecutionStatus;
  resultClass: ExecutionResultClass;
  reason?: string;
  warningReason?: string;
  traceExpectation: TraceExpectation;
  traceResult: TraceResult;
  nextAction?: string;
};

export type TraceExpectationCheck = {
  expected: TraceExpectation;
  actual: TraceResult;
  isMismatch: boolean;
  message: string;
};

export type CommandExecutionContract = {
  preconditions: string[];
  gateOrder: string[];
  blockingConditions: string[];
  warningConditions: string[];
  outputExpectation: string;
  traceExpectation: TraceExpectation;
};

export const EXECUTION_CONTRACTS: Record<GovernedCommandName, CommandExecutionContract> = {
  start: {
    preconditions: ["ops-dist startup path available", "state visibility checks available"],
    gateOrder: [
      "startup path selected",
      "preflight evaluated",
      "canonical integrity evaluated",
      "doctor diagnostics evaluated",
      "document governance evaluated",
      "session-entry verdict returned",
    ],
    blockingConditions: [
      "preflight blocking",
      "canonical integrity blocking",
      "doctor blocking",
      "document governance blocking",
    ],
    warningConditions: [
      "preflight warning",
      "doctor warning",
      "document governance warning",
    ],
    outputExpectation: "single coherent read-only session-entry report with verdict",
    traceExpectation: "optional-by-design",
  },
  preflight: {
    preconditions: ["ops-dist startup path available"],
    gateOrder: ["startup path selected", "preflight evaluated", "result returned"],
    blockingConditions: ["dist missing", "dependency invalid", "canonical integrity blocking"],
    warningConditions: ["environment mismatch", "bootstrap-allowed canonical gap"],
    outputExpectation: "structured readiness checks + actionable next action",
    traceExpectation: "optional-by-design",
  },
  init: {
    preconditions: ["preflight gate in ops flow", "canonical integrity evaluated"],
    gateOrder: [
      "startup path selected",
      "preflight evaluated",
      "canonical integrity evaluated",
      "init bootstrap logic executed",
      "trace emitted",
      "final status returned",
    ],
    blockingConditions: ["unsafe canonical reuse", "policy/canonical corruption"],
    warningConditions: ["bootstrap-required path allowed in init flow"],
    outputExpectation: "bootstrap vs blocked unsafe reuse clearly distinguished",
    traceExpectation: "required-if-business-logic",
  },
  "load-data": {
    preconditions: ["load-data type declared", "read-only project context readable"],
    gateOrder: [
      "startup path selected",
      "load-data arguments parsed",
      "read-only sources loaded",
      "prompt composed",
      "result returned",
    ],
    blockingConditions: ["unsupported load-data type", "read-only source access failure that prevents prompt generation"],
    warningConditions: ["partial source availability; fallback wording used"],
    outputExpectation: "copy-paste-ready plain-text prompt for new room bootstrap",
    traceExpectation: "optional-by-design",
  },
  migrate: {
    preconditions: ["migration source/target declared", "project path resolved", "inspection and plan completed"],
    gateOrder: [
      "startup path selected",
      "migration inspect completed",
      "migration plan completed",
      "mutation guard evaluated (apply mode)",
      "migration apply executed (or dry-run only)",
      "migration verification completed",
      "final migration report returned",
    ],
    blockingConditions: ["unsupported source/target", "unsafe project path", "dual-state conflict without force", "mutation guard denied"],
    warningConditions: ["legacy references detected", "missing lifecycle/scope normalized", "dry-run mode"],
    outputExpectation: "inspect-plan-apply-verify migration report with explicit blockers and warnings",
    traceExpectation: "required-if-business-logic",
  },
  status: {
    preconditions: ["preflight gate in ops flow", "canonical integrity safe reuse"],
    gateOrder: [
      "startup path selected",
      "preflight evaluated",
      "canonical integrity evaluated",
      "read-only status logic executed",
      "trace emitted",
      "final status returned",
    ],
    blockingConditions: ["canonical integrity blocking"],
    warningConditions: ["diagnostic warning from runtime evidence"],
    outputExpectation: "read-only runtime summary without mutation",
    traceExpectation: "required-if-business-logic",
  },
  doctor: {
    preconditions: ["preflight gate in ops flow", "canonical integrity evaluated"],
    gateOrder: [
      "startup path selected",
      "preflight evaluated",
      "canonical integrity evaluated",
      "diagnostics executed (or fallback report)",
      "trace attempted",
      "final status returned",
    ],
    blockingConditions: ["canonical corruption preventing safe diagnostics"],
    warningConditions: ["non-blocking diagnostic gaps"],
    outputExpectation: "structured diagnostics with actionable recovery guidance",
    traceExpectation: "required-if-business-logic",
  },
  "core-doctor": {
    preconditions: ["core baseline policy available"],
    gateOrder: [
      "startup path selected",
      "core baseline scanned",
      "contamination reported",
      "result returned",
    ],
    blockingConditions: ["none (read-only diagnostic command)"],
    warningConditions: ["approved generated contamination", "unapproved non-core contamination", "missing baseline core paths"],
    outputExpectation: "read-only core contamination report with baseline comparison",
    traceExpectation: "optional-by-design",
  },
  "core-clean": {
    preconditions: ["core baseline policy available", "approved removable path set resolved"],
    gateOrder: [
      "startup path selected",
      "core baseline scanned",
      "approved generated paths selected",
      "clean applied (or dry-run reported)",
      "post-clean baseline scanned",
      "result returned",
    ],
    blockingConditions: ["approved path removal failure"],
    warningConditions: ["unapproved contamination remains", "dry-run mode"],
    outputExpectation: "strictly-approved contamination clean with explicit action log",
    traceExpectation: "required-if-business-logic",
  },
  "core-restore": {
    preconditions: ["core baseline policy available"],
    gateOrder: [
      "startup path selected",
      "core clean phase executed",
      "baseline structure verified",
      "preflight/canonical checks evaluated",
      "final restore verdict returned",
    ],
    blockingConditions: ["unapproved contamination remains", "missing baseline core paths", "preflight blocking", "hard canonical blocking"],
    warningConditions: ["bootstrap canonical warning", "dry-run mode", "approved contamination still present"],
    outputExpectation: "single restore verdict with baseline and check evidence",
    traceExpectation: "required-if-business-logic",
  },
  "doc-check": {
    preconditions: ["docs/zmos structure resolvable"],
    gateOrder: [
      "startup path selected",
      "document index scanned",
      "schema/naming checks evaluated",
      "result returned",
    ],
    blockingConditions: ["duplicate document_id", "governed document schema invalid", "governed naming invalid"],
    warningConditions: ["orphan documents", "trace linkage warnings"],
    outputExpectation: "document governance summary with actionable findings",
    traceExpectation: "optional-by-design",
  },
  "doc-index": {
    preconditions: ["docs/zmos structure resolvable"],
    gateOrder: [
      "startup path selected",
      "document index scanned",
      "filters applied",
      "result returned",
    ],
    blockingConditions: ["document governance blocking state"],
    warningConditions: ["orphan documents", "trace linkage warnings"],
    outputExpectation: "filtered document listing with governance status",
    traceExpectation: "optional-by-design",
  },
  "doc-doctor": {
    preconditions: ["docs/zmos structure resolvable"],
    gateOrder: [
      "startup path selected",
      "document index scanned",
      "structure checks evaluated",
      "linkage hints evaluated",
      "result returned",
    ],
    blockingConditions: ["document governance blocking state"],
    warningConditions: ["orphan documents", "trace linkage warnings"],
    outputExpectation: "document governance diagnostics summary",
    traceExpectation: "optional-by-design",
  },
  "workflow-list": {
    preconditions: ["startup path selected"],
    gateOrder: ["startup path selected", "workflow registry loaded", "result returned"],
    blockingConditions: ["workflow registry missing"],
    warningConditions: [],
    outputExpectation: "read-only governance visibility output",
    traceExpectation: "optional-by-design",
  },
  "workflow-coverage-check": {
    preconditions: ["workflow policy file readable"],
    gateOrder: ["startup path selected", "policy coverage evaluated", "result returned"],
    blockingConditions: ["critical command mapped to unknown workflow"],
    warningConditions: ["missing critical command policy mapping"],
    outputExpectation: "coverage report for critical workflow surface",
    traceExpectation: "optional-by-design",
  },
  "workflow-runtime-check": {
    preconditions: ["preflight gate in ops flow", "canonical integrity safe reuse"],
    gateOrder: [
      "startup path selected",
      "preflight evaluated",
      "canonical integrity evaluated",
      "policy/governance checks applied",
      "workflow logic executed",
      "trace emitted",
      "final status returned",
    ],
    blockingConditions: ["invalid policy", "denied policy actions", "canonical blocking state"],
    warningConditions: ["diagnostic warning propagated from doctor"],
    outputExpectation: "policy-aligned runtime-check with no advisory AI invocation",
    traceExpectation: "required-if-business-logic",
  },
  "workflow-advisory-check": {
    preconditions: ["preflight gate in ops flow", "canonical integrity safe reuse"],
    gateOrder: [
      "startup path selected",
      "preflight evaluated",
      "canonical integrity evaluated",
      "policy/governance checks applied",
      "advisory permission validated",
      "workflow logic executed",
      "trace emitted",
      "final status returned",
    ],
    blockingConditions: ["invalid policy", "advisory permission denied", "canonical blocking state"],
    warningConditions: ["diagnostic warning propagated from doctor"],
    outputExpectation: "governed advisory-check with policy-bounded advisory invocation",
    traceExpectation: "required-if-business-logic",
  },
  "ai-test": {
    preconditions: ["canonical integrity safe reuse", "AI_PROVIDER resolved"],
    gateOrder: [
      "payload validation executed",
      "execution contract enforced",
      "AI call executed",
      "result validation executed",
      "trace emitted",
    ],
    blockingConditions: ["payload validation failure", "contract enforcement failure", "empty AI result"],
    warningConditions: ["trace write failure after successful AI call"],
    outputExpectation: "smoke test result printed to stdout confirming AI integration is operational",
    traceExpectation: "required-if-business-logic",
  },
  "ai-run": {
    preconditions: ["canonical integrity safe reuse", "AI_PROVIDER resolved", "task payload resolvable"],
    gateOrder: [
      "payload resolved (inline default or --payload file)",
      "payload validation executed",
      "execution contract enforced",
      "AI call executed",
      "result validation executed",
      "trace emitted",
    ],
    blockingConditions: [
      "payload file unreadable or malformed",
      "payload validation failure",
      "contract enforcement failure",
      "empty AI result",
    ],
    warningConditions: ["trace write failure after successful AI call"],
    outputExpectation: "governed AI task result printed to stdout with full trace record emitted",
    traceExpectation: "required-if-business-logic",
  },
};

export function renderCommandExecutionResult(result: CommandExecutionResult): string {
  const lines = [
    "Execution Result",
    `- Command: ${result.command}`,
    `- Execution Status: ${result.status}`,
    `- Result Class: ${result.resultClass}`,
    `- Trace Expectation: ${result.traceExpectation}`,
    `- Trace Result: ${result.traceResult}`,
  ];

  if (result.reason) {
    lines.push(`- Reason: ${result.reason}`);
  }

  if (result.warningReason) {
    lines.push(`- Warning: ${result.warningReason}`);
  }

  if (result.nextAction) {
    lines.push(`- Next Action: ${result.nextAction}`);
  }

  return lines.join("\n");
}

export function evaluateTraceExpectation(
  expected: TraceExpectation,
  actual: TraceResult,
): TraceExpectationCheck {
  if (expected === "required-if-business-logic" && actual !== "emitted") {
    return {
      expected,
      actual,
      isMismatch: true,
      message: "Trace expected to be emitted after business logic, but trace result is not emitted.",
    };
  }

  if (expected === "optional-by-design" && actual === "emitted") {
    return {
      expected,
      actual,
      isMismatch: true,
      message: "Trace marked optional-by-design but emitted; verify command trace policy.",
    };
  }

  return {
    expected,
    actual,
    isMismatch: false,
    message: "Trace expectation and result are coherent.",
  };
}
