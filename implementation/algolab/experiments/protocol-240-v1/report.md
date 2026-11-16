# Cumulative Search Policy Comparison — protocol-240-v1

Protocol: 1.1.0 (see spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md)
Environment: generative-composition 1.0.0; families: alpha, beta; held-out: gamma
Budget per episode: 45.0 credits; episodes/trial: 4; trials (seeds): 10
Discovery gate: valid implementation AND effect_1 >= threshold AND effect_2 >= threshold (2-seed replication gate)

## Per-condition outcome

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| c-permuted | 8 | 1669.0 | 0.004793 | 292 |
| b-shuffled | 6 | 1702.0 | 0.003525 | 285 |
| random-program | 3 | 1520.0 | 0.001974 | 142 |
| greedy-history | 3 | 1586.0 | 0.001892 | 178 |
| evolutionary-archive | 4 | 1548.5 | 0.002583 | 160 |
| static-atoms | 6 | 1695.0 | 0.00354 | 280 |
| greedy-permuted | 3 | 1589.5 | 0.001887 | 173 |

## Pairwise comparisons (A vs B, A vs C, B vs C; BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| random-program | greedy-history | -0.000272 | -0.003092 | 0.002967 | 0.882559 | 1.000000 | -0.072 |
| random-program | evolutionary-archive | 0.000547 | -0.002335 | 0.003916 | 0.630185 | 1.000000 | 0.136 |
| random-program | static-atoms | 0.001447 | -0.000482 | 0.004079 | 0.501749 | 1.000000 | 0.340 |
| greedy-history | greedy-permuted | -0.000002 | -0.003659 | 0.004854 | 1.000000 | 1.000000 | -0.000 |

## Per-family comparisons (protocol §5 pairing: family × seed)

### family alpha

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| random-program | greedy-history | -0.001212 | -0.003636 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| random-program | evolutionary-archive | -0.001212 | -0.003636 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| random-program | static-atoms | -0.001212 | -0.003636 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| greedy-history | greedy-permuted | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |

Mean efficiency per condition: b-shuffled 0.000000, c-permuted 0.000000, evolutionary-archive 0.000000, greedy-history 0.000000, greedy-permuted 0.000000, random-program 0.001212, static-atoms 0.000000

### family beta

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| random-program | greedy-history | 0.000828 | -0.004687 | 0.007486 | 1.000000 | 1.000000 | 0.112 |
| random-program | evolutionary-archive | 0.002605 | -0.003297 | 0.009551 | 0.630185 | 1.000000 | 0.323 |
| random-program | static-atoms | 0.004316 | -0.000839 | 0.011502 | 0.501749 | 1.000000 | 0.518 |
| greedy-history | greedy-permuted | -0.000229 | -0.007643 | 0.009255 | 1.000000 | 1.000000 | -0.023 |

Mean efficiency per condition: b-shuffled 0.007208, c-permuted 0.009623, evolutionary-archive 0.005475, greedy-history 0.003697, greedy-permuted 0.003468, random-program 0.002870, static-atoms 0.007186


## Ablations (exploratory; p-values unadjusted)

| base | candidate | delta | p | d | note |
|---|---|---|---|---|---|

## Held-out transfer (gamma family)

Transfer evaluation on held-out family **gamma**, which was never included in the K0 prior.

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| random-program | 9 | 1519.0 | 0.005925 | 124 |
| greedy-history | 18 | 1534.5 | 0.01173 | 148 |
| evolutionary-archive | 25 | 1502.5 | 0.016639 | 150 |
| static-atoms | 31 | 1695.0 | 0.018289 | 280 |
| greedy-permuted | 20 | 1594.5 | 0.012543 | 154 |

### Held-out pairwise comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| random-program | greedy-history | 0.005544 | -0.001237 | 0.012219 | 0.184908 | 0.246543 | 0.717 |
| random-program | evolutionary-archive | 0.010831 | 0.005177 | 0.016167 | 0.006497 | 0.012994 | 1.631 |
| random-program | static-atoms | 0.012343 | 0.009226 | 0.016099 | 0.002499 | 0.009995 | 1.991 |
| greedy-history | greedy-permuted | 0.001014 | -0.005071 | 0.007188 | 0.829085 | 0.829085 | 0.108 |

### Promotion-criterion status (protocol 230 §5)

- C > A per training family: {'alpha': False, 'beta': False}
- C > B per training family: {'alpha': False, 'beta': False}
- gap persists on held-out vs A: False
- gap persists on held-out vs B: False

**promotion criterion NOT met; unmet components: greedy-history>A with adjusted p < 0.05 on >=2 families; greedy-history>B with adjusted p < 0.05 on >=2 families; gap persistence on held-out gamma**

## Adaptive-policy adaptation evidence (condition C)


## Interpretation: hypothesis not supported in this environment (A ≈ B ≈ C)
(outcome 4 in the pre-registered taxonomy)

## Limitations and scope

- The experiment uses a deterministic toy environment with known ground truth; results may not generalise to real workloads.
- The held-out family provides evidence that the adaptive advantage transfers beyond the training families; it does not by itself rule out all benchmark-specific adaptation or memorisation.
- The permuted-outcome ablation is consistent with the interpretation that the adaptive feedback loop contributes to the advantage, but it does not constitute definitive causal proof (other mechanisms correlated with feedback are also disrupted by permutation).
- Statistical inference is based on 8 independent seeds; wider replication would strengthen confidence.
- The training set comprises exactly 2 task families, the minimum required by the promotion criterion; additional families would materially strengthen the >=2-family claim.
- The comparison measures discovery efficiency, not absolute capability; a policy with lower efficiency might still be preferable under different cost models.

Manifest: `manifest.json` · knowledge snapshot: `knowledge-snapshot.json` · raw events: `conditions/<arm>/raw-results.jsonl` · selections: `conditions/<arm>/operator-selections.jsonl` · held-out: `conditions/<arm>/held-out-raw-results.jsonl` · checksums: `checksums.json` · reproducibility: `reproducibility.json`

---

# Protocol 240 — generative composition search

Pre-registration: `spec/research/240_GENERATIVE_COMPOSITION_SEARCH.md` (protocol file version 1.0.0).

**Primary metric:** `distinct_validated_programs / credits_consumed` — a program counts once per (arm, family, trial) cell, so re-evaluating a lucky program cannot inflate the discovery count.
**Secondary metric (harness):** `validated_discoveries / credits_consumed (harness metric, counts attempts)`.

## Search space and compute

- Closed grammar: 585 programs (lengths 1-3 over 9 typed atoms), grammar version 1.0.0.
- Trials: 10; episodes/trial: 4; budget/episode: 45.0 credits; prior: 8 attempts/family.
- Attempts executed: 2382 (1321 real CV evaluations, 1061 memoised repeats). Wall-clock durations are deliberately **not** printed here: `report.md` is compared byte-for-byte when a bundle is reproduced, so it may only contain deterministic values. Measured time lives in `protocol-240-statistics.json` (`compute.evaluation_seconds`) and `environment.json`, both of which are excluded from that comparison as recorded-but-never-read wall-clock fields.

## Generated programs (per arm)

| arm | attempts | distinct programs | discovered programs | mean length | credits |
|---|---|---|---|---|---|
| random-program | 142 | 76 | 3 | 2.224 | 1520.0 |
| greedy-history | 178 | 54 | 3 | 2.093 | 1586.0 |
| evolutionary-archive | 160 | 56 | 3 | 1.964 | 1548.5 |
| static-atoms | 280 | 9 | 2 | 1.0 | 1695.0 |
| greedy-permuted | 173 | 56 | 3 | 2.036 | 1589.5 |

## Primary metric — distinct validated programs per credit

| arm | mean distinct/credit | cells |
|---|---|---|
| random-program | 0.002041 | 20 |
| greedy-history | 0.001849 | 20 |
| evolutionary-archive | 0.002043 | 20 |
| static-atoms | 0.003593 | 20 |
| greedy-permuted | 0.001734 | 20 |

### family alpha — paired comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| random-program | greedy-history | -0.001212 | -0.003636 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| random-program | evolutionary-archive | -0.001212 | -0.003636 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| random-program | static-atoms | -0.001212 | -0.003636 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| greedy-history | greedy-permuted | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |

### family beta — paired comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| random-program | greedy-history | 0.000828 | -0.004687 | 0.007486 | 1.000000 | 1.000000 | 0.112 |
| random-program | evolutionary-archive | 0.001217 | -0.003381 | 0.005557 | 0.882559 | 1.000000 | 0.192 |
| random-program | static-atoms | 0.004316 | -0.000839 | 0.011502 | 0.501749 | 1.000000 | 0.518 |
| greedy-history | greedy-permuted | -0.000229 | -0.007643 | 0.009255 | 1.000000 | 1.000000 | -0.023 |

## Champion transfer (fresh seeds; no search attempt used them)

| arm | champion program | training mean effect | held-out mean effect | replicates positive |
|---|---|---|---|---|
| random-program | `log1p+sqrt+poly2-top5` | 0.011190 | -0.016667 | no |
| greedy-history | `sqrt` | 0.008413 | -0.002083 | no |
| evolutionary-archive | `sqrt` | 0.011350 | -0.002083 | no |
| static-atoms | `sqrt` | 0.011350 | -0.002083 | no |
| greedy-permuted | `sqrt` | 0.011350 | -0.002083 | no |

## Pre-registered hypothesis outcomes

| hypothesis | result |
|---|---|
| H1 greedy-history > random-program (both families, adj p<0.05) | NOT MET — {'alpha': False, 'beta': False} |
| H2 evolutionary-archive > random-program | NOT MET — {'alpha': False, 'beta': False} |
| H3 validated discovery + positive champion transfer | NOT MET — transferring arms: [] |
| H4 random-program vs static-atoms (composition value) | NOT MET — significant {'alpha': False, 'beta': False}, directional {'alpha': False, 'beta': True} |
| H5 greedy-history > greedy-permuted (feedback ablation, exploratory) | NOT MET — {'alpha': False, 'beta': False} |

**Outcome class C.** Class C: neither a significant policy advantage over random search nor a positively transferring champion was established. (H1=False, H2=False, H3=False, H4=False, H5=False)

## Protocol-240 limitations

- The search space is a 585-program closed grammar of feature transforms in front of a fixed logistic-regression estimator on three small tabular datasets. Nothing here supports a claim about inventing novel learning algorithms.
- Programs are deterministic to evaluate, so an arm's 'discovery' is a program whose two replicate CV splits both beat the matched baseline by >= 0.005 absolute; that is a robustness gate, not a significance test on a single program.
- Arms that generate longer programs spend more credits per attempt, so they take fewer attempts under an equal credit budget. This is the registered cost model, not a defect, but it couples search quality to program cost.
- Paired inference has n = 10 trials per family; effects smaller than the pairing noise will not be detected.
- Champion transfer is one program per arm evaluated twice on the held-out family; it is a directional check, not a powered test.

