# Mission: protocol-230 reproducibility audit + protocol-240 generative discovery

**Date opened:** 2026-11-15
**Status:** Part A complete; Part B pre-registered and executed separately.

This document is the map for the two-part research task:

- **Part A — reproducibility audit.** Independently re-run an existing sealed
  experiment from a clean process and state, on evidence, whether it
  reproduces.
- **Part B — new discovery experiment.** Ask whether the system can *generate*
  candidate algorithms and find a real improvement, under a frozen
  pre-registration (`spec/research/240_GENERATIVE_COMPOSITION_SEARCH.md`).

The two parts are deliberately separate: a reproduction claim is about
*trusting past evidence*, a discovery claim is about *new evidence*. Mixing
them would let a successful reproduction imply credibility for a new result
that has not earned it.

## Part A — does protocol-230-v1 reproduce?

`scripts/verify_bundle.py` was written for this audit. It is generic (not
special-cased to protocol 230) and makes five checks:

1. **Integrity at rest** — every SHA-256 in `checksums.json` is recomputed from
   the committed bytes.
2. **Configuration from the evidence** — the CLI invocation is rebuilt from the
   committed `manifest.json`, not from current code defaults. Bundles that
   predate the explicit `workload` field recover it from the manifest's
   substrate fingerprint (environment version, task-suite version, held-out
   family, operator set); if that fingerprint is ambiguous the verifier
   *refuses to guess* and fails.
3. **Clean re-execution** — the experiment runs in a separate process with a
   fresh temporary SQLite database and a fresh artifact directory, so no state
   from the original run can be reused.
4. **Comparison** — raw per-attempt streams (`conditions/**/*.jsonl`) and
   `report.md` must match **byte-for-byte**; derived JSON must match
   **numerically at 1e-9** (the documented D-10 floating-point contract).
5. **Auditable exclusions** — wall-clock fields (`created_at`,
   `measured_operator_seconds`, `evaluation_seconds`) are excluded from
   comparison and *listed in the verdict*; additive metadata keys are accepted
   only when individually allow-listed with a written reason
   (`ADDITIVE_FIELDS`). Nothing is ignored silently.

### Part A result

| bundle | workload | integrity | re-execution | verdict |
|---|---|---|---|---|
| `experiments/protocol-230-v1` | toy (recovered) | 28/28 files | 28/28 artifacts | **REPRODUCED** |
| `experiments/protocol-239-v1` | transform | 44/44 files | 44/44 artifacts | **REPRODUCED** |

Protocol-239-v1's *first* verification attempt failed on exactly one field,
`workload_metadata.measured_operator_seconds`, a wall-clock duration; the other
43 artifacts already matched. After that field was registered as excluded, the
re-run reproduced all 44 artifacts. The exclusion is listed in the verdict
(`excluded_volatile_fields`), not applied silently — see the note below.

Two honest notes:

- Protocol-230-v1 was sealed before the `workload` field existed. The
  re-executed manifest therefore contains one *additive* key (`workload`) that
  the committed manifest does not. That key records which substrate the run
  used by construction; it cannot change a recorded result, and it is
  allow-listed by exact path with that reason. Every shared field matches.
- Protocol-239-v1 records `measured_operator_seconds`, a wall-clock duration.
  Re-execution on a different machine necessarily differs there. The field is
  excluded, listed in the verdict, and is documented in the protocol as
  recorded-but-never-read: no search decision and no statistic consumes it.
  Attempt counts, credit totals, seeds, and all derived statistics still match
  at 1e-9.

Reproduce either with:

```bash
cd implementation/algolab
.venv/bin/python scripts/verify_bundle.py experiments/protocol-230-v1
.venv/bin/python scripts/verify_bundle.py experiments/protocol-239-v1
```

## Part B — can the system generate and validate a better algorithm?

See `spec/research/240_GENERATIVE_COMPOSITION_SEARCH.md` for the frozen
pre-registration (substrate, arms, hypotheses, failure criteria) and
`implementation/algolab/experiments/protocol-240-v1/` for the sealed evidence
bundle. The experiment README next to that bundle is the authoritative report:

- research question and pre-registered hypotheses H1–H5;
- the 585-program closed grammar and why it is small on purpose;
- five arms (three of which generate programs; one is the composition-free
  control; one is the feedback ablation);
- baseline, metric, seeds, budget, and the two-replicate discovery gate;
- raw per-attempt streams for every arm;
- the champion-transfer check on the held-out dataset;
- the outcome class with its bound interpretation.

### Part B result (one confirmatory run, sealed, reproduced)

Reproduction of protocol 240 first returned `NOT REPRODUCED` on exactly two
wall-clock items (the `report.md` bytes and `compute.evaluation_seconds`); after
defect D-11 was fixed (deterministic report, cold cache per run) the bundle was
re-sealed with a fresh SQLite database and re-executed from a clean process.
Verdict: **REPRODUCED**, 35/35 integrity, 35/35 artifacts, with
`created_at`, `measured_operator_seconds` and `compute.evaluation_seconds` listed
in the verdict as excluded wall-clock fields
(`implementation/algolab/experiments/protocol-240-v1/reproduction-verification.json`).
Every science number is identical across the seals: 2382 attempts, 1321 real CV
evaluations, 1061 cache hits, the same validated programs, the same H1–H5
verdicts.

| question | answer |
|---|---|
| Did any arm generate programs that clear the 2-replicate gate on real data? | **Yes** — 14 (arm, program) validated pairs spanning **9 unique programs** (C1, literally) |
| Did a history-using arm beat uniform random search on distinct/credit, both families, BH-corrected? | **No** — H1, H2, H4, H5 all false |
| Did any arm's champion transfer to the held-out family with both replicates positive? | **No** — 4 arms converge on `sqrt` (−0.0021 on digits); random's `log1p+sqrt+poly2-top5` scores −0.0167 |
| Outcome class | **C** |

Two things this result does **not** say: that composition is worthless in
general (the space is 585 programs over three small tabular datasets, and
`alpha` is nearly saturated), and that random search is always strong (it is
strong *here*, where the space is small and per-credit cost penalises longer
programs by construction). Details, including three errata found while writing
the report — registered 900 held-out rows vs 600 executed; a "promotion
threshold" line that does not describe the executed gate; and a random control
that samples program *length* uniformly rather than uniformly over the 585
programs, which **strengthens** the baseline — are in
`experiments/protocol-240-v1/README.md` §6, §8.1 and spec §14.

## Claim discipline

What this mission does **not** claim, in either part:

- that reproducing 230/239 validates the *search mechanism* — it validates
  that the sealed evidence is what it says it is;
- that protocol 240 shows "the system invents algorithms" — its space is a
  585-program grammar of feature transforms over three small tabular datasets;
- that any arm beat random search unless the pre-registered adjusted-p and CI
  conditions were met on both training families.

The final response accompanying this work separates (A) implemented,
(B) demonstrated, (C) unproven, and (D) next steps, per the task standard.
