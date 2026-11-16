"""Compositional program grammar for the protocol-240 search space.

A *program* is an ordered sequence of 1-3 distinct typed feature transforms,
serialized as atoms joined by ``+`` (``"log1p+robust-scale"``). The grammar is
deliberately small and closed: 9 atoms, lengths 1-3, no repeated atom, which
gives 9 + 9*8 + 9*8*7 = 585 programs. Being closed makes contamination checks
and champion verification *complete* rather than probabilistic.

Nothing in this module evaluates data. It is pure structure: construction,
parsing, cost, serialization, and deterministic neighbourhood operators used by
the generative policies. Evaluation lives in ``workload_compose``.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass

GRAMMAR_VERSION = "1.0.0"
MAX_PROGRAM_LENGTH = 3

#: Atoms available to the grammar. Protocol 239's two pre-composed operators
#: (``interaction+robust``, ``poly2+log1p``) are intentionally excluded: in
#: protocol 240 they are reachable by composition, so keeping them would
#: double-count the same algorithm.
ATOMS: tuple[str, ...] = (
    "log1p",
    "sqrt",
    "clip-1_99",
    "robust-scale",
    "standard-scale",
    "quantile-bin-3",
    "interaction-top2",
    "pca-10",
    "poly2-top5",
)

#: Per-atom data cost (credits). Fit/transform cost scales with the transform.
ATOM_DATA_COST: dict[str, float] = {
    "log1p": 1.0,
    "sqrt": 1.0,
    "clip-1_99": 1.0,
    "robust-scale": 1.5,
    "standard-scale": 1.5,
    "quantile-bin-3": 2.0,
    "interaction-top2": 2.5,
    "pca-10": 3.5,
    "poly2-top5": 4.0,
}

#: Fixed per-step charge, so longer programs cost strictly more.
PER_STEP_CREDIT = 4.0


class GrammarError(ValueError):
    """A program string is not in the registered grammar."""


def parse(program: str) -> tuple[str, ...]:
    """Parse a serialized program into atoms, validating the grammar.

    Raises :class:`GrammarError` for unknown atoms, empty parts, repeats, or
    lengths outside 1..``MAX_PROGRAM_LENGTH``. Parsing is the single entry
    point for every program coming from a policy, so an invalid program can
    never reach the evaluator.
    """
    if not isinstance(program, str) or not program:
        raise GrammarError(f"empty program: {program!r}")
    parts = tuple(program.split("+"))
    if any(not p for p in parts):
        raise GrammarError(f"empty atom in program: {program!r}")
    if len(parts) > MAX_PROGRAM_LENGTH:
        raise GrammarError(
            f"program too long ({len(parts)} > {MAX_PROGRAM_LENGTH}): {program!r}")
    for atom in parts:
        if atom not in ATOM_DATA_COST:
            raise GrammarError(f"unknown atom {atom!r} in {program!r}")
    if len(set(parts)) != len(parts):
        raise GrammarError(f"repeated atom in program: {program!r}")
    return parts


def serialize(atoms: tuple[str, ...]) -> str:
    """Canonical program string for a validated atom sequence."""
    if not atoms:
        raise GrammarError("program must contain at least one atom")
    if len(set(atoms)) != len(atoms):
        raise GrammarError(f"repeated atom in program: {atoms}")
    if len(atoms) > MAX_PROGRAM_LENGTH:
        raise GrammarError(f"program too long: {atoms}")
    for atom in atoms:
        if atom not in ATOM_DATA_COST:
            raise GrammarError(f"unknown atom {atom!r}")
    return "+".join(atoms)


def program_cost(program: str) -> float:
    """Registered credit cost of one attempt at *program*.

    ``PER_STEP_CREDIT * len(atoms) + sum(atom data costs)``. Longer or
    heavier programs cost more, so the cost dimension stays live and every
    arm is charged by the same rule.
    """
    atoms = parse(program)
    return PER_STEP_CREDIT * len(atoms) + sum(ATOM_DATA_COST[a] for a in atoms)


def all_programs() -> tuple[str, ...]:
    """Every program in the grammar, in deterministic lexicographic order."""
    out: list[str] = []
    for length in range(1, MAX_PROGRAM_LENGTH + 1):
        for combo in itertools.permutations(ATOMS, length):
            out.append("+".join(combo))
    return tuple(sorted(out))


def space_size() -> int:
    """Number of programs in the grammar (585 for the registered atoms)."""
    return sum(length_class_size(length)
               for length in range(1, MAX_PROGRAM_LENGTH + 1))


def length_class_size(length: int) -> int:
    """Number of programs of exactly *length* atoms (9, 72, 504)."""
    if not 1 <= length <= MAX_PROGRAM_LENGTH:
        raise GrammarError(f"invalid length {length}")
    n = len(ATOMS)
    running = 1
    for k in range(length):
        running *= (n - k)
    return running


def random_program(rng: random.Random, *, exact_length: int | None = None) -> str:
    """Sample a program from the grammar, drawing the *length* uniformly.

    When ``exact_length`` is given the sample is uniform over programs of that
    length; otherwise the length is drawn uniformly from
    ``1..MAX_PROGRAM_LENGTH`` and then the atoms uniformly without replacement.
    That is **not** uniform over the whole grammar (length-3 programs are 504 of
    the 585 programs), which erratum E3 of protocol 240 records.
    """
    length = exact_length if exact_length is not None else rng.randint(
        1, MAX_PROGRAM_LENGTH)
    if not 1 <= length <= MAX_PROGRAM_LENGTH:
        raise GrammarError(f"invalid length {length}")
    atoms = rng.sample(list(ATOMS), length)
    return serialize(tuple(atoms))


def mutations(program: str) -> tuple[str, ...]:
    """Deterministic neighbourhood of *program* (all valid mutations).

    Three move types, in this order: append an unused atom, swap one position
    for an unused atom, drop one position (unless the program has length 1).
    The result is sorted, so it is a deterministic function of the program and
    is what makes the policies auditable: the audit trail records the chosen
    mutation's index into this tuple.
    """
    atoms = parse(program)
    used = set(atoms)
    unused = [a for a in ATOMS if a not in used]
    out: set[str] = set()
    if len(atoms) < MAX_PROGRAM_LENGTH:
        for atom in unused:
            out.add(serialize(atoms + (atom,)))
    for idx in range(len(atoms)):
        for atom in unused:
            swapped = list(atoms)
            swapped[idx] = atom
            out.add(serialize(tuple(swapped)))
    if len(atoms) > 1:
        for idx in range(len(atoms)):
            out.add(serialize(atoms[:idx] + atoms[idx + 1:]))
    return tuple(sorted(out))


def crossover(left: str, right: str, rng: random.Random) -> str:
    """One-point order-preserving crossover of two programs.

    Takes the first ``k`` atoms of *left* (k >= 1) then fills from *right* in
    order, skipping atoms already present, up to ``MAX_PROGRAM_LENGTH``. The
    result is always a valid program containing at least one atom of *left*.
    """
    a = list(parse(left))
    b = list(parse(right))
    k = rng.randint(1, len(a))
    child = a[:k]
    for atom in b:
        if len(child) >= MAX_PROGRAM_LENGTH:
            break
        if atom not in child:
            child.append(atom)
    return serialize(tuple(child))


@dataclass(frozen=True)
class ProgramStats:
    """Observed outcome summary for one program (read-only history view)."""

    program: str
    attempts: int
    discoveries: int
    sum_effect: float
    cost: float

    @property
    def mean_effect(self) -> float:
        return self.sum_effect / self.attempts if self.attempts else 0.0

    @property
    def discovery_rate(self) -> float:
        return self.discoveries / self.attempts if self.attempts else 0.0

    @property
    def effect_per_credit(self) -> float:
        return self.sum_effect / (self.cost * self.attempts) if self.attempts else 0.0


class ProgramHistory:
    """Mutable per-family record of observed program outcomes.

    This is the *live* half of the knowledge loop for the generative arms: a
    policy writes here after each attempt and reads it to choose the next one.
    Kept deliberately tiny and serializable so selection records can carry an
    exact snapshot of what the policy knew when it chose.
    """

    def __init__(self) -> None:
        self._data: dict[str, dict[str, float]] = {}

    def record(self, program: str, *, discovery: bool, effect: float,
               cost: float) -> None:
        entry = self._data.setdefault(
            program, {"attempts": 0.0, "discoveries": 0.0, "sum_effect": 0.0,
                      "cost": cost})
        entry["attempts"] += 1.0
        entry["discoveries"] += 1.0 if discovery else 0.0
        entry["sum_effect"] += float(effect)
        entry["cost"] = cost

    def stats(self, program: str) -> ProgramStats | None:
        entry = self._data.get(program)
        if entry is None:
            return None
        return ProgramStats(
            program=program,
            attempts=int(entry["attempts"]),
            discoveries=int(entry["discoveries"]),
            sum_effect=entry["sum_effect"],
            cost=entry["cost"],
        )

    def best(self, *, by: str = "mean_effect") -> str | None:
        """Best observed program by the named statistic (deterministic)."""
        best_program: str | None = None
        best_key: tuple[float, float, str] | None = None
        for program in sorted(self._data):
            st = self.stats(program)
            assert st is not None
            value = {
                "mean_effect": st.mean_effect,
                "effect_per_credit": st.effect_per_credit,
                "discovery_rate": st.discovery_rate,
            }[by]
            # Higher value wins; then cheaper program; then lexicographic.
            key = (round(value, 12), -st.cost, program)
            if best_key is None or key > best_key:
                best_key, best_program = key, program
        return best_program

    def ranked(self) -> list[str]:
        """Programs ranked best-first by mean effect (deterministic)."""
        return sorted(
            self._data,
            key=lambda p: (
                round(self.stats(p).mean_effect, 12)  # type: ignore[union-attr]
                if self.stats(p) else 0.0,
                p,
            ),
            reverse=True,
        )

    def programs(self) -> tuple[str, ...]:
        return tuple(sorted(self._data))

    def snapshot(self) -> dict[str, dict[str, float]]:
        """Serializable copy for audit trails and selection records."""
        return {p: dict(v) for p, v in sorted(self._data.items())}

    def lucky_programs(self, rng: random.Random) -> tuple[str, ...]:
        """Uniformly permuted program order (feedback ablation)."""
        programs = list(sorted(self._data))
        rng.shuffle(programs)
        return tuple(programs)


__all__ = [
    "GRAMMAR_VERSION",
    "MAX_PROGRAM_LENGTH",
    "ATOMS",
    "ATOM_DATA_COST",
    "PER_STEP_CREDIT",
    "GrammarError",
    "ProgramStats",
    "ProgramHistory",
    "parse",
    "serialize",
    "program_cost",
    "all_programs",
    "space_size",
    "length_class_size",
    "random_program",
    "mutations",
    "crossover",
]
