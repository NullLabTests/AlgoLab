# Cumulative Search Policy Comparison — protocol-230-v1

Protocol: 1.1.0 (see spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md)
Environment: toy-discovery 1.1.0; families: alpha, beta; held-out: gamma
Budget per episode: 150.0 credits; episodes/trial: 10; trials (seeds): 8
Discovery gate: valid implementation AND effect_1 >= threshold AND effect_2 >= threshold (2-seed replication gate)

## Per-condition outcome

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 195 | 11640.0 | 0.016753 | 648 |
| knowledge-informed | 239 | 11040.0 | 0.021649 | 624 |
| adaptive | 311 | 11080.0 | 0.028069 | 525 |
| random | 184 | 11060.0 | 0.016637 | 623 |
| c-permuted | 190 | 11100.0 | 0.017117 | 541 |
| b-shuffled | 265 | 11205.0 | 0.02365 | 907 |

## Pairwise comparisons (A vs B, A vs C, B vs C; BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.004896 | 0.003407 | 0.006331 | 0.006497 | 0.006497 | 2.867 |
| static | adaptive | 0.011161 | 0.007090 | 0.015430 | 0.006497 | 0.006497 | 2.478 |
| knowledge-informed | adaptive | 0.006265 | 0.003625 | 0.009127 | 0.006497 | 0.006497 | 1.361 |

## Per-family comparisons (protocol §5 pairing: family × seed)

### family alpha

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | -0.000513 | -0.001973 | 0.000796 | 0.549225 | 0.549225 | -0.287 |
| static | adaptive | 0.010732 | 0.005626 | 0.017360 | 0.006497 | 0.009745 | 1.715 |
| knowledge-informed | adaptive | 0.011245 | 0.006650 | 0.017040 | 0.006497 | 0.009745 | 1.786 |

Mean efficiency per condition: adaptive 0.027973, b-shuffled 0.025619, c-permuted 0.007494, knowledge-informed 0.016728, random 0.015277, static 0.017241

### family beta

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.010161 | 0.008256 | 0.011820 | 0.006497 | 0.009745 | 4.217 |
| static | adaptive | 0.011412 | 0.006054 | 0.017777 | 0.006497 | 0.009745 | 1.837 |
| knowledge-informed | adaptive | 0.001250 | -0.002874 | 0.006688 | 0.786107 | 0.786107 | 0.195 |

Mean efficiency per condition: adaptive 0.027679, b-shuffled 0.020295, c-permuted 0.026567, knowledge-informed 0.026429, random 0.017888, static 0.016267


## Calibration floor (condition D — uniform random)

Random selection achieves 184 discoveries over 11060.0 credits (0.016637 discoveries/credit, 0.993x of static, 0.768x of knowledge-informed, 0.593x of adaptive). This is the floor any informed policy must clear to justify its knowledge channel; arms at or below this level would indicate the task or budget carries no exploitable signal.

## Ablations (exploratory; p-values unadjusted)

| base | candidate | delta | p | d | note |
|---|---|---|---|---|---|
| adaptive | c-permuted | -0.010835 | 0.007996 | -2.041 | permuted-outcome feedback (machinery kept) |
| knowledge-informed | b-shuffled | 0.001323 | 0.803598 | 0.139 | shuffled-K0 knowledge (association destroyed) |
| b-shuffled | static | -0.006219 | 0.225887 | -0.657 | shuffled knowledge vs no knowledge |

## Held-out transfer (gamma family)

Transfer evaluation on held-out family **gamma**, which was never included in the K0 prior.

| arm | discoveries | credits | discoveries/credit | attempts |
|---|---|---|---|---|
| static | 182 | 11640.0 | 0.015636 | 648 |
| knowledge-informed | 180 | 11040.0 | 0.016304 | 624 |
| adaptive | 617 | 11770.0 | 0.052421 | 939 |
| random | 173 | 11165.0 | 0.015495 | 644 |

### Held-out pairwise comparisons (BH-adjusted)

| base | candidate | delta | CI low | CI high | p | adjusted p | d |
|---|---|---|---|---|---|---|---|
| static | knowledge-informed | 0.000669 | -0.000272 | 0.001609 | 0.262369 | 0.262369 | 0.509 |
| static | adaptive | 0.036750 | 0.030511 | 0.042434 | 0.006497 | 0.009745 | 5.015 |
| knowledge-informed | adaptive | 0.036081 | 0.029454 | 0.042099 | 0.006497 | 0.009745 | 4.955 |

### Promotion-criterion status (protocol 230 §5)

- C > A per training family: {'alpha': True, 'beta': True}
- C > B per training family: {'alpha': True, 'beta': False}
- gap persists on held-out vs A: True
- gap persists on held-out vs B: True

**promotion criterion NOT met; unmet components: C>B with adjusted p < 0.05 on >=2 families**

## Adaptive-policy adaptation evidence (condition C)

### family alpha
- fraction of selections on useful operators: early 0.581 -> late 0.692 (shifted toward useful operators)
- operator attempt counts: {'synthesize': (1, 52), 'decompose': (75, 95), 'reparameterize': (1, 54), 'tune': (52, 63), 'refresh': (0, 7), 'validate': (29, 40)}

### family beta
- fraction of selections on useful operators: early 0.879 -> late 0.935 (shifted toward useful operators)
- operator attempt counts: {'reparameterize': (68, 86), 'synthesize': (83, 108), 'decompose': (1, 8), 'validate': (0, 6), 'tune': (1, 6)}


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
