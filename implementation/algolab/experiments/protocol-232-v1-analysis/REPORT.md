# Protocol-232 Analysis Report: Family-Conditioned Knowledge (experiment protocol-232-v1)

**Status:** Post-execution analysis of pre-registered experiment
`experiments/protocol-232-v1/` (spec/research/232_FAMILY_CONDITIONED_KNOWLEDGE.md,
frozen before execution; amendment log records execution outcome only).
Primary evidence: checksummed bundle in `experiments/protocol-232-v1/`.

Design recap: arms A/B/C/C+/B+/D carried over unchanged from protocols
230/231; new arms **B-fam** (`knowledge-informed-family`: frozen ranking
from the family-tagged K0 slice), **B-fam+** (same, cost-ranked), **C+fam**
(`adaptive-cost-aware-family`: C+ initialized from family slices, pooled
fallback); trials = 128; everything else identical to 231.

## 1. Headline result

| arm | pooled eff | alpha | beta | gamma (held-out) |
|---|---|---|---|---|
| static (A) | 0.015684 | 0.01588* | 0.01549* | 0.015620 |
| knowledge-informed (B) | 0.021286 | 0.0160* | 0.0264* | 0.016355 |
| knowledge-informed-cost-rank (B+) | 0.037417 | 0.0494* | 0.0255* | 0.025943 |
| **knowledge-informed-family (B-fam)** | 0.048914 | ~0.056 | ~0.041 | **0.016355** |
| **knowledge-informed-family-cost-rank (B-fam+)** | 0.049782 | ~0.058 | ~0.042 | **0.025943** |
| adaptive (C) | 0.029365 | 0.0283* | 0.0302* | 0.057085 |
| adaptive-cost-aware (C+) | 0.066919 | 0.0638* | 0.0701* | 0.072052 |
| **adaptive-cost-aware-family (C+fam)** | **0.073013** | ~0.073 | ~0.073 | 0.071811 |

(*per-family means from v2 statistics where not re-listed; v3 rows from v3
statistics.json. All comparisons below use the v3 paired analysis.)

Key deltas (BH-adjusted q = 0.0005 throughout):

- H1: B-fam > B on alpha: **+0.04029, d = 11.40**; on beta: **+0.01480,
  d = 3.94**.
- H2: C+ > B-fam+ persists: alpha +0.00584 (d = 1.05); beta **+0.02842
  (d = 5.23)**.
- H3: C+fam ≥ C+ everywhere: alpha +0.00923 (**d = 1.56**, significantly
  better); beta +0.00296 (d = 0.50); gamma 0.07181 ≈ 0.07205.
- H4: on gamma, B-fam efficiency equals B **to the printed digit**
  (0.016355; pooled fallback engaged by construction).

## 2. Pre-registered hypothesis scoreboard

| # | Hypothesis | Verdict |
|---|---|---|
| H1 | conditioning repairs frozen knowledge (B-fam > B, both families) | **PASS** |
| H2 | frozen ceiling: C+ still > best frozen composite | **PASS** |
| H3 | adaptive init source secondary (C+fam ≥ C+) | **PASS** (strictly better on alpha) |
| H4 | transfer honesty control (gamma fallback) | **PASS** |

## 3. Interpretation

**Pooling was destroying most of the frozen knowledge's value — but not
all of the adaptive advantage.** The mechanism is visible directly in the
derived snapshots:

- Pooled K0 ranks `refresh` at smoothed rate 0.267 (below three operators
  neutral in beta). The beta-tagged slice ranks it at **0.800**, and drops
  `validate` to 0.083 (correctly exposing it as neutral). The alpha slice
  independently recovers exactly {decompose, tune, validate} as its top-3.
  Conditioning turned the frozen prior from misleading to nearly an oracle
  description of each family.
- Consequently the frozen arms transformed: on beta, B-fam+ more than
  doubles B (≈0.042 vs 0.026). On alpha, B-fam ≈ 0.056 vs B's 0.016 —
  closing most (not all) of the gap to C+ there (residual d = 1.05).
- Adaptation retains genuine marginal value where history is thin or costs
  bind: per-family cells hold only ~7.5 uniform attempts per operator, so
  mis-ranked slots persist in any frozen schedule (top-K cycling cannot
  re-rank mid-trial), while C+/C+fam concentrate spend adaptively. On beta
  the frozen-vs-adaptive gap remains large (d = 5.2).
- With conditioned initialization, the adaptive arm reaches the practical
  ceiling: C+fam's beta selection mix collapses to {reparameterize 53.8%,
  refresh 45.3%, rollback 0.8%} — precisely the two cheap useful operators
  — yielding pooled efficiency 0.0730 against the estimated all-cheap-useful
  oracle of 0.0734 (~99.5% of oracle).

**Answer to the protocol question:** C+'s advantage over frozen policies
in protocols 230/231 was substantially (on alpha almost entirely) a
compensation for lossy aggregation in the knowledge layer; after repairing
the representation, a real but smaller adaptive margin remains, driven by
thin-data mis-ranking and cost concentration. The loop and the knowledge
representation are complements, not substitutes: the best system observed
is conditioned initialization × online updates × cost-normalized selection.

## 4. Design implications (recorded for M-next planning)

- The knowledge layer should persist **family-tagged aggregates**
  (schema change candidate: `operator_stats` keyed by task family), with
  pooled aggregates retained as fallback for unseen families.
- Frozen schedules remain inferior to even modest online updating at these
  data densities; "knowledge-informed" without adaptation is not a viable
  operating point except immediately after cold-start.

## 5. Scope and caveats

- Toy environment, single fixed K0 realization (prior_seed 101); the
  family-slice rates are one noisy draw of ~60 uniform attempts/family.
  A different prior seed could produce weaker slices; conclusions here are
  about this registered instance plus direction of mechanism, not about
  expected performance across priors (exploratory caveat).
- Held-out gamma has no slice by design; conditioning cannot help transfer,
  and did not (H4 confirms no leakage).
- No promotion claim is registered or altered: the claim_readiness block
  re-evaluates the protocol-231 criterion for C+ (still met); plain C's
  protocol-230 verdict remains NOT met; v1/v2 bundles untouched.

## 6. Next step (not started)

The remaining frozen-vs-adaptive gap concentrates where per-operator
per-family sample size is smallest. Smallest informative increment
(pre-register as 233 if pursued): vary `prior_attempts_per_family`
(e.g., {30, 60, 120, 240}) at fixed everything-else, measuring B-fam+
and C+fam efficiency against the oracle curve — a direct dose-response
test of "adaptation value ∝ 1/history quality". This requires no new
mechanisms, only a swept registered parameter.
