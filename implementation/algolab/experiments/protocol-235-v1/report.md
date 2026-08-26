# Cumulative Search Policy Comparison — protocol-235-v1

Protocol: 1.1.0 (see spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md)
Environment: knn-micro-hpo 1.1.0; families: alpha, beta; held-out: gamma
Budget per episode: 150.0 credits; episodes/trial: 2; trials (seeds): 32
Discovery gate: valid implementation AND effect_1 >= threshold AND effect_2 >= threshold (2-seed replication gate)

## Per-condition outcome

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 42 | 9600.0 | 0.004375 | 960 |
| knowledge-informed | 90 | 9600.0 | 0.009375 | 960 |
| adaptive | 156 | 9600.0 | 0.01625 | 960 |
| random | 47 | 9600.0 | 0.004896 | 960 |
| adaptive-cost-aware | 149 | 9600.0 | 0.015521 | 960 |
| adaptive-cost-aware-family | 176 | 9600.0 | 0.018333 | 960 |
| knowledge-informed-family | 85 | 9600.0 | 0.008854 | 960 |
| knowledge-informed-family-cost-rank | 85 | 9600.0 | 0.008854 | 960 |
| knowledge-informed-family-commit | 195 | 9600.0 | 0.020313 | 960 |
| knowledge-informed-family-alloc | 71 | 9600.0 | 0.007396 | 960 |

## Pairwise comparisons (A vs B, A vs C, B vs C; BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.005000 | 0.002604 | 0.007500 | 0.001499 | 0.008396 | 0.477 |
| static | adaptive | 0.011875 | 0.006458 | 0.017708 | 0.001499 | 0.008396 | 0.731 |
| knowledge-informed | adaptive | 0.006875 | 0.003229 | 0.011146 | 0.005997 | 0.013993 | 0.377 |
| static | adaptive-cost-aware | 0.011146 | 0.005417 | 0.017188 | 0.002999 | 0.008396 | 0.667 |
| knowledge-informed | adaptive-cost-aware | 0.006146 | 0.001979 | 0.010938 | 0.011994 | 0.020990 | 0.330 |
| adaptive | adaptive-cost-aware | -0.000729 | -0.002604 | 0.001146 | 0.514243 | 0.599950 | -0.033 |
| knowledge-informed | knowledge-informed-family | -0.000521 | -0.001563 | 0.000000 | 1.000000 | 1.000000 | -0.041 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.006667 | 0.002396 | 0.011354 | 0.010495 | 0.020990 | 0.367 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.002812 | 0.000521 | 0.005625 | 0.042479 | 0.066078 | 0.117 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | 0.011458 | 0.005729 | 0.017708 | 0.002999 | 0.008396 | 0.532 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | -0.001979 | -0.005000 | 0.000625 | 0.193903 | 0.246786 | -0.074 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | -0.001458 | -0.003437 | 0.000208 | 0.165417 | 0.231584 | -0.128 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.010937 | 0.005833 | 0.016563 | 0.002499 | 0.008396 | 0.561 |

## Per-family comparisons (protocol §5 pairing: family × seed)

### family alpha

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.003125 | 0.000625 | 0.005625 | 0.060970 | 0.170715 | 0.334 |
| static | adaptive | 0.003125 | 0.000000 | 0.007292 | 0.123938 | 0.247876 | 0.288 |
| knowledge-informed | adaptive | 0.000000 | -0.002500 | 0.002917 | 1.000000 | 1.000000 | 0.000 |
| static | adaptive-cost-aware | 0.003125 | 0.000000 | 0.006667 | 0.251874 | 0.440780 | 0.297 |
| knowledge-informed | adaptive-cost-aware | 0.000000 | -0.002500 | 0.002083 | 0.883558 | 1.000000 | 0.000 |
| adaptive | adaptive-cost-aware | 0.000000 | -0.002917 | 0.003125 | 0.875062 | 1.000000 | 0.000 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.000000 | -0.002500 | 0.002083 | 0.883558 | 1.000000 | 0.000 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.004792 | 0.000625 | 0.010417 | 0.122939 | 0.247876 | 0.239 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | 0.010417 | 0.002083 | 0.018750 | 0.060970 | 0.170715 | 0.379 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | -0.005625 | -0.011250 | -0.001250 | 0.060970 | 0.170715 | -0.179 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | -0.003125 | -0.005625 | -0.000625 | 0.060970 | 0.170715 | -0.334 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.007917 | 0.001667 | 0.015417 | 0.060970 | 0.170715 | 0.446 |

Mean efficiency per condition: adaptive 0.005208, adaptive-cost-aware 0.005208, adaptive-cost-aware-family 0.010000, knowledge-informed 0.005208, knowledge-informed-family 0.005208, knowledge-informed-family-alloc 0.002083, knowledge-informed-family-commit 0.015625, knowledge-informed-family-cost-rank 0.005208, random 0.002083, static 0.002083

### family beta

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.006875 | 0.003125 | 0.011250 | 0.002999 | 0.018191 | 0.364 |
| static | adaptive | 0.020625 | 0.010000 | 0.032500 | 0.004998 | 0.018191 | 0.649 |
| knowledge-informed | adaptive | 0.013750 | 0.005833 | 0.022708 | 0.011994 | 0.024988 | 0.394 |
| static | adaptive-cost-aware | 0.019167 | 0.008750 | 0.030833 | 0.005497 | 0.018191 | 0.617 |
| knowledge-informed | adaptive-cost-aware | 0.012292 | 0.004375 | 0.021250 | 0.012494 | 0.024988 | 0.359 |
| adaptive | adaptive-cost-aware | -0.001458 | -0.004792 | 0.000833 | 0.616192 | 0.784244 | -0.034 |
| knowledge-informed | knowledge-informed-family | -0.001042 | -0.003125 | 0.000000 | 1.000000 | 1.000000 | -0.047 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.013333 | 0.005417 | 0.022500 | 0.006497 | 0.018191 | 0.402 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.000833 | 0.000000 | 0.001875 | 0.222889 | 0.346716 | 0.019 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | 0.012500 | 0.003125 | 0.022917 | 0.037981 | 0.066467 | 0.365 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | 0.001667 | -0.000417 | 0.004792 | 0.511244 | 0.715742 | 0.038 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | 0.000208 | -0.002083 | 0.002292 | 0.725137 | 0.845994 | 0.010 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.013958 | 0.006667 | 0.022500 | 0.005497 | 0.018191 | 0.409 |

Mean efficiency per condition: adaptive 0.027292, adaptive-cost-aware 0.025833, adaptive-cost-aware-family 0.026667, knowledge-informed 0.013542, knowledge-informed-family 0.012500, knowledge-informed-family-alloc 0.012708, knowledge-informed-family-commit 0.025000, knowledge-informed-family-cost-rank 0.012500, random 0.007708, static 0.006667


## Calibration floor (condition D — uniform random)

Random selection achieves 47 discoveries over 9600.0 credits (0.004896 discoveries/credit, 1.119x of static, 0.522x of knowledge-informed, 0.301x of adaptive). This is the floor any informed policy must clear to justify its knowledge channel; arms at or below this level would indicate the task or budget carries no exploitable signal.

## Ablations (exploratory; p-values unadjusted)

| base | candidate | delta | p | d | note |
|---|---|---|---|---|---|

## Held-out transfer (gamma family)

Transfer evaluation on held-out family **gamma**, which was never included in the K0 prior.

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 130 | 9600.0 | 0.013542 | 960 |
| knowledge-informed | 120 | 9600.0 | 0.0125 | 960 |
| adaptive | 146 | 9600.0 | 0.015208 | 960 |
| random | 122 | 9600.0 | 0.012708 | 960 |
| adaptive-cost-aware | 184 | 9600.0 | 0.019167 | 960 |
| adaptive-cost-aware-family | 153 | 9600.0 | 0.015938 | 960 |
| knowledge-informed-family | 120 | 9600.0 | 0.0125 | 960 |
| knowledge-informed-family-cost-rank | 120 | 9600.0 | 0.0125 | 960 |
| knowledge-informed-family-commit | 0 | 9600.0 | 0.0 | 960 |
| knowledge-informed-family-alloc | 77 | 9600.0 | 0.008021 | 960 |

### Held-out pairwise comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | -0.001042 | -0.003854 | 0.001771 | 0.442779 | 0.563536 | -0.092 |
| static | adaptive | 0.001667 | -0.003125 | 0.006979 | 0.565217 | 0.659420 | 0.110 |
| knowledge-informed | adaptive | 0.002708 | -0.001146 | 0.006979 | 0.208896 | 0.320440 | 0.180 |
| static | adaptive-cost-aware | 0.005625 | 0.000521 | 0.011146 | 0.070965 | 0.141929 | 0.323 |
| knowledge-informed | adaptive-cost-aware | 0.006667 | 0.001979 | 0.011667 | 0.014493 | 0.033816 | 0.385 |
| adaptive | adaptive-cost-aware | 0.003958 | -0.002292 | 0.009896 | 0.220390 | 0.320440 | 0.198 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.006667 | 0.001979 | 0.011667 | 0.014493 | 0.033816 | 0.385 |
| adaptive-cost-aware | adaptive-cost-aware-family | -0.003229 | -0.008542 | 0.001562 | 0.228886 | 0.320440 | -0.151 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | -0.012500 | -0.016146 | -0.008854 | 0.000500 | 0.003498 | -1.578 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | 0.015938 | 0.009271 | 0.023125 | 0.000500 | 0.003498 | 1.069 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | -0.004479 | -0.006875 | -0.002083 | 0.002499 | 0.011661 | -0.484 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.007917 | 0.002604 | 0.013333 | 0.010495 | 0.033816 | 0.506 |

### Promotion-criterion status (protocol 230 §5)

- C > A per training family: {'alpha': False, 'beta': True}
- C > B per training family: {'alpha': False, 'beta': True}
- gap persists on held-out vs A: True
- gap persists on held-out vs B: True

**promotion criterion NOT met; unmet components: adaptive-cost-aware>A with adjusted p < 0.05 on >=2 families; adaptive-cost-aware>B with adjusted p < 0.05 on >=2 families**

## Adaptive-policy adaptation evidence (condition C)

### adaptive · family alpha
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'k21': (0, 312), 'manhattan': (25, 69), 'k1': (0, 34), 'dist-weight': (0, 20), 'k11': (0, 16), 'chebyshev': (0, 24), 'k3': (0, 5)}

### adaptive · family beta
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'k21': (118, 368), 'manhattan': (13, 51), 'k1': (0, 20), 'k11': (0, 10), 'dist-weight': (0, 20), 'chebyshev': (0, 11)}

### adaptive-cost-aware · family alpha
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'k21': (0, 301), 'k1': (0, 31), 'chebyshev': (0, 37), 'dist-weight': (0, 26), 'manhattan': (25, 71), 'k11': (0, 10), 'k3': (0, 4)}

### adaptive-cost-aware · family beta
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'k21': (116, 354), 'k11': (0, 14), 'k1': (0, 24), 'manhattan': (8, 50), 'dist-weight': (0, 22), 'chebyshev': (0, 12), 'k3': (0, 4)}

### adaptive-cost-aware-family · family alpha
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'chebyshev': (0, 77), 'manhattan': (48, 120), 'k11': (0, 57), 'dist-weight': (0, 41), 'k1': (0, 82), 'k3': (0, 44), 'k21': (0, 59)}

### adaptive-cost-aware-family · family beta
- fraction of selections on useful operators: early 0.500 -> late 0.500 (no upward shift)
- operator attempt counts: {'k1': (0, 28), 'k21': (119, 324), 'dist-weight': (0, 41), 'manhattan': (9, 47), 'k3': (0, 6), 'k11': (0, 16), 'chebyshev': (0, 18)}


## Interpretation: H1 supported in this environment: C > B > A
(outcome 1 in the pre-registered taxonomy)

## Limitations and scope

- The experiment uses a deterministic toy environment with known ground truth; results may not generalise to real workloads.
- The held-out family provides evidence that the adaptive advantage transfers beyond the training families; it does not by itself rule out all benchmark-specific adaptation or memorisation.
- The permuted-outcome ablation is consistent with the interpretation that the adaptive feedback loop contributes to the advantage, but it does not constitute definitive causal proof (other mechanisms correlated with feedback are also disrupted by permutation).
- Statistical inference is based on 8 independent seeds; wider replication would strengthen confidence.
- The training set comprises exactly 2 task families, the minimum required by the promotion criterion; additional families would materially strengthen the >=2-family claim.
- The comparison measures discovery efficiency, not absolute capability; a policy with lower efficiency might still be preferable under different cost models.

Manifest: `manifest.json` · knowledge snapshot: `knowledge-snapshot.json` · raw events: `conditions/<arm>/raw-results.jsonl` · selections: `conditions/<arm>/operator-selections.jsonl` · held-out: `conditions/<arm>/held-out-raw-results.jsonl` · checksums: `checksums.json` · reproducibility: `reproducibility.json`
