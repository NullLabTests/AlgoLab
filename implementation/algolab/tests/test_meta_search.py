"""Protocol 241 / meta-search capability tests (Phase 10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from algolab.meta_search.evaluation import (
    PromotionStatus,
    evaluate_policy,
    promote,
    replay_evaluation,
)
from algolab.meta_search.policies import (
    BASELINE_POLICY,
    CONTROL_POLICY,
    EVOLVED_POLICY,
    REPLAY_POLICY,
    Observation,
    propose_policy,
)
from algolab.meta_search.protocol_241 import build_pilot_trace, run_pilot, verify_pilot
from algolab.meta_search.replay import (
    OutcomeKind,
    ReplayEnv,
    assert_not_prospective,
)
from algolab.meta_search.traces import (
    TRACE_SCHEMA_VERSION,
    DiscoveryTrace,
    TraceIntegrityError,
    TraceNode,
)


def _node(
    trace: DiscoveryTrace,
    parent: str | None,
    method: str,
    *,
    discovery: bool = True,
    credits: float = 1.0,
) -> TraceNode:
    return trace.append(
        TraceNode(
            experiment_id=trace.experiment_id,
            parent_id=parent,
            policy_id=BASELINE_POLICY.policy_id,
            policy_version=BASELINE_POLICY.version,
            candidate_id=f"c-{method}",
            candidate_generation_method=method,
            selection_decision=f"pick {method}",
            compute_credits=credits,
            seed=7,
            dataset_id="toy",
            eval_split_id="train",
            observation={"discovery": discovery, "valid": True, "mean_effect": 0.3},
            derived_metrics={"mean_effect": 0.3},
            evaluation_result={"cost_credits": credits, "discovery": discovery},
        )
    )


@pytest.fixture()
def trace() -> DiscoveryTrace:
    result = DiscoveryTrace(trace_id="trace-test", experiment_id="EXP-TEST")
    root = _node(result, None, "root", discovery=False)
    _node(result, root.node_id, "tune")
    _node(result, root.node_id, "refresh", discovery=False)
    return result


class TestTraceInfrastructure:
    def test_creation_integrity_and_relationships(self, trace: DiscoveryTrace) -> None:
        assert trace.verify_integrity()
        assert len(trace.children(None)) == 1
        root = trace.children(None)[0]
        assert {
            c.candidate_generation_method for c in trace.children(root.node_id)
        } == {"tune", "refresh"}
        assert trace.head_checksum == trace.nodes[-1].checksum

    def test_stable_ids_and_canonical_serialization(
        self, trace: DiscoveryTrace
    ) -> None:
        payload = trace.to_canonical_json()
        assert payload == json.dumps(
            trace.to_dict(), sort_keys=True, separators=(",", ":")
        )
        restored = DiscoveryTrace.from_dict(json.loads(payload))
        assert [n.node_id for n in restored.nodes] == [n.node_id for n in trace.nodes]
        assert restored.verify_integrity()

    def test_file_roundtrip_and_checksum_guard(
        self, trace: DiscoveryTrace, tmp_path: Path
    ) -> None:
        path = trace.write(tmp_path / "trace.json")
        assert DiscoveryTrace.load(path).verify_integrity()
        path.write_bytes(path.read_bytes() + b" ")
        with pytest.raises(TraceIntegrityError):
            DiscoveryTrace.load(path)

    def test_corruption_and_unknown_parent_fail(self, trace: DiscoveryTrace) -> None:
        raw = trace.to_dict()
        raw["nodes"][1]["derived_metrics"] = {"mean_effect": 999.0}
        with pytest.raises(TraceIntegrityError):
            DiscoveryTrace.from_dict(raw)
        with pytest.raises(TraceIntegrityError):
            trace.append(
                TraceNode(
                    experiment_id="EXP-TEST",
                    parent_id="missing",
                    policy_id="p",
                    policy_version=1,
                    candidate_id="c",
                    candidate_generation_method="x",
                )
            )

    def test_schema_version_and_statement_kinds(self, trace: DiscoveryTrace) -> None:
        assert trace.schema_version == TRACE_SCHEMA_VERSION
        raw = trace.to_dict()
        raw["schema_version"] = "meta-trace/0.0"
        with pytest.raises(TraceIntegrityError):
            DiscoveryTrace.from_dict(raw)
        assert trace.nodes[0].statement_kind == "observation"


class TestReplay:
    def test_deterministic_and_observed_outcomes(self, trace: DiscoveryTrace) -> None:
        env = ReplayEnv(trace)
        a = env.run(REPLAY_POLICY, seed=3)
        b = env.run(REPLAY_POLICY, seed=3)
        assert [d.chosen_method for d in a.decisions] == [
            d.chosen_method for d in b.decisions
        ]
        assert a.to_dict() == b.to_dict()
        assert a.observed_count + a.uncertain_count == len(a.decisions)

    def test_counterfactual_uncertainty_and_no_manufactured_outcome(
        self, trace: DiscoveryTrace
    ) -> None:
        env = ReplayEnv(trace, unexplored_candidates=("never-explored",))
        result = env.run(CONTROL_POLICY, seed=99)
        counterfactual = [
            d
            for d in result.decisions
            if d.outcome_kind == OutcomeKind.COUNTERFACTUAL_UNCERTAIN
        ]
        assert counterfactual
        for decision in counterfactual:
            assert decision.observed_outcome is None
            assert decision.estimated_outcome is None
            assert decision.uncertain and decision.uncertainty_reason
        assert_not_prospective(result)  # valid replay output is not prospective
        from dataclasses import replace

        from algolab.meta_search.replay import ReplayResult

        forged = ReplayResult(
            trace_id="x",
            policy_id="x",
            decisions=[
                replace(counterfactual[0], outcome_kind=OutcomeKind.PROSPECTIVE)
            ],
        )
        with pytest.raises(ValueError):
            assert_not_prospective(forged)

    def test_replay_cannot_be_prospective(self, trace: DiscoveryTrace) -> None:
        artifact = ReplayEnv(trace).deterministic_artifact(BASELINE_POLICY)
        assert artifact["is_prospective_evidence"] is False
        assert artifact["limitations"]
        assert (
            ReplayEnv(trace).run(BASELINE_POLICY).to_dict()["evidence_class"]
            == "historical_replay"
        )


class TestPolicies:
    def test_versioning_and_structured_proposal(self) -> None:
        child = propose_policy(
            REPLAY_POLICY,
            name="test-child",
            config={"beta": 2.0},
            exact_change="beta 0.75 -> 2.0",
            rationale="commit harder to cheap methods",
            expected_effect="more discoveries per credit",
            evidence=("protocol-230-v2",),
            budget=12.0,
        )
        assert child.version == REPLAY_POLICY.version + 1
        assert child.parent_policy_id == REPLAY_POLICY.policy_id
        assert child.checksum() != REPLAY_POLICY.checksum()
        assert child.rollback_path and child.proposed_evaluation

    def test_deterministic_selection_and_baseline_difference(self) -> None:
        observations = (
            Observation("tune", 1.0, 0.3, True),
            Observation("refresh", 4.0, 0.3, True),
        )
        candidates = ("tune", "refresh", "validate")
        assert BASELINE_POLICY.select(
            candidates, observations, seed=1
        ) == BASELINE_POLICY.select(candidates, observations, seed=2)
        assert REPLAY_POLICY.select(candidates, observations, seed=1).method == "tune"
        assert CONTROL_POLICY.select(candidates, (), seed=5) == CONTROL_POLICY.select(
            candidates, (), seed=5
        )

    def test_invalid_policy_rejected(self) -> None:
        with pytest.raises(ValueError):
            propose_policy(
                BASELINE_POLICY, name="bad", config={}, exact_change="", rationale=""
            )


class TestPromotion:
    def test_historical_replay_alone_cannot_promote(
        self, trace: DiscoveryTrace
    ) -> None:
        evaluation = evaluate_policy(
            EVOLVED_POLICY,
            BASELINE_POLICY,
            replay_env=ReplayEnv(trace),
            trials=3,
            episodes=6,
            bootstrap_iterations=200,
        )
        decision = promote(EVOLVED_POLICY, BASELINE_POLICY, evaluation)
        assert decision.status != PromotionStatus.PROMOTED
        assert evaluation["stage_a"]["decision_quality_agreement"] >= 0.0
        # Even a perfect replay score with no prospective evidence fails closed.
        replay_only = dict(evaluation)
        replay_only["stage_b"] = dict(evaluation["stage_b"])
        replay_only["stage_b"]["is_prospective_evidence"] = False
        replay_only["stage_a"] = dict(evaluation["stage_a"])
        replay_only["stage_a"]["decision_quality_agreement"] = 1.0
        assert (
            promote(EVOLVED_POLICY, BASELINE_POLICY, replay_only).status
            != PromotionStatus.PROMOTED
        )

    def test_missing_stage_fails_closed(self) -> None:
        decision = promote(EVOLVED_POLICY, BASELINE_POLICY, {"stage_a": {}})
        assert decision.status == PromotionStatus.REJECTED_INCOMPLETE

    def test_prospective_failure_rejected(self) -> None:
        evaluation = {
            "stage_a": {"x": 1},
            "stage_b": {
                "is_prospective_evidence": True,
                "primary": {"delta": -1.0, "ci_low": -2.0, "p_value": 0.9},
                "secondary": {"ci_low": -1.0},
            },
            "stage_c": {
                "is_prospective_evidence": True,
                "primary": {"delta": 1.0, "ci_low": 0.1},
            },
        }
        decision = promote(EVOLVED_POLICY, BASELINE_POLICY, evaluation)
        assert decision.status in (
            PromotionStatus.REJECTED_PROSPECTIVE,
            PromotionStatus.REJECTED_INDEPENDENT,
        )
        assert decision.checksum()

    def test_replay_evaluation_reports_limits(self, trace: DiscoveryTrace) -> None:
        metrics = replay_evaluation(ReplayEnv(trace), REPLAY_POLICY)
        assert metrics["is_prospective_evidence"] is False
        assert metrics["replay_limitations"]


class TestPilotAndVerification:
    @pytest.fixture(scope="class")
    def bundle(self, tmp_path_factory: pytest.TempPathFactory) -> Path:
        path = tmp_path_factory.mktemp("meta") / "protocol-241-v1"
        run_pilot(path, trials=3, episodes=6, bootstrap_iterations=200)
        return path

    def test_bundle_is_deterministic_and_verifies(self, bundle: Path) -> None:
        verdict = verify_pilot(bundle)
        assert verdict["verified"] is True
        assert verdict["n_files_verified"] > 5
        assert verdict["trace_integrity"] is True
        first = (bundle / "checksums.json").read_bytes()
        run_pilot(bundle, trials=3, episodes=6, bootstrap_iterations=200)
        assert (bundle / "checksums.json").read_bytes() == first

    def test_tampered_artifact_detected(self, bundle: Path) -> None:
        report = bundle / "report.md"
        original = report.read_text()
        report.write_text(original + "\nTAMPERED\n")
        verdict = verify_pilot(bundle)
        assert verdict["verified"] is False
        assert "report.md" in verdict["mismatches"]
        report.write_text(original)

    def test_corrupted_trace_detected(self, bundle: Path, tmp_path: Path) -> None:
        copy = tmp_path / "bundle-copy"
        copy.mkdir()
        for path in bundle.rglob("*"):
            if path.is_file():
                dest = copy / path.relative_to(bundle)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(path.read_bytes())
        trace_path = copy / "trace.json"
        raw = json.loads(trace_path.read_text())
        raw["nodes"][1]["observation"]["discovery"] = True
        trace_path.write_text(json.dumps(raw))
        verdict = verify_pilot(copy)
        assert verdict["verified"] is False

    def test_training_trace_is_labelled_synthetic(self, bundle: Path) -> None:
        manifest = json.loads((bundle / "manifest.json").read_text())
        assert manifest["trace_kind"] == "synthetic_pilot_trace"
        assert manifest["trace_is_prospective_evidence"] is False
        assert build_pilot_trace().verify_integrity()
