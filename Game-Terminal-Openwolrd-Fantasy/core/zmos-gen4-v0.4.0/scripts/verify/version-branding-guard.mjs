#!/usr/bin/env node

import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

const ROOT = process.cwd();

const STALE_PATTERNS = [
  /Z-MOS v3\.0\.0/g,
  /Z-MOS v3\.0\.1/g,
  /v3\.0\.0 "Purity"/g,
  /v3\.0\.1 "Purity"/g,
];

const HISTORICAL_ALLOWLIST = [
  "docs/legacy/",
  "docs/roadmap/",
  "docs/v3.0.1-purity-status.md",
];

function toPosix(value) {
  return value.split(path.sep).join("/");
}

function isHistoricalAllowed(relPath) {
  return HISTORICAL_ALLOWLIST.some((entry) =>
    entry.endsWith("/") ? relPath.startsWith(entry) : relPath === entry,
  );
}

function listFilesRecursive(baseDir) {
  const out = [];
  const stack = [baseDir];
  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of readdirSync(current)) {
      const fullPath = path.join(current, entry);
      const s = statSync(fullPath);
      if (s.isDirectory()) {
        stack.push(fullPath);
      } else if (s.isFile()) {
        out.push(fullPath);
      }
    }
  }
  return out;
}

function collectTargets() {
  const targets = new Set();

  for (const file of listFilesRecursive(path.join(ROOT, "bin"))) {
    targets.add(file);
  }
  for (const file of listFilesRecursive(path.join(ROOT, "cli"))) {
    targets.add(file);
  }

  targets.add(path.join(ROOT, "sdk", "version.ts"));

  for (const file of readdirSync(path.join(ROOT, "docs"))) {
    const full = path.join(ROOT, "docs", file);
    if (statSync(full).isFile() && file.endsWith(".md")) {
      targets.add(full);
    }
  }
  for (const file of listFilesRecursive(path.join(ROOT, "docs", "architecture"))) {
    targets.add(file);
  }
  for (const file of listFilesRecursive(path.join(ROOT, "docs", "operations"))) {
    targets.add(file);
  }

  return [...targets];
}

function findViolations(filePath) {
  const relPath = toPosix(path.relative(ROOT, filePath));
  if (isHistoricalAllowed(relPath)) {
    return [];
  }

  const content = readFileSync(filePath, "utf8");
  const violations = [];

  for (const pattern of STALE_PATTERNS) {
    pattern.lastIndex = 0;
    let match;
    while ((match = pattern.exec(content)) !== null) {
      const before = content.slice(0, match.index);
      const line = before.split("\n").length;
      violations.push({
        relPath,
        line,
        token: match[0],
      });
    }
  }

  return violations;
}

function main() {
  const targets = collectTargets();
  const violations = [];

  for (const filePath of targets) {
    violations.push(...findViolations(filePath));
  }

  if (violations.length > 0) {
    console.error("version-branding-guard: FAILED");
    for (const v of violations) {
      console.error(`- ${v.relPath}:${v.line} -> ${v.token}`);
    }
    process.exit(1);
  }

  console.log("version-branding-guard: PASS");
  console.log(`scanned_files=${targets.length}`);
}

main();
