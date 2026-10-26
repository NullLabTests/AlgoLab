# Reproducibility Guide

AlgoLab is designed with reproducibility as a core requirement. This guide explains how to reproduce experiments and verify results.

## Principles

1. **Determinism** - Same code revision, config, environment, and seeds produce identical results
2. **Provenance** - Every run is tracked with full lineage (code commit, config hash, dataset hash, environment)
3. **Checksums** - All artifacts are hash-sealed and verified
4. **Pre-registration** - Protocols are frozen before execution
5. **Transparency** - Raw results are preserved, never overwritten

## Reproducing a Sealed Experiment

All completed protocols have sealed bundles in `implementation/algolab/experiments/`. To verify a bundle:

```bash
cd implementation/algolab
python -c "
from algolab.search.harness import verify_bundle
import json, sys
# Verify checksums
with open('experiments/protocol-230-v2/checksums.json') as f:
    checksums = json.load(f)
# ... verification logic
"
```

Or use the built-in verification:
```python
from pathlib import Path
from algolab.search import PolicyComparison, ExperimentConfig
# Load and verify
```

## Reproducing Protocol 230-v2 (Example)

```bash
cd implementation/algolab
.venv/bin/python -m algolab.cli.main search-run protocol-230-v2-repro \
  --workload toy \
  --dir /tmp/repro-230-v2 \
  --trials 16 --episodes 2 --prior-attempts 60 \
  --arms static,knowledge-informed,adaptive,random,cost-aware-adaptive \
  --force
```

Compare against sealed bundle in `experiments/protocol-230-v2/`.

## Environment Requirements

- Python 3.11+
- Dependencies pinned in `pyproject.toml`
- CPU-only, no network calls during tests
- sklearn built-in datasets only

## Known Reproducibility Boundaries

- Floating point operations may have tiny variations across platforms (we check to 1e-9 as noted in README)
- Results are reproducible on the same platform with same dependencies
- Some experiments note environment-specific details in their reports

## Verification Checklist

When reviewing a protocol:
- [ ] Pre-registered spec exists and is committed before bundle
- [ ] `checksums.json` verifies all artifacts
- [ ] `manifest.json` contains correct seeds, arms, parameters
- [ ] `environment.json` records dependencies and versions
- [ ] Raw results in `conditions/*/raw-results.jsonl` are present
- [ ] Statistics computed from raw data match `statistics.json`
- [ ] Report separates observation/interpretation/limitations

## Artifacts

Each sealed bundle contains:
- `manifest.json` - Experiment configuration (frozen)
- `environment.json` - Environment metadata
- `conditions/{arm}/` - Per-arm raw results and operator selections
- `knowledge-snapshot*.json` - Knowledge state at key points
- `statistics.json` - Computed statistics
- `report.md` - Human-readable report
- `checksums.json` - SHA256 hashes of all files
- `qd-archive.json` (if applicable) - Quality-diversity archive
