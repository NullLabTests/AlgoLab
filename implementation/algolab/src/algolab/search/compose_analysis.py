"""Protocol-240 analysis: distinct validated programs and champion transfer.

The harness metric (``validated_discoveries / credits``) counts *attempts* that
pass the 2-replicate gate. For a deterministic evaluator that is exploitable in
a way it is not for the noisy toy substrate: re-evaluating the same program can
yield another "discovery" without discovering anything new. Protocol 240
therefore pre-registers a stricter primary metric, computed here from the raw
attempt streams (so it is recomputable by any reviewer from the sealed bundle):

    distinct_efficiency(arm, family, trial)
        = |{programs with >= 1 validated discovery in that cell}| / credits

A program contributes at most once per (arm, family, trial) cell, no matter how
many times it was evaluated.

Everything in this module is a pure function of the recorded streams plus, for
champion transfer, the frozen workload evaluator. No hidden state is read, and
nothing here can change a search decision: analysis runs only after the search
finished.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from algolab.search import candidates, workload_compose
from algolab.search.harness import PolicyComparison, primary_comparisons_for
from algolab.statistics import benjamini_hochberg

#: Fresh seed offsets for champion transfer: far outside every search seed
#: (search uses trial ids < 1e5 and held-out uses trial+100_000).
CHAMPION_TRIAL_BASE = 900_000
CHAMPION_REPLICATES = 2
CHAMPION_EPISODES = 7


@dataclass(frozen=True)
class AttemptRecord:
    """One raw attempt as recorded in ``conditions/<arm>/raw-results.jsonl``."""

    arm: str
    trial: int
    episode: int
    family: str
    step: int
    program: str
    cost: float
    valid: bool
    effect_1: float
    effect_2: float
    mean_effect: float
    discovery: bool


def load_streams(artifact_dir: Path,
                 arms: Sequence[str]) -> dict[str, tuple[AttemptRecord, ...]]:
    """Read the per-arm raw attempt streams from a bundle directory."""
    out: dict[str, tuple[AttemptRecord, ...]] = {}
    for arm in arms:
        path = artifact_dir / "conditions" / arm / "raw-results.jsonl"
        if not path.is_file():
            raise FileNotFoundError(f"missing raw stream for arm {arm!r}: {path}")
        records: list[AttemptRecord] = []
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            records.append(AttemptRecord(
                arm=arm,
                trial=int(row["trial"]),
                episode=int(row["episode"]),
                family=str(row["family"]),
                step=int(row["step"]),
                program=str(row["operator"]),
                cost=float(row["cost"]),
                valid=bool(row["valid"]),
                effect_1=float(row["effect_1"]),
                effect_2=float(row["effect_2"]),
                mean_effect=float(row["mean_effect"]),
                discovery=bool(row["discovery"]),
            ))
        out[arm] = tuple(records)
    return out


def distinct_efficiency_series(
    streams: Mapping[str, Sequence[AttemptRecord]],
    families: Sequence[str],
) -> dict[str, dict[str, list[float]]]:
    """Per-family paired series of distinct-discovery efficiency.

    Returns ``{family: {arm: [efficiency per trial]}}`` with one entry per
    (trial) that the arm actually ran on that family, ordered by trial id. All
    arms share the rotation, so index ``i`` of every series corresponds to the
    same trial.
    """
    out: dict[str, dict[str, list[float]]] = {f: {} for f in families}
    for arm, records in streams.items():
        cells: dict[tuple[str, int], dict[str, Any]] = {}
        for r in records:
            if r.family not in out:
                continue
            cell = cells.setdefault(
                (r.family, r.trial), {"credits": 0.0, "programs": set()})
            cell["credits"] += r.cost
            if r.discovery:
                cell["programs"].add(r.program)
        per_family: dict[str, list[tuple[int, float]]] = {f: [] for f in families}
        for (family, trial), cell in cells.items():
            credits = cell["credits"] if cell["credits"] > 0 else 1.0
            per_family[family].append((trial, len(cell["programs"]) / credits))
        for family, pairs in per_family.items():
            if pairs:
                pairs.sort(key=lambda p: p[0])
                out[family][arm] = [v for _, v in pairs]
    return out


def champion(records: Sequence[AttemptRecord]) -> dict[str, Any] | None:
    """The protocol-240 champion rule, applied to one arm's training stream.

    Highest observed ``mean_effect``; ties broken by lower credit cost, then
    lexicographically **largest** program string (the same tie-break order the
    policies use in ``ProgramHistory.best``). Only valid attempts are eligible.
    This is a deterministic function of the training stream, so no gamma
    information can leak into the choice.
    """
    best: dict[str, Any] | None = None
    for r in records:
        if not r.valid:
            continue
        key = (round(r.mean_effect, 12), -r.cost, r.program)
        if best is None or key > (round(best["mean_effect"], 12),
                                  -best["cost"], best["program"]):
            best = {
                "program": r.program,
                "mean_effect": r.mean_effect,
                "cost": r.cost,
                "found_in_family": r.family,
                "found_in_trial": r.trial,
            }
    return best


def evaluate_program_fresh(
    family: str,
    program: str,
    *,
    trials: int = CHAMPION_REPLICATES,
    seed_base: int = 7,
    episode: int = CHAMPION_EPISODES,
) -> dict[str, Any]:
    """Re-evaluate *program* on *family* with seeds no search attempt used.

    Returns the raw replicate effects (not a pass/fail), so the transfer claim
    can be judged rather than asserted.
    """
    effects = []
    for k in range(trials):
        attempt = workload_compose.run_attempt(
            family, program, seed_base=seed_base,
            trial=CHAMPION_TRIAL_BASE + k, episode=episode, attempt=0)
        effects.append({
            "replicate": k + 1,
            "effect_1": attempt.effect_1,
            "effect_2": attempt.effect_2,
            "mean_effect": attempt.mean_effect,
            "discovery": attempt.discovery,
            "valid": attempt.valid,
        })
    n = len(effects) if effects else 1
    mean = sum(e["mean_effect"] for e in effects) / n
    positive = all(e["mean_effect"] > 0 for e in effects)
    return {
        "family": family,
        "program": program,
        "program_length": len(candidates.parse(program)),
        "cost_credits": candidates.program_cost(program),
        "replicates": effects,
        "mean_effect": round(mean, 6),
        "all_replicates_positive": positive,
        "validated": bool(positive and mean >= workload_compose.DISCOVERY_MARGIN),
    }


def paired_comparisons(
    per_family_series: Mapping[str, Mapping[str, Sequence[float]]],
    arms: Sequence[str],
    *,
    seed: int,
) -> dict[str, Any]:
    """Pre-registered paired comparisons on the distinct-discovery metric.

    Reuses the harness's comparison matrix and BH correction so protocol-240
    inference is statistically identical to protocols 230-239 (paired bootstrap
    CI, Welch fallback, Cohen's d, BH across the registered pairs). Tests are
    run *within* each family, matching protocol 230 §5's (family, seed)
    pairing; the concatenated-across-family comparison would break that
    pairing, so it is deliberately not computed.
    """
    pairs = primary_comparisons_for(tuple(arms))
    descriptive: dict[str, dict[str, float]] = {}
    for arm in arms:
        values = [v for series in per_family_series.values()
                  for v in series.get(arm, [])]
        if values:
            descriptive[arm] = {
                "efficiency_mean": round(sum(values) / len(values), 9),
                "cells": float(len(values)),
            }
    per_family: dict[str, dict[str, Any]] = {}
    for family, series in per_family_series.items():
        rows, fam_p = PolicyComparison._comparison_matrix(
            {arm: list(vals) for arm, vals in series.items()}, pairs,
            metric=f"distinct_discoveries_per_credit ({family})", seed=seed)
        fam_adj = list(benjamini_hochberg(fam_p))
        for row, q in zip(rows, fam_adj, strict=True):
            row["adjusted_p"] = q
        per_family[family] = {
            "comparisons": rows,
            "per_condition": {
                arm: {"efficiency_mean": round(sum(v) / len(v), 9),
                      "trials": len(v)}
                for arm, v in series.items() if v
            },
        }
    return {"descriptive": descriptive, "per_family": per_family}


def _row(rows: Iterable[dict[str, Any]], base: str,
         cand: str) -> dict[str, Any] | None:
    return next((r for r in rows
                 if r["base"] == base and r["candidate"] == cand), None)


def evaluate_hypotheses(
    analysis: Mapping[str, Any],
    *,
    families: Sequence[str],
    champion_transfers: Mapping[str, Mapping[str, Any]],
    arms: Sequence[str],
    arms_with_training_discovery: Sequence[str],
) -> dict[str, Any]:
    """Apply the pre-registered H1-H5 decision rules to the analysis.

    Deliberately mechanical: each hypothesis maps to explicit numeric
    predicates over the recorded statistics, so the verdict cannot drift with
    the narrative written around it.
    """
    per_family = analysis["per_family"]

    def beats(base: str, cand: str) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for family in families:
            row = _row(per_family.get(family, {}).get("comparisons", []),
                       base, cand)
            out[family] = bool(
                row is not None and row["delta"] > 0
                and row["adjusted_p"] < 0.05 and row["ci_low"] > 0)
        return out

    def directional(base: str, cand: str) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for family in families:
            row = _row(per_family.get(family, {}).get("comparisons", []),
                       base, cand)
            out[family] = bool(row is not None and row["delta"] > 0)
        return out

    greedy_vs_random = beats("random-program", "greedy-history")
    evo_vs_random = beats("random-program", "evolutionary-archive")
    randomised_vs_atoms = beats("random-program", "static-atoms")
    rand_vs_atoms_directional = directional("random-program", "static-atoms")
    greedy_vs_permuted = directional("greedy-history", "greedy-permuted")

    h1 = all(greedy_vs_random.values()) and bool(greedy_vs_random)
    h2 = all(evo_vs_random.values()) and bool(evo_vs_random)
    h4 = any(randomised_vs_atoms.values()) or all(
        rand_vs_atoms_directional.values())
    h5 = all(greedy_vs_permuted.values()) and bool(greedy_vs_permuted)

    # H3: a validated improvement found in training *and* that arm's champion
    # transferring with a positive 2-replicate mean effect on the held-out
    # family. The positive transfer must come from an arm that actually
    # produced a training discovery, so an arm that never found anything
    # cannot satisfy H3 by transferring a merely least-bad program.
    training_discovery_arms = sorted(arms_with_training_discovery)
    transferring = sorted(
        arm for arm, block in champion_transfers.items()
        if arm in training_discovery_arms
        and block.get("transfer") is not None
        and block["transfer"]["all_replicates_positive"])
    h3 = bool(transferring) and bool(training_discovery_arms)

    if h1 and h3:
        outcome = "A"
    elif h3:
        outcome = "B"
    else:
        outcome = "C"

    return {
        "H1_greedy_vs_random_significant_by_family": greedy_vs_random,
        "H2_evolutionary_vs_random_significant_by_family": evo_vs_random,
        "H4_random_vs_static_atoms_significant_by_family": randomised_vs_atoms,
        "H4_random_vs_static_atoms_directional_by_family": rand_vs_atoms_directional,
        "H5_greedy_vs_permuted_directional_by_family": greedy_vs_permuted,
        "H1_met": h1,
        "H2_met": h2,
        "H3_met": h3,
        "H4_met": h4,
        "H5_met": h5,
        "arms_with_champions": sorted(champion_transfers),
        "arms_with_transferring_champion": transferring,
        "outcome_class": outcome,
        "claim": _claim_text(outcome, h1, h2, h3, h4, h5),
    }


def _claim_text(outcome: str, h1: bool, h2: bool, h3: bool,
                h4: bool, h5: bool) -> str:
    if outcome == "A":
        base = ("Class A: history-using generative search beat random program "
                "search on both training families (adjusted p<0.05, CI>0) AND "
                "a champion transferred positively to the held-out family.")
    elif outcome == "B":
        base = ("Class B: a validated algorithmic improvement was generated, "
                "evaluated, and transferred, but history-using search did not "
                "significantly beat uniform random search per credit.")
    else:
        base = ("Class C: neither a significant policy advantage over random "
                "search nor a positively transferring champion was "
                "established.")
    detail = (
        f" (H1={h1}, H2={h2}, H3={h3}, H4={h4}, H5={h5})")
    return base + detail


def summarise_programs(
    streams: Mapping[str, Sequence[AttemptRecord]],
) -> dict[str, Any]:
    """Per-arm descriptive summary of the programs that were generated."""
    out: dict[str, Any] = {}
    for arm, records in streams.items():
        programs = sorted({r.program for r in records})
        discovered = sorted({r.program for r in records if r.discovery})
        lengths = [len(candidates.parse(p)) for p in programs]
        out[arm] = {
            "attempts": len(records),
            "distinct_programs_evaluated": len(programs),
            "distinct_programs_discovered": len(discovered),
            "discovered_programs": discovered,
            "mean_program_length": round(
                sum(lengths) / len(lengths), 3) if lengths else 0.0,
            "credits": round(sum(r.cost for r in records), 1),
            "invalid_attempts": sum(1 for r in records if not r.valid),
        }
    return out


__all__ = [
    "CHAMPION_TRIAL_BASE",
    "CHAMPION_REPLICATES",
    "AttemptRecord",
    "load_streams",
    "distinct_efficiency_series",
    "champion",
    "evaluate_program_fresh",
    "paired_comparisons",
    "evaluate_hypotheses",
    "summarise_programs",
]
