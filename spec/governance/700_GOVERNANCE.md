# Governance and Safety

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
