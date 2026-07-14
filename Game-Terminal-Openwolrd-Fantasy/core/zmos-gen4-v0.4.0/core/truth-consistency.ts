type ConsistencyStatus = "CONSISTENT" | "DRIFT";
type DriftLevel = 0 | 1 | 2;
type EscalationVerdict = "PASS" | "WARNING" | "CONTINUE-WITH-RISK";

export type ConsistencyReport = {
  status: ConsistencyStatus;
  driftLevel: DriftLevel;
  escalationVerdict: EscalationVerdict;
  escalationAction: "NONE" | "WARN" | "SOFT_BLOCK";
  reason: "NONE" | "NON_CRITICAL_DRIFT" | "CRITICAL_DRIFT";
  hardBlock: boolean;
  warnings: string[];
  checks: {
    git_branch: "match" | "drift" | "not-enough-evidence";
    commit_sha: "match" | "drift" | "not-enough-evidence";
    target_environment: "match" | "drift" | "not-enough-evidence";
    phase_or_gate: "match" | "drift" | "not-enough-evidence";
  };
};

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function normalizeEnv(value: string | null): string | null {
  if (!value) return null;
  const normalized = value.trim().toLowerCase();
  if (normalized === "prod") return "production";
  if (normalized === "dev") return "development";
  if (normalized === "stage") return "staging";
  return normalized;
}

export function evaluateTruthConsistency(args: {
  truth: unknown | null;
  currentGit?: { commit: string | null; branch: string | null } | null;
  currentEnv?: string | null;
}): ConsistencyReport {
  const report: ConsistencyReport = {
    status: "CONSISTENT",
    driftLevel: 0,
    escalationVerdict: "PASS",
    escalationAction: "NONE",
    reason: "NONE",
    hardBlock: false,
    warnings: [],
    checks: {
      git_branch: "not-enough-evidence",
      commit_sha: "not-enough-evidence",
      target_environment: "not-enough-evidence",
      phase_or_gate: "match",
    },
  };

  const truthObj = (typeof args.truth === "object" && args.truth !== null ? args.truth : null) as
    | Record<string, unknown>
    | null;
  if (!truthObj) return report;

  const truthCode = truthObj.code_ref as Record<string, unknown> | undefined;
  const truthEnv = truthObj.env_ref as Record<string, unknown> | undefined;
  const truthBranch = asString(truthCode?.branch);
  const truthCommit = asString(truthCode?.commit) || asString(truthCode?.commit_sha);
  const truthTargetEnv = normalizeEnv(asString(truthEnv?.target_env));

  const effectiveBranch = asString(args.currentGit?.branch);
  const effectiveCommit = asString(args.currentGit?.commit);
  const effectiveEnv = normalizeEnv(asString(args.currentEnv));

  if (truthBranch && effectiveBranch) {
    report.checks.git_branch = truthBranch === effectiveBranch ? "match" : "drift";
  }
  if (truthCommit && effectiveCommit) {
    report.checks.commit_sha = truthCommit === effectiveCommit ? "match" : "drift";
  }
  if (truthTargetEnv && effectiveEnv) {
    report.checks.target_environment = truthTargetEnv === effectiveEnv ? "match" : "drift";
  } else if (truthTargetEnv && !effectiveEnv) {
    // Missing runtime env evidence is treated as unsafe when truth requires a target environment.
    report.checks.target_environment = "drift";
  }

  for (const [name, result] of Object.entries(report.checks)) {
    if (name === "phase_or_gate") continue;
    if (result === "drift") {
      report.status = "DRIFT";
      report.warnings.push(`TRUTH_DRIFT:${name}`);
    }
  }

  const criticalDrift =
    report.checks.commit_sha === "drift" || report.checks.target_environment === "drift";
  const hasAnyDrift = report.status === "DRIFT";

  if (criticalDrift) {
    report.driftLevel = 2;
    report.escalationVerdict = "CONTINUE-WITH-RISK";
    report.escalationAction = "SOFT_BLOCK";
    report.reason = "CRITICAL_DRIFT";
    report.hardBlock = true;
  } else if (hasAnyDrift) {
    report.driftLevel = 1;
    report.escalationVerdict = "WARNING";
    report.escalationAction = "WARN";
    report.reason = "NON_CRITICAL_DRIFT";
  }

  return report;
}
