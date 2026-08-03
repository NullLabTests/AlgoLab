# Research Method

## Hypothesis template

A valid hypothesis must state:

- Existing observation:
- Proposed mechanism:
- Intervention:
- Baseline:
- Primary metric:
- Predicted direction and minimum effect:
- Tasks and model scale:
- Confounders:
- Disconfirmation condition:
- Expected compute:
- Novelty basis:
- Ablation plan:

## Decision rules

Reject before execution when:
- the hypothesis is not falsifiable;
- no valid baseline exists;
- predicted effect is smaller than measurement noise;
- novelty cannot be distinguished from prior work;
- cost exceeds available budget;
- implementation cannot be independently validated.

Promote after screening only when:
- implementation tests pass;
- primary metric moves in predicted direction;
- no severe regression occurs;
- effect survives seed variation;
- cost estimate permits confirmation.

## Negative results

Negative results must record whether the failure is:
- theory failure;
- implementation failure;
- insufficient power;
- incompatible scale;
- benchmark limitation;
- compute limitation;
- inconclusive.

Only theory failures with validated implementation update the scientific prior
strongly.
