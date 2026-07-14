// REMOVED in Z-MOS v1.3.0 (Fix-first Lean)
// This command required ai/ollama/context/ files that were not shipped,
// causing ENOENT failures at runtime. Removed as part of the Fix-first Lean release.
// Use your agent (Claude Code, Cursor, etc.) directly for repository analysis.
// Governed AI execution remains available via: zcl ai run

export async function runAnalyzeCommand(): Promise<void> {
  console.error(
    [
      "zcl ai analyze: removed in Z-MOS v1.3.0",
      "",
      "This command has been removed. It depended on context files that are not",
      "part of this release and failed with ENOENT errors at runtime.",
      "",
      "Alternatives:",
      "  - Use your AI agent (Claude Code, Cursor, etc.) directly for analysis",
      "  - Use governed task execution: zcl ai run --payload <file.json>",
    ].join("\n"),
  );
  process.exitCode = 1;
}
