"""Independently compare a reproduced meta-search bundle with its sealed original.

Usage:
    python scripts/verify_meta_reproduction.py ORIGINAL REPRODUCTION [--out FILE]

The original bundle is authoritative: every path in its ``checksums.json`` is
compared byte-for-byte first, then numerically (tolerance 1e-9) for JSON files
so that last-ULP differences across interpreter/BLAS builds are reported rather
than silently accepted. Extra files in either tree are a failure. Both bundles
are passed through the independent ``verify_pilot`` re-hasher.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from algolab.meta_search.protocol_241 import verify_pilot

TOLERANCE = 1e-9


def _numeric_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) <= TOLERANCE
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            _numeric_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _numeric_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def compare(original: Path, reproduction: Path) -> dict[str, Any]:
    """Return a structured comparison verdict for two sealed bundles."""
    expected: dict[str, str] = json.loads(
        (original / "checksums.json").read_text(encoding="utf-8")
    )
    results: list[dict[str, Any]] = []
    for rel, digest in expected.items():
        source = original / rel
        target = reproduction / rel
        entry: dict[str, Any] = {"file": rel, "mode": "byte_exact", "pass": False}
        if not target.is_file():
            entry["problems"] = ["missing in reproduction"]
        elif source.read_bytes() == target.read_bytes():
            entry["pass"] = True
            entry["problems"] = []
        elif rel.endswith(".json"):
            entry["mode"] = "numeric_1e-9"
            left = json.loads(source.read_text(encoding="utf-8"))
            right = json.loads(target.read_text(encoding="utf-8"))
            if _numeric_equal(left, right):
                entry["pass"] = True
                entry["problems"] = []
            else:
                entry["problems"] = ["byte and numeric comparison both differ"]
        else:
            entry["problems"] = ["byte mismatch (non-JSON; no numeric fallback)"]
        entry["expected_sha256"] = digest
        results.append(entry)

    extra: list[str] = []
    for tree in (original, reproduction):
        for path in tree.rglob("*"):
            if (
                path.is_file()
                and path.name != "checksums.json"  # the seal itself, not sealed content
                and path.relative_to(tree).as_posix() not in expected
            ):
                extra.append(f"{tree.name}:{path.relative_to(tree).as_posix()}")

    original_verdict = verify_pilot(original)
    reproduction_verdict = verify_pilot(reproduction)
    failures = [entry["file"] for entry in results if not entry["pass"]]
    passed = (
        not failures
        and not extra
        and original_verdict["verified"]
        and reproduction_verdict["verified"]
    )
    return {
        "original": str(original),
        "reproduction": str(reproduction),
        "tolerance": TOLERANCE,
        "pass": passed,
        "files_checked": len(results),
        "failures": failures,
        "extra_files": sorted(extra),
        "original_verification": original_verdict,
        "reproduction_verification": reproduction_verdict,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("reproduction", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    verdict = compare(args.original, args.reproduction)
    payload = json.dumps(verdict, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(
        f"pass={verdict['pass']} files={verdict['files_checked']} "
        f"failures={verdict['failures']} extra={verdict['extra_files']}"
    )
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
