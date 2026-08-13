# Governance and Safety

## Autonomy model

**Human oversight by default, autonomy by exception.** The platform starts
fully human-scheduled; autonomy is granted one stage at a time, only when
a pre-registered protocol demonstrates the capability that justifies it,
and never by changing the rules after the fact.

The staged ladder (see `spec/research/230_KNOWLEDGE_LOOP_EVALUATION.md`):

- Level 0 — no autonomous choices; all scheduling is human-approved.
- Level 1 — operator choice within the approved catalog, same budget,
  after the knowledge-loop A/B/C protocol passes in the toy environment.
- Level 2 — new task families may register under default review, after
  transfer to a held-out family is demonstrated.
- Level 3 — budget expansion under prior approval, after stability at
  higher budgets is demonstrated.

Each stage requires: a passing pre-registered evaluation, the default-deny
permission model unchanged, and re-review of this governance document.

## Permission model

Default deny. Each service has an allowlist of:
- filesystem paths;
- commands;
- network destinations;
- credentials;
- maximum process count;
- resource limits.

## Human approval required for
- spending beyond the pre-approved limit;
- external publication;
- repository push to protected branches;
- adding new credentials or network destinations;
- changing discovery criteria;
- enabling self-modification in production;
- distributing execution to new machines.

## Emergency stop

The stop mechanism must:
- prevent new scheduling immediately;
- signal active workers to checkpoint or terminate;
- revoke temporary credentials;
- preserve logs and state;
- require explicit manual reset.

## Research integrity

The system must never:
- delete failed runs to improve apparent success;
- change primary metrics after seeing results without labeling exploration;
- present exploratory findings as confirmatory;
- omit material regressions;
- fabricate citations, runs, metrics, or artifacts.
