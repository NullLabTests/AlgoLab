# Cumulative Search Policy Comparison — protocol-234-p120

Protocol: 1.1.0 (see spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md)
Environment: toy-discovery 1.1.0; families: alpha, beta; held-out: gamma
Budget per episode: 150.0 credits; episodes/trial: 10; trials (seeds): 128
Discovery gate: valid implementation AND effect_1 >= threshold AND effect_2 >= threshold (2-seed replication gate)

## Per-condition outcome

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 2921 | 186240.0 | 0.015684 | 10368 |
| knowledge-informed | 3823 | 179200.0 | 0.021334 | 10240 |
| adaptive | 8992 | 186370.0 | 0.048248 | 14787 |
| random | 2949 | 177835.0 | 0.016583 | 10487 |
| adaptive-cost-aware | 12393 | 192000.0 | 0.064547 | 19200 |
| knowledge-informed-cost-rank | 7192 | 192000.0 | 0.037458 | 19200 |
| adaptive-cost-aware-family | 14086 | 191970.0 | 0.073376 | 19200 |
| knowledge-informed-family | 8828 | 179200.0 | 0.049263 | 12032 |
| knowledge-informed-family-cost-rank | 8921 | 179200.0 | 0.049782 | 12160 |
| knowledge-informed-family-commit | 14090 | 192000.0 | 0.073385 | 19200 |
| knowledge-informed-family-alloc | 9905 | 183680.0 | 0.053925 | 15488 |
| c-permuted | 5309 | 186100.0 | 0.028528 | 14118 |
| b-shuffled | 3577 | 178145.0 | 0.020079 | 12401 |
| c-plus-permuted | 7137 | 191515.0 | 0.037266 | 19249 |

## Pairwise comparisons (A vs B, A vs C, B vs C; BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.005650 | 0.005288 | 0.006010 | 0.000500 | 0.000535 | 2.934 |
| static | adaptive | 0.032505 | 0.031216 | 0.033886 | 0.000500 | 0.000535 | 5.650 |
| knowledge-informed | adaptive | 0.026855 | 0.025524 | 0.028270 | 0.000500 | 0.000535 | 4.607 |
| static | adaptive-cost-aware | 0.048863 | 0.048098 | 0.049620 | 0.000500 | 0.000535 | 14.353 |
| knowledge-informed | adaptive-cost-aware | 0.043213 | 0.042451 | 0.043953 | 0.000500 | 0.000535 | 12.235 |
| adaptive | adaptive-cost-aware | 0.016358 | 0.014935 | 0.017673 | 0.000500 | 0.000535 | 2.528 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.027089 | 0.026417 | 0.027740 | 0.000500 | 0.000535 | 7.216 |
| knowledge-informed | knowledge-informed-family | 0.027930 | 0.027478 | 0.028348 | 0.000500 | 0.000535 | 10.494 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000519 | 0.000463 | 0.000575 | 0.000500 | 0.000535 | 0.167 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.014765 | 0.014188 | 0.015348 | 0.000500 | 0.000535 | 3.803 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.008829 | 0.008451 | 0.009188 | 0.000500 | 0.000535 | 2.129 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | 0.023603 | 0.023218 | 0.023996 | 0.000500 | 0.000535 | 6.839 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | -0.000009 | -0.000024 | 0.000003 | 0.244878 | 0.244878 | -0.003 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | 0.004143 | 0.003865 | 0.004426 | 0.000500 | 0.000535 | 1.328 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.019451 | 0.019093 | 0.019797 | 0.000500 | 0.000535 | 5.649 |

## Per-family comparisons (protocol §5 pairing: family × seed)

### family alpha

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.000344 | -0.000076 | 0.000762 | 0.120940 | 0.129578 | 0.140 |
| static | adaptive | 0.045973 | 0.044215 | 0.047496 | 0.000500 | 0.000577 | 6.152 |
| knowledge-informed | adaptive | 0.045629 | 0.043901 | 0.047135 | 0.000500 | 0.000577 | 6.100 |
| static | adaptive-cost-aware | 0.054710 | 0.053660 | 0.055675 | 0.000500 | 0.000577 | 12.056 |
| knowledge-informed | adaptive-cost-aware | 0.054366 | 0.053358 | 0.055312 | 0.000500 | 0.000577 | 11.952 |
| adaptive | adaptive-cost-aware | 0.008737 | 0.007386 | 0.010252 | 0.000500 | 0.000577 | 1.040 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.021135 | 0.020458 | 0.021823 | 0.000500 | 0.000577 | 4.091 |
| knowledge-informed | knowledge-informed-family | 0.040881 | 0.040198 | 0.041561 | 0.000500 | 0.000577 | 11.471 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000816 | 0.000805 | 0.000826 | 0.000500 | 0.000577 | 0.184 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.012670 | 0.012005 | 0.013312 | 0.000500 | 0.000577 | 2.413 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.002889 | 0.002531 | 0.003275 | 0.000500 | 0.000577 | 0.521 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | 0.015565 | 0.015039 | 0.016078 | 0.000500 | 0.000577 | 3.243 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | -0.000007 | -0.000020 | 0.000000 | 1.000000 | 1.000000 | -0.001 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | 0.000691 | 0.000335 | 0.001053 | 0.000500 | 0.000577 | 0.156 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.014868 | 0.014398 | 0.015297 | 0.000500 | 0.000577 | 3.112 |

Mean efficiency per condition: adaptive 0.061857, adaptive-cost-aware 0.070594, adaptive-cost-aware-family 0.073483, b-shuffled 0.020377, c-permuted 0.040551, c-plus-permuted 0.054440, knowledge-informed 0.016228, knowledge-informed-cost-rank 0.049458, knowledge-informed-family 0.057108, knowledge-informed-family-alloc 0.058615, knowledge-informed-family-commit 0.073490, knowledge-informed-family-cost-rank 0.057924, random 0.017022, static 0.015884

### family beta

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.010954 | 0.010400 | 0.011499 | 0.000500 | 0.000535 | 3.739 |
| static | adaptive | 0.018286 | 0.016367 | 0.020467 | 0.000500 | 0.000535 | 2.093 |
| knowledge-informed | adaptive | 0.007333 | 0.005344 | 0.009587 | 0.000500 | 0.000535 | 0.822 |
| static | adaptive-cost-aware | 0.043014 | 0.041918 | 0.044154 | 0.000500 | 0.000535 | 8.597 |
| knowledge-informed | adaptive-cost-aware | 0.032060 | 0.030993 | 0.033134 | 0.000500 | 0.000535 | 6.022 |
| adaptive | adaptive-cost-aware | 0.024728 | 0.022350 | 0.026946 | 0.000500 | 0.000535 | 2.522 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.033042 | 0.032010 | 0.034094 | 0.000500 | 0.000535 | 6.175 |
| knowledge-informed | knowledge-informed-family | 0.014751 | 0.014238 | 0.015241 | 0.000500 | 0.000535 | 3.825 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000450 | 0.000337 | 0.000558 | 0.000500 | 0.000535 | 0.106 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.016859 | 0.015901 | 0.017825 | 0.000500 | 0.000535 | 3.007 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.014769 | 0.014093 | 0.015399 | 0.000500 | 0.000535 | 2.432 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | 0.031641 | 0.031063 | 0.032240 | 0.000500 | 0.000535 | 6.514 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | -0.000012 | -0.000037 | 0.000009 | 0.437281 | 0.437281 | -0.002 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | 0.007562 | 0.007120 | 0.008021 | 0.000500 | 0.000535 | 1.809 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.024067 | 0.023533 | 0.024615 | 0.000500 | 0.000535 | 5.028 |

Mean efficiency per condition: adaptive 0.033772, adaptive-cost-aware 0.058500, adaptive-cost-aware-family 0.073269, b-shuffled 0.019034, c-permuted 0.016411, c-plus-permuted 0.020151, knowledge-informed 0.026440, knowledge-informed-cost-rank 0.025458, knowledge-informed-family 0.041191, knowledge-informed-family-alloc 0.049202, knowledge-informed-family-commit 0.073281, knowledge-informed-family-cost-rank 0.041641, random 0.016120, static 0.015486


## Calibration floor (condition D — uniform random)

Random selection achieves 2949 discoveries over 177835.0 credits (0.016583 discoveries/credit, 1.057x of static, 0.777x of knowledge-informed, 0.344x of adaptive). This is the floor any informed policy must clear to justify its knowledge channel; arms at or below this level would indicate the task or budget carries no exploitable signal.

## Ablations (exploratory; p-values unadjusted)

| base | candidate | delta | p | d | note |
|---|---|---|---|---|---|
| adaptive | c-permuted | -0.019685 | 0.000500 | -2.850 | permuted-outcome feedback (machinery kept) |
| knowledge-informed | b-shuffled | -0.001621 | 0.060970 | -0.233 | shuffled-K0 knowledge (association destroyed) |
| b-shuffled | static | -0.004029 | 0.000500 | -0.584 | shuffled knowledge vs no knowledge |
| adaptive-cost-aware | c-plus-permuted | -0.027278 | 0.000500 | -5.536 | permuted-outcome feedback on cost-aware machinery |

## Held-out transfer (gamma family)

Transfer evaluation on held-out family **gamma**, which was never included in the K0 prior.

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 2909 | 186240.0 | 0.01562 | 10368 |
| knowledge-informed | 2911 | 179200.0 | 0.016244 | 10240 |
| adaptive | 9213 | 187940.0 | 0.049021 | 14551 |
| random | 3117 | 178195.0 | 0.017492 | 10575 |
| adaptive-cost-aware | 12750 | 191995.0 | 0.066408 | 19200 |
| knowledge-informed-cost-rank | 4883 | 192000.0 | 0.025432 | 19200 |
| adaptive-cost-aware-family | 12783 | 192000.0 | 0.066578 | 19200 |
| knowledge-informed-family | 2911 | 179200.0 | 0.016244 | 10240 |
| knowledge-informed-family-cost-rank | 4883 | 192000.0 | 0.025432 | 19200 |
| knowledge-informed-family-commit | 286 | 192000.0 | 0.00149 | 19200 |
| knowledge-informed-family-alloc | 5414 | 184320.0 | 0.029373 | 15488 |

### Held-out pairwise comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.000625 | 0.000306 | 0.000938 | 0.000500 | 0.000577 | 0.372 |
| static | adaptive | 0.033280 | 0.031416 | 0.035150 | 0.000500 | 0.000577 | 4.237 |
| knowledge-informed | adaptive | 0.032655 | 0.030761 | 0.034567 | 0.000500 | 0.000577 | 4.147 |
| static | adaptive-cost-aware | 0.050788 | 0.050096 | 0.051485 | 0.000500 | 0.000577 | 14.712 |
| knowledge-informed | adaptive-cost-aware | 0.050163 | 0.049481 | 0.050894 | 0.000500 | 0.000577 | 14.354 |
| adaptive | adaptive-cost-aware | 0.017508 | 0.015678 | 0.019415 | 0.000500 | 0.000577 | 2.076 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.040975 | 0.040327 | 0.041661 | 0.000500 | 0.000577 | 11.346 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.009188 | 0.008932 | 0.009452 | 0.000500 | 0.000577 | 4.623 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.040975 | 0.040327 | 0.041661 | 0.000500 | 0.000577 | 11.346 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.000170 | -0.000344 | 0.000660 | 0.488756 | 0.523667 | 0.038 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-commit | -0.023943 | -0.024333 | -0.023583 | 0.000500 | 0.000577 | -13.853 |
| knowledge-informed-family-commit | adaptive-cost-aware-family | 0.065089 | 0.064318 | 0.065880 | 0.000500 | 0.000577 | 20.376 |
| knowledge-informed-family-cost-rank | knowledge-informed-family-alloc | 0.003941 | 0.003528 | 0.004323 | 0.000500 | 0.000577 | 1.699 |
| knowledge-informed-family-alloc | adaptive-cost-aware-family | 0.037205 | 0.036578 | 0.037839 | 0.000500 | 0.000577 | 10.482 |

### Promotion-criterion status (protocol 230 §5)

- C > A per training family: {'alpha': True, 'beta': True}
- C > B per training family: {'alpha': True, 'beta': True}
- gap persists on held-out vs A: True
- gap persists on held-out vs B: True

**promotion criterion MET: adaptive-cost-aware > A and adaptive-cost-aware > B (adjusted p < 0.05, CI excluding 0) on all 2 training families, and the gap persists on held-out gamma**

## Adaptive-policy adaptation evidence (condition C)

### adaptive · family alpha
- fraction of selections on useful operators: early 0.934 -> late 0.935 (shifted toward useful operators)
- operator attempt counts: {'synthesize': (3, 191), 'validate': (5383, 7320), 'reparameterize': (7, 268), 'decompose': (267, 366), 'tune': (225, 323), 'refresh': (2, 100)}

### adaptive · family beta
- fraction of selections on useful operators: early 0.680 -> late 0.677 (no upward shift)
- operator attempt counts: {'validate': (19, 1245), 'tune': (4, 357), 'reparameterize': (2013, 2767), 'decompose': (9, 397), 'synthesize': (605, 838), 'refresh': (455, 615)}

### adaptive-cost-aware · family alpha
- fraction of selections on useful operators: early 0.959 -> late 0.958 (no upward shift)
- operator attempt counts: {'reparameterize': (2, 284), 'validate': (6485, 8819), 'refresh': (0, 116), 'tune': (290, 381)}

### adaptive-cost-aware · family beta
- fraction of selections on useful operators: early 0.802 -> late 0.797 (no upward shift)
- operator attempt counts: {'reparameterize': (4335, 5965), 'refresh': (1252, 1707), 'validate': (23, 1437), 'tune': (6, 491)}

### adaptive-cost-aware-family · family alpha
- fraction of selections on useful operators: early 1.000 -> late 1.000 (shifted toward useful operators)
- operator attempt counts: {'validate': (2588, 3532), 'tune': (4466, 6067), 'rollback': (0, 1)}

### adaptive-cost-aware-family · family beta
- fraction of selections on useful operators: early 0.999 -> late 1.000 (shifted toward useful operators)
- operator attempt counts: {'reparameterize': (4531, 6160), 'refresh': (2501, 3435), 'rollback': (0, 5)}


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
