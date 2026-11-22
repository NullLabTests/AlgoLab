# protocol-244 — Real-workload policy transfer

Status: **preregistered experiment** (spec committed before execution). Replay is diagnostic only; no policy is promoted on replay evidence.

| Workload | Arm | Primary Δ/credit | 95% CI low | p | q (BH) | Held-out Δ | Promotion |
|---|---|---|---|---|---|---|---|
| transform | evolved | +0.004045 | -0.003175 | 0.4093 | 0.5052 | +0.000000 | REJECTED_PROSPECTIVE |
| hpo | evolved | +0.002500 | +0.000000 | 0.5052 | 0.5052 | +0.012500 | REJECTED_PROSPECTIVE |

Primary outcome: validated discoveries per credit. Secondary: distinct useful methods per credit. Negative and inconclusive results are reported as measured; no threshold was changed after results were seen.
