#!/usr/bin/env python3
"""Independent reproduction verifier for a sealed AlgoLab experiment bundle.

Given a bundle directory (e.g. ``experiments/protocol-230-v1``), this script:

1. verifies every recorded SHA-256 in ``checksums.json`` against the bytes at
   rest (integrity);
2. reconstructs the experiment configuration **from the committed manifest**,
   not from code defaults, so the run is defined by the evidence rather than by
   whatever the current defaults happen to be;
3. re-executes the experiment in a *separate process* with a fresh temporary
   database and artifact directory (no shared state with the original run);
4. compares the regenerated artifacts to the committed ones:
   - ``report.md`` is compared **byte-for-byte**;
   - raw attempt streams (``conditions/**/*.jsonl``) are compared *portably*:
     discrete fields (trial, family, operator, validity, discovery, cost, ...)
     must match exactly, while the three cross-validation effect fields may
     differ by at most two validation samples (see :data:`RAW_EFFECT_TOL`).
     Byte-exact identity is still recorded per file in ``byte_exact``, but it
     is host-specific: the same pinned scikit-learn can flip one CV sample on
     a different CPU/BLAS kernel without changing any decision;
   - derived JSON is compared **numerically** at 1e-9 relative/absolute
     (bootstrap/BLAS last-digit differences; defect D-10);
   - ``manifest.json`` / ``plan.json`` are compared field-by-field with
     wall-clock fields excluded (``created_at``, ``measured_operator_seconds``,
     ``evaluation_seconds`` — recorded but never read by any decision), the
     interpreter version excluded as provenance (``python_version``; the
     portable raw-stream comparison still detects any decision change), and a
     small, justified allow-list of *additive* metadata fields accepted (see
     :data:`ADDITIVE_FIELDS`). Every excluded field is listed in the verdict,
     so the exclusion is auditable rather than silent. Numerical library
     versions (``numpy_version``, ``sklearn_version``) remain compared: they
     have changed raw results in practice and are therefore decision-relevant.
5. writes ``<bundle>/reproduction-verification.json`` (or ``--out``) with the
   per-file verdicts and exits non-zero on any failure.

Usage
-----
    python scripts/verify_bundle.py experiments/protocol-230-v1
    python scripts/verify_bundle.py experiments/protocol-240-v1 --keep
    python scripts/verify_bundle.py experiments/protocol-240-v1 --out /tmp/r.json

The verifier never writes into the bundle directory except for the optional
verdict file (which is excluded from checksums by the harness convention).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"

BYTE_EXACT_FILES = ("report.md",)
#: Fields that legitimately differ between two runs of the same experiment.
#: Stripping is by key name at any depth, so nothing about a record's structure
#: is hidden. ``created_at`` is a wall-clock timestamp; every ``*_seconds``
#: field is a measured wall-clock duration. Both are *recorded but never read*:
#: no search decision, no statistic, and no artifact value depends on them
#: (protocol 240 §8 states this contract explicitly). ``python_version`` is
#: interpreter provenance: the same pinned numerical libraries produce the same
#: byte-exact raw streams on Python 3.11/3.12/3.14, so comparing the interpreter
#: string alone would reject an otherwise exact reproduction. Attempt counts,
#: credit totals, seeds, library versions, and every derived statistic are still
#: compared.
VOLATILE_FIELDS = ("created_at", "measured_operator_seconds",
                   "evaluation_seconds", "python_version")
#: Committed-field additions the verifier accepts without treating the bundle
#: as unreproduced. Each entry must name *why* the extra field cannot change an
#: outcome; a field is never allowed merely because it is convenient. The
#: committed evidence must still reproduce exactly, and any value that differs
#: for a shared field is still a failure.
ADDITIVE_FIELDS: dict[str, str] = {
    "manifest.json.workload": (
        "workload key added to the manifest when multiple substrates were "
        "registered; it records which substrate a run already used by "
        "construction and does not alter any recorded result"),
    "plan.json.workload": (
        "same additive workload key, mirrored into the run plan"),
}
REL_TOL = 1e-9
ABS_TOL = 1e-9
#: Effect fields whose cross-validation values can differ by a couple of
#: validation samples across CPU/BLAS kernels even with identical libraries.
#: The smallest CV fold in the compose workload is the wine family
#: (178 rows / 5 folds ~= 35), so two samples are ~= 0.057. ``discovery`` is
#: compared exactly, so a tolerance that crossed the 0.005 discovery gate
#: would still be reported as a failure.
RAW_EFFECT_FIELDS = ("effect_1", "effect_2", "mean_effect")
RAW_EFFECT_TOL = 0.06


class VerificationError(RuntimeError):
    """The bundle could not be verified (structural problem, not a mismatch)."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_checksums(bundle: Path) -> dict[str, Any]:
    """Verify every recorded digest against the bytes at rest."""
    checksum_path = bundle / "checksums.json"
    if not checksum_path.is_file():
        raise VerificationError(f"no checksums.json in {bundle}")
    recorded = json.loads(checksum_path.read_text())
    problems: list[str] = []
    for rel, digest in sorted(recorded.items()):
        target = bundle / rel
        if not target.is_file():
            problems.append(f"MISSING {rel}")
        elif sha256_file(target) != digest:
            problems.append(f"MISMATCH {rel}")
    return {
        "check": "checksums_at_rest",
        "files": len(recorded),
        "problems": problems,
        "pass": not problems,
    }


def _strip_volatile(value: Any, excluded: list[str] | None = None,
                    path: str = "") -> Any:
    """Remove :data:`VOLATILE_FIELDS` at any depth.

    Keys actually removed are appended to ``excluded`` (dotted paths) so the
    verdict records exactly what was not compared, rather than silently
    ignoring it.
    """
    out_keys = excluded if excluded is not None else []
    if isinstance(value, dict):
        kept: dict[str, Any] = {}
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if key in VOLATILE_FIELDS:
                out_keys.append(child)
                continue
            kept[key] = _strip_volatile(item, excluded, child)
        return kept
    if isinstance(value, list):
        return [_strip_volatile(v, excluded, f"{path}[{i}]")
                for i, v in enumerate(value)]
    return value


def compare_values(committed: Any, regenerated: Any,
                   path: str = "",
                   *,
                   allowed_additions: list[str] | None = None) -> list[str]:
    """Numeric-tolerant deep comparison; returns a list of differences.

    A key present only in the regenerated run is either a failure or, when its
    dotted path is listed in :data:`ADDITIVE_FIELDS`, recorded in
    ``allowed_additions`` and otherwise ignored. A key missing from the
    regenerated run is always a failure: the run must reproduce every piece of
    evidence that was sealed.
    """
    additions = allowed_additions if allowed_additions is not None else []
    problems: list[str] = []
    if isinstance(committed, bool) != isinstance(regenerated, bool):
        # ``True == 1`` in Python; a JSON type change is still a schema change
        # and must not be silently accepted as an equal value.
        problems.append(f"{path}: type changed between bool and non-bool")
    elif isinstance(committed, bool):
        if committed != regenerated:
            problems.append(f"{path}: {committed!r} != {regenerated!r}")
    elif isinstance(committed, (int, float)) and isinstance(regenerated, (int, float)):
        if not math.isclose(committed, regenerated,
                            rel_tol=REL_TOL, abs_tol=ABS_TOL):
            problems.append(f"{path}: {committed!r} != {regenerated!r}")
    elif isinstance(committed, dict) and isinstance(regenerated, dict):
        for key in sorted(set(committed) | set(regenerated)):
            child = f"{path}.{key}" if path else key
            if key not in committed:
                if child in ADDITIVE_FIELDS:
                    additions.append(child)
                else:
                    problems.append(f"{child}: unexpected in regenerated run")
            elif key not in regenerated:
                problems.append(f"{child}: missing from regenerated run")
            else:
                problems.extend(compare_values(
                    committed[key], regenerated[key], child,
                    allowed_additions=additions))
    elif isinstance(committed, list) and isinstance(regenerated, list):
        if len(committed) != len(regenerated):
            problems.append(
                f"{path}: length {len(committed)} != {len(regenerated)}")
        else:
            for i, (a, b) in enumerate(zip(committed, regenerated, strict=True)):
                problems.extend(compare_values(
                    a, b, f"{path}[{i}]", allowed_additions=additions))
    elif committed != regenerated:
        problems.append(f"{path}: {committed!r} != {regenerated!r}")
    return problems


def _recorded_operators(manifest: dict[str, Any]) -> tuple[str, ...]:
    """Operator fingerprint from a manifest, across both manifest eras.

    Newer manifests record an ``operators`` list. Bundles sealed before that
    field existed still record the oracle ``ground_truth`` for toy workloads,
    whose per-family keys are exactly the operator set, so both are accepted.
    """
    ops = manifest.get("operators")
    if ops:
        return tuple(ops)
    ground_truth = manifest.get("ground_truth") or {}
    for family in sorted(ground_truth):
        return tuple(sorted(ground_truth[family]))
    return ()


def infer_workload(manifest: dict[str, Any]) -> str:
    """Recover the workload a historical bundle ran on.

    Manifests written before the ``workload`` field existed (protocols 230-234)
    do not name their workload, so the default cannot simply be assumed. The
    workload is instead identified by the substrate fingerprint recorded in the
    manifest: ``(environment_version, task_suite_version, held_out_family,
    operators)``. The operator list is what distinguishes workloads sharing a
    version triple (``toy`` and ``hpo`` both report 1.1.0/1.1.0/gamma). The
    recovery fails loudly if a bundle matches nothing or more than one workload.
    """
    explicit = manifest.get("workload")
    if explicit:
        return str(explicit)
    from algolab.search.harness import WORKLOAD_NAMES, resolve_workload

    identity = (
        manifest.get("environment_version"),
        manifest.get("task_suite_version"),
        manifest.get("held_out_family"),
        _recorded_operators(manifest),
    )
    matches: list[str] = []
    for key in WORKLOAD_NAMES:
        view = resolve_workload(key)
        if (view.environment_version, view.task_suite_version,
                view.held_out_family) != identity[:3]:
            continue
        if frozenset(view.operators) != frozenset(identity[3]):
            continue
        matches.append(key)
    if len(matches) != 1:
        raise VerificationError(
            "cannot infer workload from manifest identity "
            f"{identity!r}: matches {matches}. This bundle predates the "
            "explicit 'workload' field; the verifier refuses to guess.")
    return matches[0]


def reconstruct_cli_args(manifest: dict[str, Any], out_dir: Path,
                         db_path: Path) -> list[str]:
    """Build the CLI invocation that re-executes the committed manifest."""
    arms = ",".join(manifest["arms"])
    args = [
        sys.executable, "-m", "algolab.cli.main", "search-run",
        str(manifest["experiment_id"]),
        "--workload", infer_workload(manifest),
        "--dir", str(out_dir),
        "--path", str(db_path),
        "--trials", str(manifest["trials"]),
        "--episodes", str(manifest["episodes_per_trial"]),
        "--prior-attempts", str(manifest["prior_attempts_per_family"]),
        "--budget", str(manifest["budget_credits"]),
        "--prior-seed", str(manifest["prior_seed"]),
        "--analysis-seed", str(manifest["analysis_seed"]),
        "--seed-base", str(manifest["seed_base"]),
        "--top-k", str(manifest["top_k"]),
        "--arms", arms,
        "--force",
    ]
    return args


def reexecute(manifest: dict[str, Any], workdir: Path) -> Path:
    """Run the experiment in a fresh subprocess; return the artifact dir."""
    out_dir = workdir / "artifacts"
    db_path = workdir / "repro.sqlite"
    cmd = reconstruct_cli_args(manifest, out_dir, db_path)
    # Pin the BLAS kernel and thread count. The sealed bundle was produced on
    # an AVX2 host; on AVX512 CI hosts OpenBLAS can take a different PCA/SVD
    # path and return different (but otherwise deterministic) effect values
    # for identical operator programs. Forcing the Haswell kernel keeps the
    # byte-exact raw streams host-independent without changing any historical
    # artifact or relaxing a scientific comparison.
    env = {
        "PYTHONPATH": str(SRC),
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "OPENBLAS_CORETYPE": "Haswell",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        cmd, cwd=str(REPO_ROOT), env=env,
        capture_output=True, text=True)
    if result.returncode != 0:
        raise VerificationError(
            "re-execution failed\nSTDOUT:\n"
            f"{result.stdout}\nSTDERR:\n{result.stderr}")
    if not (out_dir / "statistics.json").is_file():
        raise VerificationError(f"re-execution produced no statistics in {out_dir}")
    return out_dir


def _stream_differences(committed: Path, regenerated: Path,
                        limit: int = 5) -> list[str]:
    """Explain a byte-exact JSONL mismatch at field level.

    A byte difference may be only a last-digit floating-point change caused by
    BLAS/CPU dispatch. Reporting the differing fields (rather than just
    ``bytes differ``) makes that distinction auditable in the verdict.
    """
    old_lines = committed.read_text().splitlines()
    new_lines = regenerated.read_text().splitlines()
    if len(old_lines) != len(new_lines):
        return [f"line count {len(old_lines)} != {len(new_lines)}"]
    problems: list[str] = []
    for number, (old_line, new_line) in enumerate(
            zip(old_lines, new_lines, strict=True), start=1):
        try:
            old_record = json.loads(old_line)
            new_record = json.loads(new_line)
        except json.JSONDecodeError:
            if old_line != new_line:
                problems.append(f"line {number}: non-JSON bytes differ")
        else:
            problems.extend(f"line {number}:{problem}" for problem in
                            compare_values(old_record, new_record))
        if len(problems) >= limit:
            break
    return problems[:limit]


def compare_raw_stream(committed: Path, regenerated: Path,
                       limit: int = 20) -> list[str]:
    """Portable JSONL comparison: exact decisions, sample-tolerant effects."""
    old_lines = committed.read_text().splitlines()
    new_lines = regenerated.read_text().splitlines()
    if len(old_lines) != len(new_lines):
        return [f"line count {len(old_lines)} != {len(new_lines)}"]
    problems: list[str] = []
    for number, (old_line, new_line) in enumerate(
            zip(old_lines, new_lines, strict=True), start=1):
        try:
            old_record = json.loads(old_line)
            new_record = json.loads(new_line)
        except json.JSONDecodeError:
            if old_line != new_line:
                problems.append(f"line {number}: non-JSON bytes differ")
            continue
        if not isinstance(old_record, dict) or not isinstance(new_record, dict):
            if old_record != new_record:
                problems.append(f"line {number}: record type changed")
            continue
        for key in sorted(set(old_record) | set(new_record)):
            child = f"line {number}:{key}"
            if key not in old_record or key not in new_record:
                problems.append(f"{child}: field missing from one run")
                continue
            old_value, new_value = old_record[key], new_record[key]
            if key in RAW_EFFECT_FIELDS and isinstance(
                    old_value, (int, float)) and isinstance(
                    new_value, (int, float)) and not isinstance(
                    old_value, bool) and not isinstance(new_value, bool):
                if not math.isclose(old_value, new_value,
                                    rel_tol=0.0, abs_tol=RAW_EFFECT_TOL):
                    problems.append(
                        f"{child}: {old_value!r} != {new_value!r} "
                        f"(tol {RAW_EFFECT_TOL})")
            else:
                problems.extend(f"line {number}:{problem}" for problem in
                                compare_values(old_value, new_value, key))
        if len(problems) >= limit:
            break
    return problems[:limit]


def compare_bundles(committed_dir: Path, regenerated_dir: Path) -> dict[str, Any]:
    """Compare the regenerated artifacts to the committed ones."""
    results: list[dict[str, Any]] = []

    for name in BYTE_EXACT_FILES:
        a, b = committed_dir / name, regenerated_dir / name
        if not a.is_file() or not b.is_file():
            results.append({"file": name, "pass": False,
                            "problems": ["missing file"]})
            continue
        same = a.read_bytes() == b.read_bytes()
        results.append({
            "file": name, "mode": "byte_exact", "pass": same,
            "problems": [] if same else ["bytes differ"],
        })

    committed_streams = sorted(committed_dir.glob("conditions/*/*.jsonl"))
    if not committed_streams:
        results.append({"file": "conditions/**/*.jsonl", "pass": False,
                        "problems": ["no committed streams found"]})
    for stream in committed_streams:
        rel = stream.relative_to(committed_dir)
        other = regenerated_dir / rel
        if not other.is_file():
            results.append({"file": str(rel), "pass": False,
                            "problems": ["missing in regenerated run"]})
            continue
        same = stream.read_bytes() == other.read_bytes()
        problems = compare_raw_stream(stream, other)
        results.append({
            "file": str(rel),
            "mode": f"jsonl_portable_1e-9/effect_{RAW_EFFECT_TOL:g}",
            "pass": not problems,
            "byte_exact": same,
            "byte_differences": (_stream_differences(stream, other)
                                 if not same else []),
            "problems": problems,
        })

    json_files = sorted(
        p for p in committed_dir.glob("*.json")
        if p.name not in ("checksums.json", "reproducibility.json",
                          "reproduction-verification.json"))
    for path in json_files:
        other = regenerated_dir / path.name
        if not other.is_file():
            results.append({"file": path.name, "pass": False,
                            "problems": ["missing in regenerated run"]})
            continue
        excluded: list[str] = []
        committed = _strip_volatile(json.loads(path.read_text()), excluded)
        regenerated = _strip_volatile(json.loads(other.read_text()))
        additions: list[str] = []
        problems = compare_values(committed, regenerated, path.name,
                                  allowed_additions=additions)
        results.append({
            "file": path.name, "mode": "numeric_1e-9", "pass": not problems,
            "problems": problems[:20],
            "problem_count": len(problems),
            "allowed_additions": additions,
            "excluded_volatile_fields": sorted(set(excluded)),
        })

    return {
        "files_checked": len(results),
        "failures": [r for r in results if not r["pass"]],
        "results": results,
        "byte_exact": all(r.get("byte_exact", True) for r in results),
        "pass": all(r["pass"] for r in results),
    }


def verify_bundle(bundle: Path, *, keep: bool = False) -> dict[str, Any]:
    """Full verification: integrity + clean re-execution + comparison."""
    manifest_path = bundle / "manifest.json"
    if not manifest_path.is_file():
        raise VerificationError(f"no manifest.json in {bundle}")
    manifest = json.loads(manifest_path.read_text())

    integrity = verify_checksums(bundle)

    with tempfile.TemporaryDirectory(prefix="algolab-repro-") as tmp:
        workdir = Path(tmp) if keep else Path(tmp)
        regenerated = reexecute(manifest, workdir)
        comparison = compare_bundles(bundle, regenerated)
        if keep:
            kept = Path(tempfile.mkdtemp(prefix="algolab-repro-kept-"))
            import shutil

            shutil.copytree(regenerated, kept / "artifacts")
            comparison["kept_at"] = str(kept)

    verdict = {
        "bundle": str(bundle),
        "experiment_id": manifest.get("experiment_id"),
        "workload": infer_workload(manifest),
        "protocol_version": manifest.get("protocol_version"),
        "integrity": integrity,
        "reproduction": comparison,
        "pass": bool(integrity["pass"] and comparison["pass"]),
    }
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify that a sealed AlgoLab bundle re-executes.")
    parser.add_argument("bundle", type=Path,
                        help="bundle directory containing manifest.json")
    parser.add_argument("--out", type=Path, default=None,
                        help="write the verdict JSON here "
                             "(default: <bundle>/reproduction-verification.json)")
    parser.add_argument("--keep", action="store_true",
                        help="keep the regenerated artifacts for inspection")
    parser.add_argument("--quiet", action="store_true", help="verdict only")
    args = parser.parse_args(argv)

    try:
        verdict = verify_bundle(args.bundle, keep=args.keep)
    except VerificationError as exc:
        print(f"VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 2

    out = args.out or (args.bundle / "reproduction-verification.json")
    out.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n")

    if not args.quiet:
        integrity = verdict["integrity"]
        repro = verdict["reproduction"]
        print(f"bundle:      {verdict['bundle']}")
        print(f"experiment:  {verdict['experiment_id']} "
              f"({verdict['workload']}, protocol {verdict['protocol_version']})")
        print(f"integrity:   {integrity['files']} files, "
              f"{'PASS' if integrity['pass'] else 'FAIL'}")
        print(f"re-execution: {repro['files_checked']} artifacts compared, "
              f"{'PASS' if repro['pass'] else 'FAIL'} "
              f"(byte-exact: {'yes' if repro['byte_exact'] else 'no'})")
        for failure in repro["failures"]:
            print(f"  FAIL {failure['file']}: "
                  f"{failure.get('problems', [])[:3]}")
    print(f"verdict: {'REPRODUCED' if verdict['pass'] else 'NOT REPRODUCED'}")
    print(f"written: {out}")
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
