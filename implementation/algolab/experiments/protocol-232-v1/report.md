# Cumulative Search Policy Comparison — protocol-232-v1

Protocol: 1.1.0 (see spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md)
Environment: toy-discovery 1.1.0; families: alpha, beta; held-out: gamma
Budget per episode: 150.0 credits; episodes/trial: 10; trials (seeds): 128
Discovery gate: valid implementation AND effect_1 >= threshold AND effect_2 >= threshold (2-seed replication gate)

## Per-condition outcome

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 2921 | 186240.0 | 0.015684 | 10368 |
| knowledge-informed | 3760 | 176640.0 | 0.021286 | 9984 |
| adaptive | 5268 | 179400.0 | 0.029365 | 9298 |
| random | 2949 | 177835.0 | 0.016583 | 10487 |
| adaptive-cost-aware | 12823 | 191620.0 | 0.066919 | 19207 |
| knowledge-informed-cost-rank | 7184 | 192000.0 | 0.037417 | 19200 |
| adaptive-cost-aware-family | 13955 | 191130.0 | 0.073013 | 19199 |
| knowledge-informed-family | 8828 | 180480.0 | 0.048914 | 12032 |
| knowledge-informed-family-cost-rank | 8921 | 179200.0 | 0.049782 | 12160 |
| c-permuted | 2965 | 177165.0 | 0.016736 | 8086 |
| b-shuffled | 3559 | 178355.0 | 0.019955 | 12418 |
| c-plus-permuted | 6542 | 189975.0 | 0.034436 | 20127 |

## Pairwise comparisons (A vs B, A vs C, B vs C; BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.005602 | 0.005262 | 0.005934 | 0.000500 | 0.000500 | 2.891 |
| static | adaptive | 0.013602 | 0.012404 | 0.014800 | 0.000500 | 0.000500 | 2.601 |
| knowledge-informed | adaptive | 0.008000 | 0.006868 | 0.009118 | 0.000500 | 0.000500 | 1.504 |
| static | adaptive-cost-aware | 0.051231 | 0.050422 | 0.051978 | 0.000500 | 0.000500 | 14.251 |
| knowledge-informed | adaptive-cost-aware | 0.045629 | 0.044868 | 0.046342 | 0.000500 | 0.000500 | 12.258 |
| adaptive | adaptive-cost-aware | 0.037629 | 0.036285 | 0.039014 | 0.000500 | 0.000500 | 6.149 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.029499 | 0.028873 | 0.030109 | 0.000500 | 0.000500 | 7.410 |
| knowledge-informed | knowledge-informed-family | 0.027628 | 0.027188 | 0.028017 | 0.000500 | 0.000500 | 10.394 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000868 | 0.000812 | 0.000923 | 0.000500 | 0.000500 | 0.280 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.017133 | 0.016550 | 0.017688 | 0.000500 | 0.000500 | 4.230 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.006095 | 0.005726 | 0.006489 | 0.000500 | 0.000500 | 1.410 |

## Per-family comparisons (protocol §5 pairing: family × seed)

### family alpha

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.000143 | -0.000344 | 0.000628 | 0.553723 | 0.553723 | 0.058 |
| static | adaptive | 0.012378 | 0.010907 | 0.013829 | 0.000500 | 0.000550 | 2.000 |
| knowledge-informed | adaptive | 0.012235 | 0.010857 | 0.013602 | 0.000500 | 0.000550 | 1.973 |
| static | adaptive-cost-aware | 0.047876 | 0.046766 | 0.048896 | 0.000500 | 0.000550 | 9.788 |
| knowledge-informed | adaptive-cost-aware | 0.047733 | 0.046609 | 0.048765 | 0.000500 | 0.000550 | 9.726 |
| adaptive | adaptive-cost-aware | 0.035499 | 0.033698 | 0.037214 | 0.000500 | 0.000550 | 4.731 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.014396 | 0.013590 | 0.015141 | 0.000500 | 0.000550 | 2.651 |
| knowledge-informed | knowledge-informed-family | 0.040288 | 0.039589 | 0.040903 | 0.000500 | 0.000550 | 11.396 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.001609 | 0.001588 | 0.001630 | 0.000500 | 0.000550 | 0.366 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.005836 | 0.005025 | 0.006589 | 0.000500 | 0.000550 | 1.050 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.009231 | 0.008648 | 0.009847 | 0.000500 | 0.000550 | 1.555 |

Mean efficiency per condition: adaptive 0.028262, adaptive-cost-aware 0.063760, adaptive-cost-aware-family 0.072991, b-shuffled 0.020307, c-permuted 0.007638, c-plus-permuted 0.024143, knowledge-informed 0.016027, knowledge-informed-cost-rank 0.049365, knowledge-informed-family 0.056315, knowledge-informed-family-cost-rank 0.057924, random 0.017022, static 0.015884

### family beta

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.010909 | 0.010428 | 0.011382 | 0.000500 | 0.000500 | 3.903 |
| static | adaptive | 0.014674 | 0.012834 | 0.016546 | 0.000500 | 0.000500 | 1.778 |
| knowledge-informed | adaptive | 0.003765 | 0.001947 | 0.005602 | 0.000500 | 0.000500 | 0.448 |
| static | adaptive-cost-aware | 0.054576 | 0.053571 | 0.055579 | 0.000500 | 0.000500 | 11.349 |
| knowledge-informed | adaptive-cost-aware | 0.043667 | 0.042744 | 0.044567 | 0.000500 | 0.000500 | 8.620 |
| adaptive | adaptive-cost-aware | 0.039903 | 0.037852 | 0.041925 | 0.000500 | 0.000500 | 4.303 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.044594 | 0.043658 | 0.045481 | 0.000500 | 0.000500 | 8.530 |
| knowledge-informed | knowledge-informed-family | 0.014796 | 0.014307 | 0.015243 | 0.000500 | 0.000500 | 3.941 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000450 | 0.000337 | 0.000558 | 0.000500 | 0.000500 | 0.106 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.028422 | 0.027685 | 0.029172 | 0.000500 | 0.000500 | 5.231 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.002956 | 0.002538 | 0.003369 | 0.000500 | 0.000500 | 0.501 |

Mean efficiency per condition: adaptive 0.030160, adaptive-cost-aware 0.070062, adaptive-cost-aware-family 0.073019, b-shuffled 0.018821, c-permuted 0.025865, c-plus-permuted 0.044746, knowledge-informed 0.026395, knowledge-informed-cost-rank 0.025469, knowledge-informed-family 0.041191, knowledge-informed-family-cost-rank 0.041641, random 0.016120, static 0.015486


## Calibration floor (condition D — uniform random)

Random selection achieves 2949 discoveries over 177835.0 credits (0.016583 discoveries/credit, 1.057x of static, 0.779x of knowledge-informed, 0.565x of adaptive). This is the floor any informed policy must clear to justify its knowledge channel; arms at or below this level would indicate the task or budget carries no exploitable signal.

## Ablations (exploratory; p-values unadjusted)

| base | candidate | delta | p | d | note |
|---|---|---|---|---|---|
| adaptive | c-permuted | -0.012566 | 0.000500 | -2.244 | permuted-outcome feedback (machinery kept) |
| knowledge-informed | b-shuffled | -0.001713 | 0.051974 | -0.247 | shuffled-K0 knowledge (association destroyed) |
| b-shuffled | static | -0.003889 | 0.000500 | -0.567 | shuffled knowledge vs no knowledge |
| adaptive-cost-aware | c-plus-permuted | -0.032476 | 0.000500 | -5.698 | permuted-outcome feedback on cost-aware machinery |

## Held-out transfer (gamma family)

Transfer evaluation on held-out family **gamma**, which was never included in the K0 prior.

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 2909 | 186240.0 | 0.01562 | 10368 |
| knowledge-informed | 2889 | 176640.0 | 0.016355 | 9984 |
| adaptive | 10761 | 188510.0 | 0.057085 | 15685 |
| random | 3117 | 178195.0 | 0.017492 | 10575 |
| adaptive-cost-aware | 13820 | 191805.0 | 0.072052 | 19200 |
| knowledge-informed-cost-rank | 4981 | 192000.0 | 0.025943 | 19200 |
| adaptive-cost-aware-family | 13773 | 191795.0 | 0.071811 | 19202 |
| knowledge-informed-family | 2889 | 176640.0 | 0.016355 | 9984 |
| knowledge-informed-family-cost-rank | 4981 | 192000.0 | 0.025943 | 19200 |

### Held-out pairwise comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.000736 | 0.000396 | 0.001053 | 0.000500 | 0.000611 | 0.445 |
| static | adaptive | 0.041396 | 0.039903 | 0.042996 | 0.000500 | 0.000611 | 6.138 |
| knowledge-informed | adaptive | 0.040661 | 0.039114 | 0.042261 | 0.000500 | 0.000611 | 6.015 |
| static | adaptive-cost-aware | 0.056431 | 0.055826 | 0.057087 | 0.000500 | 0.000611 | 17.786 |
| knowledge-informed | adaptive-cost-aware | 0.055696 | 0.055039 | 0.056400 | 0.000500 | 0.000611 | 17.380 |
| adaptive | adaptive-cost-aware | 0.015035 | 0.013725 | 0.016430 | 0.000500 | 0.000611 | 2.065 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.046108 | 0.045481 | 0.046747 | 0.000500 | 0.000611 | 13.818 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.009587 | 0.009329 | 0.009864 | 0.000500 | 0.000611 | 4.920 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.046108 | 0.045481 | 0.046747 | 0.000500 | 0.000611 | 13.818 |
| adaptive-cost-aware | adaptive-cost-aware-family | -0.000241 | -0.000521 | 0.000020 | 0.093453 | 0.102799 | -0.057 |

### Promotion-criterion status (protocol 230 §5)

- C > A per training family: {'alpha': True, 'beta': True}
- C > B per training family: {'alpha': True, 'beta': True}
- gap persists on held-out vs A: True
- gap persists on held-out vs B: True

**promotion criterion MET: adaptive-cost-aware > A and adaptive-cost-aware > B (adjusted p < 0.05, CI excluding 0) on all 2 training families, and the gap persists on held-out gamma**

## Adaptive-policy adaptation evidence (condition C)

### adaptive · family alpha
- fraction of selections on useful operators: early 0.661 -> late 0.635 (no upward shift)
- operator attempt counts: {'synthesize': (12, 902), 'decompose': (831, 1111), 'reparameterize': (15, 840), 'tune': (1209, 1636), 'refresh': (2, 140), 'validate': (527, 723)}

### adaptive · family beta
- fraction of selections on useful operators: early 0.916 -> late 0.919 (shifted toward useful operators)
- operator attempt counts: {'reparameterize': (1484, 2001), 'synthesize': (1142, 1565), 'decompose': (2, 130), 'validate': (0, 89), 'tune': (3, 106), 'refresh': (41, 55)}

### adaptive-cost-aware · family alpha
- fraction of selections on useful operators: early 0.860 -> late 0.864 (shifted toward useful operators)
- operator attempt counts: {'reparameterize': (17, 1034), 'validate': (2252, 3045), 'tune': (3830, 5233), 'refresh': (4, 219), 'rollback': (0, 70), 'decompose': (2, 4)}

### adaptive-cost-aware · family beta
- fraction of selections on useful operators: early 0.960 -> late 0.946 (no upward shift)
- operator attempt counts: {'reparameterize': (6572, 8958), 'tune': (1, 229), 'refresh': (142, 194), 'validate': (3, 187), 'rollback': (0, 32), 'decompose': (0, 2)}

### adaptive-cost-aware-family · family alpha
- fraction of selections on useful operators: early 0.988 -> late 0.989 (shifted toward useful operators)
- operator attempt counts: {'validate': (2999, 4041), 'tune': (3966, 5437), 'rollback': (0, 109), 'decompose': (7, 9)}

### adaptive-cost-aware-family · family beta
- fraction of selections on useful operators: early 0.992 -> late 0.991 (no upward shift)
- operator attempt counts: {'refresh': (3165, 4352), 'reparameterize': (3818, 5170), 'rollback': (0, 81)}


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
