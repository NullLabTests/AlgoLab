"""AlgoLab CLI (M0): database initialization and manifest validation.

Usage:
    algolab init-db [--config PATH]
    algolab validate-manifest --type hypothesis|candidate|experiment --file PATH
    algolab budget-state [--config PATH]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from algolab.control.budget import BudgetLedger
from algolab.control.config import AlgolabConfig, load_config
from algolab.schemas import SchemaNotFound, available_types
from algolab.storage.db import check_append_only, connect
from algolab.storage.event_store import EventStore
from algolab.validation.schema_validator import (
    ManifestValidationError,
    validate_manifest,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="algolab",
        description="AlgoLab contracts layer (M0)",
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
    db_path = override_path if override_path is not None else config.storage.path
    conn = connect(db_path, initialize=True)
    check_append_only(conn)
    return conn, config


def cmd_init_db(args: argparse.Namespace) -> int:
    conn, config = _open(args.config, args.path)
    path = args.path or config.storage.path
    print(f"initialized AlgoLab database at {path} "
          f"(schema user_version={1})")
    conn.close()
    return 0


def cmd_validate_manifest(args: argparse.Namespace) -> int:
    if not args.file.exists():
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(args.file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.file}: {exc}", file=sys.stderr)
        return 2
    try:
        validate_manifest(manifest, args.schema_type)
    except SchemaNotFound as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
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


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "init-db":
        return cmd_init_db(args)
    if args.command == "validate-manifest":
        return cmd_validate_manifest(args)
    if args.command == "budget-state":
        return cmd_budget_state(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
