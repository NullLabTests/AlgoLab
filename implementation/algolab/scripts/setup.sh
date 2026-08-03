#!/usr/bin/env bash
# Reproducible local setup for AlgoLab M0.
# Creates a virtualenv and installs the package in editable mode with dev deps.
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
"$PYTHON" -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -e ".[dev]"

echo
echo "setup complete. Run:"
echo "  make lint && make type && make test"
