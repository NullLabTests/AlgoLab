# Cumulative Search Policy Comparison — protocol-239-v1

Protocol: 1.1.0 (see spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md)
Environment: typed-feature-transform 1.0.0; families: alpha, beta; held-out: gamma
Budget per episode: 100.0 credits; episodes/trial: 2; trials (seeds): 8
Discovery gate: valid implementation AND effect_1 >= threshold AND effect_2 >= threshold (2-seed replication gate)

## Per-condition outcome

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 6 | 1528.0 | 0.003927 | 168 |
| adaptive | 9 | 1508.0 | 0.005968 | 136 |
| random | 8 | 1507.0 | 0.005309 | 137 |
| adaptive-cost-aware | 16 | 1537.0 | 0.01041 | 217 |
| knowledge-informed-family-commit | 20 | 1568.0 | 0.012755 | 288 |
| c-permuted | 5 | 1500.0 | 0.003333 | 137 |
| b-shuffled | 8 | 1515.0 | 0.005281 | 153 |
| c-plus-permuted | 11 | 1516.0 | 0.007256 | 140 |

## Pairwise comparisons (A vs B, A vs C, B vs C; BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | adaptive | 0.002060 | -0.001085 | 0.006412 | 0.382309 | 0.764618 | 0.313 |
| static | adaptive-cost-aware | 0.006600 | -0.003927 | 0.025034 | 1.000000 | 1.000000 | 0.308 |
| adaptive | adaptive-cost-aware | 0.004540 | -0.009164 | 0.026021 | 1.000000 | 1.000000 | 0.209 |
| static | qd-adaptive-cost-aware | 0.008411 | -0.001938 | 0.027159 | 0.756622 | 1.000000 | 0.382 |
| adaptive-cost-aware | qd-adaptive-cost-aware | 0.001811 | 0.000000 | 0.003459 | 0.248876 | 0.663668 | 0.060 |
| static | basin-escape | -0.003927 | -0.007853 | -0.000654 | 0.130935 | 0.663668 | -1.025 |
| adaptive-cost-aware | basin-escape | -0.010526 | -0.031579 | 0.000000 | 1.000000 | 1.000000 | -0.500 |
| qd-adaptive-cost-aware | basin-escape | -0.012337 | -0.034390 | 0.000000 | 0.248876 | 0.663668 | -0.568 |

## Per-family comparisons (protocol §5 pairing: family × seed)

### family alpha

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | adaptive | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| static | adaptive-cost-aware | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| adaptive | adaptive-cost-aware | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| static | qd-adaptive-cost-aware | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| adaptive-cost-aware | qd-adaptive-cost-aware | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| static | basin-escape | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| adaptive-cost-aware | basin-escape | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| qd-adaptive-cost-aware | basin-escape | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |

Mean efficiency per condition: adaptive 0.000000, adaptive-cost-aware 0.000000, b-shuffled 0.000000, basin-escape 0.000000, c-permuted 0.000000, c-plus-permuted 0.000000, knowledge-informed-family-commit 0.000000, qd-adaptive-cost-aware 0.000000, random 0.000000, static 0.000000

### family beta

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | adaptive | 0.003841 | -0.002257 | 0.012413 | 0.382309 | 0.764618 | 0.291 |
| static | adaptive-cost-aware | 0.011935 | -0.008065 | 0.046559 | 1.000000 | 1.000000 | 0.293 |
| adaptive | adaptive-cost-aware | 0.008094 | -0.018065 | 0.048802 | 1.000000 | 1.000000 | 0.196 |
| static | qd-adaptive-cost-aware | 0.016447 | -0.004074 | 0.053583 | 1.000000 | 1.000000 | 0.375 |
| adaptive-cost-aware | qd-adaptive-cost-aware | 0.004511 | 0.000000 | 0.008931 | 0.248876 | 0.663668 | 0.077 |
| static | basin-escape | -0.008065 | -0.016129 | -0.001344 | 0.130935 | 0.663668 | -1.025 |
| adaptive-cost-aware | basin-escape | -0.020000 | -0.060000 | 0.000000 | 1.000000 | 1.000000 | -0.500 |
| qd-adaptive-cost-aware | basin-escape | -0.024511 | -0.068326 | 0.000000 | 0.248876 | 0.663668 | -0.567 |

Mean efficiency per condition: adaptive 0.011906, adaptive-cost-aware 0.020000, b-shuffled 0.010382, basin-escape 0.000000, c-permuted 0.006665, c-plus-permuted 0.014180, knowledge-informed-family-commit 0.025000, qd-adaptive-cost-aware 0.024511, random 0.010930, static 0.008065


## Calibration floor (condition D — uniform random)

Random selection achieves 8 discoveries over 1507.0 credits (0.005309 discoveries/credit, 1.352x of static, n/a of knowledge-informed, 0.890x of adaptive). This is the floor any informed policy must clear to justify its knowledge channel; arms at or below this level would indicate the task or budget carries no exploitable signal.

## Ablations (exploratory; p-values unadjusted)

| base | candidate | delta | p | d | note |
|---|---|---|---|---|---|
| adaptive | c-permuted | -0.002552 | 0.517241 | -0.332 | permuted-outcome feedback (machinery kept) |
| b-shuffled | static | -0.001302 | 0.495752 | -0.202 | shuffled knowledge vs no knowledge |
| adaptive-cost-aware | c-plus-permuted | -0.003416 | 1.000000 | -0.155 | permuted-outcome feedback on cost-aware machinery |

## Held-out transfer (gamma family)

Transfer evaluation on held-out family **gamma**, which was never included in the K0 prior.

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 7 | 1528.0 | 0.004581 | 168 |
| adaptive | 48 | 1508.0 | 0.03183 | 124 |
| random | 22 | 1508.0 | 0.014589 | 144 |
| adaptive-cost-aware | 28 | 1510.0 | 0.018543 | 205 |
| knowledge-informed-family-commit | 0 | 1600.0 | 0.0 | 320 |

### Held-out pairwise comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | adaptive | 0.027126 | 0.015868 | 0.036777 | 0.009995 | 0.057571 | 2.468 |
| static | adaptive-cost-aware | 0.014177 | 0.000130 | 0.034600 | 0.153923 | 0.205231 | 0.707 |
| adaptive | adaptive-cost-aware | -0.012949 | -0.031809 | 0.009165 | 0.269865 | 0.308417 | -0.573 |
| static | qd-adaptive-cost-aware | 0.012363 | 0.004018 | 0.021005 | 0.028486 | 0.057571 | 1.284 |
| adaptive-cost-aware | qd-adaptive-cost-aware | -0.001814 | -0.015874 | 0.008491 | 0.896552 | 0.896552 | -0.082 |
| static | basin-escape | -0.004581 | -0.006545 | -0.002618 | 0.034483 | 0.057571 | -1.931 |
| adaptive-cost-aware | basin-escape | -0.018758 | -0.039257 | -0.004741 | 0.035982 | 0.057571 | -0.942 |
| qd-adaptive-cost-aware | basin-escape | -0.016945 | -0.025863 | -0.008638 | 0.028486 | 0.057571 | -1.816 |

### Promotion-criterion status (protocol 230 §5)

- C > A per training family: {'alpha': False, 'beta': False}
- C > B per training family: {'alpha': False, 'beta': False}
- gap persists on held-out vs A: True
- gap persists on held-out vs B: False

**promotion criterion NOT met; unmet components: adaptive-cost-aware>A with adjusted p < 0.05 on >=2 families; adaptive-cost-aware>B with adjusted p < 0.05 on >=2 families; gap persistence on held-out gamma**

## Adaptive-policy adaptation evidence (condition C)

### adaptive · family alpha
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'standard-scale': (0, 5), 'poly2-all': (0, 10), 'poly2+log1p': (0, 11), 'power-yeo-johnson': (0, 6), 'interaction-top2': (0, 4), 'clip-1_99': (0, 11), 'log1p': (0, 9), 'pca-10': (0, 5), 'interaction+robust': (0, 3), 'poly2-top5': (0, 2), 'sqrt': (0, 3)}

### adaptive · family beta
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'log1p': (1, 9), 'poly2-all': (0, 8), 'poly2+log1p': (8, 14), 'interaction-top2': (0, 5), 'clip-1_99': (0, 11), 'standard-scale': (0, 6), 'pca-10': (0, 5), 'sqrt': (0, 2), 'power-yeo-johnson': (0, 4), 'poly2-top5': (0, 2), 'quantile-bin-5': (0, 1)}

### adaptive-cost-aware · family alpha
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'power-yeo-johnson': (0, 6), 'clip-1_99': (0, 18), 'log1p': (0, 27), 'poly2+log1p': (0, 4), 'standard-scale': (0, 12), 'sqrt': (0, 20), 'poly2-all': (0, 5), 'quantile-bin-3': (0, 7), 'poly2-top5': (0, 2), 'interaction-top2': (0, 1), 'pca-10': (0, 1)}

### adaptive-cost-aware · family beta
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'log1p': (15, 42), 'clip-1_99': (0, 23), 'sqrt': (1, 19), 'interaction-top2': (0, 3), 'standard-scale': (0, 7), 'power-yeo-johnson': (0, 4), 'robust-scale': (0, 1), 'pca-10': (0, 5), 'quantile-bin-5': (0, 1), 'poly2+log1p': (0, 2), 'poly2-all': (0, 2), 'quantile-bin-3': (0, 4), 'poly2-top5': (0, 1)}


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
