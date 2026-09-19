.PHONY: setup lint type test test-slow all clean

PYTHON ?= .venv/bin/python

setup:
	bash scripts/setup.sh

lint:
	$(PYTHON) -m ruff check src tests scripts

type:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m pytest -m "not slow"

test-slow:
	$(PYTHON) -m pytest -m "slow"

all: lint type test

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
