# Core Ontology

## Relations

- A hypothesis `motivates` one or more candidates.
- A candidate `descends_from` zero or more parent candidates.
- An experiment `tests` one or more hypotheses.
- A run `instantiates` one experiment configuration.
- A result `is_output_of` one run.
- A discovery `is_supported_by` results.
- A report `makes_claims_about` discoveries or negative results.
- Every claim `is_backed_by` explicit result IDs.

## Invariants

1. No result exists without a run.
2. No run exists without an approved experiment.
3. No experiment exists without a falsifiable hypothesis or baseline-validation purpose.
4. No discovery exists without replication evidence.
5. No report claim exists without evidence links.
6. No entity may overwrite its provenance.
