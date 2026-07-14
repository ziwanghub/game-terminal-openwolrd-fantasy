# Ollama Context Layer

`ai/ollama/context/` stores approved, curated project context for Ollama.
Its purpose is to help Ollama understand the project through controlled summaries instead of unrestricted repository reading.

This folder is intended for governance-first, read-only-oriented context artifacts such as:

- project map
- repository digest
- selected file summaries
- approved context snapshots

## Usage

Context files in this folder should be:

- evidence-based
- concise
- derived from observable repository state
- safe for Ollama to read without granting broader repository authority

These files help Codex prepare disciplined context for Ollama.
They do not replace canonical truth and must not override official records in `.z-mos/`, `core/`, `contracts/`, `governance/`, or `docs/`.
