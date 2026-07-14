# Ollama Workspace

`ai/ollama/` is the governed local workspace for Ollama inside `zmos-core`.
It exists to support Ollama's working context, temporary memory, prompt assets, cache data, and generated reports without changing canonical project truth.

This workspace is for learning, analysis, prompts, cache, and reports.
It is a support area for local AI work, not an official system-of-record.

## Subfolders

- `context/`: approved reference context prepared for Ollama to read during local tasks
- `memory/`: temporary working memory and retained notes for local AI assistance
- `prompts/`: prompt templates, prompt fragments, and controlled instruction assets
- `cache/`: non-canonical cached outputs or intermediate artifacts
- `reports/`: generated analysis reports and advisory outputs

## Governance Meaning

Ollama may write only inside `ai/ollama/`.
Files here do not override official Z-MOS state, governance, contracts, or documentation.

Canonical system truth remains in:

- `.z-mos/`
- `core/`
- `contracts/`
- `governance/`
- `docs/`

Any content under `ai/ollama/` should be treated as supporting material unless an authorized actor promotes it into a canonical location.
