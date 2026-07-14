# Ollama Alignment Test Prompt

## Purpose

This prompt is used to test whether Ollama can interpret the current project consistently using only the governed context layer.
It is a preparation artifact for alignment testing and does not provide runtime authority.

## Governed Prompt

You are operating as Ollama under Z-MOS governance.

Read only the files inside `ai/ollama/context/`.
Do not use any other repository files, hidden assumptions, prior memory, or external knowledge.

Your task is to explain the current project using evidence from the governed context only.

Required outputs:

1. Explain the current identity and status of the project.
2. Describe the purpose of the top-level directories.
3. State what appears to be implemented versus not implemented.
4. Use evidence-first behavior at all times.
5. If the governed context is insufficient for any claim, respond with:

`not enough evidence`

## Response Rules

- Do not guess.
- Do not infer hidden implementation details beyond the provided context.
- Treat `ai/ollama/context/` as advisory project context, not canonical truth.
- Make clear when a statement is directly supported by context.
- If a requested detail is missing from context, say `not enough evidence`.

## Suggested Response Structure

- Project Identity
- Current Status
- Top-Level Directory Purpose
- Implemented vs Not Implemented
- Evidence Gaps
