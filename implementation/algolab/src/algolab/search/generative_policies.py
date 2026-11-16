"""Generative search policies for protocol 240.

The protocol-230 policy family selects from a fixed operator list. The arms in
this module instead **construct** candidate programs from the closed grammar in
:mod:`algolab.search.candidates` — the selection is over an open-ended set of
compositions, and the search space is never enumerated at policy level.

Arms
----
- ``GenerativeRandomPolicy`` (``random-program``): random program, drawing the
  length uniformly and then the atoms without replacement (i.e. uniform within
  each length class, **not** uniform over the 585-program space — erratum E3 of
  protocol 240). The standard strong baseline for discrete search and the
  primary control for the protocol-240 policy hypothesis.
- ``GreedyHistoryPolicy`` (``greedy-history``): starts from the best atom in the
  family-conditioned K0 snapshot, then does an epsilon-greedy local search over
  the mutation neighbourhood of the best-scoring program observed so far. Reads
  its own outcomes through the ``observe`` hook (effect magnitude, not just the
  binary discovery flag).
- ``EvolutionaryArchivePolicy`` (``evolutionary-archive``): a population of 6
  programs per family with tournament selection, mutation, and one-point
  crossover, plus a deterministic quality-diversity archive keyed by
  (program length, cost tier).
- ``StaticAtomsPolicy`` (``static-atoms``): round-robin over the 9 single-atom
  programs; the protocol-239-style control that isolates the value of
  composition.
- ``PermutedGreedyHistoryPolicy`` (``greedy-permuted``): identical machinery to
  ``greedy-history`` with the outcome→program association destroyed by a seeded
  permutation. This is the causal ablation of the feedback channel.

Determinism
-----------
Every policy is a pure function of its ``rng_seed`` and the observations it has
received. No wall-clock value, set iteration order, or dict order affects a
choice: candidate lists are sorted before sampling, and every random draw is
documented. Two runs of the same arm and seeds therefore produce the same
program stream (tested in ``tests/test_protocol_240.py``).

Audit trail
-----------
``operator-selections.jsonl`` records, for every selection, the program, a
human-readable reason, and ``selection_probability``: the probability of the
chosen program **given the policy's state and the branch it took**. It is exact
for the draw it describes (a length class for the random sampler, a mutation
neighbourhood, a crossover point) and is *not* a distribution normalised over the
585-program space. Erratum E3 of protocol 240 records that the random arm is
length-stratified, which is why its per-program probability depends on length.
"""

from __future__ import annotations

import random
from collections.abc import Mapping

from algolab.search import candidates
from algolab.search.policies import (
    KnowledgeSnapshot,
    PolicyError,
    SelectionRecord,
)
from algolab.search.toy import Attempt

RANDOM_PROGRAM_POLICY_VERSION = "1.0.0"
GREEDY_HISTORY_POLICY_VERSION = "1.0.0"
EVOLUTIONARY_ARCHIVE_POLICY_VERSION = "1.0.0"
STATIC_ATOMS_POLICY_VERSION = "1.0.0"
PERMUTED_GREEDY_POLICY_VERSION = "1.0.0"

#: Exploration probability for the epsilon-greedy branch.
GREEDY_EPSILON = 0.2
#: Population size for the evolutionary arm.
POPULATION_SIZE = 6
#: Tournament size for the evolutionary arm.
TOURNAMENT_SIZE = 2


def _prior_stats(program: str, snapshot: KnowledgeSnapshot | None) -> dict[str, float]:
    """Frozen-K0 success rate per atom of *program* (audit trail)."""
    if snapshot is None:
        return {}
    return {
        atom: round(snapshot.success_rate(atom), 6)
        for atom in candidates.parse(program)
    }


def _sampled_probability(program: str) -> float:
    """Per-program probability of a ``candidates.random_program`` draw.

    The sampler draws the *length* uniformly from ``1..MAX_PROGRAM_LENGTH`` and
    then the atoms uniformly without replacement, so a length-``L`` program is
    drawn with probability ``(1 / MAX_PROGRAM_LENGTH) / length_class_size(L)``.
    This is deliberately **not** ``1 / space_size()``: protocol-240 erratum E3
    records that the sampler is length-stratified, and the audit trail has to
    describe the sampler that actually ran.
    """
    length = len(candidates.parse(program))
    return 1.0 / (candidates.MAX_PROGRAM_LENGTH
                  * candidates.length_class_size(length))


def _record(*, step: int, program: str, policy: str, version: str,
            family: str, prior: dict[str, float] | None,
            posterior: dict[str, float] | None, score: float,
            probability: float, reason: str) -> SelectionRecord:
    return SelectionRecord(
        step=step, operator=program, policy=policy, policy_version=version,
        family=family, prior_stats=prior, posterior_stats=posterior,
        selection_score=round(score, 9), selection_probability=round(probability, 9),
        reason=reason)


class GenerativeRandomPolicy:
    """Random program search, length-stratified (primary control)."""

    label = "random-program"
    version = RANDOM_PROGRAM_POLICY_VERSION

    def __init__(self, snapshot: KnowledgeSnapshot | None, seed: int):
        del snapshot  # deliberately unread: this arm ignores all knowledge
        self._rng = random.Random(seed)

    def select(self, family: str, step: int) -> tuple[str, SelectionRecord]:
        program = candidates.random_program(self._rng)
        probability = _sampled_probability(program)
        record = _record(
            step=step, program=program, policy=self.label, version=self.version,
            family=family, prior=None, posterior=None, score=0.0,
            probability=probability,
            reason="length-uniform then atom-uniform sample "
                   "(erratum E3: not uniform over the 585-program space)")
        return program, record

    def reset(self) -> None:
        return None


class StaticAtomsPolicy:
    """Round-robin over single-atom programs (composition-free control)."""

    label = "static-atoms"
    version = STATIC_ATOMS_POLICY_VERSION

    def __init__(self) -> None:
        self._atoms = tuple(sorted(candidates.ATOMS))
        self._pointer = 0

    def select(self, family: str, step: int) -> tuple[str, SelectionRecord]:
        program = self._atoms[self._pointer % len(self._atoms)]
        self._pointer += 1
        record = _record(
            step=step, program=program, policy=self.label, version=self.version,
            family=family, prior=None, posterior=None, score=1.0, probability=1.0,
            reason="round-robin atom schedule (length-1 programs only)")
        return program, record

    def reset(self) -> None:
        self._pointer = 0


class _HistoryPolicyBase:
    """Shared history plumbing for the history-using arms."""

    version = "0.0.0"

    def __init__(
        self,
        snapshot: KnowledgeSnapshot | None,
        seed: int,
        *,
        snapshots_by_family: Mapping[str, KnowledgeSnapshot] | None = None,
    ):
        self._rng = random.Random(seed)
        self._seed = seed
        self._snapshot = snapshot
        self._by_family = dict(snapshots_by_family or {})
        self._history: dict[str, candidates.ProgramHistory] = {}
        self._selected: dict[str, int] = {}

    # -- history ---------------------------------------------------------
    def _fam_history(self, family: str) -> candidates.ProgramHistory:
        if family not in self._history:
            self._history[family] = candidates.ProgramHistory()
        return self._history[family]

    def _fam_snapshot(self, family: str) -> KnowledgeSnapshot | None:
        snap = self._by_family.get(family)
        return snap if snap is not None and snap.attempts else self._snapshot

    def _seed_program(self, family: str) -> str:
        """Best single atom for *family* from the frozen prior (or mid atom)."""
        snap = self._fam_snapshot(family)
        if snap is not None and snap.attempts:
            ranked = snap.ranking()
            if ranked:
                return ranked[0]
        # Deterministic fallback: middle atom in sorted order.
        atoms = sorted(candidates.ATOMS)
        return atoms[len(atoms) // 2]

    # -- observation -----------------------------------------------------
    def observe(self, family: str, program: str, attempt: Attempt) -> None:
        """Record the realised outcome of an evaluated program."""
        raise NotImplementedError

    def update(self, family: str, operator: str, discovery: bool) -> None:
        """The harness's binary-feedback hook.

        These arms read the full effect through :meth:`observe`; the binary
        hook is intentionally a no-op so an observation is never double-counted.
        """
        del family, operator, discovery

    def reset(self) -> None:
        self._rng = random.Random(self._seed)
        self._history = {}
        self._selected = {}

    # -- helpers ---------------------------------------------------------
    def _posterior(self, history: candidates.ProgramHistory,
                   program: str) -> dict[str, float] | None:
        st = history.stats(program)
        if st is None:
            return None
        return {
            "attempts": float(st.attempts),
            "discoveries": float(st.discoveries),
            "mean_effect": round(st.mean_effect, 6),
        }

    def history_snapshot(self, family: str) -> dict[str, dict[str, float]]:
        """Public read-only view of live history (used by analyses/tests)."""
        return self._fam_history(family).snapshot()


class GreedyHistoryPolicy(_HistoryPolicyBase):
    """Epsilon-greedy local search over the mutation neighbourhood."""

    label = "greedy-history"
    version = GREEDY_HISTORY_POLICY_VERSION

    def __init__(self, snapshot: KnowledgeSnapshot | None, seed: int, *,
                 snapshots_by_family: Mapping[str, KnowledgeSnapshot] | None = None,
                 epsilon: float = GREEDY_EPSILON):
        super().__init__(snapshot, seed, snapshots_by_family=snapshots_by_family)
        self._epsilon = epsilon

    def select(self, family: str, step: int) -> tuple[str, SelectionRecord]:
        history = self._fam_history(family)
        best = history.best(by="mean_effect")
        if best is None:
            program = self._seed_program(family)
            reason = ("cold start: best atom in the frozen K0 slice"
                      if self._fam_snapshot(family) is not None
                      else "cold start: deterministic fallback atom")
            score = 0.0
            probability = 1.0  # deterministic given the frozen prior
        elif self._rng.random() < self._epsilon or not candidates.mutations(best):
            program = candidates.random_program(self._rng)
            reason = (f"explore (epsilon={self._epsilon}): "
                      "length-uniform then atom-uniform sample")
            score = 0.0
            probability = _sampled_probability(program)
        else:
            neighbours = candidates.mutations(best)
            program = neighbours[self._rng.randrange(len(neighbours))]
            reason = f"exploit: mutation of best observed program {best}"
            st = history.stats(best)
            score = st.mean_effect if st is not None else 0.0
            probability = 1.0 / len(neighbours)
        self._selected[program] = self._selected.get(program, 0) + 1
        record = _record(
            step=step, program=program, policy=self.label, version=self.version,
            family=family,
            prior=_prior_stats(program, self._fam_snapshot(family)),
            posterior=self._posterior(history, best) if best else None,
            score=score, probability=probability, reason=reason)
        return program, record

    def observe(self, family: str, program: str, attempt: Attempt) -> None:
        discovery = bool(attempt.discovery)
        effect = float(attempt.mean_effect)
        cost = float(attempt.cost_credits)
        self._fam_history(family).record(
            program, discovery=discovery, effect=effect, cost=cost)


class PermutedGreedyHistoryPolicy(GreedyHistoryPolicy):
    """Ablation: same machinery, outcome→program association permuted.

    The realised outcome is attributed to a *different* program drawn from the
    history (including possibly the true one), which keeps the marginal
    distribution of effects intact while destroying the signal that local
    search depends on.
    """

    label = "greedy-permuted"
    version = PERMUTED_GREEDY_POLICY_VERSION

    def __init__(self, snapshot: KnowledgeSnapshot | None, seed: int, *,
                 snapshots_by_family: Mapping[str, KnowledgeSnapshot] | None = None,
                 epsilon: float = GREEDY_EPSILON):
        super().__init__(snapshot, seed,
                         snapshots_by_family=snapshots_by_family,
                         epsilon=epsilon)
        self._shuffle_rng = random.Random(seed + 999)

    def reset(self) -> None:
        # The permutation stream is part of this arm's state: resetting must
        # restore it, or a reused instance would diverge from a fresh one.
        super().reset()
        self._shuffle_rng = random.Random(self._seed + 999)

    def observe(self, family: str, program: str, attempt: Attempt) -> None:
        history = self._fam_history(family)
        known = sorted(set(history.programs()) | {program})
        target = known[self._shuffle_rng.randrange(len(known))]
        history.record(
            target,
            discovery=bool(attempt.discovery),
            effect=float(attempt.mean_effect),
            cost=float(attempt.cost_credits))


class EvolutionaryArchivePolicy(_HistoryPolicyBase):
    """Population search with mutation/crossover and a QD archive."""

    label = "evolutionary-archive"
    version = EVOLUTIONARY_ARCHIVE_POLICY_VERSION

    def __init__(self, snapshot: KnowledgeSnapshot | None, seed: int, *,
                 snapshots_by_family: Mapping[str, KnowledgeSnapshot] | None = None,
                 population_size: int = POPULATION_SIZE):
        super().__init__(snapshot, seed, snapshots_by_family=snapshots_by_family)
        self._population_size = population_size
        self._population: dict[str, list[str]] = {}
        #: family -> {(length, cost tier): (mean_effect, program)}
        self._archive: dict[str, dict[tuple[int, float], tuple[float, str]]] = {}

    def _fam_population(self, family: str) -> list[str]:
        if family not in self._population:
            snap = self._fam_snapshot(family)
            seeds: list[str] = []
            if snap is not None and snap.attempts:
                seeds = [p for p in snap.ranking() if p in candidates.ATOMS]
            while len(seeds) < self._population_size:
                seeds.append(candidates.random_program(self._rng))
            self._population[family] = seeds[: self._population_size]
        return self._population[family]

    def _score(self, family: str, program: str) -> float:
        st = self._fam_history(family).stats(program)
        return st.mean_effect if st is not None else 0.0

    def _tournament(self, family: str, pool: list[str]) -> str:
        if not pool:
            raise PolicyError("empty population")
        entrants = [pool[self._rng.randrange(len(pool))]
                    for _ in range(TOURNAMENT_SIZE)]
        return max(entrants, key=lambda p: (round(self._score(family, p), 12), p))

    def select(self, family: str, step: int) -> tuple[str, SelectionRecord]:
        pop = self._fam_population(family)
        parent_a = self._tournament(family, pop)
        if self._rng.random() < 0.5:
            parent_b = self._tournament(family, pop)
            child = candidates.crossover(parent_a, parent_b, self._rng)
            reason = f"crossover({parent_a}, {parent_b})"
            # Exact for this draw: the crossover point k is uniform over the
            # parent's positions and the child is deterministic given k.
            probability = 1.0 / len(candidates.parse(parent_a))
        else:
            neighbours = candidates.mutations(parent_a)
            if not neighbours:  # pragma: no cover - every program has neighbours
                child = candidates.random_program(self._rng)
                reason = "fallback random program"
                probability = _sampled_probability(child)
            else:
                child = neighbours[self._rng.randrange(len(neighbours))]
                reason = f"mutation of tournament winner {parent_a}"
                probability = 1.0 / len(neighbours)
        record = _record(
            step=step, program=child, policy=self.label, version=self.version,
            family=family,
            prior=_prior_stats(child, self._fam_snapshot(family)),
            posterior=self._posterior(self._fam_history(family), parent_a),
            score=self._score(family, parent_a),
            probability=probability,
            reason=reason)
        return child, record

    def observe(self, family: str, program: str, attempt: Attempt) -> None:
        history = self._fam_history(family)
        history.record(
            program,
            discovery=bool(attempt.discovery),
            effect=float(attempt.mean_effect),
            cost=float(attempt.cost_credits))
        pop = self._fam_population(family)
        if program in pop:
            return
        scored = sorted(
            ((self._score(family, p), p) for p in pop),
            key=lambda item: (round(item[0], 12), item[1]))
        if self._score(family, program) > scored[0][0]:
            worst_score, worst_program = scored[0]
            pop[pop.index(worst_program)] = program
        atoms = candidates.parse(program)
        tier = round(candidates.program_cost(program), 1)
        cell = (len(atoms), tier)
        archive = self._archive.setdefault(family, {})
        current = archive.get(cell)
        if current is None or (self._score(family, program), program) > current:
            archive[cell] = (self._score(family, program), program)

    def archive_snapshot(self, family: str) -> dict[str, dict[str, float | str]]:
        """QD archive view: one best program per (length, cost tier) cell."""
        out: dict[str, dict[str, float | str]] = {}
        for (length, tier), (score, program) in sorted(
                self._archive.get(family, {}).items()):
            out[f"len{length}/cost{tier}"] = {
                "program": program, "mean_effect": round(score, 6)}
        return out

    def population_snapshot(self, family: str) -> list[str]:
        return list(self._fam_population(family))


__all__ = [
    "RANDOM_PROGRAM_POLICY_VERSION",
    "GREEDY_HISTORY_POLICY_VERSION",
    "EVOLUTIONARY_ARCHIVE_POLICY_VERSION",
    "STATIC_ATOMS_POLICY_VERSION",
    "PERMUTED_GREEDY_POLICY_VERSION",
    "GREEDY_EPSILON",
    "POPULATION_SIZE",
    "TOURNAMENT_SIZE",
    "GenerativeRandomPolicy",
    "GreedyHistoryPolicy",
    "PermutedGreedyHistoryPolicy",
    "EvolutionaryArchivePolicy",
    "StaticAtomsPolicy",
]
