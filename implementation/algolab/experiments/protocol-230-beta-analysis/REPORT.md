# Beta-Family Analysis: Why Adaptive (C) ≈ Knowledge-Informed (B) on beta

**Status:** Post-hoc exploratory analysis of the frozen, pre-registered
experiment `experiments/protocol-230-v1/` (protocol 230 v1.1.0).
**Not part of the pre-registered result.** The original artifact bundle is
unchanged (all 28 checksums re-verified after this analysis was written).

Analysis date: 2026-08-23. Inputs: existing artifacts only
(`statistics.json`, `held-out-statistics.json`, `knowledge-snapshot.json`,
`conditions/*/raw-results.jsonl`, `conditions/*/operator-selections.jsonl`,
`manifest.json`, source in `src/algolab/search/`). No experiment re-runs,
no parameter changes.

---

## 1. Question

Why does C ≈ B on the beta family? Candidates:

(a) frozen historical knowledge already captures essentially all useful
information; (b) C fails to learn additional useful information; (c) beta
provides too little opportunity for adaptation; (d) insufficient statistical
power; (e) implementation/measurement issue.

## 2. Current evidence

From `statistics.json` / `report.md` (n = 8 paired trials, metric =
validated discoveries / credit):

| quantity | alpha | beta |
|---|---|---|
| B mean efficiency | 0.016728 | 0.026429 |
| C mean efficiency | 0.027973 | 0.027679 |
| delta (C−B) | +0.011245 | **+0.001250** |
| adjusted p | 0.009745 | **0.786107** |
| Cohen's d | 1.786 | **0.195** |
| 95% CI | [+0.0067, +0.0170] | [−0.0029, +0.0067] |

Held-out gamma: C ≫ B (delta +0.0361, d ≈ 5.0). Ablation c-permuted:
collapses on alpha (eff 0.0075 vs C's 0.0280) but **not on beta**
(0.0266 vs C's 0.0277) — destroying C's outcome→operator feedback barely
changes its beta performance.

## 3. Behavioral comparison (beta, all 8 trials)

Selection shares over 40 beta episodes per arm:

| operator | true β effect | cost | B share | B disc/attempt | C share | C disc/attempt |
|---|---|---|---|---|---|---|
| synthesize | +0.35 useful | 40 | 0.250 | 0.700 | 0.505 | 0.769 |
| reparameterize | +0.35 useful | 10 | 0.375 | 0.758 | 0.402 | 0.791 |
| validate | 0.02 neutral | 10 | 0.375 | 0.008 | 0.028 | 0.000 |
| tune/decompose | neutral | 10/20 | 0 | — | 0.065 | mixed |
| refresh | +0.35 useful | 10 | 0 | — | **0** | — |

- B deterministically cycles K0 top-3 = {synthesize, reparameterize,
  validate}: 62.5% of attempts useful, 37.5% wasted on a neutral operator.
- C concentrates on {synthesize, reparameterize} (90.7% useful selections)
  and drops the neutral tier — but that is exactly B's useful set.
- Selection-distribution overlap (total-variation intersection): **0.653**.
- Early→late within-trial: C shifts 43/43 (reparam/synth) → 38/56, i.e.
  toward the *more expensive* useful operator; early eff 0.0293 → late
  0.0264 (slightly worse).

## 4. Knowledge evolution (did C learn?)

C's Beta posteriors did move materially and *correctly*, read from the
per-step `prior_stats` in `operator-selections.jsonl`:

- reparameterize mean 0.4706 → 0.6875 (+0.217)
- synthesize mean 0.5000 → 0.6538 (+0.154)
- tune/decompose/validate: small downward drifts from failed probes
- refresh/polyglot/rollback: **never updated — never selected**

So "C fails to learn" is false in general: it learned what its feedback
channel could express (P(discovery | operator)) and acted on it. What C
never learned is (i) that refresh is also useful on beta and (ii) that
reparameterize is worth 4× more than synthesize per credit. Its observation
is a binary discovery flag; selection ignores credit cost entirely.

## 5. Prior saturation (does B already know enough?)

Largely yes. The pooled K0 snapshot (60 uniform attempts × {alpha, beta})
ranks synthesize (smoothed rate 0.500) and reparameterize (0.471) first and
second — both beta-useful — with validate third only via sum-effect
tiebreak. Two mechanisms produced this:

1. Both operators are genuinely useful on beta, so ~70–80% of their beta
   prior attempts succeeded.
2. Pooling dilutes family specificity: refresh is useful only on beta but
   ranks 6th (rate 0.267), below three operators that are neutral on beta.

Expected efficiencies under known ground truth (P(discovery|useful)=0.734,
neutral=0.016):

| schedule | expected eff | vs B actual |
|---|---|---|
| B actual cycle (s, r, validate) | 0.0247 | 1.00× |
| oracle top-3 (swap validate→refresh) | 0.0367 | 1.48× |
| oracle cost-aware (all reparameterize) | 0.0734 | 2.96× |

K0 saturation explains why B starts near C's level; it does **not** explain
away the remaining 48–196% headroom — that gap requires learning C cannot
express (see §4, §6). The c-permuted ablation confirms the diagnosis: on
beta, C's performance is carried by its K0 initialization, not by online
feedback (permuted ≈ true feedback there; on alpha permuted collapses).

## 6. Learning opportunity

Beta offers real headroom but almost no reachable signal for C as
implemented:

- Per trial, C gets only ~20–33 beta attempts (mean ≈ 27); posteriors reset
  every trial; beta updates are interleaved with alpha episodes.
- Exploration starvation of refresh: Monte-Carlo under C's exact frozen K0
  initialization gives E[refresh selections] ≈ 4.7 per 214 draws
  (P(≥1 try) ≈ 0.99); with online reinforcement of synth/reparam the share
  collapses. Observed: **0 selections in 214 attempts across all trials.**
  The prior ranks refresh below three neutral operators, and since an
  untried operator never accumulates evidence, Thompson sampling never
  rescues it.
- Cost-blindness: selection maximizes a success-probability draw, not
  discovery per credit. Synthesize and reparameterize have nearly equal
  success probability (~0.77) at 40 vs 10 credits; late-run C actually
  drifts toward the expensive one.
- Outcome diversity exists (C probed the neutral tier and was punished),
  so signal is present — but the two dimensions that matter for beating B
  on beta (relative value of refresh; credit cost) are outside C's
  hypothesis space.

Verdict: (b)+(c) combined — C learns, but the learnable target
(P(discovery|op) ranking) is already saturated by K0, and the unlearned
margins are unreachable through this observation channel and selection rule.

## 7. Statistical power (EXPLORATORY — not pre-registered)

Per-trial paired differences (C−B): mean +0.00125, sd 0.00766, t=0.46
(df=7), permutation p = 0.786 (matches statistics.json).

- Minimal detectable difference at n=8, 80% power, α=0.05: **±0.0076**
  (~29% of B's mean). The design cannot resolve effects smaller than ~29%
  relative; the observed +4.7% relative is far inside the noise floor.
- Trials needed to detect the observed effect at 80% power: **~295/arm**.
- The CI [−0.0029, +0.0067] admits anything from a tiny negative effect to
  +24% relative. So "genuinely close to zero" and "small real effect" are
  indistinguishable here — but even the CI upper bound is far below the
  +48%/+178% an oracle swap/cost-aware policy would achieve, so low power
  alone does not explain the failure against the achievable optimum.

## 8. Implementation audit

No bug found. Checked specifically:

- Update timing: `policy.update(family, operator, attempt.discovery)`
  fires after every completed attempt, before the next select
  (`harness.py` `_run_trial`).
- State isolation: fresh policy instance per (arm, trial); snapshot is a
  frozen dataclass copied into fresh posterior dicts; K0 provably unchanged
  after full runs (`test_k0_snapshot_unchanged_after_full_run`).
- Family isolation: posteriors keyed by family; held-out gamma lazily
  initialized from pure K0 (`test_held_out_adaptive_starts_from_k0_not_run_state`).
- No accidental freezing of C: posteriors demonstrably moved within-run
  (§4); B has no update channel at all (`test_b_cannot_update_from_own_outcomes`).
- Attribution: update lands on the operator actually selected (the
  mis-attribution path exists only behind the deliberate c-permuted flag).
- Seeds/reproducibility: manifest-frozen integers; arm streams replayable
  (`test_random_arm_stream_rebuildable_from_manifest`); environment seeds
  shared across arms at matched positions (common random numbers) — no bias.
- Metric arithmetic recomputed from raw JSONL matches `statistics.json`
  exactly (also covered by `TestMetricArithmetic`).
- Known quirk (not a bug): `select()` runs before the affordability check,
  so a final unaffordable selection still advances the deterministic
  pointer/consumes one RNG draw. Deterministic, documented in tests, and
  symmetric across arms; it shifts B's cycle phase but does not affect any
  comparison conclusion.

Original artifacts remain unchanged (checksums re-verified: 28/28 pass).

## 9. Most likely explanation (ranked by evidence)

1. **Prior saturation + exploration starvation (primary).** K0 already
   ranks two of beta's three useful operators on top, so B plays them
   deterministically; C converges to the same set. The only differentiating
   operator (refresh) is ranked below the neutral tier by the pooled prior
   and is never sampled, so C can never discover it. Evidence: §3 shares,
   §4 zero refresh-updates, §5 ceiling table, c-permuted≈C on beta vs ≪C on
   alpha.
2. **Cost-blind objective (secondary).** Even where C learns correctly
   (success probabilities), its argmax ignores credit cost, so it captures
   none of the 2.8× cost-aware headroom and slightly degrades late within
   trials by drifting to the pricier useful operator. Evidence: §3 early/
   late shift, §5 oracle rows.
3. **Insufficient power (contributing, not sufficient).** n=8 gives MDE ≈
   29% relative; a true small positive effect cannot be excluded. But the
   achievable-effect scale (+48…+178%) dwarfs the detection floor, so power
   does not rescue the adaptive claim on beta.
4. **Implementation issue: ruled out.** §8.

## 10. Scientific interpretation

The beta null does not contradict the knowledge-loop hypothesis; it
localizes it. Where the frozen prior is *misaligned* with the target family
(alpha: only 1 of B's top-3 useful; gamma: B's top-1 actively useless), the
adaptive loop produces large, significant gains (d ≈ 1.8 and ≈ 5.0). Where
the prior is already *aligned* (beta: 2 of 3 useful ops ranked 1st–2nd),
the loop adds nothing measurable — because the residual advantage requires
either exploring a prior-suppressed alternative or reasoning about cost,
neither of which C's binary-feedback, cost-blind design can do. In other
words: C's advantage tracks prior misalignment, not family identity. The
promotion criterion's ≥2-family requirement correctly refuses to certify a
loop whose benefit disappears precisely when history is already good.

## 11. Recommended next experiment (smallest justified step)

**Pre-register a cost-aware-selection variant of C (C+) evaluated on the
same frozen artifacts protocol — no changes to A/B/D, seeds, budgets,
families, gate, or promotion criterion.** Single mechanism change: score
operators by posterior-mean × P(discovery) per credit (or equivalently
Thompson-sample then divide by operator cost), leaving priors, observations,
and everything else identical.

Rationale from evidence: §5 shows the dominant unrealized margin on beta is
cost allocation (oracle 0.0734 vs played ≈0.028), not knowledge; §4 shows
the missing second margin (refresh) is unreachable without changing either
exploration or the prior — out of scope for the smallest step. This tests
one falsifiable sub-hypothesis ("the loop's beta failure is a cost-blindness
artifact of the selector, not of adaptation itself") while leaving the
original C and the pre-registered v1 result intact as the reference point.
If C+ still ties B on beta, the honest conclusion is prior saturation, and
the next lever would be prior construction (family-conditioned K0), which
should then be pre-registered separately.
