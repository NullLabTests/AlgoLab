# Search and Evolution

## Candidate representation

Candidates are typed graphs of components and transformations, not unstructured
prose. Each transformation names a validator.

Core mutation operators:
- replace component;
- insert component;
- remove component;
- duplicate branch;
- change objective weight;
- change optimizer or schedule;
- alter memory/routing policy;
- compose two compatible candidates;
- revert a prior mutation.

## Selection

Maintain a Pareto frontier over:
- capability;
- compute;
- latency;
- memory;
- robustness;
- reproducibility;
- novelty.

Do not collapse all objectives into one score for final promotion. A scalar
priority score may schedule experiments, but the archive retains the full vector.

## Diversity

Use lineage distance, embedding distance, and behavioral distance. Apply a
diversity floor so the population does not converge entirely on one family.

## Pseudocode

```text
population <- seed_candidates()
while budget_available:
    parents <- select_from_pareto_front(population)
    proposals <- mutate_or_recombine(parents)
    valid <- static_validate(proposals)
    ranked <- estimate_value_information_cost(valid)
    approved <- governance_filter(ranked)
    results <- staged_evaluate(approved)
    population <- update_archive(population, results)
    update_search_priors(results)
```
