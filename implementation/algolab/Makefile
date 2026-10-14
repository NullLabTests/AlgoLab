.PHONY: setup lint type test test-slow test-full all clean

PYTHON ?= .venv/bin/python

setup:
	bash scripts/setup.sh

lint:
	$(PYTHON) -m ruff check src tests scripts

type:
	$(PYTHON) -m mypy

# Fast lane: everything except tests marked @pytest.mark.slow.
test:
	$(PYTHON) -m pytest -m "not slow"

# Slow lane. No tests are marked @slow today, so pytest collects nothing and
# exits 5 (a hard failure, not a silent pass). Mark a test @slow to use this.
test-slow:
	$(PYTHON) -m pytest -m "slow"

# Entire suite regardless of marker (currently identical to `test`).
test-full:
	$(PYTHON) -m pytest

all: lint type test

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
