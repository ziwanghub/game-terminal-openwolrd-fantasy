# Alignment Test Report

## Purpose

This file is a simple template for recording an Ollama alignment test performed against the governed context layer.
It is an advisory report only and does not modify canonical system truth.

## Test Inputs

- Prompt file:
- Context files used:
- Test date:
- Test operator:

## Ollama Response

Paste the full Ollama response here.

## Alignment Result

- Overall result:
- Correctly aligned points:
- Misaligned points:

## Evidence Issues

- Missing context:
- Ambiguous context:
- Unsupported claims:

## Recommended Context Improvements

- Improvement 1:
- Improvement 2:
- Improvement 3:

---

## Test Inputs

- Prompt file: `ai/ollama/prompts/alignment-test-prompt.md`
- Context files used:
- `ai/ollama/context/README.md`
- `ai/ollama/context/project-map.md`
- `ai/ollama/context/workspace-summary.md`
- `ai/ollama/context/zmos-framework-goal.md`
- Test date: `2026-03-18`
- Test operator: `Codex via terminal`

## Ollama Response

# Ollama Alignment Test Prompt Response

**Project Identity**
The current project is named Z-MOS.

**Current Status**
Based on the provided context, the project is in an early phase of development, focusing on governance and workspace preparation. The repository has been initialized with a minimal Node.js project structure (`zmos-core`), and `package.json` exists to declare ES module mode. However, most core implementation areas remain scaffolding and are not yet implemented.

**Top-Level Directory Purpose**
The provided context files (`project-map.md` and `workspace-summary.md`) describe the top-level directories as follows:
- `ai/`: contains governed workspace for Ollama support materials.
- `bin/`: intended CLI executable location.
- `cli/`: intended command gateway and routing layer.
- `contracts/`: intended shared contracts and schemas.
- `core/`: intended core runtime and bootstrap logic.
- `docs/`: documentation and Z-MOS planning materials.
- `governance/`: intended governance logic and rules.
- `scripts/`: intended helper or project scripts.
- `tests/`: intended test location.
- `trace/`: intended trace and evidence output layer.

**Implemented vs Not Implemented**
Based on the provided context, the following directories are not implemented:
- Most core implementation areas (`cli`, `core`, etc.).
- AI runtime code has not been added yet.
However, some preparation has been done for Ollama governance under `ai/ollama/`.

**Evidence Gaps**
While the context provides a clear outline of the project's structure and intended direction, there are gaps in evidence for certain claims:
- The current repository status is described in controlled summaries, but direct implementation details are not provided.
- Governance interpretation relies on approved documentation and planning materials.

To answer each part with evidence-first behavior:

1. The current identity and status of the project are derived from the `workspace-summary.md` file, which indicates that the project is named Z-MOS and is in an early phase focusing on governance and workspace preparation.
2. The purpose of the top-level directories is explained in the `project-map.md` file, which describes each directory's intended use based on the current repository structure.
3. As mentioned earlier, most core implementation areas are currently empty, indicating they are not yet implemented.
4. To maintain evidence-first behavior, I've relied solely on the provided context files (`README.md`, `project-map.md`, `workspace-summary.md`, and `zmos-framework-goal.md`) without inferring or guessing information not present in these documents.
5. Whenever a requested detail was missing from the context, I responded with "not enough evidence" as per the Response Rules.

## Alignment Result

- Overall result: `partial alignment`
- Correctly aligned points: identified the project as an early governance/workspace-preparation scaffold; described top-level directories consistently with `project-map.md`; correctly stated that most core areas are not yet implemented; recognized that AI runtime code is not yet present; stayed within the governed context scope
- Misaligned points: stated "The current project is named Z-MOS" too strongly when the prepared context distinguishes between the repository package identity `zmos-core` and the broader framework goal `Z-MOS`; claimed "the following directories are not implemented" but then summarized categories rather than directory-by-directory evidence; said it responded with `not enough evidence`, but no direct instance of that response was actually needed in the output

## Evidence Issues

- Missing context: a dedicated file that separates repository identity (`zmos-core`) from framework identity (`Z-MOS`)
- Ambiguous context: the current context mixes "project", "repository", and "framework" language, which can lead Ollama to collapse them into one identity
- Unsupported claims: the phrase "the project is named Z-MOS" is weaker than desired from an evidence-first standpoint because the repository summary more directly names the package `zmos-core`

## Recommended Context Improvements

- Improvement 1: add a `repository-identity.md` context file that explicitly distinguishes repo name, package identity, and framework identity
- Improvement 2: add an `implementation-status.md` context file with an evidence-based checklist for what exists versus what is still scaffold only
- Improvement 3: revise `workspace-summary.md` to say whether statements apply to the repository, the package, or the broader Z-MOS framework
