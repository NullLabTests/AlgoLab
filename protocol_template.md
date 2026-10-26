# Protocol Template

Copy this template to create a new pre-registered protocol in `spec/research/`.

## Protocol: [NUMBER] - [TITLE]

**Status:** Pre-registered (not yet executed)  
**Date:** [YYYY-MM-DD]  
**Authors:** [names]

## Question

[Clear research question in one sentence]

## Hypotheses

### H1: [Primary hypothesis]
**Falsifiable statement:** "On substrate [X], at n=[Y], [treatment] will [effect] compared to [control] on [metric] with margin [M]."

**Disconfirmation:** [Specific condition that would falsify]

### H2: [Secondary hypotheses...] (if any)

## Substrate

- **Name:** [workload identifier]
- **Type:** [toy/hpo/transform/custom]
- **Datasets/Families:** [list all families, mark held-out]
- **Description:** [brief description]

## Experimental Design

### Treatments
| Arm | Description | Pre-registered? |
|---|---|---|
| control | [baseline description] | Yes |
| treatment1 | [description] | Yes |
| ... | ... | Yes |

### Parameters
- **Trials:** [number]
- **Episodes per trial:** [number]
- **Prior attempts per family:** [number]
- **Budget credits:** [number]
- **Seeds:** [base seeds]
- **Promotion threshold:** [margin]

### Controls
- [List confounds and controls]

## Metrics

### Primary Metric
**[metric_name]** - [definition]

### Secondary Metrics
- [list]

## Promotion Criteria
- [ ] Effect observed on >= [N] families
- [ ] Adjusted p-value < [threshold] (with FDR correction)
- [ ] Confidence interval excludes zero
- [ ] Direction persists on held-out family (if applicable)
- [ ] Effect meets pre-registered minimum margin

## Analysis Plan
- Statistical tests: [specify]
- Multiple comparison correction: [Benjamini-Hochberg / etc.]
- Power analysis: [if applicable]
- Robustness checks: [planned]

## Implementation Requirements
- [ ] Workload module created: `src/algolab/search/workload_[name].py`
- [ ] Registered in `search/harness.py`
- [ ] Tests added
- [ ] CLI support (if needed)

## Risks and Limitations
- [Known limitations]

## References
- [Related protocols/specs]
