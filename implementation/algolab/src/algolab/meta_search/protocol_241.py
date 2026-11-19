"""Protocol 241: bounded meta-search pilot and independent verification.

This is the smallest honest experiment for the new capability.  It compares
four deterministic search policies (fixed baseline, replay/cost-aware, evolved,
seeded random control) under matched seeds on the toy substrate, plus a held-out
family confirmation.  A *synthetic pilot trace* is generated from the same
deterministic substrate so the replay environment has a frozen history to
replay; it is labelled as synthetic and is never prospective evidence.

All decisions are pure functions of preregistered integers.  Output is a sealed
bundle: every content file is listed in ``checksums.json`` and re-verifiable by
``verify_pilot`` / ``algolab meta-verify``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from algolab.meta_search.evaluation import evaluate_policy, promote
from algolab.meta_search.policies import (
    BASELINE_POLICY,
    CONTROL_POLICY,
    EVOLVED_POLICY,
    REPLAY_POLICY,
    SearchPolicy,
)
from algolab.meta_search.replay import ReplayEnv
from algolab.meta_search.traces import DiscoveryTrace, TraceIntegrityError, TraceNode
from algolab.search.toy import run_attempt

PROTOCOL_ID = "protocol-241"
PROTOCOL_VERSION = "1.0.0"
BUNDLE_SCHEMA_VERSION = "meta-pilot/1.0"
ARMS: tuple[SearchPolicy, ...] = (
    BASELINE_POLICY,
    REPLAY_POLICY,
    EVOLVED_POLICY,
    CONTROL_POLICY,
)
TRACE_SEED = 77_100
FAMILIES = ("alpha", "beta")


def build_pilot_trace() -> DiscoveryTrace:
    """Create a deterministic, clearly-labelled synthetic historical trace."""
    trace = DiscoveryTrace(trace_id="trace-pilot-241", experiment_id="EXP-META-241")
    root = TraceNode(
        experiment_id="EXP-META-241",
        parent_id=None,
        policy_id=BASELINE_POLICY.policy_id,
        policy_version=str(BASELINE_POLICY.version),
        candidate_id="root",
        candidate_generation_method="fixed-baseline",
        search_parameters={"families": list(FAMILIES)},
        selection_decision="seed root",
        seed=TRACE_SEED,
        dataset_id="toy",
        eval_split_id="train",
        observation={"discovery": False, "valid": True},
        derived_metrics={"mean_effect": 0.0},
        created_at_utc="synthetic-pilot",
        execution_provenance={
            "source": "synthetic_pilot_trace",
            "protocol": PROTOCOL_ID,
        },
    )
    root_node = trace.append(root)
    for index, method in enumerate(("tune", "reparameterize", "decompose", "refresh")):
        family = FAMILIES[index % 2]
        attempt = run_attempt(
            family,
            method,
            seed_base=TRACE_SEED,
            trial=index,
            episode=0,
            attempt=index,
        )
        trace.append(
            TraceNode(
                experiment_id="EXP-META-241",
                parent_id=root_node.node_id,
                policy_id=BASELINE_POLICY.policy_id,
                policy_version=str(BASELINE_POLICY.version),
                candidate_id=f"cand-{method}",
                candidate_generation_method=method,
                search_parameters={"family": family, "trial": index},
                selection_decision=f"expand {method}",
                evaluation_result={
                    "cost_credits": attempt.cost_credits,
                    "discovery": attempt.discovery,
                },
                compute_credits=attempt.cost_credits,
                seed=TRACE_SEED + index,
                dataset_id="toy",
                eval_split_id="train",
                observation={
                    "discovery": attempt.discovery,
                    "valid": attempt.valid,
                    "mean_effect": attempt.mean_effect,
                },
                derived_metrics={"mean_effect": attempt.mean_effect},
                created_at_utc="synthetic-pilot",
                execution_provenance={
                    "source": "synthetic_pilot_trace",
                    "protocol": PROTOCOL_ID,
                },
            )
        )
    return trace


def run_pilot(
    out_dir: str | Path,
    *,
    trials: int = 4,
    episodes: int = 8,
    budget: float = 10.0,
    seed_base: int = 424_242,
    confirmation_seed_base: int = 989_898,
    bootstrap_iterations: int = 1000,
) -> dict[str, Any]:
    """Run the preregistered pilot and seal a deterministic artifact bundle."""
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    trace = build_pilot_trace()
    trace.write(target / "trace.json")
    env = ReplayEnv(
        trace,
        unexplored_candidates=("synthesize", "validate", "polyglot", "rollback"),
    )
    (target / "replay").mkdir(exist_ok=True)
    (target / "evaluations").mkdir(exist_ok=True)
    (target / "promotions").mkdir(exist_ok=True)

    summaries: list[dict[str, Any]] = []
    for policy in ARMS:
        replay = env.deterministic_artifact(policy, seed=17)
        _write_json(target / "replay" / f"{policy.name}.json", replay)
        evaluation = evaluate_policy(
            policy,
            BASELINE_POLICY,
            replay_env=env,
            families=FAMILIES,
            seed_base=seed_base,
            confirmation_seed_base=confirmation_seed_base,
            trials=trials,
            episodes=episodes,
            budget=budget,
            bootstrap_iterations=bootstrap_iterations,
        )
        _write_json(target / "evaluations" / f"{policy.name}.json", evaluation)
        decision = promote(policy, BASELINE_POLICY, evaluation)
        _write_json(target / "promotions" / f"{policy.name}.json", decision.to_dict())
        b = evaluation["stage_b"]["primary"]
        c = evaluation["stage_c"]["primary"]
        summaries.append(
            {
                "arm": policy.name,
                "policy_id": policy.policy_id,
                "historical_agreement": evaluation["stage_a"][
                    "decision_quality_agreement"
                ],
                "prospective_delta": b["delta"],
                "prospective_ci_low": b["ci_low"],
                "prospective_p": b["p_value"],
                "confirmation_delta": c["delta"],
                "confirmation_ci_low": c["ci_low"],
                "promotion": decision.status.value,
            }
        )

    manifest = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "protocol": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "trace_kind": "synthetic_pilot_trace",
        "trace_is_prospective_evidence": False,
        "substrate": "algolab.search.toy",
        "families": list(FAMILIES),
        "held_out_family": "gamma",
        "trials": trials,
        "episodes": episodes,
        "budget": budget,
        "seed_base": seed_base,
        "confirmation_seed_base": confirmation_seed_base,
        "bootstrap_iterations": bootstrap_iterations,
        "arms": [p.name for p in ARMS],
        "promotion_gate": (
            "stage A replay-only never promotes; B requires positive CI and p<0.05; "
            "C requires non-negative delta and CI>=-0.001 on held-out gamma"
        ),
    }
    _write_json(target / "manifest.json", manifest)
    report = _render_report(manifest, summaries)
    (target / "report.md").write_text(report, encoding="utf-8")
    checksums = _seal(target)
    _write_json(target / "checksums.json", checksums)
    return {"manifest": manifest, "summaries": summaries, "checksums": checksums}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), indent=None) + "\n",
        encoding="utf-8",
    )


def _render_report(manifest: dict[str, Any], summaries: list[dict[str, Any]]) -> str:
    lines = [
        f"# {manifest['protocol']} — Meta-Search bounded pilot",
        "",
        "Status: **exploratory pilot**. The historical trace is synthetic and is "
        "not prospective evidence. No policy is promoted on replay performance.",
        "",
        "| Arm | Replay agreement | Prospective Δ/credit | 95% CI low | "
        "p | Held-out Δ | Promotion |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lines.append(
            f"| {s['arm']} | {s['historical_agreement']:.3f} | "
            f"{s['prospective_delta']:+.6f} | {s['prospective_ci_low']:+.6f} | "
            f"{s['prospective_p']:.4f} | {s['confirmation_delta']:+.6f} | "
            f"{s['promotion']} |"
        )
    lines += [
        "",
        "Primary outcome: validated discoveries per credit (paired across matched "
        "trials). Secondary: distinct useful methods per credit. Negative results "
        "are reported as measured.",
        "",
    ]
    return "\n".join(lines)


def _seal(target: Path) -> dict[str, str]:
    skip = {"checksums.json"}
    files: dict[str, str] = {}
    for path in sorted(target.rglob("*")):
        if not path.is_file() or path.name in skip:
            continue
        rel = path.relative_to(target).as_posix()
        files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def verify_pilot(out_dir: str | Path) -> dict[str, Any]:
    """Independently re-check every sealed file and promotion verdict."""
    target = Path(out_dir)
    checksums_path = target / "checksums.json"
    if not checksums_path.exists():
        raise FileNotFoundError(f"no checksums.json in {target}")
    expected: dict[str, str] = json.loads(checksums_path.read_text(encoding="utf-8"))
    mismatches: list[str] = []
    for rel, digest in expected.items():
        path = target / rel
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            mismatches.append(rel)
    extra = sorted(
        p.relative_to(target).as_posix()
        for p in target.rglob("*")
        if p.is_file()
        and p.name != "checksums.json"
        and p.relative_to(target).as_posix() not in expected
    )
    trace_integrity = False
    try:
        trace_integrity = DiscoveryTrace.load(target / "trace.json").verify_integrity()
    except (TraceIntegrityError, ValueError, OSError, json.JSONDecodeError):
        trace_integrity = False
    promotions = {}
    for path in sorted((target / "promotions").glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        promotions[path.stem] = raw.get("status")
    replay_only_promoted = False
    for path in sorted((target / "promotions").glob("*.json")):
        verdict = json.loads(path.read_text(encoding="utf-8"))
        if verdict.get("status") != "PROMOTED":
            continue
        evaluation = json.loads(
            (target / "evaluations" / f"{path.stem}.json").read_text(encoding="utf-8")
        )
        if not evaluation["stage_b"]["is_prospective_evidence"]:
            replay_only_promoted = True
    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "verified": not mismatches
        and not extra
        and trace_integrity
        and not replay_only_promoted,
        "n_files_verified": len(expected),
        "mismatches": mismatches,
        "extra_files": extra,
        "trace_integrity": trace_integrity,
        "replay_only_promotion_detected": replay_only_promoted,
        "promotion_verdicts": promotions,
    }


__all__ = [
    "PROTOCOL_ID",
    "PROTOCOL_VERSION",
    "BUNDLE_SCHEMA_VERSION",
    "ARMS",
    "build_pilot_trace",
    "run_pilot",
    "verify_pilot",
]
