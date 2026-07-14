import { execSync } from "node:child_process";

export function getGitContext() {
  try {
    const hash = execSync("git rev-parse --short HEAD", { stdio: "pipe" }).toString().trim();
    const branch = execSync("git branch --show-current", { stdio: "pipe" }).toString().trim();

    return {
      commit: hash || null,
      branch: branch || null,
    };
  } catch {
    return {
      commit: null,
      branch: null,
    };
  }
}

export function getGitChangedFiles(): string[] {
  try {
    const unstaged = execSync("git diff --name-only", { stdio: "pipe" }).toString().trim();
    const staged = execSync("git diff --cached --name-only", { stdio: "pipe" }).toString().trim();
    const untracked = execSync("git ls-files --others --exclude-standard", { stdio: "pipe" }).toString().trim();

    const files = new Set<string>();

    if (unstaged) {
      unstaged.split("\n").forEach((f) => files.add(f.trim()));
    }
    if (staged) {
      staged.split("\n").forEach((f) => files.add(f.trim()));
    }
    if (untracked) {
      untracked.split("\n").forEach((f) => files.add(f.trim()));
    }

    return Array.from(files).filter(Boolean);
  } catch {
    return [];
  }
}
