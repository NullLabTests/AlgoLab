"""AlgoLab CLI (M0 contracts + M1 execution core).

Usage:
    algolab init-db [--config PATH] [--path PATH]
    algolab validate-manifest --type hypothesis|candidate|experiment --file PATH
    algolab budget-state [--config PATH]
    algolab create-hypothesis --file PATH
    algolab create-candidate --file PATH
    algolab create-experiment --file PATH
    algolab approve-experiment EXP_ID
    algolab expand-experiment EXP_ID --key IDEMPOTENCY_KEY
    algolab list-runs [--experiment EXP] [--status S] [--json]
    algolab show-run RUN_ID [--json]
    algolab cancel-run RUN_ID
    algolab worker [--once] [--poll-interval SECONDS]
    algolab recover-runs [--json]
    algolab aggregate-experiment EXP_ID [--json]
    algolab audit-log [--entity ID] [--limit N] [--json]

Exit codes: 0 = success, 1 = business failure, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from algolab.control.budget import BudgetLedger
from algolab.control.config import AlgolabConfig, load_config
from algolab.core.models import (
    Candidate,
    Experiment,
    Hypothesis,
)
from algolab.execution.aggregation import aggregate_experiment
from algolab.execution.expansion import ExperimentExpansion
from algolab.execution.logging import configure_logging
from algolab.execution.queue import RunQueue
from algolab.execution.recovery import recover_runs
from algolab.execution.worker import Worker
from algolab.schemas import SchemaNotFound, available_types
from algolab.storage.db import SCHEMA_VERSION, check_append_only, connect
from algolab.storage.event_store import EventStore
from algolab.storage.repositories import (
    CandidateRepository,
    ExperimentRepository,
    HypothesisRepository,
)
from algolab.validation.schema_validator import (
    ManifestValidationError,
    validate_manifest,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="algolab",
        description="AlgoLab contracts + deterministic execution core (M1)",
    )
    parser.add_argument(
        "--config", type=Path, default=Path("configs/algolab.yaml"),
        help="path to algolab.yaml (default: configs/algolab.yaml)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-db", help="create/initialize the SQLite database")
    p_init.add_argument("--path", type=Path, default=None,
                        help="override database path from config")

    p_val = sub.add_parser("validate-manifest",
                           help="validate a manifest against its canonical schema")
    p_val.add_argument("--type", dest="schema_type", required=True,
                       choices=sorted(available_types()),
                       help="manifest type (hypothesis, candidate, experiment)")
    p_val.add_argument("--file", type=Path, required=True,
                       help="path to a JSON manifest file")

    p_state = sub.add_parser("budget-state", help="show budget ledger position")
    p_state.add_argument("--path", type=Path, default=None,
                         help="override database path from config")

    p_grant = sub.add_parser("budget-grant",
                             help="grant compute credits to the budget pool")
    p_grant.add_argument("--credits", type=float, required=True,
                         help="credits to grant")
    p_grant.add_argument("--cost", type=float, default=0.0,
                         help="monetary budget to grant (overrides credits)")
    p_grant.add_argument("--key", default=None,
                         help="idempotency key")

    for kind in ("hypothesis", "candidate", "experiment"):
        p_create = sub.add_parser(
            f"create-{kind}", help=f"create a {kind} entity from a JSON manifest")
        p_create.add_argument("--file", type=Path, required=True,
                              help="path to a JSON manifest")

    p_approve = sub.add_parser("approve-experiment",
                               help="approve an experiment (planned -> approved)")
    p_approve.add_argument("experiment_id", help="EXP-... id")

    p_expand = sub.add_parser("expand-experiment",
                              help="materialize runs for an approved experiment")
    p_expand.add_argument("experiment_id", help="EXP-... id")
    p_expand.add_argument("--key", dest="idempotency_key", required=True,
                          help="idempotency key (repeat calls are no-ops)")

    p_list = sub.add_parser("list-runs", help="list runs")
    p_list.add_argument("--experiment", default=None, help="filter by EXP-... id")
    p_list.add_argument("--status", default=None, help="filter by run status")
    p_list.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show-run", help="show one run")
    p_show.add_argument("run_id", help="RUN-... id")
    p_show.add_argument("--json", action="store_true")

    p_cancel = sub.add_parser("cancel-run", help="cancel a run")
    p_cancel.add_argument("run_id", help="RUN-... id")

    p_worker = sub.add_parser("worker", help="run the execution worker")
    p_worker.add_argument("--once", action="store_true",
                          help="claim and execute a single run, then exit")
    p_worker.add_argument("--poll-interval", type=float, default=5.0,
                          help="seconds between queue polls when idle")

    p_recover = sub.add_parser("recover-runs",
                               help="reconcile orphaned runs (leases, artifacts)")
    p_recover.add_argument("--json", action="store_true")

    p_agg = sub.add_parser("aggregate-experiment",
                           help="aggregate run metrics for an experiment")
    p_agg.add_argument("experiment_id", help="EXP-... id")
    p_agg.add_argument("--json", action="store_true")

    p_audit = sub.add_parser("audit-log", help="print the append-only audit log")
    p_audit.add_argument("--entity", default=None, help="filter by entity id")
    p_audit.add_argument("--limit", type=int, default=100)
    p_audit.add_argument("--json", action="store_true")

    return parser


def _open(
    config_path: Path, override_path: Path | None = None
) -> tuple[sqlite3.Connection, AlgolabConfig]:
    if override_path is not None:
        # --path overrides configuration entirely (no config file required).
        from algolab.control.config import default_config

        config = default_config()
    else:
        config = load_config(config_path)
    # Relative storage paths are resolved against the current directory so
    # workers, adapters, and recovery all agree on absolute artifact paths.
    from algolab.control.config import StorageConfig

    if not config.storage.path.is_absolute() \
            or not config.storage.artifacts_dir.is_absolute():
        config = config.model_copy(update={"storage": StorageConfig(
            path=config.storage.path.resolve(),
            artifacts_dir=config.storage.artifacts_dir.resolve(),
        )})
    db_path = override_path if override_path is not None else config.storage.path
    conn = connect(db_path, initialize=True)
    check_append_only(conn)
    return conn, config


def _error(message: str, code: int = 1) -> int:
    print(f"error: {message}", file=sys.stderr)
    return code


def _emit(payload: Any, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(payload)
    return 0


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def cmd_init_db(args: argparse.Namespace) -> int:
    conn, config = _open(args.config, args.path)
    path = args.path or config.storage.path
    print(f"initialized AlgoLab database at {path} "
          f"(schema user_version={SCHEMA_VERSION})")
    conn.close()
    return 0


def cmd_validate_manifest(args: argparse.Namespace) -> int:
    if not args.file.exists():
        return _error(f"file not found: {args.file}", 2)
    try:
        manifest = json.loads(args.file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _error(f"invalid JSON in {args.file}: {exc}", 2)
    try:
        validate_manifest(manifest, args.schema_type)
    except SchemaNotFound as exc:
        return _error(str(exc), 2)
    except ManifestValidationError as exc:
        print(f"invalid {args.schema_type} manifest: {exc}", file=sys.stderr)
        for error in exc.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"OK: {args.file} is a valid {args.schema_type} manifest")
    return 0


def cmd_budget_state(args: argparse.Namespace) -> int:
    conn, config = _open(args.config, args.path)
    ledger = BudgetLedger(conn, producer=config.producer)
    balance = ledger.balance()
    print("budget ledger:")
    for key, value in balance.items():
        print(f"  {key}: {value}")
    events = EventStore(conn).count()
    print(f"  audit events: {events}")
    conn.close()
    return 0


def cmd_budget_grant(args: argparse.Namespace) -> int:
    conn, config = _open(args.config)
    try:
        with conn:
            BudgetLedger(conn, producer=config.producer).grant(
                args.credits, cost=args.cost, key=args.key)
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc))
    print(f"granted {args.credits} credits (cost {args.cost})")
    conn.close()
    return 0


def cmd_create(args: argparse.Namespace, entity_type: str) -> int:
    try:
        manifest = _load_manifest(args.file)
        validate_manifest(manifest, entity_type)
    except ValueError as exc:
        return _error(str(exc))
    conn, config = _open(args.config)
    constructors: dict[str, Any] = {
        "hypothesis": Hypothesis.model_validate,
        "candidate": Candidate.model_validate,
        "experiment": Experiment.model_validate,
    }
    repo_classes: dict[str, Any] = {
        "hypothesis": HypothesisRepository,
        "candidate": CandidateRepository,
        "experiment": ExperimentRepository,
    }
    try:
        with conn:
            entity = constructors[entity_type](manifest)
            entity_id = repo_classes[entity_type](
                conn, producer=config.producer).create(entity)
    except Exception as exc:  # noqa: BLE001 - report cleanly
        return _error(str(exc))
    print(f"created {entity_type} {entity_id}")
    return 0


def cmd_approve_experiment(args: argparse.Namespace) -> int:
    conn, config = _open(args.config)
    try:
        with conn:
            ExperimentRepository(conn, producer=config.producer).transition(
                args.experiment_id, "approved")
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc))
    print(f"approved {args.experiment_id}")
    return 0


def cmd_expand_experiment(args: argparse.Namespace) -> int:
    conn, config = _open(args.config)
    try:
        result = ExperimentExpansion(conn, config).expand(
            args.experiment_id, args.idempotency_key)
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc))
    print(f"expanded {args.experiment_id}: {result.created} created, "
          f"{result.existing} existing")
    for run_id in result.run_ids:
        print(f"  {run_id}")
    return 0


def cmd_list_runs(args: argparse.Namespace) -> int:
    conn, config = _open(args.config)
    from algolab.storage.run_repository import RunRepository

    runs = RunRepository(conn, producer=config.producer).list_runs(
        experiment_id=args.experiment, status=args.status)
    if args.json:
        return _emit([_run_dict(r) for r in runs], True)
    if not runs:
        print("no runs")
        return 0
    print(f"{'RUN ID':<22} {'EXP':<22} {'CAND':<22} {'BASELINE':<8} "
          f"{'SEED':<6} {'STATUS':<10} {'CREDITS':<8}")
    for r in runs:
        print(f"{r.run_id:<22} {r.experiment_id:<22} "
              f"{(r.candidate_id or '-'):<22} {str(r.is_baseline):<8} "
              f"{r.seed:<6} {r.status:<10} {r.credits_charged:<8.4f}")
    return 0


def _run_dict(run: Any) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "experiment_id": run.experiment_id,
        "candidate_id": run.candidate_id,
        "is_baseline": run.is_baseline,
        "seed": run.seed,
        "workload": run.workload,
        "status": run.status,
        "attempt_number": run.attempt_number,
        "max_attempts": run.max_attempts,
        "worker_id": run.worker_id,
        "credits_reserved": run.credits_reserved,
        "credits_charged": run.credits_charged,
        "cost_charged": run.cost_charged,
        "error_code": run.error_code,
        "artifact_dir": run.artifact_dir,
        "metrics": run.metrics,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


def cmd_show_run(args: argparse.Namespace) -> int:
    conn, config = _open(args.config)
    from algolab.storage.run_repository import RunNotFound, RunRepository

    try:
        run = RunRepository(conn, producer=config.producer).get(args.run_id)
    except RunNotFound as exc:
        return _error(str(exc))
    if args.json:
        return _emit(_run_dict(run), True)
    print(f"run_id:      {run.run_id}")
    print(f"experiment:  {run.experiment_id}")
    print(f"candidate:   {run.candidate_id or '-'}")
    print(f"is_baseline: {run.is_baseline}")
    print(f"seed:        {run.seed}")
    print(f"workload:    {run.workload}")
    print(f"status:      {run.status}")
    print(f"attempts:    {run.attempt_number}/{run.max_attempts}")
    print(f"worker:      {run.worker_id or '-'}")
    print(f"error_code:  {run.error_code or '-'}")
    print(f"credits:     reserved={run.credits_reserved} "
          f"charged={run.credits_charged}")
    print(f"artifacts:   {run.artifact_dir or '-'}")
    print("config:")
    for key, value in run.config.items():
        print(f"  {key}: {value}")
    return 0


def cmd_cancel_run(args: argparse.Namespace) -> int:
    conn, config = _open(args.config)
    try:
        status = RunQueue(conn, config).cancel(args.run_id)
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc))
    print(f"cancelled {args.run_id} (status now {status})")
    return 0


def cmd_worker(args: argparse.Namespace) -> int:
    conn, config = _open(args.config)
    configure_logging()
    worker = Worker(conn, config)
    if args.once:
        worker.run_once()
    else:
        worker.run_loop(args.poll_interval)
    conn.close()
    return 0


def cmd_recover_runs(args: argparse.Namespace) -> int:
    conn, config = _open(args.config)
    try:
        report = recover_runs(conn, config)
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc))
    return _emit(report.to_dict(), args.json)


def cmd_aggregate_experiment(args: argparse.Namespace) -> int:
    conn, config = _open(args.config)
    try:
        report = aggregate_experiment(conn, args.experiment_id)
    except Exception as exc:  # noqa: BLE001
        return _error(str(exc))
    return _emit(report, args.json)


def cmd_audit_log(args: argparse.Namespace) -> int:
    conn, config = _open(args.config)
    store = EventStore(conn)
    if args.entity is not None:
        events = store.list_for_entity(args.entity)
    else:
        events = store.list_all(limit=args.limit)
    if args.json:
        return _emit([e.model_dump(mode="json") for e in events], True)
    if not events:
        print("no events")
        return 0
    for event in events:
        transition = ""
        if event.old_state or event.new_state:
            transition = f" {event.old_state} -> {event.new_state}"
        print(f"{event.created_at} {event.event_id} {event.entity_type} "
              f"{event.entity_id} {event.mutation}{transition} "
              f"producer={event.producer}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = args.command
    if command == "init-db":
        return cmd_init_db(args)
    if command == "validate-manifest":
        return cmd_validate_manifest(args)
    if command == "budget-state":
        return cmd_budget_state(args)
    if command == "budget-grant":
        return cmd_budget_grant(args)
    if command in ("create-hypothesis", "create-candidate", "create-experiment"):
        return cmd_create(args, command.split("-", 1)[1])
    if command == "approve-experiment":
        return cmd_approve_experiment(args)
    if command == "expand-experiment":
        return cmd_expand_experiment(args)
    if command == "list-runs":
        return cmd_list_runs(args)
    if command == "show-run":
        return cmd_show_run(args)
    if command == "cancel-run":
        return cmd_cancel_run(args)
    if command == "worker":
        return cmd_worker(args)
    if command == "recover-runs":
        return cmd_recover_runs(args)
    if command == "aggregate-experiment":
        return cmd_aggregate_experiment(args)
    if command == "audit-log":
        return cmd_audit_log(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
