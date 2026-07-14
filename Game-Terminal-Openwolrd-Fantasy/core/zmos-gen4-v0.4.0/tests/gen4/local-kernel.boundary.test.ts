import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import {
  formatBoundaryFindings,
  scanLocalKernelBoundary,
  scanTextForBoundaryViolations,
} from "./helpers/no-network-boundary.ts";

test("current local-kernel source passes static no-network boundary guard", () => {
  const findings = scanLocalKernelBoundary({
    localKernelRoot: path.resolve("core/gen4/local-kernel"),
    fsAllowedFiles: [path.resolve("core/gen4/local-kernel/trace-persistence.ts")],
  });

  assert.equal(findings.length, 0, formatBoundaryFindings(findings));
});

test("fixture/helper files do not import forbidden network modules", () => {
  const source = `
    import { runLocalIntent } from "../../../core/gen4/local-kernel/harness.ts";
    import { buildValidTrustEnvelope } from "./trust-envelope.fixtures.ts";
  `;

  const findings = scanTextForBoundaryViolations({
    source_text: source,
    file_path: "tests/gen4/fixtures/local-kernel.fixtures.ts",
    allow_fs_modules: false,
  });

  assert.equal(findings.length, 0, formatBoundaryFindings(findings));
});

test("synthetic forbidden ES import is detected", () => {
  const source = `import http from "node:http";`;
  const findings = scanTextForBoundaryViolations({
    source_text: source,
    file_path: "synthetic.ts",
    allow_fs_modules: false,
  });

  assert.equal(findings.some((finding) => finding.kind === "forbidden-es-import"), true);
});

test("synthetic dynamic import is detected", () => {
  const source = `const x = import("node:https");`;
  const findings = scanTextForBoundaryViolations({
    source_text: source,
    file_path: "synthetic.ts",
    allow_fs_modules: false,
  });

  assert.equal(findings.some((finding) => finding.kind === "forbidden-dynamic-import"), true);
});

test("synthetic require() forbidden import is detected", () => {
  const source = `const x = require("node:net");`;
  const findings = scanTextForBoundaryViolations({
    source_text: source,
    file_path: "synthetic.ts",
    allow_fs_modules: false,
  });

  assert.equal(findings.some((finding) => finding.kind === "forbidden-require"), true);
});

test("approved fs/path usage in trace persistence remains allowed", () => {
  const source = `
    import { appendFile } from "node:fs/promises";
    import path from "node:path";
  `;

  const findings = scanTextForBoundaryViolations({
    source_text: source,
    file_path: "core/gen4/local-kernel/trace-persistence.ts",
    allow_fs_modules: true,
  });

  assert.equal(findings.length, 0, formatBoundaryFindings(findings));
});

test("unapproved fs usage fails guard deterministically", () => {
  const source = `import { readFileSync } from "node:fs";`;
  const findings = scanTextForBoundaryViolations({
    source_text: source,
    file_path: "core/gen4/local-kernel/replay.ts",
    allow_fs_modules: false,
  });

  assert.equal(findings.length > 0, true);
  assert.equal(findings[0].kind, "unapproved-fs-import");
});
