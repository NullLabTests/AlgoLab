"""Real-workload transfer evaluation (protocol 244).

This module does **not** change the evaluator. It reuses the frozen
``algolab.statistics.analyze`` primitive and the fail-closed
``algolab.meta_search.evaluation.promote`` gate, and mirrors the A/B/C stage
layout of ``evaluation.py`` so that protocol 244 is directly comparable with
protocols 241–243. Only the source of attempts changes: real sklearn workloads
replace the planted-truth toy generator.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from algolab.meta_search.evaluation import (
    PRIMARY_METRIC,
    SECONDARY_METRIC,
    promote,
    replay_evaluation,
)
from algolab.meta_search.policies import (
    BASELINE_POLICY,
    EVOLVED_POLICY,
    Observation,
    SearchPolicy,
)
from algolab.meta_search.replay import ReplayEnv
from algolab.meta_search.traces import DiscoveryTrace, TraceNode
from algolab.search import workload_hpo, workload_transform
from algolab.search.toy import Attempt
from algolab.statistics import analyze, benjamini_hochberg

TRANSFER_SCHEMA_VERSION = "meta-transfer/1.0"
DEFAULT_WORKLOADS = ("transform", "hpo")
ARMS: tuple[SearchPolicy, ...] = (BASELINE_POLICY, EVOLVED_POLICY)
TraceAttempt = Callable[..., Attempt]


@dataclass(frozen=True)
class _Workload:
    name: str
    version: str
    families: tuple[str, ...]
    held_out: str
    operators: tuple[str, ...]
    costs: dict[str, float]
    attempt: TraceAttempt
    environment: dict[str, Any]


def _load_workload(name: str) -> _Workload:
    if name == "transform":
        module: Any = workload_transform
        version = workload_transform.WORKLOAD_VERSION
    elif name == "hpo":
        module = workload_hpo
        version = workload_hpo.HPO_WORKLOAD_VERSION
    else:
        raise ValueError(f"unsupported transfer workload: {name!r}")
    operators = tuple(module.operators())
    environment = dict(module.environment_metadata())
    # Wall-clock counters are reporting-only state, not part of the frozen world.
    workload_meta = dict(environment.get("workload_metadata", {}))
    workload_meta.pop("measured_operator_seconds", None)
    workload_meta.pop("measured_attempts", None)
    environment["workload_metadata"] = workload_meta
    return _Workload(
        name=name,
        version=version,
        families=tuple(module.TASK_FAMILIES),
        held_out=str(module.HELD_OUT_FAMILY),
        operators=operators,
        costs={op: float(module.operator_cost(op)) for op in operators},
        attempt=module.run_attempt,
        environment=environment,
    )


def build_transfer_trace(
    workloads: tuple[_Workload, ...], *, trace_seed: int
) -> DiscoveryTrace:
    """Build a frozen, real-attempt trace; replay output is diagnostic only."""
    trace = DiscoveryTrace(
        trace_id="trace-transfer-244", experiment_id="EXP-META-244"
    )
    all_costs: dict[str, float] = {}
    for workload in workloads:
        root = trace.append(
            TraceNode(
                experiment_id="EXP-META-244",
                parent_id=None,
                policy_id=BASELINE_POLICY.policy_id,
                policy_version=str(BASELINE_POLICY.version),
                candidate_id=f"root-{workload.name}",
                candidate_generation_method=f"root-{workload.name}",
                search_parameters={
                    "workload": workload.name,
                    "historical_choice": workload.operators[0],
                },
                selection_decision=f"seed {workload.name} root",
                compute_credits=0.0,
                seed=trace_seed,
                dataset_id=workload.name,
                eval_split_id="train",
                observation={"discovery": False, "valid": True},
                derived_metrics={"mean_effect": 0.0},
                created_at_utc="real-workload-frozen-trace",
                execution_provenance={
                    "source": "real_workload_attempts",
                    "workload": workload.name,
                },
            )
        )
        for index, operator in enumerate(workload.operators[:3]):
            attempt = workload.attempt(
                workload.families[0],
                operator,
                seed_base=trace_seed,
                trial=0,
                episode=index,
                attempt=index,
            )
            all_costs[operator] = attempt.cost_credits
            trace.append(
                TraceNode(
                    experiment_id="EXP-META-244",
                    parent_id=root.node_id,
                    policy_id=BASELINE_POLICY.policy_id,
                    policy_version=str(BASELINE_POLICY.version),
                    candidate_id=f"cand-{workload.name}-{operator}",
                    candidate_generation_method=operator,
                    search_parameters={
                        "workload": workload.name,
                        "family": workload.families[0],
                        "trial": 0,
                    },
                    selection_decision=f"expand {operator}",
                    evaluation_result={
                        "cost_credits": attempt.cost_credits,
                        "discovery": attempt.discovery,
                    },
                    compute_credits=attempt.cost_credits,
                    seed=trace_seed + index,
                    dataset_id=workload.name,
                    eval_split_id="train",
                    observation={
                        "discovery": attempt.discovery,
                        "valid": attempt.valid,
                        "mean_effect": attempt.mean_effect,
                    },
                    derived_metrics={"mean_effect": attempt.mean_effect},
                    created_at_utc="real-workload-frozen-trace",
                    execution_provenance={
                        "source": "real_workload_attempts",
                        "workload": workload.name,
                    },
                )
            )
    return trace


def _trial_score(
    policy: SearchPolicy,
    workload: _Workload,
    *,
    family: str,
    seed_base: int,
    trial: int,
    episodes: int,
    budget: float,
) -> dict[str, float]:
    """One deterministic prospective trial on a real workload."""
    observations: list[Observation] = []
    credits = 0.0
    discoveries = 0
    useful_found: set[str] = set()
    for episode in range(episodes):
        selection = policy.select(
            workload.operators,
            tuple(observations),
            seed=seed_base + trial * 100_000 + episode,
            costs=workload.costs,
        )
        attempt = workload.attempt(
            family,
            selection.method,
            seed_base=seed_base,
            trial=trial,
            episode=episode,
            attempt=episode,
        )
        credits += attempt.cost_credits
        if credits > budget:
            break
        if attempt.discovery:
            discoveries += 1
            useful_found.add(selection.method)
        observations.append(
            Observation(
                method=selection.method,
                cost_credits=attempt.cost_credits,
                mean_effect=attempt.mean_effect,
                discovery=attempt.discovery,
                valid=attempt.valid,
            )
        )
    denom = max(credits, 1e-9)
    return {
        "credits": credits,
        "discoveries": float(discoveries),
        PRIMARY_METRIC: discoveries / denom,
        SECONDARY_METRIC: len(useful_found) / denom,
    }


def _stage(
    policy: SearchPolicy,
    baseline: SearchPolicy,
    workload: _Workload,
    *,
    families: tuple[str, ...],
    seed_base: int,
    trials: int,
    episodes: int,
    budget: float,
    bootstrap_iterations: int,
    alpha: float,
) -> tuple[dict[str, Any], int]:
    def scores(candidate: SearchPolicy, metric: str) -> list[float]:
        values: list[float] = []
        for family in families:
            for trial in range(trials):
                result = _trial_score(
                    candidate,
                    workload,
                    family=family,
                    seed_base=seed_base,
                    trial=trial,
                    episodes=episodes,
                    budget=budget,
                )
                values.append(result[metric])
        return values

    primary = analyze(
        scores(baseline, PRIMARY_METRIC),
        scores(policy, PRIMARY_METRIC),
        metric=PRIMARY_METRIC,
        seed=seed_base + 1,
        bootstrap_iterations=bootstrap_iterations,
        alpha=alpha,
    )
    secondary = analyze(
        scores(baseline, SECONDARY_METRIC),
        scores(policy, SECONDARY_METRIC),
        metric=SECONDARY_METRIC,
        seed=seed_base + 2,
        bootstrap_iterations=bootstrap_iterations,
        alpha=alpha,
    )
    stage = {
        "families": list(families),
        "trials_per_family": trials,
        "episodes": episodes,
        "budget": budget,
        "seed_base": seed_base,
        "workload": workload.name,
        "primary": {
            "delta": primary.delta,
            "ci_low": primary.ci_low,
            "ci_high": primary.ci_high,
            "p_value": primary.p_value,
            "effect_size": primary.effect_size,
            "baseline_mean": primary.baseline.mean,
            "candidate_mean": primary.candidate.mean,
        },
        "secondary": {
            "delta": secondary.delta,
            "ci_low": secondary.ci_low,
            "ci_high": secondary.ci_high,
            "p_value": secondary.p_value,
        },
    }
    return stage, len(families) * trials


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _render_report(manifest: dict[str, Any], summaries: list[dict[str, Any]]) -> str:
    lines = [
        f"# {manifest['protocol']} — Real-workload policy transfer",
        "",
        "Status: **preregistered experiment** (spec committed before execution). "
        "Replay is diagnostic only; no policy is promoted on replay evidence.",
        "",
        "| Workload | Arm | Primary Δ/credit | 95% CI low | p | q (BH) | "
        "Held-out Δ | Promotion |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in summaries:
        q = f"{item['primary_q']:.4f}" if "primary_q" in item else "—"
        lines.append(
            f"| {item['workload']} | {item['arm']} | "
            f"{item['prospective_delta']:+.6f} | {item['prospective_ci_low']:+.6f} | "
            f"{item['prospective_p']:.4f} | {q} | {item['confirmation_delta']:+.6f} | "
            f"{item['promotion']} |"
        )
    lines += [
        "",
        "Primary outcome: validated discoveries per credit. Secondary: distinct "
        "useful methods per credit. Negative and inconclusive results are reported "
        "as measured; no threshold was changed after results were seen.",
        "",
    ]
    return "\n".join(lines)


def _seal(target: Path) -> dict[str, str]:
    return {
        path.relative_to(target).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(target.rglob("*"))
        if path.is_file() and path.name != "checksums.json"
    }


def run_transfer(
    out_dir: str | Path,
    *,
    workloads: tuple[str, ...] = DEFAULT_WORKLOADS,
    trials: int = 8,
    episodes: int = 8,
    budget: float = 40.0,
    seed_base: int = 924_211,
    confirmation_seed_base: int = 351_773,
    bootstrap_iterations: int = 2_000,
    protocol_id: str = "protocol-244",
    apply_bh: bool = True,
) -> dict[str, Any]:
    """Run the preregistered transfer experiment and seal its bundle."""
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    specs = tuple(_load_workload(name) for name in workloads)
    trace = build_transfer_trace(specs, trace_seed=77_100)
    trace.write(target / "trace.json")
    combined_costs: dict[str, float] = {}
    for spec in specs:
        combined_costs.update(spec.costs)
    env = ReplayEnv(trace, costs=combined_costs)
    for path in ("replay", "evaluations", "promotions"):
        (target / path).mkdir(exist_ok=True)

    summaries: list[dict[str, Any]] = []
    evaluations: dict[tuple[str, str], dict[str, Any]] = {}
    attempts = 0
    credits_spent = 0.0
    for spec in specs:
        for policy in ARMS:
            replay = env.deterministic_artifact(policy, seed=17)
            _write_json(target / "replay" / f"{spec.name}-{policy.name}.json", replay)
            stage_a = replay_evaluation(env, policy, seed=17)
            stage_b, b_trials = _stage(
                policy,
                BASELINE_POLICY,
                spec,
                families=spec.families,
                seed_base=seed_base,
                trials=trials,
                episodes=episodes,
                budget=budget,
                bootstrap_iterations=bootstrap_iterations,
                alpha=0.05,
            )
            stage_b["stage"] = "B_prospective"
            stage_b["is_prospective_evidence"] = True
            stage_c, c_trials = _stage(
                policy,
                BASELINE_POLICY,
                spec,
                families=(spec.held_out,),
                seed_base=confirmation_seed_base,
                trials=trials,
                episodes=episodes,
                budget=budget,
                bootstrap_iterations=bootstrap_iterations,
                alpha=0.05,
            )
            stage_c["stage"] = "C_independent_confirmation"
            stage_c["is_prospective_evidence"] = True
            payload = {
                "schema_version": TRANSFER_SCHEMA_VERSION,
                "candidate_policy_id": policy.policy_id,
                "baseline_policy_id": BASELINE_POLICY.policy_id,
                "workload": spec.name,
                "workload_version": spec.version,
                "stage_a": stage_a,
                "stage_b": stage_b,
                "stage_c": stage_c,
                "preregistered": True,
            }
            evaluations[(spec.name, policy.name)] = payload
            _write_json(
                target / "evaluations" / f"{spec.name}-{policy.name}.json", payload
            )
            attempts += 2 * (b_trials + c_trials) * episodes
            credits_spent += (b_trials + c_trials) * budget * 2
            if policy is BASELINE_POLICY:
                continue
            summaries.append(
                {
                    "workload": spec.name,
                    "arm": policy.name,
                    "historical_agreement": stage_a["decision_quality_agreement"],
                    "prospective_delta": stage_b["primary"]["delta"],
                    "prospective_ci_low": stage_b["primary"]["ci_low"],
                    "prospective_p": stage_b["primary"]["p_value"],
                    "confirmation_delta": stage_c["primary"]["delta"],
                    "confirmation_ci_low": stage_c["primary"]["ci_low"],
                    "secondary_ci_low": stage_b["secondary"]["ci_low"],
                }
            )

    if apply_bh:
        q_values = benjamini_hochberg([item["prospective_p"] for item in summaries])
        for item, q in zip(summaries, q_values, strict=True):
            item["primary_q"] = q
            payload = evaluations[(item["workload"], item["arm"])]
            stage_b = cast(dict[str, Any], payload["stage_b"])
            primary = cast(dict[str, Any], stage_b["primary"])
            primary["p_adjusted"] = q
            _write_json(
                target / "evaluations" / f"{item['workload']}-{item['arm']}.json",
                payload,
            )

    for item in summaries:
        policy = next(p for p in ARMS if p.name == item["arm"])
        decision = promote(
            policy,
            BASELINE_POLICY,
            evaluations[(item["workload"], item["arm"])],
        )
        _write_json(
            target / "promotions" / f"{item['workload']}-{item['arm']}.json",
            decision.to_dict(),
        )
        item["promotion"] = decision.status.value

    manifest = {
        "schema_version": TRANSFER_SCHEMA_VERSION,
        "protocol": protocol_id,
        "protocol_version": "1.0.0",
        "preregistration": "spec/research/244_META_SEARCH_REAL_WORKLOAD_TRANSFER.md",
        "trace_kind": "real_workload_frozen_trace",
        "trace_is_prospective_evidence": False,
        "substrates": [f"algolab.search.workload_{n}" for n in workloads],
        "workloads": [
            {"name": spec.name, "version": spec.version, "held_out": spec.held_out}
            for spec in specs
        ],
        "arms": [p.name for p in ARMS],
        "trials": trials,
        "episodes": episodes,
        "budget": budget,
        "seed_base": seed_base,
        "confirmation_seed_base": confirmation_seed_base,
        "bootstrap_iterations": bootstrap_iterations,
        "multiple_comparison_correction": (
            "benjamini-hochberg" if apply_bh else "none"
        ),
        "promotion_gate": (
            "unchanged from protocol 243; replay diagnostic only; B requires "
            "positive CI and q<0.05; C requires held-out delta>=0 and CI>=-0.001"
        ),
        "compute": {
            "planned_upper_bound_attempts": attempts,
            "nominal_credits_upper_bound": credits_spent,
            "timing_is_decision_relevant": False,
        },
    }
    for spec in specs:
        _write_json(target / f"environment-{spec.name}.json", spec.environment)
    _write_json(target / "manifest.json", manifest)
    (target / "report.md").write_text(
        _render_report(manifest, summaries), encoding="utf-8"
    )
    checksums = _seal(target)
    _write_json(target / "checksums.json", checksums)
    return {"manifest": manifest, "summaries": summaries, "checksums": checksums}


__all__ = [
    "TRANSFER_SCHEMA_VERSION",
    "DEFAULT_WORKLOADS",
    "ARMS",
    "build_transfer_trace",
    "run_transfer",
]
