.PHONY: setup lint type test all clean

PYTHON ?= .venv/bin/python

setup:
	bash scripts/setup.sh

lint:
	$(PYTHON) -m ruff check src tests

type:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m pytest

all: lint type test

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
