# FREE CPU RUNBOOK

This sprint's contract: **zero incremental cost**. All science runs on local
CPU or a free-tier CPU Codespace; never on GPU or paid compute.

## Local (default — currently in use)

```bash
# One-time setup (already done in this repo; re-run only for a fresh clone)
cd AlgoLaB
bash scripts/setup.sh            # creates .venv + editable install
cd implementation/algolab

# Every phase gate
make lint                        # ruff     (must: All checks passed)
make type                        # mypy --strict (must: no issues)
make test                        # pytest, default = fast set (-m "not slow") < 3 min
make test-slow                   # @slow full-protocol runs, each < 10 min

# git identity for this repo must be NullLabTests
gh auth status
gh api user --jq .login          # MUST print: NullLabTests
```

CPU budget rule: if a @slow run exceeds ~10 min on 2–4 cores, abort and
shrink the grid (or, if shrinking defeats the purpose, document
UNRESOLVED-POWER instead of forcing it).

## Codespace bootstrap (only if local install is not cheap)

Local Python 3.11+ plus project deps here install cheaply, so this branch is
NOT used. Record it for reproducibility if conditions ever change:

```bash
# Reuse an existing stopped/running space if one exists
gh codespace list --repo NullLabTests/AlgoLab

# Create only if none exists; smallest CPU machine; never GPU
gh codespace create --repo NullLabTests/AlgoLab --branch main \
  --display-name algolab-great-cpu --idle-timeout 30m \
  --retention-period 24h --default-permissions

gh codespace ssh -c <CODESPACE_NAME> -- 'uname -a && nproc && python3 --version'
cd /workspaces/AlgoLab && bash scripts/setup.sh && make test && make lint && make type

# Copy results back if needed
gh codespace cp -r -e remote:/workspaces/AlgoLab/implementation/algolab/experiments/. \
  implementation/algolab/experiments/

# Never leave it running
gh codespace stop -c <CODESPACE_NAME>
```

A `.devcontainer/devcontainer.json` is created only if the Codespace branch is
used, and only CPU-oriented (no CUDA mounts, modest `hostRequirements.cpus`).

## Contract

- No GPU/TPU, no paid cloud/model APIs, no large downloads.
- `pip install` only to keep current tests green + the S2 substrate.
- Money block → cut the task, record it; never buy compute.