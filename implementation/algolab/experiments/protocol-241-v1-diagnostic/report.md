# protocol-241 — Meta-Search bounded pilot

Status: **exploratory pilot**. The historical trace is synthetic and is not prospective evidence. No policy is promoted on replay performance.

| Arm | Replay agreement | Prospective Δ/credit | 95% CI low | p | Held-out Δ | Promotion |
|---|---|---|---|---|---|---|
| fixed-baseline | 0.000 | +0.000000 | +0.000000 | 1.0000 | +0.000000 | REJECTED_PROSPECTIVE |
| replay-cost-aware | 0.000 | -0.006548 | -0.012500 | 0.1399 | -0.012500 | REJECTED_PROSPECTIVE |
| evolved | 0.000 | -0.006548 | -0.012500 | 0.1399 | -0.012500 | REJECTED_PROSPECTIVE |
| random-control | 0.000 | -0.007540 | -0.018353 | 0.3107 | -0.019621 | REJECTED_PROSPECTIVE |

Primary outcome: validated discoveries per credit (paired across matched trials). Secondary: distinct useful methods per credit. Negative results are reported as measured.
