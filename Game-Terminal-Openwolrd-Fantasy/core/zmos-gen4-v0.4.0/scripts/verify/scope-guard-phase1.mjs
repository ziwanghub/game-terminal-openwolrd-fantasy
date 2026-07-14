import assert from "node:assert/strict";
import { evaluateScopeGuard } from "../../dist/core/scope-guard.js";

function testStrictEmptyAllowListFails() {
  const result = evaluateScopeGuard(
    {
      schema_version: "2.0.0",
      mode: "strict",
      allowed_files: [],
      allowed_patterns: [],
    },
    ["core/scope-guard.ts"],
  );

  assert.equal(result.status, "FAIL");
  assert.equal(result.mode, "strict");
  assert.ok(result.violations.some((v) => v.reason === "EMPTY_SCOPE_NOT_ALLOWED_IN_STRICT_MODE"));
}

function testAdvisoryEmptyAllowListPassesWhenNoProtectedViolation() {
  const result = evaluateScopeGuard(
    {
      schema_version: "2.0.0",
      mode: "advisory",
      allowed_files: [],
      allowed_patterns: [],
      protected_files: [],
      protected_patterns: [],
    },
    ["docs/readme.md"],
  );

  assert.equal(result.status, "PASS");
}

function main() {
  testStrictEmptyAllowListFails();
  testAdvisoryEmptyAllowListPassesWhenNoProtectedViolation();
  console.log("scope-guard-phase1: PASS");
}

main();
