# AlgoLab — Project Intent

This document states the durable intent, scope, and constraints of AlgoLab.
It is deliberately short and stable. Detailed designs live in `MASTER_SPEC.md`,
`spec/`, `spec/research/`, and `planning/MILESTONES.md`; this file records *why*
the project exists and what counts as success.

## What AlgoLab is

AlgoLab is a bounded, reproducible research platform for proposing,
implementing, testing, rejecting, refining, and reporting candidate
improvements to AI systems. It encodes the scientific method as an executable
pipeline with hard compute budgets, immutable provenance, and statistical gates
that no claim may bypass.

Its objective is **not** to "invent AGI on command." It is to maximize the rate
of *valid, reproducible algorithmic discoveries per unit of compute and human
oversight* — and, where relevant, to establish honest negative results.

## Problem being addressed

Autonomous research systems routinely overclaim: they run code, produce a
number, and present it as a discovery. AlgoLab exists to make that failure mode
structurally difficult by requiring, for every non-trivial claim:

- a pre-registered, falsifiable hypothesis;
- a compute-matched baseline and a control;
- an evaluation protocol frozen before confirmatory results are seen;
- deterministic, versioned, checksummed artifacts;
- statistical inference appropriate to the design (effect sizes, intervals,
  multiplicity correction);
- and a promotion gate that cannot be weakened after outcomes are known.

## Intended users and use cases

- Research engineers who want to run bounded, auditable experiments on
  algorithm- and hyperparameter-search policies.
- Reviewers/skeptics who want to independently re-run an experiment and
  challenge its conclusions from the committed evidence bundle.
- Contributors who want to add a new pre-registered protocol without guessing
  the project's conventions.

## Constraints

- **CPU-friendly, zero incremental cost.** Local CPU or a free-tier CPU
  environment only. No GPU/TPU, no paid model APIs, no large downloads.
- **Human oversight by default, autonomy by exception.** Autonomy is earned
  experimentally, stage by stage, never asserted by a design change.
- **Reproducibility.** Deterministic runs must be byte-reproducible within an
  explicitly stated boundary (same code revision, config, environment, seeds).
  Where external nondeterminism or unavailable dependencies prevent exact
  reproduction, that limit must be recorded, not hidden.
- **Open-source usability.** MIT-licensed; a new contributor can install, test,
  and run a minimal example from a clean environment using documented commands.
- **No self-modification** outside versioned, reviewable proposals.
- **No uncontrolled external actions or credential use.**

## Definition of a meaningful algorithmic discovery

Within this repository, a *validated discovery* is a candidate change that:

1. beats the split-matched, compute-matched baseline by at least the
   pre-registered margin on **every** required replicate/seed;
2. survives the pre-registered statistical promotion criterion (adjusted
   p < 0.05 and a confidence interval excluding zero) on the required number of
   independent task families; and
3. persists in the pre-registered direction on a held-out family that was never
   used to build prior knowledge or to tune the policy.

Anything weaker is reported as a partial result, an inconclusive result, or a
negative result — never as a discovery.

## What evidence would justify a scientific claim

A claim is justified when (a) its hypothesis and acceptance criteria were frozen
before confirmatory execution, (b) raw observations and derived summaries are
distinguishable and checksummed, (c) the statistical procedure matches the
design, and (d) an independent party can re-run the experiment from committed
inputs and obtain a result consistent with the claim within stated bounds.

## Explicitly out of scope

- Replacing or paralleling the existing `implementation/algolab` architecture.
- Unrestricted autonomous operation, self-improvement, or GPU-scale compute.
- Claims about general algorithm-discovery capability from toy substrates.
- Editing the scaffold specs under `spec/AI-Algorithm-Discovery-Lab-Spec/`.
- Manufactured or retro-fitted success: thresholds, seeds, preregistrations, and
  acceptance criteria are never changed to obtain a passing result.

## Dimensions this project is judged on (kept separate)

1. **Software engineering quality** — installs, tests, types, lint, CI, DX.
2. **Scientific validity** — design, baselines, leakage control, inference.
3. **Reproducibility & provenance** — manifests, checksums, re-run commands.
4. **Research governance** — budgets, promotion gates, auditability.
5. **Open-source quality** — docs, examples, contribution path, license.
6. **Maintainability** — failures become regressions; feedback loops close.

A technically excellent laboratory can produce a negative scientific result.
These dimensions are scored independently; a green test suite is not evidence of
scientific validity, and a README assertion is not experimental evidence.

## Current capability vs. aspiration

- **Demonstrated:** a contracts + deterministic-execution core (M0, M1); a
  deterministic statistics layer; a knowledge-loop research line on a
  planted-truth toy substrate (protocols 230–234) and a first real-workload
  bridge (protocol 235) whose strict promotion bar was honestly reported unmet.
- **Hypothesis / provisional:** that the knowledge loop's adaptive advantage is
  "insurance against distribution shift" rather than an in-domain efficiency
  win. This is supported at small n on one real workload and remains to be
  confirmed at higher power.
- **Aspiration (not demonstrated):** higher-power real-workload promotion; a
  genuinely distinct second substrate; LLM-assisted ideation (M3); evolutionary
  search (M4); controlled meta-improvement (M5).

See `docs/audits/initial-audit.md` for the evidence behind these statements and
`docs/quality/acceptance-criteria.md` for the quality gates this project holds
itself to.
