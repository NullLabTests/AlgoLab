# ABORTED — not evidence, do not cite

This directory archives an **interrupted, partial** run of the higher-N
experiment. It is kept **only as provenance** for why no `protocol-236-v1`
bundle exists; it is **not** a sealed bundle and **must never be cited as a
result** (audit finding D-2, `docs/quality/protocol-236-conflict.md`).

## What happened

- `manifest.json` (`created_at` 2026-09-19T15:06:51Z) and the two prior
  knowledge snapshots were written.
- The run then aborted before any conditions were executed. The committing
  `HEAD` message names the cause: shell shebang error 126, a stale sqlite WAL
  lock, and the tool time cap. The advance was **not** executed.
- Therefore only three files exist here; there is **no** `conditions/`,
  `statistics.json`, `report.md`, or `checksums.json`.

## Why it is archived (and not deleted) here

- It documents the aborted higher-N attempt honestly (acceptance criterion B9),
  so provenance is durable rather than living only as an untracked file.
- It was moved out of `experiments/protocol-236-v1/` because that path is
  reserved for the **future sealed** bundle, and the run driver
  (`scripts/run_protocol_236.py`) refuses to start when a `manifest.json`
  already exists there.

## Two inconsistencies this archive records

1. The `notes` claim the alpha discovery margin moved `0.005 -> 0.0035` and the
   gate version `1.0.0 -> 1.1.0`, but the recorded fields do **not** reflect
   that (`promotion_threshold` is still `0.005`; `discovery_gate_version` is
   absent/`1.0.0`). The margin lever was never implemented — see the
   pre-registration `spec/research/236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md`.
2. This run used `"workload": "hpo"` (higher-N HPO), consistent with the
   resolved identity **236 = higher-N real-workload promotion**; the S2
   substrate was re-designated **protocol 237**
   (`spec/research/237_SECOND_SUBSTRATE_TRANSFER.md`).

## Integrity

Nothing here is checksummed, and nothing here is loaded by the test suite; the
artifact-integrity guard enumerates only sealed bundles (those with a
`checksums.json`, i.e. direct children of `experiments/`). This directory is a
direct child of `experiments/_aborted/`, so it is intentionally outside that
set. Do not add a `checksums.json` here.
