# Cumulative Search Policy Comparison — protocol-233-p240

Protocol: 1.1.0 (see spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md)
Environment: toy-discovery 1.1.0; families: alpha, beta; held-out: gamma
Budget per episode: 150.0 credits; episodes/trial: 10; trials (seeds): 128
Discovery gate: valid implementation AND effect_1 >= threshold AND effect_2 >= threshold (2-seed replication gate)

## Per-condition outcome

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 2921 | 186240.0 | 0.015684 | 10368 |
| knowledge-informed | 3837 | 179200.0 | 0.021412 | 10240 |
| adaptive | 8870 | 186740.0 | 0.047499 | 14848 |
| random | 2949 | 177835.0 | 0.016583 | 10487 |
| adaptive-cost-aware | 12281 | 192000.0 | 0.063964 | 19200 |
| knowledge-informed-cost-rank | 7184 | 192000.0 | 0.037417 | 19200 |
| adaptive-cost-aware-family | 14090 | 192000.0 | 0.073385 | 19200 |
| knowledge-informed-family | 8921 | 181760.0 | 0.049081 | 12160 |
| knowledge-informed-family-cost-rank | 8921 | 179200.0 | 0.049782 | 12160 |
| c-permuted | 4862 | 183500.0 | 0.026496 | 12796 |
| b-shuffled | 3395 | 177370.0 | 0.019141 | 11963 |
| c-plus-permuted | 7336 | 191930.0 | 0.038222 | 19201 |

## Pairwise comparisons (A vs B, A vs C, B vs C; BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.005728 | 0.005379 | 0.006076 | 0.000500 | 0.000500 | 2.934 |
| static | adaptive | 0.031743 | 0.030242 | 0.033157 | 0.000500 | 0.000500 | 5.098 |
| knowledge-informed | adaptive | 0.026015 | 0.024517 | 0.027430 | 0.000500 | 0.000500 | 4.126 |
| static | adaptive-cost-aware | 0.048279 | 0.047542 | 0.048977 | 0.000500 | 0.000500 | 14.563 |
| knowledge-informed | adaptive-cost-aware | 0.042552 | 0.041884 | 0.043196 | 0.000500 | 0.000500 | 12.294 |
| adaptive | adaptive-cost-aware | 0.016536 | 0.015157 | 0.018038 | 0.000500 | 0.000500 | 2.414 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.026547 | 0.025927 | 0.027167 | 0.000500 | 0.000500 | 7.117 |
| knowledge-informed | knowledge-informed-family | 0.027669 | 0.027241 | 0.028064 | 0.000500 | 0.000500 | 10.341 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000701 | 0.000693 | 0.000708 | 0.000500 | 0.000500 | 0.226 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.014181 | 0.013552 | 0.014768 | 0.000500 | 0.000500 | 3.727 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.009422 | 0.008969 | 0.009891 | 0.000500 | 0.000500 | 2.313 |

## Per-family comparisons (protocol §5 pairing: family × seed)

### family alpha

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.000545 | 0.000055 | 0.001040 | 0.029985 | 0.029985 | 0.214 |
| static | adaptive | 0.028139 | 0.026246 | 0.029988 | 0.000500 | 0.000550 | 3.618 |
| knowledge-informed | adaptive | 0.027594 | 0.025717 | 0.029450 | 0.000500 | 0.000550 | 3.531 |
| static | adaptive-cost-aware | 0.045075 | 0.043957 | 0.046191 | 0.000500 | 0.000550 | 9.252 |
| knowledge-informed | adaptive-cost-aware | 0.044530 | 0.043430 | 0.045614 | 0.000500 | 0.000550 | 9.026 |
| adaptive | adaptive-cost-aware | 0.016936 | 0.015329 | 0.018575 | 0.000500 | 0.000550 | 1.914 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.011594 | 0.010729 | 0.012490 | 0.000500 | 0.000550 | 2.142 |
| knowledge-informed | knowledge-informed-family | 0.039887 | 0.039218 | 0.040513 | 0.000500 | 0.000550 | 11.090 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.001609 | 0.001588 | 0.001630 | 0.000500 | 0.000550 | 0.366 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.003034 | 0.002131 | 0.003934 | 0.000500 | 0.000550 | 0.547 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.012531 | 0.011844 | 0.013219 | 0.000500 | 0.000550 | 2.152 |

Mean efficiency per condition: adaptive 0.044023, adaptive-cost-aware 0.060958, adaptive-cost-aware-family 0.073490, b-shuffled 0.020941, c-permuted 0.019405, c-plus-permuted 0.031115, knowledge-informed 0.016429, knowledge-informed-cost-rank 0.049365, knowledge-informed-family 0.056315, knowledge-informed-family-cost-rank 0.057924, random 0.017022, static 0.015884

### family beta

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.010909 | 0.010428 | 0.011382 | 0.000500 | 0.000550 | 3.903 |
| static | adaptive | 0.035188 | 0.032889 | 0.037333 | 0.000500 | 0.000550 | 3.718 |
| knowledge-informed | adaptive | 0.024279 | 0.022061 | 0.026306 | 0.000500 | 0.000550 | 2.529 |
| static | adaptive-cost-aware | 0.051483 | 0.050304 | 0.052661 | 0.000500 | 0.000550 | 9.822 |
| knowledge-informed | adaptive-cost-aware | 0.040574 | 0.039536 | 0.041578 | 0.000500 | 0.000550 | 7.407 |
| adaptive | adaptive-cost-aware | 0.016295 | 0.014234 | 0.018484 | 0.000500 | 0.000550 | 1.541 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.041500 | 0.040417 | 0.042552 | 0.000500 | 0.000550 | 7.373 |
| knowledge-informed | knowledge-informed-family | 0.015246 | 0.014743 | 0.015725 | 0.000500 | 0.000550 | 4.045 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.025328 | 0.024456 | 0.026217 | 0.000500 | 0.000550 | 4.352 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.006313 | 0.005729 | 0.006927 | 0.000500 | 0.000550 | 1.006 |

Mean efficiency per condition: adaptive 0.050674, adaptive-cost-aware 0.066969, adaptive-cost-aware-family 0.073281, b-shuffled 0.016683, c-permuted 0.033574, c-plus-permuted 0.045340, knowledge-informed 0.026395, knowledge-informed-cost-rank 0.025469, knowledge-informed-family 0.041641, knowledge-informed-family-cost-rank 0.041641, random 0.016120, static 0.015486


## Calibration floor (condition D — uniform random)

Random selection achieves 2949 discoveries over 177835.0 credits (0.016583 discoveries/credit, 1.057x of static, 0.774x of knowledge-informed, 0.349x of adaptive). This is the floor any informed policy must clear to justify its knowledge channel; arms at or below this level would indicate the task or budget carries no exploitable signal.

## Ablations (exploratory; p-values unadjusted)

| base | candidate | delta | p | d | note |
|---|---|---|---|---|---|
| adaptive | c-permuted | -0.020942 | 0.000500 | -3.018 | permuted-outcome feedback (machinery kept) |
| knowledge-informed | b-shuffled | -0.002602 | 0.001499 | -0.394 | shuffled-K0 knowledge (association destroyed) |
| b-shuffled | static | -0.003126 | 0.001000 | -0.479 | shuffled knowledge vs no knowledge |
| adaptive-cost-aware | c-plus-permuted | -0.025741 | 0.000500 | -5.144 | permuted-outcome feedback on cost-aware machinery |

## Held-out transfer (gamma family)

Transfer evaluation on held-out family **gamma**, which was never included in the K0 prior.

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 2909 | 186240.0 | 0.01562 | 10368 |
| knowledge-informed | 2985 | 179200.0 | 0.016657 | 10240 |
| adaptive | 12432 | 190110.0 | 0.065394 | 17956 |
| random | 3117 | 178195.0 | 0.017492 | 10575 |
| adaptive-cost-aware | 13532 | 192000.0 | 0.070479 | 19200 |
| knowledge-informed-cost-rank | 4981 | 192000.0 | 0.025943 | 19200 |
| adaptive-cost-aware-family | 13537 | 192000.0 | 0.070505 | 19200 |
| knowledge-informed-family | 2985 | 179200.0 | 0.016657 | 10240 |
| knowledge-informed-family-cost-rank | 4981 | 192000.0 | 0.025943 | 19200 |

### Held-out pairwise comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.001038 | 0.000730 | 0.001333 | 0.000500 | 0.000611 | 0.638 |
| static | adaptive | 0.049753 | 0.048801 | 0.050675 | 0.000500 | 0.000611 | 11.828 |
| knowledge-informed | adaptive | 0.048715 | 0.047804 | 0.049640 | 0.000500 | 0.000611 | 11.543 |
| static | adaptive-cost-aware | 0.054860 | 0.054235 | 0.055482 | 0.000500 | 0.000611 | 17.758 |
| knowledge-informed | adaptive-cost-aware | 0.053822 | 0.053178 | 0.054484 | 0.000500 | 0.000611 | 17.316 |
| adaptive | adaptive-cost-aware | 0.005107 | 0.004380 | 0.005863 | 0.000500 | 0.000611 | 1.027 |
| knowledge-informed-cost-rank | adaptive-cost-aware | 0.044536 | 0.043911 | 0.045161 | 0.000500 | 0.000611 | 13.672 |
| knowledge-informed | knowledge-informed-family | 0.000000 | 0.000000 | 0.000000 | 1.000000 | 1.000000 | 0.000 |
| knowledge-informed-family | knowledge-informed-family-cost-rank | 0.009285 | 0.009055 | 0.009528 | 0.000500 | 0.000611 | 4.819 |
| knowledge-informed-family-cost-rank | adaptive-cost-aware | 0.044536 | 0.043911 | 0.045161 | 0.000500 | 0.000611 | 13.672 |
| adaptive-cost-aware | adaptive-cost-aware-family | 0.000026 | -0.000292 | 0.000354 | 0.897551 | 0.987306 | 0.006 |

### Promotion-criterion status (protocol 230 §5)

- C > A per training family: {'alpha': True, 'beta': True}
- C > B per training family: {'alpha': True, 'beta': True}
- gap persists on held-out vs A: True
- gap persists on held-out vs B: True

**promotion criterion MET: adaptive-cost-aware > A and adaptive-cost-aware > B (adjusted p < 0.05, CI excluding 0) on all 2 training families, and the gap persists on held-out gamma**

## Adaptive-policy adaptation evidence (condition C)

### adaptive · family alpha
- fraction of selections on useful operators: early 0.728 -> late 0.735 (shifted toward useful operators)
- operator attempt counts: {'synthesize': (12, 554), 'validate': (3274, 4446), 'refresh': (19, 1092), 'tune': (697, 921), 'reparameterize': (6, 379), 'decompose': (114, 148)}

### adaptive · family beta
- fraction of selections on useful operators: early 0.888 -> late 0.894 (shifted toward useful operators)
- operator attempt counts: {'refresh': (3958, 5434), 'validate': (9, 519), 'decompose': (3, 66), 'tune': (4, 213), 'reparameterize': (301, 426), 'synthesize': (473, 650)}

### adaptive-cost-aware · family alpha
- fraction of selections on useful operators: early 0.836 -> late 0.821 (no upward shift)
- operator attempt counts: {'reparameterize': (10, 477), 'refresh': (13, 1168), 'tune': (1005, 1348), 'validate': (4824, 6607)}

### adaptive-cost-aware · family beta
- fraction of selections on useful operators: early 0.914 -> late 0.911 (no upward shift)
- operator attempt counts: {'validate': (7, 564), 'refresh': (6023, 8205), 'reparameterize': (392, 557), 'tune': (7, 274)}

### adaptive-cost-aware-family · family alpha
- fraction of selections on useful operators: early 1.000 -> late 1.000 (no upward shift)
- operator attempt counts: {'validate': (3685, 5032), 'tune': (3370, 4568)}

### adaptive-cost-aware-family · family beta
- fraction of selections on useful operators: early 1.000 -> late 1.000 (no upward shift)
- operator attempt counts: {'refresh': (2574, 3493), 'reparameterize': (4461, 6107)}


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
