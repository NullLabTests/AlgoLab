# Experiment Protocol

## Required stages

1. Schema validation.
2. Dependency and security scan.
3. Unit tests.
4. Deterministic smoke test.
5. Baseline reproduction.
6. Candidate low-fidelity screen.
7. Multi-seed confirmation.
8. Ablation.
9. Clean-environment replication.
10. Final analysis.

## Cancellation rules

Cancel when:
- loss is NaN or diverges beyond configured threshold;
- wall-clock or compute cap is reached;
- baseline cannot be reproduced;
- candidate violates declared resource bounds;
- interim analysis shows futility at the configured confidence level;
- governance stop is active.

## Artifacts

Every run retains:
- resolved configuration;
- source commit and patch;
- environment lock;
- logs;
- checkpoints when required;
- raw predictions where legally and practically allowed;
- metrics JSON;
- hardware telemetry;
- result manifest.
