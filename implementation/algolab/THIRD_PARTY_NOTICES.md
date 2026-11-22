# Third-party notices

## DREAM-RSI (ideas adapted, no source copied)

- Project: https://github.com/google-research/dream-rsi
- Inspected commit: `8ec35bd2538220517ce1bfca4282db21b8c518db`
- Copyright: 2026 Google LLC
- License: Apache License 2.0 (full text in the upstream `LICENSE` file).

AlgoLab's `src/algolab/meta_search/` reimplements the following ideas from
DREAM-RSI using AlgoLab's own infrastructure: frozen replay traces, prefix-only
replay decisions with explicit counterfactual uncertainty, a small versioned
policy contract, and qualification-gated fail-closed promotion. No DREAM-RSI
source files (and no files from its `third_party/` tree, which is MIT, or its
AGPL-3.0 fetched tasks) were copied into this repository.

Full audit: `docs/research/DREAM_RSI_INTEGRATION_AUDIT.md`.
