# Protocol-236 Identity Conflict — Governance Record

- **Status:** **RESOLVED** (human decision, 2026-10-14). Decision: **Option 1**.
- **Recorded:** 2026-10-14, at HEAD `93e5f11220f8b98bb97a2c63d95be5054cd380e4`.
- **Resolved:** 2026-10-14 by the repository owner.
- **Related:** `docs/audits/initial-audit.md` §4 D-2; `docs/quality/improvement-plan.md` WP-1.

## 0. Resolution (2026-10-14)

**Decision (owner):** keep the committed pre-registration authoritative —
**protocol 236 = the higher-N real-workload promotion**
(`spec/research/236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md`). The competing
"S2 / second-substrate-transfer" substrate is **re-designated protocol 237**
with its own pre-registration,
`spec/research/237_SECOND_SUBSTRATE_TRANSFER.md` (transcribed from the
implemented `workload_s2.py` and frozen before any 237 run).

Rationale: the committed spec holds the number 236, and renumbering a
pre-registered design (Option 2) is exactly what pre-registration governance
exists to prevent. The S2 substrate was never sealed, so giving it a fresh
number and a written pre-registration is safe.

Changes made under this decision:

- **New spec:** `spec/research/237_SECOND_SUBSTRATE_TRANSFER.md`.
- **236 spec:** marked authoritative; a note records that the registered
  alpha-margin lever is **not yet implemented** (so no `protocol-236-v1`
  bundle may be sealed).
- **Code:** `src/algolab/search/workload_s2.py` docstring now names protocol
  237 and the real spec; the module/harness key stays the neutral `s2`.
- **CLI:** `search-run --workload s2` is now reachable (WP-6, previously
  deferred to this naming decision); covered by
  `tests/test_search.py::test_cli_search_run_s2_workload_is_reachable`.
- **Tests:** `tests/test_protocol_236.py` → `tests/test_rules_library.py`
  (it tests the rules library + frozen 235 substrate, not protocol 236).
- **Driver:** `scripts/run_protocol_236.py` docstring/notes now state it is
  **not yet conformant** (only the trials lever is implemented) and it prints
  a warning before sealing.
- **Docs:** root `README.md`, `docs/STATUS.md`, and
  `implementation/algolab/GREAT_PLAN.md` updated (236 = higher-N; 237 = S2).

**Still open (not a naming issue):** implementing the registered 236
alpha-margin recalibration and sealing a conformant `protocol-236-v1` bundle
(requires authorization + compute; see D-2 §4 and the 236 spec §3).

---

This note also preserves the original conflict record for provenance.

This note records a conflict between the **pre-registered** definition of
protocol 236 and the **implemented/tested** definition. It deliberately did not
rewrite the pre-registration or assign a new number, because doing so would
change a scientific question and therefore requires human approval (now given
— see §0).

## 1. The two definitions

### 1a. Pre-registered (the committed specification)

`spec/research/236_HIGHER_N_REAL_WORKLOAD_PROMOTION.md` (committed at HEAD)
defines protocol 236 as a **higher-N real-workload promotion run**:

- substrate: the KNN micro-HPO workload (protocol 235);
- the single registered lever: trials 32 → **96**;
- the alpha discovery margin recalibrated **0.005 → 0.0035** (lattice-derived),
  beta/gamma unchanged at 0.005;
- `HPO_WORKLOAD_VERSION`/`HPO_TASK_SUITE_VERSION` 1.1.0 → **1.2.0**;
  `discovery_gate_version` → **1.1.0**;
- experiment id `protocol-236-v1`; machine-invariant control: trials 0..31 must
  byte-reproduce protocol-235-v1's beta/gamma outcomes.

### 1b. Implemented / tested / documented (the other definition)

- `tests/test_protocol_236.py:1-9` says protocol 236 **re-scopes to the "S2"
  substrate** and that all families keep the frozen 0.005 margin.
- `GREAT_PLAN.md:94-103` (Phase 2) assigns `236_SECOND_SUBSTRATE_TRANSFER.md`
  (LogReg / DecisionTree / GaussianNB) to protocol 236, and puts the higher-N
  margin work in Phase 3 under the name **235b** with
  `235b_POWERED_REPLICATION.md`.
- `src/algolab/search/workload_s2.py` implements the "S2" substrate — but with
  **KNN knobs only** (`:52-60`), contradicting its own docstring's claim of
  "operators … across three estimators" (`:12`), and cites
  `spec/research/236_SECOND_SUBSTRATE_TRANSFER.md` (`:3`), which **does not
  exist**.
- The root `README.md` and `docs/STATUS.md` describe 236 as the S2 / family-shift
  substrate and reference `235b_*` / `protocol-235-v2/`, none of which exist.

In short: the file that holds the number 236 is the **higher-N** design, while
the code, tests and docs mostly treat 236 as the **S2** design and shunt the
higher-N design to the (nonexistent) name 235b.

## 2. What the implementation actually does

- `src/algolab/search/workload_hpo.py:39-40,63,169` keeps 1.1.0 / 0.005 / gate
  1.0.0 — i.e. it does **not** implement the registered 236 lever.
- `scripts/run_protocol_236.py:45` passes `promotion_threshold=hpo.DISCOVERY_MARGIN`
  (0.005) with no per-family margins, so running it would seal a
  `protocol-236-v1` bundle that does **not** match the pre-registered 236.
- `workload_s2.py` is registered in the harness (`harness.py:169`) but is not
  reachable from the CLI (`cli/main.py:160` allows only `toy`/`hpo`) and is not
  imported by any test.

## 3. Evidence status

- **No confirmatory bundle exists for either definition.**
- `experiments/protocol-236-v1/` (untracked at baseline; since 2026-10-14 archived
  and committed at `experiments/_aborted/protocol-236-v1-2026-09-19/` with an
  `ABORTED.md` marker) is an **aborted run**: it contains
  only `manifest.json` + `knowledge-snapshot{,-by-family}.json`; there are no
  `conditions/`, `statistics.json`, `report.md`, or `checksums.json`. Its
  manifest (`trials: 96`, `environment_version: 1.1.0`,
  `discovery_gate_version: 1.0.0`, `promotion_threshold: 0.005`, no family
  margins) matches **neither** design cleanly. HEAD's commit message confirms it
  was not executed. It must not be cited as a result.
- **No `protocol-235-v2/` bundle exists**, despite `docs/STATUS.md:21`.

## 4. Consequence

Any future run named `protocol-236-v1` is currently unciteable: a reader cannot
tell from the name which design it tested, and the two candidate designs differ
in substrate, sample size, margin, and versioning. Claim style
("on substrate X, at n=Y, rule R beat S on pre-registered metric M") cannot be
formed without first resolving the name.

## 5. Options (human decision)

> **Chosen: Option 1** (see §0). The options are retained below for the record.

1. **Keep 236 = higher-N real workload** (as the committed spec says) and
   re-label the S2 substrate as a new protocol number with its own
   pre-registration. Requires editing code/tests/docs that currently say "236
   S2".
2. **Keep 236 = S2** and re-label the higher-N design (e.g. 235b/237), creating
   the missing preregistration and updating the spec filename.
3. **Withdraw the S2 substrate** (delete it and its docstring/spec references)
   and keep the single higher-N 236 design.

All options touch a pre-registered design or a scientific question, so the
choice required human approval. Approval was given on 2026-10-14 (Option 1);
see §0 for the changes made. This section is retained as the pre-decision
record.
