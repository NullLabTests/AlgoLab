"""Protocol-240 tests: generative composition search on real pipelines.

Covers four things, in order of importance:

1. **Grammar invariants** — the registered space is exactly 585 programs,
   parsing rejects every out-of-grammar string, costs are strictly increasing
   in program length, and the neighbourhood operators only ever return valid
   programs.
2. **Determinism and leakage** — the evaluator is a pure function of
   (family, program, seed_base, trial, episode); repeating an attempt with a
   different ``attempt`` index gives the identical measurement; the prior
   phase never touches the held-out family; and no policy's choices depend on
   wall clock.
3. **Policy determinism** — two instances of the same generative arm with the
   same seed produce the same program stream given the same observations.
4. **End-to-end bundle + reproducibility** — a tiny run seals a bundle whose
   checksums verify, and the committed bundle (when present) re-executes in a
   clean process via ``scripts/verify_bundle.py`` with no mismatches.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from algolab.search import ExperimentConfig, PolicyComparison, candidates
from algolab.search import compose_analysis as ca
from algolab.search import generative_policies as gp
from algolab.search import workload_compose as wc
from algolab.search.harness import ARMS_PROTOCOL_240, resolve_workload
from algolab.search.policies import KnowledgeSnapshot
from algolab.storage.db import connect

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_BUNDLE = REPO_ROOT / "experiments" / "protocol-240-v1"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "verify_bundle.py"


# ---------------------------------------------------------------------------
# 1. Grammar invariants
# ---------------------------------------------------------------------------


class TestGrammar:
    def test_registered_space_is_exactly_585_programs(self) -> None:
        programs = candidates.all_programs()
        assert len(programs) == 585
        assert candidates.space_size() == 585
        assert len(set(programs)) == 585
        assert programs == tuple(sorted(programs))

    def test_space_size_matches_the_combinatorial_formula(self) -> None:
        n = len(candidates.ATOMS)
        expected = n + n * (n - 1) + n * (n - 1) * (n - 2)
        assert expected == candidates.space_size() == 585

    def test_every_program_round_trips(self) -> None:
        for program in candidates.all_programs():
            atoms = candidates.parse(program)
            assert 1 <= len(atoms) <= candidates.MAX_PROGRAM_LENGTH
            assert len(set(atoms)) == len(atoms)
            assert candidates.serialize(atoms) == program

    @pytest.mark.parametrize("bad", [
        "", "log1p+", "+log1p", "log1p+log1p", "not-an-atom",
        "log1p+sqrt+clip-1_99+pca-10",
        "log1p+sqrt+nope",
    ])
    def test_invalid_programs_are_rejected(self, bad: str) -> None:
        with pytest.raises(candidates.GrammarError):
            candidates.parse(bad)

    def test_cost_is_positive_and_increases_with_length(self) -> None:
        by_length: dict[int, list[float]] = {1: [], 2: [], 3: []}
        for program in candidates.all_programs():
            by_length[len(candidates.parse(program))].append(
                candidates.program_cost(program))
        for length, costs in by_length.items():
            assert costs
            # Every program pays the fixed per-step charge.
            assert min(costs) >= candidates.PER_STEP_CREDIT * length
        # The cheapest program of each length is strictly more expensive than
        # the cheapest of the previous length. (The *most* expensive length-2
        # program can out-cost the cheapest length-3 one: cost is length plus
        # per-atom data cost, not length alone.)
        assert min(by_length[1]) < min(by_length[2]) < min(by_length[3])
        assert max(by_length[1]) < max(by_length[2]) < max(by_length[3])

    def test_mutations_only_return_valid_programs(self) -> None:
        for program in ("log1p", "log1p+sqrt", "log1p+sqrt+clip-1_99"):
            neighbours = candidates.mutations(program)
            assert neighbours == tuple(sorted(neighbours))
            assert neighbours, program
            for candidate in neighbours:
                candidates.parse(candidate)
                assert candidate != program
            # A length-3 program has no append moves left.
            if len(candidates.parse(program)) == candidates.MAX_PROGRAM_LENGTH:
                assert all(len(candidates.parse(c)) <= 3 for c in neighbours)

    def test_crossover_always_produces_a_valid_program(self) -> None:
        import random

        rng = random.Random(0)
        left = "poly2-top5+log1p"
        right = "pca-10+sqrt+robust-scale"
        for _ in range(50):
            child = candidates.crossover(left, right, rng)
            atoms = candidates.parse(child)
            assert 1 <= len(atoms) <= candidates.MAX_PROGRAM_LENGTH
            assert atoms[0] == "poly2-top5"  # order-preserving from left

    def test_grammar_and_evaluator_agree_on_atoms(self) -> None:
        assert set(wc.ATOM_FACTORIES) == set(candidates.ATOMS)


# ---------------------------------------------------------------------------
# 2. Evaluator determinism and leakage
# ---------------------------------------------------------------------------


class TestComposeWorkload:
    def test_repeat_attempt_is_identical(self) -> None:
        a1 = wc.run_attempt("beta", "log1p+sqrt", seed_base=7,
                            trial=0, episode=0, attempt=0)
        a2 = wc.run_attempt("beta", "log1p+sqrt", seed_base=7,
                            trial=0, episode=0, attempt=12345)
        assert a1 == a2

    def test_distinct_trials_give_distinct_measurements(self) -> None:
        a1 = wc.run_attempt("beta", "log1p", seed_base=7,
                            trial=0, episode=0, attempt=0)
        a2 = wc.run_attempt("beta", "log1p", seed_base=7,
                            trial=1, episode=0, attempt=0)
        assert (a1.effect_1, a1.effect_2) != (a2.effect_1, a2.effect_2)

    def test_gamma_is_a_different_dataset(self) -> None:
        alpha = wc.run_attempt("alpha", "log1p", seed_base=7,
                               trial=0, episode=0, attempt=0)
        gamma = wc.run_attempt(wc.HELD_OUT_FAMILY, "log1p", seed_base=7,
                               trial=0, episode=0, attempt=0)
        assert (alpha.effect_1, alpha.effect_2) != \
            (gamma.effect_1, gamma.effect_2)

    def test_effect_is_a_paired_difference_against_identity(self) -> None:
        attempt = wc.run_attempt("alpha", "log1p+robust-scale", seed_base=7,
                                 trial=0, episode=0, attempt=0)
        seed_a = wc._measure_seed(7, 0, 0, 1)
        seed_b = wc._measure_seed(7, 0, 0, 2)
        base_a = wc._baseline_accuracy("alpha", seed_a)
        base_b = wc._baseline_accuracy("alpha", seed_b)
        acc_a = wc._cv_accuracy(
            "alpha", wc.program_transformer("log1p+robust-scale"), seed_a)
        acc_b = wc._cv_accuracy(
            "alpha", wc.program_transformer("log1p+robust-scale"), seed_b)
        assert attempt.effect_1 == pytest.approx(acc_a - base_a, abs=2e-6)
        assert attempt.effect_2 == pytest.approx(acc_b - base_b, abs=2e-6)

    def test_view_resolution(self) -> None:
        view = resolve_workload("compose")
        assert not view.has_oracle
        assert view.families == ("alpha", "beta")
        assert view.held_out_family == "gamma"
        assert tuple(view.operators) == candidates.ATOMS

    def test_metadata_records_the_closed_space(self) -> None:
        meta = wc.environment_metadata()
        wm = meta["workload_metadata"]
        assert wm["search_space_size"] == 585
        assert wm["search_space_is_closed"] is True
        assert wm["replicates"] == 2
        assert meta["held_out_family"] == "gamma"
        assert set(wm["dataset_shapes"]) == {"alpha", "beta", "gamma"}

    def test_prior_phase_never_touches_gamma(self, tmp_path) -> None:
        cfg = _smoke_cfg("protocol-240-prior")
        conn = connect(":memory:", initialize=True)
        comp = PolicyComparison(cfg, conn, tmp_path / "art")
        comp.ensure_manifest()
        comp.run_prior()
        by_family = json.loads(
            (tmp_path / "art" / "knowledge-snapshot-by-family.json").read_text())
        assert set(by_family) == {"alpha", "beta"}


# ---------------------------------------------------------------------------
# 3. Policy determinism
# ---------------------------------------------------------------------------


def _snapshot() -> KnowledgeSnapshot:
    """Frozen prior with a deliberate success-rate ordering over the atoms."""
    attempts: dict[str, int] = {}
    successes: dict[str, int] = {}
    sum_effect: dict[str, float] = {}
    sum_effect_sq: dict[str, float] = {}
    credits: dict[str, float] = {}
    for atom, rate in zip(candidates.ATOMS, [0.5, 0.2, 0.1, 0.4, 0.3,
                                             0.0, 0.25, 0.15, 0.35],
                          strict=True):
        attempts[atom] = 3
        successes[atom] = round(rate * 3)
        sum_effect[atom] = 0.01 * successes[atom]
        sum_effect_sq[atom] = (0.01 ** 2) * successes[atom]
        credits[atom] = candidates.program_cost(atom)
    return KnowledgeSnapshot(
        snapshot_id="test-k0", version="1.0.0",
        event_range=["test"], attempts=attempts, successes=successes,
        sum_effect=sum_effect, sum_effect_sq=sum_effect_sq, credits=credits)


class TestGenerativePolicies:
    def test_arms_are_registered(self) -> None:
        assert set(ARMS_PROTOCOL_240) == {
            "random-program", "greedy-history", "evolutionary-archive",
            "static-atoms", "greedy-permuted"}

    def test_random_program_stream_is_seed_deterministic(self) -> None:
        a = gp.GenerativeRandomPolicy(None, seed=11)
        b = gp.GenerativeRandomPolicy(None, seed=11)
        stream_a = [a.select("alpha", step)[0] for step in range(20)]
        stream_b = [b.select("alpha", step)[0] for step in range(20)]
        assert stream_a == stream_b
        assert len(set(stream_a)) > 1

    def test_static_atoms_only_emits_length_one_programs(self) -> None:
        policy = gp.StaticAtomsPolicy()
        programs = [policy.select("alpha", step)[0] for step in range(20)]
        assert all(len(candidates.parse(p)) == 1 for p in programs)
        assert set(programs) == set(candidates.ATOMS)

    def test_length_class_sizes_match_the_enumerated_grammar(self) -> None:
        by_length: dict[int, int] = {}
        for program in candidates.all_programs():
            n = len(candidates.parse(program))
            by_length[n] = by_length.get(n, 0) + 1
        assert {n: candidates.length_class_size(n) for n in by_length} == by_length
        assert sum(by_length.values()) == 585
        for bad in (0, candidates.MAX_PROGRAM_LENGTH + 1):
            with pytest.raises(candidates.GrammarError):
                candidates.length_class_size(bad)

    def test_random_arm_reports_its_actual_sampler(self) -> None:
        """Erratum E3: the control is length-stratified, and its audit trail
        must say so instead of claiming a 1/585 draw."""
        policy = gp.GenerativeRandomPolicy(None, seed=17)
        for step in range(60):
            program, record = policy.select("alpha", step)
            length = len(candidates.parse(program))
            expected = 1.0 / (candidates.MAX_PROGRAM_LENGTH
                             * candidates.length_class_size(length))
            assert record.selection_probability == pytest.approx(expected)
            assert record.reason.startswith("length-uniform then atom-uniform")
            assert "erratum E3" in record.reason

    def test_greedy_history_stream_is_deterministic(self) -> None:
        def run() -> list[str]:
            policy = gp.GreedyHistoryPolicy(_snapshot(), seed=13)
            out: list[str] = []
            for step in range(12):
                program, _ = policy.select("alpha", step)
                out.append(program)
                policy.observe("alpha", program, _FakeAttempt(
                    discovery=step % 4 == 0, mean_effect=0.01 * (step % 5),
                    cost_credits=candidates.program_cost(program)))
            return out

        assert run() == run()

    def test_permuted_ablation_differs_from_greedy(self) -> None:
        def run(policy_cls: type) -> list[str]:
            policy = policy_cls(_snapshot(), seed=13)
            out: list[str] = []
            for step in range(16):
                program, _ = policy.select("alpha", step)
                out.append(program)
                policy.observe("alpha", program, _FakeAttempt(
                    discovery=step % 3 == 0, mean_effect=0.02,
                    cost_credits=candidates.program_cost(program)))
            return out

        assert run(gp.GreedyHistoryPolicy) != \
            run(gp.PermutedGreedyHistoryPolicy)

    def test_evolutionary_population_stays_valid(self) -> None:
        policy = gp.EvolutionaryArchivePolicy(_snapshot(), seed=17)
        for step in range(18):
            program, record = policy.select("alpha", step)
            candidates.parse(program)
            assert record.family == "alpha"
            policy.observe("alpha", program, _FakeAttempt(
                discovery=step % 5 == 0, mean_effect=0.005 * step,
                cost_credits=candidates.program_cost(program)))
        pop = policy.population_snapshot("alpha")
        assert len(pop) == gp.POPULATION_SIZE
        for program in pop:
            candidates.parse(program)
        assert policy.archive_snapshot("alpha")

    def test_reset_restores_the_initial_stream(self) -> None:
        policy = gp.GreedyHistoryPolicy(_snapshot(), seed=19)
        first = [policy.select("beta", s)[0] for s in range(5)]
        policy.reset()
        assert [policy.select("beta", s)[0] for s in range(5)] == first

    def test_reset_fully_restores_the_permuted_ablation(self) -> None:
        policy = gp.PermutedGreedyHistoryPolicy(_snapshot(), seed=23)

        def drive() -> list[str]:
            out: list[str] = []
            for step in range(8):
                program, _ = policy.select("alpha", step)
                out.append(program)
                policy.observe("alpha", program, _FakeAttempt(
                    discovery=step % 2 == 0, mean_effect=0.01,
                    cost_credits=candidates.program_cost(program)))
            return out

        first = drive()
        policy.reset()
        assert drive() == first


class _FakeAttempt:
    """Minimal Attempt stand-in for policy tests (no data evaluation)."""

    def __init__(self, *, discovery: bool, mean_effect: float,
                 cost_credits: float):
        self.discovery = discovery
        self.mean_effect = mean_effect
        self.cost_credits = cost_credits


# ---------------------------------------------------------------------------
# 4. Analysis units
# ---------------------------------------------------------------------------


class TestComposeAnalysis:
    def _record(self, arm: str, trial: int, program: str, *,
                discovery: bool, cost: float = 5.0,
                mean_effect: float = 0.01) -> ca.AttemptRecord:
        return ca.AttemptRecord(
            arm=arm, trial=trial, episode=0, family="alpha", step=0,
            program=program, cost=cost, valid=True, effect_1=mean_effect,
            effect_2=mean_effect, mean_effect=mean_effect,
            discovery=discovery)

    def test_distinct_metric_counts_a_program_once_per_cell(self) -> None:
        # The same program discovered three times in one cell counts once.
        records = [
            self._record("greedy-history", 0, "log1p", discovery=True),
            self._record("greedy-history", 0, "log1p", discovery=True),
            self._record("greedy-history", 0, "log1p", discovery=True),
            self._record("greedy-history", 1, "log1p", discovery=True),
        ]
        series = ca.distinct_efficiency_series(
            {"greedy-history": records}, ["alpha"])
        # Cell (alpha, trial 0): 1 distinct program / 15 credits.
        assert series["alpha"]["greedy-history"][0] == pytest.approx(1 / 15)
        assert series["alpha"]["greedy-history"][1] == pytest.approx(1 / 5)

    def test_champion_rule_is_tie_broken_by_cost_then_name(self) -> None:
        records = [
            self._record("a", 0, "log1p+sqrt", discovery=False,
                         mean_effect=0.02, cost=10.0),
            self._record("a", 1, "sqrt+log1p", discovery=False,
                         mean_effect=0.02, cost=10.0),
            self._record("a", 2, "pca-10", discovery=False,
                         mean_effect=0.02, cost=7.5),
        ]
        champ = ca.champion(records)
        assert champ is not None
        assert champ["program"] == "pca-10"

    def test_champion_ignores_invalid_attempts(self) -> None:
        bad = self._record("a", 0, "log1p", discovery=False, mean_effect=0.5)
        bad = ca.AttemptRecord(
            arm="a", trial=0, episode=0, family="alpha", step=0,
            program="log1p", cost=5.0, valid=False, effect_1=0.0,
            effect_2=0.0, mean_effect=0.0, discovery=False)
        good = self._record("a", 1, "sqrt", discovery=True, mean_effect=0.01)
        champ = ca.champion([bad, good])
        assert champ is not None and champ["program"] == "sqrt"

    def test_h3_requires_transfer_from_a_discovering_arm(self) -> None:
        analysis = {
            "per_family": {
                "alpha": {"comparisons": []},
                "beta": {"comparisons": []},
            },
        }
        transfers = {
            "random-program": {
                "transfer": {"all_replicates_positive": True}},
            "greedy-history": {
                "transfer": {"all_replicates_positive": False}},
        }
        # A champion transfers positively, but only for an arm with no
        # training discovery -> H3 must not be met.
        hyp = ca.evaluate_hypotheses(
            analysis, families=["alpha", "beta"],
            champion_transfers=transfers, arms=tuple(transfers),
            arms_with_training_discovery=["greedy-history"])
        assert hyp["H3_met"] is False

        hyp2 = ca.evaluate_hypotheses(
            analysis, families=["alpha", "beta"],
            champion_transfers=transfers, arms=tuple(transfers),
            arms_with_training_discovery=["random-program"])
        assert hyp2["H3_met"] is True

    def test_fresh_transfer_seeds_are_outside_the_search_range(self) -> None:
        assert ca.CHAMPION_TRIAL_BASE > 100_000
        assert ca.CHAMPION_REPLICATES >= 2


# ---------------------------------------------------------------------------
# 5. End-to-end bundle and cleanliness
# ---------------------------------------------------------------------------


def _smoke_cfg(experiment_id: str) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id=experiment_id,
        workload="compose",
        trials=2,
        episodes_per_trial=2,
        prior_attempts_per_family=1,
        budget_credits=25.0,
        promotion_threshold=wc.DISCOVERY_MARGIN,
        arms=ARMS_PROTOCOL_240,
        ablations=(),
    )


class TestProtocol240Bundle:
    def test_smoke_run_seals_a_verifiable_bundle(self, tmp_path) -> None:
        from algolab.search.compose_experiment import run_protocol_240

        cfg = _smoke_cfg("protocol-240-smoke")
        art = tmp_path / "art"
        conn = connect(":memory:", initialize=True)
        run_protocol_240(cfg, conn, art)

        for name in ("manifest.json", "statistics.json", "report.md",
                     "checksums.json", "protocol-240-statistics.json",
                     "reproducibility.json"):
            assert (art / name).is_file(), name

        manifest = json.loads((art / "manifest.json").read_text())
        assert manifest["workload"] == "compose"
        # The four base procedural arms are always recorded for historical
        # comparability; every protocol-240 arm must be present too.
        assert set(ARMS_PROTOCOL_240) <= set(manifest["policy_versions"])
        for arm in ARMS_PROTOCOL_240:
            assert manifest["policy_versions"][arm] == "1.0.0"

        stats = json.loads((art / "protocol-240-statistics.json").read_text())
        assert stats["search_space"]["size"] == 585
        assert stats["primary_metric"] == (
            "distinct_validated_programs / credits_consumed")
        assert stats["hypotheses"]["outcome_class"] in {"A", "B", "C"}

        import hashlib

        recorded = json.loads((art / "checksums.json").read_text())
        assert recorded
        for rel, digest in recorded.items():
            actual = hashlib.sha256((art / rel).read_bytes()).hexdigest()
            assert actual == digest, rel

    def test_report_contains_the_pre_registered_hypotheses(self,
                                                           tmp_path) -> None:
        from algolab.search.compose_experiment import run_protocol_240

        cfg = _smoke_cfg("protocol-240-report")
        art = tmp_path / "art"
        conn = connect(":memory:", initialize=True)
        run_protocol_240(cfg, conn, art)
        report = (art / "report.md").read_text()
        for marker in ("Protocol 240", "H1", "H2", "H3", "H4", "H5",
                       "Outcome class"):
            assert marker in report, marker

    def test_report_is_byte_stable_across_runs(self, tmp_path) -> None:
        """``report.md`` is compared byte-for-byte on reproduction, so it must
        not embed wall-clock durations (defect D-11: the first seal did, which
        made a clean re-execution impossible to match)."""
        from algolab.search.compose_experiment import run_protocol_240

        reports = []
        for i in range(2):
            art = tmp_path / f"art{i}"
            conn = connect(":memory:", initialize=True)
            run_protocol_240(_smoke_cfg("protocol-240-stable"), conn, art)
            reports.append((art / "report.md").read_bytes())
        assert reports[0] == reports[1]
        text = reports[0].decode()
        for volatile in ("evaluation time", "measured_operator_seconds"):
            assert volatile not in text, volatile


def _numerical_environment() -> dict[str, str]:
    """Versions that determine byte-exact raw streams for this bundle."""
    import numpy
    import sklearn

    meta = json.loads(
        (COMMITTED_BUNDLE / "environment.json").read_text())["workload_metadata"]
    return {
        "sealed": {
            "numpy": str(meta["numpy_version"]),
            "sklearn": str(meta["sklearn_version"]),
        },
        "installed": {
            "numpy": str(numpy.__version__),
            "sklearn": str(sklearn.__version__),
        },
    }


@pytest.mark.skipif(not COMMITTED_BUNDLE.is_dir(),
                    reason="protocol-240-v1 bundle not sealed in this tree")
class TestCommittedBundleReproduces:
    def test_committed_bundle_checksums_verify(self) -> None:
        recorded = json.loads(
            (COMMITTED_BUNDLE / "checksums.json").read_text())
        assert recorded
        import hashlib

        for rel, digest in recorded.items():
            actual = hashlib.sha256(
                (COMMITTED_BUNDLE / rel).read_bytes()).hexdigest()
            assert actual == digest, rel

    def test_committed_bundle_reproduces_in_a_clean_process(self,
                                                            tmp_path) -> None:
        versions = _numerical_environment()
        if versions["sealed"] != versions["installed"]:
            pytest.skip(
                "protocol-240-v1 was sealed with "
                f"{versions['sealed']}; installed {versions['installed']}. "
                "Byte-exact reproduction runs in the pinned CI repro job.")
        out = tmp_path / "verdict.json"
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [sys.executable, str(VERIFY_SCRIPT), str(COMMITTED_BUNDLE),
             "--out", str(out), "--quiet"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=3600)
        assert result.returncode == 0, result.stdout + result.stderr
        verdict = json.loads(out.read_text())
        assert verdict["integrity"]["pass"] is True
        assert verdict["reproduction"]["pass"] is True
        assert verdict["pass"] is True
