# Cumulative Search Policy Comparison — protocol-233-p30

Protocol: 1.1.0 (see spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md)
Environment: toy-discovery 1.1.0; families: alpha, beta; held-out: gamma
Budget per episode: 150.0 credits; episodes/trial: 10; trials (seeds): 128
Discovery gate: valid implementation AND effect_1 >= threshold AND effect_2 >= threshold (2-seed replication gate)

## Per-condition outcome

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 2921 | 186240.0 | 0.015684 | 10368 |
| knowledge-informed | 3809 | 179200.0 | 0.021256 | 10240 |
| adaptive | 9105 | 187425.0 | 0.048579 | 14631 |
| random | 2949 | 177835.0 | 0.016583 | 10487 |
| adaptive-cost-aware | 12192 | 190355.0 | 0.064049 | 19263 |
| knowledge-informed-cost-rank | 7162 | 192000.0 | 0.037302 | 19200 |
| adaptive-cost-aware-family | 13542 | 189905.0 | 0.071309 | 19395 |
| knowledge-informed-family | 8921 | 179200.0 | 0.049782 | 12160 |
| knowledge-informed-family-cost-rank | 10816 | 185600.0 | 0.058276 | 18560 |
| c-permuted | 5211 | 186595.0 | 0.027927 | 14640 |
| b-shuffled | 3402 | 177885.0 | 0.019125 | 11894 |
| c-plus-permuted | 5981 | 189810.0 | 0.03151 | 20922 |

## Pairwise comparisons (A vs B, A vs C, B vs C; BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.005572 | 0.005210 | 0.005914 | 0.000500 | 0.000500 | 2.867 |
| static | adaptive | 0.032843 | 0.031614 | 0.034071 | 0.000500 | 0.000500 | 6.157 |
| knowledge-informed | adaptive | 0.027271 | 0.026107 | 0.028404 | 0.000500 | 0.000500 | 5.029 |
| static | adaptive-cost-aware | 0.048359 | 0.047567 | 0.049116 | 0.000500 | 0.000500 | 14.128 |
| knowledge-informed | adaptive-cost-aware | 0.042787 | 0.042073 | 0.043429 | 0.000500 | 0.000500 | 12.020 |
| adaptive | adaptive-cost-aware | 0.015516 | 0.014320 | 0.016718 | 0.000500 | 0.000500 | 2.539 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.026741 | 0.026094 | 0.027363 | 0.000500 | 0.000500 | 6.920 |
| knowledge-informed | knowledge-informed-family | 0.028527 | 0.028131 | 0.028901 | 0.000500 | 0.000500 | 10.587 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.008493 | 0.008162 | 0.008822 | 0.000500 | 0.000500 | 2.554 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.005767 | 0.005193 | 0.006334 | 0.000500 | 0.000500 | 1.421 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.007262 | 0.006837 | 0.007697 | 0.000500 | 0.000500 | 1.672 |

## Per-family comparisons (protocol §5 pairing: family × seed)

### family alpha

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | -0.015013 | -0.015438 | -0.014560 | 0.000500 | 0.000611 | -8.042 |
| static | adaptive | 0.020711 | 0.019178 | 0.022335 | 0.000500 | 0.000611 | 3.219 |
| knowledge-informed | adaptive | 0.035724 | 0.034218 | 0.037302 | 0.000500 | 0.000611 | 5.721 |
| static | adaptive-cost-aware | 0.041587 | 0.040461 | 0.042678 | 0.000500 | 0.000611 | 8.387 |
| knowledge-informed | adaptive-cost-aware | 0.056600 | 0.055451 | 0.057723 | 0.000500 | 0.000611 | 12.021 |
| adaptive | adaptive-cost-aware | 0.020876 | 0.019074 | 0.022578 | 0.000500 | 0.000611 | 2.693 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.032137 | 0.031050 | 0.033153 | 0.000500 | 0.000611 | 6.306 |
| knowledge-informed | knowledge-informed-family | 0.057054 | 0.056261 | 0.057801 | 0.000500 | 0.000611 | 17.638 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | -0.000453 | -0.001341 | 0.000405 | 0.321839 | 0.354023 | -0.081 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.014341 | 0.013579 | 0.015079 | 0.000500 | 0.000611 | 2.308 |

Mean efficiency per condition: adaptive 0.036594, adaptive-cost-aware 0.057471, adaptive-cost-aware-family 0.071812, b-shuffled 0.020044, c-permuted 0.011005, c-plus-permuted 0.011026, knowledge-informed 0.000871, knowledge-informed-cost-rank 0.025333, knowledge-informed-family 0.057924, knowledge-informed-family-cost-rank 0.057924, random 0.017022, static 0.015884

### family beta

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.026155 | 0.025559 | 0.026702 | 0.000500 | 0.000611 | 7.656 |
| static | adaptive | 0.044760 | 0.042835 | 0.046527 | 0.000500 | 0.000611 | 5.525 |
| knowledge-informed | adaptive | 0.018605 | 0.016849 | 0.020204 | 0.000500 | 0.000611 | 2.192 |
| static | adaptive-cost-aware | 0.055104 | 0.054100 | 0.056054 | 0.000500 | 0.000611 | 12.111 |
| knowledge-informed | adaptive-cost-aware | 0.028949 | 0.028279 | 0.029637 | 0.000500 | 0.000611 | 5.561 |
| adaptive | adaptive-cost-aware | 0.010345 | 0.008911 | 0.011927 | 0.000500 | 0.000611 | 1.149 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.021319 | 0.020667 | 0.021963 | 0.000500 | 0.000611 | 3.856 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.016964 | 0.016315 | 0.017600 | 0.000500 | 0.000611 | 3.535 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.011986 | 0.011270 | 0.012689 | 0.000500 | 0.000611 | 2.117 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.000201 | -0.000216 | 0.000613 | 0.345827 | 0.380410 | 0.035 |

Mean efficiency per condition: adaptive 0.060246, adaptive-cost-aware 0.070590, adaptive-cost-aware-family 0.070792, b-shuffled 0.017487, c-permuted 0.044760, c-plus-permuted 0.052022, knowledge-informed 0.041641, knowledge-informed-cost-rank 0.049271, knowledge-informed-family 0.041641, knowledge-informed-family-cost-rank 0.058604, random 0.016120, static 0.015486


## Calibration floor (condition D — uniform random)

Random selection achieves 2949 discoveries over 177835.0 credits (0.016583 discoveries/credit, 1.057x of static, 0.780x of knowledge-informed, 0.341x of adaptive). This is the floor any informed policy must clear to justify its knowledge channel; arms at or below this level would indicate the task or budget carries no exploitable signal.

## Ablations (exploratory; p-values unadjusted)

| base | candidate | delta | p | d | note |
|---|---|---|---|---|---|
| adaptive | c-permuted | -0.020621 | 0.000500 | -3.182 | permuted-outcome feedback (machinery kept) |
| knowledge-informed | b-shuffled | -0.002492 | 0.004498 | -0.355 | shuffled-K0 knowledge (association destroyed) |
| b-shuffled | static | -0.003079 | 0.000500 | -0.443 | shuffled knowledge vs no knowledge |
| adaptive-cost-aware | c-plus-permuted | -0.032530 | 0.000500 | -6.493 | permuted-outcome feedback on cost-aware machinery |

## Held-out transfer (gamma family)

Transfer evaluation on held-out family **gamma**, which was never included in the K0 prior.

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 2909 | 186240.0 | 0.01562 | 10368 |
| knowledge-informed | 5752 | 179200.0 | 0.032098 | 10240 |
| adaptive | 12147 | 190060.0 | 0.063911 | 16921 |
| random | 3117 | 178195.0 | 0.017492 | 10575 |
| adaptive-cost-aware | 13834 | 191060.0 | 0.072407 | 19217 |
| knowledge-informed-cost-rank | 9578 | 192000.0 | 0.049885 | 19200 |
| adaptive-cost-aware-family | 13790 | 190945.0 | 0.07222 | 19225 |
| knowledge-informed-family | 5752 | 179200.0 | 0.032098 | 10240 |
| knowledge-informed-family-cost-rank | 9578 | 192000.0 | 0.049885 | 19200 |

### Held-out pairwise comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.016479 | 0.016123 | 0.016831 | 0.000500 | 0.000611 | 8.155 |
| static | adaptive | 0.048255 | 0.046962 | 0.049674 | 0.000500 | 0.000611 | 8.235 |
| knowledge-informed | adaptive | 0.031776 | 0.030504 | 0.033108 | 0.000500 | 0.000611 | 5.304 |
| static | adaptive-cost-aware | 0.056784 | 0.056163 | 0.057391 | 0.000500 | 0.000611 | 18.292 |
| knowledge-informed | adaptive-cost-aware | 0.040306 | 0.039778 | 0.040871 | 0.000500 | 0.000611 | 12.048 |
| adaptive | adaptive-cost-aware | 0.008530 | 0.007350 | 0.009721 | 0.000500 | 0.000611 | 1.325 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.022519 | 0.022065 | 0.022974 | 0.000500 | 0.000611 | 6.349 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.017787 | 0.017475 | 0.018119 | 0.000500 | 0.000611 | 6.710 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.022519 | 0.022065 | 0.022974 | 0.000500 | 0.000611 | 6.349 |
| adaptive-cost-aware | adaptive-cost-aware-family | -0.000188 | -0.000411 | 0.000027 | 0.099450 | 0.109395 | -0.045 |

### Promotion-criterion status (protocol 230 §5)

- C > A per training family: {'alpha': True, 'beta': True}
- C > B per training family: {'alpha': True, 'beta': True}
- gap persists on held-out vs A: True
- gap persists on held-out vs B: True

**promotion criterion MET: adaptive-cost-aware > A and adaptive-cost-aware > B (adjusted p < 0.05, CI excluding 0) on all 2 training families, and the gap persists on held-out gamma**

## Adaptive-policy adaptation evidence (condition C)

### adaptive · family alpha
- fraction of selections on useful operators: early 0.709 -> late 0.712 (shifted toward useful operators)
- operator attempt counts: {'synthesize': (4, 307), 'reparameterize': (13, 706), 'refresh': (8, 861), 'validate': (1121, 1505), 'tune': (870, 1180), 'decompose': (1401, 1920), 'rollback': (0, 3)}

### adaptive · family beta
- fraction of selections on useful operators: early 0.957 -> late 0.951 (no upward shift)
- operator attempt counts: {'reparameterize': (2593, 3528), 'refresh': (2825, 3881), 'synthesize': (263, 365), 'decompose': (0, 177), 'tune': (7, 93), 'validate': (0, 105)}

### adaptive-cost-aware · family alpha
- fraction of selections on useful operators: early 0.768 -> late 0.766 (no upward shift)
- operator attempt counts: {'reparameterize': (19, 899), 'refresh': (10, 1055), 'validate': (3407, 4566), 'rollback': (0, 296), 'tune': (2023, 2827), 'decompose': (5, 5)}

### adaptive-cost-aware · family beta
- fraction of selections on useful operators: early 0.955 -> late 0.958 (shifted toward useful operators)
- operator attempt counts: {'tune': (2, 114), 'reparameterize': (2976, 4097), 'refresh': (3746, 5098), 'validate': (4, 134), 'rollback': (0, 171), 'decompose': (0, 1)}

### adaptive-cost-aware-family · family alpha
- fraction of selections on useful operators: early 0.967 -> late 0.967 (no upward shift)
- operator attempt counts: {'validate': (3386, 4590), 'tune': (3440, 4699), 'rollback': (0, 224), 'refresh': (1, 48), 'reparameterize': (1, 48), 'decompose': (10, 12)}

### adaptive-cost-aware-family · family beta
- fraction of selections on useful operators: early 0.938 -> late 0.936 (no upward shift)
- operator attempt counts: {'reparameterize': (3300, 4561), 'refresh': (3404, 4594), 'rollback': (0, 609), 'validate': (0, 2), 'tune': (0, 8)}


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
