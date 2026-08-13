"""Built-in ``quadratic_optimizer`` workload (M1).

Adapter + standalone script. The script is invoked by the worker as:

    python quadratic_optimizer.py --config resolved_config.json \
        --seed <int> --out metrics.json

It is intentionally dependency-free and deterministic: every random draw
comes from ``random.Random(seed)`` in a fixed order, so identical config +
seed always produce identical scientific metrics. The script supports
documented test hooks (``sleep_seconds``, ``raise_on_start``,
``emit_invalid_metrics``, ``extra_bytes``, ``print_bytes``) used only by
integration tests.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

from algolab.workloads.base import (
    ConfigInvalid,
    MetricsInvalid,
    WorkloadAdapter,
)

_STRATEGIES = ("gradient_descent", "momentum", "nesterov")

_CONFIG_KEYS = frozenset({
    "strategy",
    "learning_rate",
    "max_iterations",
    "dim",
    "convergence_tolerance",
    "noise_scale",
    "objective_threshold",
    "timeout_seconds",
    # test hooks (documented; used only by integration tests)
    "sleep_seconds",
    "raise_on_start",
    "emit_invalid_metrics",
    "extra_bytes",
    "print_bytes",
})

_METRIC_KEYS = frozenset({
    "final_objective",
    "initial_objective",
    "converged",
    "iterations",
    "compute_units",
    "gradient_norm",
    "strategy",
    "seed",
    "dim",
})


class QuadraticOptimizerAdapter(WorkloadAdapter):
    """Deterministic quadratic-form minimization with pass/fail metrics."""

    name = "quadratic_optimizer"
    version = "1.0.0"
    description = (
        "minimize sum(a_i * (x_i - target_i)^2) with a seeded optimizer; "
        "converged/objective give workload-level pass/fail signals"
    )

    def defaults(self) -> dict[str, Any]:
        return {
            "strategy": "gradient_descent",
            "learning_rate": 0.1,
            "max_iterations": 2000,
            "dim": 16,
            "convergence_tolerance": 1e-9,
            "noise_scale": 0.0,
            "objective_threshold": None,
            "timeout_seconds": 60.0,
        }

    def config_from_changes(self, changes: list[dict[str, Any]]) -> dict[str, Any]:
        config = dict(self.defaults())
        for change in changes:
            for key, value in change.items():
                if key in _CONFIG_KEYS:
                    config[key] = value
        self.validate_config(config)
        return config

    def validate_config(self, config: dict[str, Any]) -> None:
        if config.get("strategy") not in _STRATEGIES:
            raise ConfigInvalid(
                f"strategy must be one of {_STRATEGIES}, got "
                f"{config.get('strategy')!r}"
            )
        if (
            not isinstance(config.get("learning_rate"), (int, float))
            or config["learning_rate"] <= 0
        ):
            raise ConfigInvalid("learning_rate must be a positive number")
        if (
            not isinstance(config.get("max_iterations"), int)
            or config["max_iterations"] < 1
        ):
            raise ConfigInvalid("max_iterations must be a positive integer")
        if not isinstance(config.get("dim"), int) or config["dim"] < 1:
            raise ConfigInvalid("dim must be a positive integer")
        if (
            not isinstance(config.get("convergence_tolerance"), (int, float))
            or config["convergence_tolerance"] <= 0
        ):
            raise ConfigInvalid("convergence_tolerance must be a positive number")
        if (
            not isinstance(config.get("noise_scale"), (int, float))
            or config["noise_scale"] < 0
        ):
            raise ConfigInvalid("noise_scale must be a non-negative number")
        threshold = config.get("objective_threshold")
        if threshold is not None and (
            not isinstance(threshold, (int, float)) or threshold < 0
        ):
            raise ConfigInvalid(
                "objective_threshold must be a non-negative number or null"
            )
        for hook in ("sleep_seconds", "extra_bytes", "print_bytes"):
            if hook in config and (
                not isinstance(config[hook], (int, float)) or config[hook] < 0
            ):
                raise ConfigInvalid(f"{hook} must be a non-negative number")
        for flag in ("raise_on_start", "emit_invalid_metrics"):
            if flag in config and not isinstance(config[flag], bool):
                raise ConfigInvalid(f"{flag} must be a boolean")

    def command(self, run_dir: Path, config: dict[str, Any], seed: int
                ) -> list[str]:
        script = Path(__file__).resolve().parent / "quadratic_optimizer.py"
        return [
            sys.executable,
            str(script),
            "--config", str(run_dir / "resolved_config.json"),
            "--seed", str(seed),
            "--out", str(run_dir / "metrics.json"),
        ]

    def timeout_seconds(self, config: dict[str, Any]) -> float:
        value = config.get("timeout_seconds")
        if not isinstance(value, (int, float)) or value <= 0:
            raise ConfigInvalid("timeout_seconds must be a positive number")
        return float(value)

    def estimate_compute_units(self, config: dict[str, Any]) -> float:
        return float(int(config["max_iterations"]) * int(config["dim"]))

    def validate_metrics(self, metrics: dict[str, Any]) -> None:
        missing = _METRIC_KEYS - set(metrics)
        if missing:
            raise MetricsInvalid(
                f"metrics missing required keys: {sorted(missing)}"
            )
        for key in ("final_objective", "initial_objective",
                    "compute_units", "gradient_norm"):
            if not isinstance(metrics[key], (int, float)):
                raise MetricsInvalid(f"metrics.{key} must be a number")
        if not isinstance(metrics["converged"], bool):
            raise MetricsInvalid("metrics.converged must be a boolean")
        if not isinstance(metrics["iterations"], int) or metrics["iterations"] < 0:
            raise MetricsInvalid("metrics.iterations must be a non-negative integer")
        if metrics["compute_units"] < 0:
            raise MetricsInvalid("metrics.compute_units must be non-negative")

    @property
    def expected_artifacts(self) -> tuple[str, ...]:
        return ("metrics.json",)


# ---------------------------------------------------------------------------
# Standalone script
# ---------------------------------------------------------------------------


def _optimize(config: dict[str, Any], seed: int) -> dict[str, Any]:
    """Deterministic seeded optimization loop."""
    dim = int(config["dim"])
    max_iterations = int(config["max_iterations"])
    learning_rate = float(config["learning_rate"])
    strategy = str(config["strategy"])
    tolerance = float(config["convergence_tolerance"])
    noise_scale = float(config.get("noise_scale", 0.0))

    rng = random.Random(seed)
    target = [rng.uniform(-1.0, 1.0) for _ in range(dim)]
    weights = [rng.uniform(0.5, 2.0) for _ in range(dim)]
    x = [rng.uniform(-1.0, 1.0) for _ in range(dim)]

    def objective(xv: list[float]) -> float:
        return sum(weights[i] * (xv[i] - target[i]) ** 2 for i in range(dim))

    def gradient(xv: list[float]) -> list[float]:
        grad = [2.0 * weights[i] * (xv[i] - target[i]) for i in range(dim)]
        if noise_scale > 0.0:
            grad = [g + rng.gauss(0.0, noise_scale) for g in grad]
        return grad

    initial_objective = objective(x)
    velocity = [0.0] * dim
    grad_norm = float("inf")
    iterations = 0
    converged = False
    for _ in range(max_iterations):
        iterations += 1
        if strategy == "gradient_descent":
            grad = gradient(x)
            step = [learning_rate * g for g in grad]
        elif strategy == "momentum":
            grad = gradient(x)
            velocity = [
                0.9 * v + learning_rate * g
                for v, g in zip(velocity, grad, strict=True)
            ]
            step = list(velocity)
        else:  # nesterov
            lookahead = [x[i] - 0.9 * velocity[i] for i in range(dim)]
            grad = gradient(lookahead)
            velocity = [
                0.9 * v + learning_rate * g
                for v, g in zip(velocity, grad, strict=True)
            ]
            step = list(velocity)
        x = [x[i] - step[i] for i in range(dim)]
        grad_norm = math.sqrt(sum(g * g for g in grad))
        if grad_norm < tolerance:
            converged = True
            break

    final_objective = objective(x)
    threshold = config.get("objective_threshold")
    if threshold is not None and final_objective > float(threshold):
        converged = False
    return {
        "final_objective": final_objective,
        "initial_objective": initial_objective,
        "converged": converged,
        "iterations": iterations,
        "compute_units": float(iterations * dim),
        "gradient_norm": grad_norm,
        "strategy": strategy,
        "seed": seed,
        "dim": dim,
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="quadratic_optimizer",
        description="deterministic quadratic minimization workload",
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        with open(args.config, encoding="utf-8") as fh:
            config = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"quadratic_optimizer: cannot read config: {exc}", file=sys.stderr)
        return 2

    if config.get("raise_on_start"):
        print("quadratic_optimizer: raise_on_start hook triggered", file=sys.stderr)
        return 1

    sleep_seconds = float(config.get("sleep_seconds", 0.0))
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)

    if config.get("emit_invalid_metrics"):
        payload: Any = {"not": "metrics"}
    else:
        payload = _optimize(config, args.seed)

    extra_bytes = int(config.get("extra_bytes", 0))
    if extra_bytes > 0:
        with open(Path(args.out).parent / "junk.bin", "wb") as fh:
            fh.write(b"x" * extra_bytes)

    print_bytes = int(config.get("print_bytes", 0))
    if print_bytes > 0:
        sys.stdout.write("p" * print_bytes)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
