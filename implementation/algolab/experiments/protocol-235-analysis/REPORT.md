# Protocol-235 Analysis Report: The Real-Workload Bridge

**Status:** Post-execution analysis of pre-registered experiment
`experiments/protocol-235-v1/` (spec/research/235_REAL_WORKLOAD_BRIDGE.md,
including its dated PRE-EXECUTION instrumentation amendment). Evidence:
checksummed bundle in `experiments/protocol-235-v1/`.

Design recap: the protocol-232/234 machinery (eleven arms, seeds discipline,
2-replicate gate, promotion criterion, BH-corrected paired statistics,
n = 32 trials) run unchanged against a genuine ML search problem —
KNN hyperparameter selection on breast_cancer (alpha) / wine (beta), with
digits-900 as held-out gamma; discovery = both replicate CV accuracies beat
the split-matched baseline by ≥ 0.5pt; ground truth unknown ex ante.
Total runtime ~30 minutes on CPU.

## 1. Headline result

**The loop survives contact with reality — partially.** On beta, the
pre-registered ordering reproduces with strong significance:
static 0.0067 < B 0.0135 < C 0.0273 ≈ C+ 0.0258 (B→C delta +0.01375,
q = 0.025). On alpha, discovery events are too rare for any separation
(all arms n.s.). The strict promotion criterion (≥2 families) is therefore
honestly **NOT met** — reported as such, no threshold moved.

| family | static | B | C | C+ | B-com | C+fam |
|---|---|---|---|---|---|---|
| alpha | 0.0021 | 0.0052 | 0.0052 | 0.0052 | **0.0156** | 0.0100 |
| beta | 0.0067 | 0.0135 | **0.0273** | 0.0258 | 0.0250 | 0.0267 |
| gamma (held out) | 0.0135 | 0.0125 | 0.0152 | **0.0192** | **0.0000** | 0.0159 |

## 2. Pre-registered hypothesis scoreboard

| # | Hypothesis | Verdict |
|---|---|---|
| H1 | promotion criterion transfers (C+ > A,B on ≥2 families + held-out direction) | **NOT met** — beta only; alpha underpowered by rare discoveries |
| H2 | B-com ≥ B-fam+ (directional) | **PASS** — beta +0.0125 (q=0.066), alpha +0.0104 |
| H3 | family-conditioning helps somewhere | **FAIL** — B vs B-fam flat/negative at this prior size |
| H4 | informed > random floor | **PASS** directionally (except alpha ties) |

## 3. The finding that matters most: adaptation is insurance, empirically

Protocol 234 ended with a caveat: commitment's fragility (wrong argmax →
unrecoverable) was theorized but never observed. Protocol 235 observed it:

- **In-domain**, B-com's frozen argmax was right (manhattan on alpha;
  k21 on beta — 29% pooled discovery rate, best of seven arms) and B-com
  posted the best training-phase efficiency overall (0.0203).
- **Under distribution shift (held-out gamma)**, the operator-value
  structure *inverts*: pooled per-operator discovery rates flip from
  k21 = 0.290 (beta) to k21 = **0.000 across 3933 attempts** (gamma),
  while k1/dist-weight rise to 0.42/0.37. B-com — unable to move — scored
  exactly **zero discoveries in every gamma episode**.
- **C+, the adaptive arm, recovered**: Thompson exploration reached k1 and
  dist-weight within the held-out phase and finished the gamma table
  *first* (0.0192).

That is the insurance hypothesis made concrete: commitment converts good
knowledge into maximal performance and bad knowledge into catastrophe;
adaptation pays a small in-domain premium for the ability to survive
knowledge that does not transfer. Neither pole dominates universally — the
trade-off is now measured, not asserted.

## 4. Secondary observations (exploratory)

- C+ locked onto k21 on beta almost immediately (73% of selections early,
  75% late) while correctly avoiding chebyshev/k3 (pooled rate 0/201,
  0/207) — the feedback loop did real work against real uncertainty.
- Family-conditioning failed here where it starred in protocol 232:
  with 20 prior attempts/family (~2.9 per operator), per-family slices are
  noise-dominated; pooled-vs-sliced rankings barely differ. The 232 effect
  required informative slice sizes — representation quality is data-
  dependent, not free.
- Alpha's near-zero separability (baseline CV accuracy 96.5%, few
  operators ever clear the gate) shows the gate margin interacts with
  dataset headroom; a workload with more alpha-like difficulty spread
  would strengthen future designs.

## 5. Where this leaves the research line

Combined with protocols 230–234, the evidence now supports a three-part
claim, all on recorded experiments:

1. Knowledge must be **family-conditioned** when history is rich enough
   (232) — else it misleads.
2. The consumer's **decision rule must match the metric** — commit over
   cycle (234) — and its fragility is real (235, gamma collapse).
3. The **adaptive loop is the insurance policy** that pays precisely under
   representation/format failure or distribution shift (230/231 in-toy;
   235 held-out, in reality).

The strict 231-style promotion bar was met in-toy (231) and not met on the
first real workload at n=32 (this protocol) — the honest state is "loop
value confirmed qualitatively on reality, criterion-level confirmation
pending a workload with more alpha-headroom or higher n."

## 6. Next steps (not started)

1. **Protocol 236 (smallest):** re-run this exact grid with trials=96 and
   an alpha-side margin recalibration (or a third training family with
   richer discovery structure) to give H1 statistical room; everything else
   frozen.
2. Insurance pricing across prior seeds (the standing 235 §6 proposal)
   now has a concrete catastrophic case (gamma collapse) to price against.
3. Schema change candidate: family-keyed `operator_stats` (232 lesson)
   remains open engineering work.
