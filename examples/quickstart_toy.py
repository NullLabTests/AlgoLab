#!/usr/bin/env python3
"""Quickstart example: Run a minimal AlgoLab toy search comparison.

This demonstrates the core functionality with small parameters for fast execution.
"""

import tempfile
from pathlib import Path

from algolab.search import ExperimentConfig, PolicyComparison
from algolab.storage.db import connect


def main():
    print("AlgoLab Quickstart - Toy Substrate")
    print("=" * 40)
    
    # Create a minimal experiment configuration
    cfg = ExperimentConfig(
        experiment_id="quickstart-demo",
        workload="toy",
        trials=4,  # Small for quick demo
        episodes_per_trial=2,
        prior_attempts_per_family=10,
        budget_credits=40.0,
        arms=("static", "knowledge-informed", "adaptive", "random"),
        ablations=(),
    )
    
    print(f"Configuration:")
    print(f"  Trials per family: {cfg.trials}")
    print(f"  Budget: {cfg.budget_credits} credits")
    print(f"  Arms: {', '.join(cfg.arms)}")
    print()
    
    # Run the comparison
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "results"
        conn = connect(":memory:", initialize=True)
        
        print("Running comparison...")
        comp = PolicyComparison(cfg, conn, out_dir)
        results = comp.run()
        stats = comp.analyze(results)
        comp.write_report(results, stats, None)
        
        print("\nResults:")
        print("-" * 40)
        per_cond = stats.get("per_condition", {})
        for arm in cfg.arms:
            if arm in per_cond:
                arm_stats = per_cond[arm]
                eff = arm_stats.get("mean_efficiency", 0)
                discoveries = arm_stats.get("total_discoveries", 0)
                print(f"{arm:20s}: {eff:.4f} discoveries/credit, {discoveries} discoveries")
        
        print(f"\nReport written to: {out_dir / 'report.md'}")
        print("\nFor full reproducible experiments, see experiments/ directory.")


if __name__ == "__main__":
    main()
