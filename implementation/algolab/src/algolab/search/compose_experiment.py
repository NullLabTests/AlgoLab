"""Protocol-240 runner: generative composition search end to end.

This module is the protocol-specific layer on top of the generic harness. It

1. runs the frozen pre-registered comparison through
   :class:`algolab.search.harness.PolicyComparison` (unchanged behaviour, same
   statistics path as protocols 230-239);
2. computes the protocol-240 *primary* metric — distinct validated programs per
   credit — from the raw attempt streams;
3. applies the pre-registered H1-H5 decision rules;
4. evaluates each arm's champion program on the held-out family with fresh
   seeds;
5. writes the protocol-240 artifacts and then the standard evidence bundle
   (manifest, statistics, report, checksums, reproducibility verdict).

Nothing in this module influences the search; every function here runs after
the search has finished and reads only recorded artifacts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from algolab.search import candidates, workload_compose
from algolab.search import compose_analysis as ca
from algolab.search.harness import (
    ExperimentConfig,
    PolicyComparison,
    primary_comparisons_for,
)

PROTOCOL_240_VERSION = "1.0.0"
PRIMARY_METRIC = "distinct_validated_programs / credits_consumed"

PRE_REGISTERED_ARMS: tuple[str, ...] = (
    "random-program",
    "greedy-history",
    "evolutionary-archive",
    "static-atoms",
    "greedy-permuted",
)


def run_protocol_240(
    cfg: ExperimentConfig,
    conn: Any,
    artifact_dir: Path,
    *,
    force: bool = False,
    out: TextIO = sys.stdout,
) -> dict[str, Any]:
    """Execute protocol 240 and seal the evidence bundle."""
    if cfg.workload != "compose":
        raise ValueError(
            f"protocol 240 requires workload 'compose', got {cfg.workload!r}")
    if tuple(cfg.arms) != PRE_REGISTERED_ARMS:
        raise ValueError(
            "protocol 240 arms are frozen by the pre-registration: "
            f"expected {PRE_REGISTERED_ARMS}, got {tuple(cfg.arms)}")

    workload_compose.reset_timing_stats()
    # Timing starts at zero *and* the memo cache starts cold, so the reported
    # ``evaluations`` / ``cache_hits`` split is a property of this run rather
    # than of whatever else the process did earlier (defect D-11: it is part of
    # a byte-compared artifact).
    workload_compose.clear_caches()
    comp = PolicyComparison(cfg, conn, artifact_dir, force=force)
    results = comp.run()
    stats = comp.analyze(results)
    held_out_results = comp.run_held_out()
    held_out_stats = comp.analyze_held_out(held_out_results)
    held_out_stats["claim_readiness"] = PolicyComparison.evaluate_claim(
        stats.get("per_family", {}), held_out_stats,
        candidate="greedy-history",
        held_out_family=cfg.workload_view.held_out_family)

    timing = workload_compose.timing_stats()

    # ---- protocol-240 primary analysis (post-hoc, records only) ----------
    streams = ca.load_streams(artifact_dir, PRE_REGISTERED_ARMS)
    families = list(cfg.workload_view.families)
    series = ca.distinct_efficiency_series(streams, families)
    primary = ca.paired_comparisons(series, PRE_REGISTERED_ARMS,
                                    seed=cfg.analysis_seed)

    champions: dict[str, Any] = {}
    for arm in PRE_REGISTERED_ARMS:
        champ = ca.champion(streams[arm])
        transfer = None
        if champ is not None:
            transfer = ca.evaluate_program_fresh(
                cfg.workload_view.held_out_family, champ["program"],
                seed_base=cfg.seed_base)
        champions[arm] = {"champion": champ, "transfer": transfer}

    discovered: dict[str, Any] = {
        arm: sorted({r.program for r in streams[arm] if r.discovery})
        for arm in PRE_REGISTERED_ARMS
    }
    arms_with_discovery = [arm for arm, progs in discovered.items() if progs]

    hypotheses = ca.evaluate_hypotheses(
        primary, families=families, champion_transfers=champions,
        arms=PRE_REGISTERED_ARMS,
        arms_with_training_discovery=arms_with_discovery)

    protocol_stats: dict[str, Any] = {
        "protocol_version": PROTOCOL_240_VERSION,
        "experiment_id": cfg.experiment_id,
        "primary_metric": PRIMARY_METRIC,
        "secondary_metric": "validated_discoveries / credits_consumed "
                            "(harness metric, counts attempts)",
        "families": families,
        "held_out_family": cfg.workload_view.held_out_family,
        "arms": list(PRE_REGISTERED_ARMS),
        "primary_comparisons": [
            {"base": b, "candidate": c}
            for b, c in primary_comparisons_for(PRE_REGISTERED_ARMS)],
        "search_space": {
            "size": candidates.space_size(),
            "atoms": list(candidates.ATOMS),
            "max_program_length": candidates.MAX_PROGRAM_LENGTH,
            "closed": True,
            "grammar_version": candidates.GRAMMAR_VERSION,
        },
        "distinct_discovery_analysis": primary,
        "program_summary": ca.summarise_programs(streams),
        "discovered_programs": discovered,
        "arms_with_training_discovery": arms_with_discovery,
        "champion_transfer": champions,
        "hypotheses": hypotheses,
        "harness_secondary_statistics": {
            "per_condition": stats["per_condition"],
            "per_family_comparisons": {
                fam: block["comparisons"]
                for fam, block in stats.get("per_family", {}).items()},
            "held_out_per_condition": held_out_stats["per_condition"],
        },
        "compute": {
            "attempts": int(timing["attempts"]),
            "evaluations": int(timing["evaluations"]),
            "cache_hits": int(timing["cache_hits"]),
            "evaluation_seconds": round(timing["operator_seconds"], 2),
            "trials": cfg.trials,
            "episodes_per_trial": cfg.episodes_per_trial,
            "budget_credits_per_episode": cfg.budget_credits,
            "prior_attempts_per_family": cfg.prior_attempts_per_family,
        },
    }
    (artifact_dir / "protocol-240-statistics.json").write_text(
        json.dumps(protocol_stats, indent=2, sort_keys=True) + "\n")

    # Official report (harness format) plus the protocol-240 sections.
    comp.write_report(results, stats, held_out_stats)
    _append_protocol_240_report(
        artifact_dir / "report.md", protocol_stats, cfg)

    # Seal: checksums cover every artifact written above.
    comp.write_artifact_bundle(stats, held_out_stats)

    out.write(f"experiment {cfg.experiment_id} complete; "
              f"report: {artifact_dir / 'report.md'}\n")
    out.write(f"primary metric: {PRIMARY_METRIC}\n")
    for arm in PRE_REGISTERED_ARMS:
        desc = primary["descriptive"].get(arm, {})
        out.write(
            f"  {arm:<22} distinct/credit={desc.get('efficiency_mean', 0.0):.6f} "
            f"discovered={len(discovered[arm]):>2} "
            f"attempts={protocol_stats['program_summary'][arm]['attempts']:>3}\n")
    out.write(f"outcome class: {hypotheses['outcome_class']}\n")
    out.write(f"claim: {hypotheses['claim']}\n")
    return protocol_stats


def _append_protocol_240_report(path: Path, st: dict[str, Any],
                                cfg: ExperimentConfig) -> None:
    """Append the protocol-240 primary analysis to the harness report."""
    lines: list[str] = [
        "",
        "---",
        "",
        "# Protocol 240 — generative composition search",
        "",
        f"Pre-registration: `spec/research/240_GENERATIVE_COMPOSITION_SEARCH.md`"
        f" (protocol file version {st['protocol_version']}).",
        "",
        f"**Primary metric:** `{st['primary_metric']}` — a program counts once "
        "per (arm, family, trial) cell, so re-evaluating a lucky program cannot "
        "inflate the discovery count.",
        f"**Secondary metric (harness):** `{st['secondary_metric']}`.",
        "",
        "## Search space and compute",
        "",
        f"- Closed grammar: {st['search_space']['size']} programs "
        f"(lengths 1-{st['search_space']['max_program_length']} over "
        f"{len(st['search_space']['atoms'])} typed atoms), "
        f"grammar version {st['search_space']['grammar_version']}.",
        f"- Trials: {st['compute']['trials']}; episodes/trial: "
        f"{st['compute']['episodes_per_trial']}; budget/episode: "
        f"{st['compute']['budget_credits_per_episode']} credits; prior: "
        f"{st['compute']['prior_attempts_per_family']} attempts/family.",
        f"- Attempts executed: {st['compute']['attempts']} "
        f"({st['compute']['evaluations']} real CV evaluations, "
        f"{st['compute']['cache_hits']} memoised repeats). Wall-clock "
        "durations are deliberately **not** printed here: `report.md` is "
        "compared byte-for-byte when a bundle is reproduced, so it may only "
        "contain deterministic values. Measured time lives in "
        "`protocol-240-statistics.json` (`compute.evaluation_seconds`) and "
        "`environment.json`, both of which are excluded from that comparison "
        "as recorded-but-never-read wall-clock fields.",
        "",
        "## Generated programs (per arm)",
        "",
        "| arm | attempts | distinct programs | discovered programs | "
        "mean length | credits |",
        "|---|---|---|---|---|---|",
    ]
    for arm, block in st["program_summary"].items():
        lines.append(
            f"| {arm} | {block['attempts']} | "
            f"{block['distinct_programs_evaluated']} | "
            f"{block['distinct_programs_discovered']} | "
            f"{block['mean_program_length']} | {block['credits']} |")
    lines += [
        "",
        "## Primary metric — distinct validated programs per credit",
        "",
        "| arm | mean distinct/credit | cells |",
        "|---|---|---|",
    ]
    for arm, block in st["distinct_discovery_analysis"]["descriptive"].items():
        lines.append(
            f"| {arm} | {block['efficiency_mean']:.6f} | {block['cells']:.0f} |")
    for family, block in st["distinct_discovery_analysis"]["per_family"].items():
        lines += [
            "",
            f"### family {family} — paired comparisons (BH-adjusted)",
            "",
            "| base | candidate | delta | CI low | CI high | p | adjusted p | d |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for row in block["comparisons"]:
            lines.append(
                f"| {row['base']} | {row['candidate']} | {row['delta']:.6f} "
                f"| {row['ci_low']:.6f} | {row['ci_high']:.6f} "
                f"| {row['p_value']:.6f} | {row['adjusted_p']:.6f} "
                f"| {row['effect_size']:.3f} |")
    lines += [
        "",
        "## Champion transfer (fresh seeds; no search attempt used them)",
        "",
        "| arm | champion program | training mean effect | held-out mean effect "
        "| replicates positive |",
        "|---|---|---|---|---|",
    ]
    for arm, block in st["champion_transfer"].items():
        champ = block["champion"]
        transfer = block["transfer"]
        if champ is None:
            lines.append(f"| {arm} | (no valid attempt) | — | — | — |")
            continue
        t_mean = f"{transfer['mean_effect']:.6f}" if transfer else "—"
        positive = (
            "yes" if transfer and transfer["all_replicates_positive"] else "no"
        ) if transfer else "—"
        lines.append(
            f"| {arm} | `{champ['program']}` | {champ['mean_effect']:.6f} "
            f"| {t_mean} | {positive} |")
    hyp = st["hypotheses"]
    lines += [
        "",
        "## Pre-registered hypothesis outcomes",
        "",
        "| hypothesis | result |",
        "|---|---|",
        f"| H1 greedy-history > random-program (both families, adj p<0.05) "
        f"| {'MET' if hyp['H1_met'] else 'NOT MET'} — "
        f"{hyp['H1_greedy_vs_random_significant_by_family']} |",
        f"| H2 evolutionary-archive > random-program | "
        f"{'MET' if hyp['H2_met'] else 'NOT MET'} — "
        f"{hyp['H2_evolutionary_vs_random_significant_by_family']} |",
        f"| H3 validated discovery + positive champion transfer | "
        f"{'MET' if hyp['H3_met'] else 'NOT MET'} — transferring arms: "
        f"{hyp['arms_with_transferring_champion']} |",
        f"| H4 random-program vs static-atoms (composition value) | "
        f"{'MET' if hyp['H4_met'] else 'NOT MET'} — significant "
        f"{hyp['H4_random_vs_static_atoms_significant_by_family']}, "
        f"directional {hyp['H4_random_vs_static_atoms_directional_by_family']} |",
        f"| H5 greedy-history > greedy-permuted (feedback ablation, "
        f"exploratory) | {'MET' if hyp['H5_met'] else 'NOT MET'} — "
        f"{hyp['H5_greedy_vs_permuted_directional_by_family']} |",
        "",
        f"**Outcome class {hyp['outcome_class']}.** {hyp['claim']}",
        "",
        "## Protocol-240 limitations",
        "",
        "- The search space is a 585-program closed grammar of feature "
        "transforms in front of a fixed logistic-regression estimator on three "
        "small tabular datasets. Nothing here supports a claim about inventing "
        "novel learning algorithms.",
        "- Programs are deterministic to evaluate, so an arm's 'discovery' is a "
        "program whose two replicate CV splits both beat the matched baseline "
        "by >= 0.005 absolute; that is a robustness gate, not a significance "
        "test on a single program.",
        "- Arms that generate longer programs spend more credits per attempt, so "
        "they take fewer attempts under an equal credit budget. This is the "
        "registered cost model, not a defect, but it couples search quality to "
        "program cost.",
        "- Paired inference has n = "
        f"{cfg.trials} trials per family; effects smaller than the pairing "
        "noise will not be detected.",
        "- Champion transfer is one program per arm evaluated twice on the "
        "held-out family; it is a directional check, not a powered test.",
        "",
    ]
    with path.open("a") as fh:
        fh.write("\n".join(lines) + "\n")


__all__ = [
    "PROTOCOL_240_VERSION",
    "PRIMARY_METRIC",
    "PRE_REGISTERED_ARMS",
    "run_protocol_240",
]
