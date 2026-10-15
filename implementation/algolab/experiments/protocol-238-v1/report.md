# Cumulative Search Policy Comparison — protocol-238-v1

Protocol: 1.1.0 (see spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md)
Environment: knn-micro-hpo 1.1.0; families: alpha, beta; held-out: gamma
Budget per episode: 60.0 credits; episodes/trial: 2; trials (seeds): 2
Discovery gate: valid implementation AND effect_1 >= threshold AND effect_2 >= threshold (2-seed replication gate)

## Per-condition outcome

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 2 | 240.0 | 0.008333 | 24 |
| knowledge-informed | 4 | 240.0 | 0.016667 | 24 |
| adaptive | 3 | 240.0 | 0.0125 | 24 |
| random | 0 | 240.0 | 0.0 | 24 |
| adaptive-cost-aware | 7 | 240.0 | 0.029167 | 24 |
| knowledge-informed-cost-rank | 4 | 240.0 | 0.016667 | 24 |
| adaptive-cost-aware-family | 3 | 240.0 | 0.0125 | 24 |
| knowledge-informed-family | 4 | 240.0 | 0.016667 | 24 |
| knowledge-informed-family-cost-rank | 4 | 240.0 | 0.016667 | 24 |
| knowledge-informed-family-commit | 6 | 240.0 | 0.025 | 24 |
| knowledge-informed-family-alloc | 2 | 240.0 | 0.008333 | 24 |
| c-permuted | 6 | 240.0 | 0.025 | 24 |
| b-shuffled | 2 | 240.0 | 0.008333 | 24 |
| c-plus-permuted | 3 | 240.0 | 0.0125 | 24 |

## Pairwise comparisons (A vs B, A vs C, B vs C; BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 0.447 |
| static | adaptive | 0.004167 | 0.000000 | 0.008333 | 1.000000 | 1.000000 | 0.277 |
| knowledge-informed | adaptive | -0.004167 | -0.008333 | 0.000000 | 1.000000 | 1.000000 | -0.200 |
| static | adaptive-cost-aware | 0.020833 | 0.000000 | 0.041667 | 1.000000 | 1.000000 | 0.687 |
| knowledge-informed | adaptive-cost-aware | 0.012500 | 0.000000 | 0.025000 | 1.000000 | 1.000000 | 0.372 |
| adaptive | adaptive-cost-aware | 0.016667 | 0.000000 | 0.033333 | 1.000000 | 1.000000 | 0.525 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.012500 | 0.000000 | 0.025000 | 1.000000 | 1.000000 | 0.372 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.012500 | 0.000000 | 0.025000 | 1.000000 | 1.000000 | 0.372 |
| adaptive-cost-aware | adaptive-cost-aware-family | -0.016667 | -0.033333 | 0.000000 | 1.000000 | 1.000000 | -0.525 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 0.277 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | -0.012500 | -0.025000 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | -0.008333 | -0.016667 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.004167 | 0.000000 | 0.008333 | 1.000000 | 1.000000 | 0.277 |
| static | qd-adaptive-cost-aware | 0.016667 | 0.000000 | 0.033333 | 1.000000 | 1.000000 | 0.632 |
| knowledge-informed | qd-adaptive-cost-aware | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 0.277 |
| adaptive-cost-aware | qd-adaptive-cost-aware | -0.004167 | -0.008333 | 0.000000 | 1.000000 | 1.000000 | -0.108 |
| static | basin-escape | 0.016667 | 0.000000 | 0.033333 | 1.000000 | 1.000000 | 0.632 |
| knowledge-informed | basin-escape | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 0.277 |
| adaptive-cost-aware | basin-escape | -0.004167 | -0.008333 | 0.000000 | 1.000000 | 1.000000 | -0.108 |
| qd-adaptive-cost-aware | basin-escape | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |

## Per-family comparisons (protocol §5 pairing: family × seed)

### family alpha

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 0.447 |
| static | adaptive | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 0.447 |
| knowledge-informed | adaptive | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| static | adaptive-cost-aware | 0.041667 | 0.000000 | 0.083333 | 1.000000 | 1.000000 | 0.822 |
| knowledge-informed | adaptive-cost-aware | 0.033333 | 0.000000 | 0.066667 | 1.000000 | 1.000000 | 0.632 |
| adaptive | adaptive-cost-aware | 0.033333 | 0.000000 | 0.066667 | 1.000000 | 1.000000 | 0.632 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.033333 | 0.000000 | 0.066667 | 1.000000 | 1.000000 | 0.632 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.033333 | 0.000000 | 0.066667 | 1.000000 | 1.000000 | 0.632 |
| adaptive-cost-aware | adaptive-cost-aware-family | -0.025000 | -0.050000 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | 0.033333 | 0.000000 | 0.066667 | 1.000000 | 1.000000 | 0.632 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | -0.025000 | -0.050000 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | -0.008333 | -0.016667 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.016667 | 0.000000 | 0.033333 | 1.000000 | 1.000000 | 0.632 |
| static | qd-adaptive-cost-aware | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 0.447 |
| knowledge-informed | qd-adaptive-cost-aware | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| adaptive-cost-aware | qd-adaptive-cost-aware | -0.033333 | -0.066667 | 0.000000 | 1.000000 | 1.000000 | -0.632 |
| static | basin-escape | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 0.447 |
| knowledge-informed | basin-escape | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| adaptive-cost-aware | basin-escape | -0.033333 | -0.066667 | 0.000000 | 1.000000 | 1.000000 | -0.632 |
| qd-adaptive-cost-aware | basin-escape | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |

Mean efficiency per condition: adaptive 0.016667, adaptive-cost-aware 0.050000, adaptive-cost-aware-family 0.025000, b-shuffled 0.000000, basin-escape 0.016667, c-permuted 0.033333, c-plus-permuted 0.016667, knowledge-informed 0.016667, knowledge-informed-cost-rank 0.016667, knowledge-informed-family 0.016667, knowledge-informed-family-alloc 0.008333, knowledge-informed-family-commit 0.050000, knowledge-informed-family-cost-rank 0.016667, qd-adaptive-cost-aware 0.016667, random 0.000000, static 0.008333

### family beta

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 0.447 |
| static | adaptive | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed | adaptive | -0.008333 | -0.016667 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| static | adaptive-cost-aware | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed | adaptive-cost-aware | -0.008333 | -0.016667 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| adaptive | adaptive-cost-aware | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-cost-rank | adaptive-cost-aware | -0.008333 | -0.016667 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | -0.008333 | -0.016667 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| adaptive-cost-aware | adaptive-cost-aware-family | -0.008333 | -0.016667 | 0.000000 | 1.000000 | 1.000000 | -1.000 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | -0.016667 | -0.033333 | 0.000000 | 1.000000 | 1.000000 | -1.000 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | -0.008333 | -0.016667 | 0.000000 | 1.000000 | 1.000000 | -0.447 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | -0.008333 | -0.016667 | 0.000000 | 1.000000 | 1.000000 | -1.000 |
| static | qd-adaptive-cost-aware | 0.025000 | 0.000000 | 0.050000 | 1.000000 | 1.000000 | 0.728 |
| knowledge-informed | qd-adaptive-cost-aware | 0.016667 | 0.000000 | 0.033333 | 1.000000 | 1.000000 | 0.447 |
| adaptive-cost-aware | qd-adaptive-cost-aware | 0.025000 | 0.000000 | 0.050000 | 1.000000 | 1.000000 | 0.728 |
| static | basin-escape | 0.025000 | 0.000000 | 0.050000 | 1.000000 | 1.000000 | 0.728 |
| knowledge-informed | basin-escape | 0.016667 | 0.000000 | 0.033333 | 1.000000 | 1.000000 | 0.447 |
| adaptive-cost-aware | basin-escape | 0.025000 | 0.000000 | 0.050000 | 1.000000 | 1.000000 | 0.728 |
| qd-adaptive-cost-aware | basin-escape | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |

Mean efficiency per condition: adaptive 0.008333, adaptive-cost-aware 0.008333, adaptive-cost-aware-family 0.000000, b-shuffled 0.016667, basin-escape 0.033333, c-permuted 0.016667, c-plus-permuted 0.008333, knowledge-informed 0.016667, knowledge-informed-cost-rank 0.016667, knowledge-informed-family 0.016667, knowledge-informed-family-alloc 0.008333, knowledge-informed-family-commit 0.000000, knowledge-informed-family-cost-rank 0.016667, qd-adaptive-cost-aware 0.033333, random 0.000000, static 0.008333


## Calibration floor (condition D — uniform random)

Random selection achieves 0 discoveries over 240.0 credits (0.000000 discoveries/credit, n/a of static, n/a of knowledge-informed, n/a of adaptive). This is the floor any informed policy must clear to justify its knowledge channel; arms at or below this level would indicate the task or budget carries no exploitable signal.

## Ablations (exploratory; p-values unadjusted)

| base | candidate | delta | p | d | note |
|---|---|---|---|---|---|
| adaptive | c-permuted | 0.012500 | 1.000000 | 0.447 | permuted-outcome feedback (machinery kept) |
| knowledge-informed | b-shuffled | -0.008333 | 1.000000 | -0.447 | shuffled-K0 knowledge (association destroyed) |
| b-shuffled | static | 0.000000 | 1.000000 | 0.000 | shuffled knowledge vs no knowledge |
| adaptive-cost-aware | c-plus-permuted | -0.016667 | 1.000000 | -0.525 | permuted-outcome feedback on cost-aware machinery |

## Held-out transfer (gamma family)

Transfer evaluation on held-out family **gamma**, which was never included in the K0 prior.

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 5 | 240.0 | 0.020833 | 24 |
| knowledge-informed | 0 | 240.0 | 0.0 | 24 |
| adaptive | 4 | 240.0 | 0.016667 | 24 |
| random | 5 | 240.0 | 0.020833 | 24 |
| adaptive-cost-aware | 3 | 240.0 | 0.0125 | 24 |
| knowledge-informed-cost-rank | 0 | 240.0 | 0.0 | 24 |
| adaptive-cost-aware-family | 7 | 240.0 | 0.029167 | 24 |
| knowledge-informed-family | 0 | 240.0 | 0.0 | 24 |
| knowledge-informed-family-cost-rank | 0 | 240.0 | 0.0 | 24 |
| knowledge-informed-family-commit | 0 | 240.0 | 0.0 | 24 |
| knowledge-informed-family-alloc | 4 | 240.0 | 0.016667 | 24 |

### Held-out pairwise comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | -0.020833 | -0.025000 | -0.016667 | 0.502249 | 0.849960 | -5.000 |
| static | adaptive | -0.004167 | -0.008333 | 0.000000 | 1.000000 | 1.000000 | -1.000 |
| knowledge-informed | adaptive | 0.016667 | 0.016667 | 0.016667 | 0.502249 | 0.849960 | 0.000 |
| static | adaptive-cost-aware | -0.008333 | -0.008333 | -0.008333 | 0.502249 | 0.849960 | -1.414 |
| knowledge-informed | adaptive-cost-aware | 0.012500 | 0.008333 | 0.016667 | 0.502249 | 0.849960 | 3.000 |
| adaptive | adaptive-cost-aware | -0.004167 | -0.008333 | 0.000000 | 1.000000 | 1.000000 | -1.000 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.012500 | 0.008333 | 0.016667 | 0.502249 | 0.849960 | 3.000 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.012500 | 0.008333 | 0.016667 | 0.502249 | 0.849960 | 3.000 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.016667 | 0.008333 | 0.025000 | 0.502249 | 0.849960 | 2.828 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | 0.029167 | 0.025000 | 0.033333 | 0.502249 | 0.849960 | 7.000 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | 0.016667 | 0.016667 | 0.016667 | 0.502249 | 0.849960 | 0.000 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.012500 | 0.008333 | 0.016667 | 0.502249 | 0.849960 | 3.000 |
| static | qd-adaptive-cost-aware | 0.000000 | -0.008333 | 0.008333 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed | qd-adaptive-cost-aware | 0.020833 | 0.016667 | 0.025000 | 0.502249 | 0.849960 | 5.000 |
| adaptive-cost-aware | qd-adaptive-cost-aware | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 1.414 |
| static | basin-escape | 0.008333 | 0.000000 | 0.016667 | 1.000000 | 1.000000 | 0.632 |
| knowledge-informed | basin-escape | 0.029167 | 0.016667 | 0.041667 | 0.502249 | 0.849960 | 2.333 |
| adaptive-cost-aware | basin-escape | 0.016667 | 0.008333 | 0.025000 | 0.502249 | 0.849960 | 1.265 |
| qd-adaptive-cost-aware | basin-escape | 0.008333 | -0.008333 | 0.025000 | 1.000000 | 1.000000 | 0.632 |

### Promotion-criterion status (protocol 230 §5)

- C > A per training family: {'alpha': False, 'beta': False}
- C > B per training family: {'alpha': False, 'beta': False}
- gap persists on held-out vs A: False
- gap persists on held-out vs B: True

**promotion criterion NOT met; unmet components: adaptive-cost-aware>A with adjusted p < 0.05 on >=2 families; adaptive-cost-aware>B with adjusted p < 0.05 on >=2 families; gap persistence on held-out gamma**

## Adaptive-policy adaptation evidence (condition C)

### adaptive · family alpha
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'k11': (0, 2), 'k1': (0, 2), 'k21': (0, 2), 'manhattan': (2, 3), 'chebyshev': (0, 2), 'k3': (0, 1)}

### adaptive · family beta
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'manhattan': (0, 4), 'k1': (0, 1), 'k21': (1, 3), 'k3': (0, 2), 'k11': (0, 1), 'chebyshev': (0, 1)}

### adaptive-cost-aware · family alpha
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'manhattan': (6, 8), 'k21': (0, 1), 'k11': (0, 2), 'k3': (0, 1)}

### adaptive-cost-aware · family beta
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'k21': (1, 2), 'k1': (0, 3), 'dist-weight': (0, 1), 'manhattan': (0, 3), 'chebyshev': (0, 1), 'k11': (0, 2)}

### adaptive-cost-aware-family · family alpha
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'k21': (0, 2), 'manhattan': (3, 4), 'chebyshev': (0, 1), 'k3': (0, 3), 'k11': (0, 1), 'k1': (0, 1)}

### adaptive-cost-aware-family · family beta
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'manhattan': (0, 3), 'chebyshev': (0, 2), 'k1': (0, 3), 'k11': (0, 3), 'dist-weight': (0, 1)}


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
