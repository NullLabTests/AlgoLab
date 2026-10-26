# Contributing to AlgoLab

Thank you for your interest in contributing to AlgoLab! This project aims to be a rigorous, reproducible platform for algorithm discovery research. We welcome contributions from researchers, engineers, and anyone interested in systematic AI research.

## Getting Started

1. Read the [Master Specification](MASTER_SPEC.md) to understand the design philosophy
2. Read the [AlgoLab execution core README](implementation/algolab/README.md)
3. Set up your development environment:
   ```bash
   cd implementation/algolab
   bash scripts/setup.sh
   ```

## Development Workflow

### Running Tests

```bash
cd implementation/algolab
make lint      # ruff linting
make type      # mypy type checking (strict)
make test      # fast test suite
make test-full # all tests
```

### Adding a New Research Protocol

See [Contributing a Protocol](implementation/algolab/CONTRIBUTING.md) for detailed instructions on adding pre-registered experiments.

Key requirements:
- **Pre-register before running** - Spec must be committed before execution
- **Follow the scientific method** - Include falsifiable hypotheses, baselines, promotion criteria
- **Maintain provenance** - All artifacts must be checksummed and reproducible
- **CPU-only by default** - Use only built-in datasets, no paid APIs/GPU requirements

## Code Style

- Python 3.11+ with type hints
- Follow existing codebase patterns
- All code must pass `ruff` and `mypy --strict`
- Write tests for new functionality
- Keep changes focused and well-documented

## Pull Requests

1. Fork the repository and create a feature branch
2. Make your changes with clear, descriptive commits
3. Ensure all tests pass and linting is clean
4. Update relevant documentation
5. Submit a PR with a clear description of the changes and rationale

## Research Contributions

If you're adding a new protocol or substrate:
1. Write a pre-registered spec in `spec/research/`
2. Implement the workload following existing patterns
3. Add tests
4. Run and seal the experiment with checksums
5. Document results honestly (including negative results)

## Questions?

- Check the [documentation](docs/) for more details
- Look at existing protocols (230-239) as examples
- Review [STATUS.md](docs/STATUS.md) for current state

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
