# protocol-242 — Meta-Search bounded experiment

Status: **preregistered experiment**. The historical trace is synthetic and is not prospective evidence. No policy is promoted on replay performance.

| Arm | Replay agreement | Prospective Δ/credit | 95% CI low | p | q (BH) | Held-out Δ | Promotion |
|---|---|---|---|---|---|---|---|
| fixed-baseline | 0.000 | +0.000000 | +0.000000 | 1.0000 | — | +0.000000 | REJECTED_PROSPECTIVE |
| replay-cost-aware | 0.000 | +0.018056 | +0.001042 | 0.0605 | 0.0907 | +0.020000 | REJECTED_PROSPECTIVE |
| evolved | 0.000 | +0.020833 | +0.003819 | 0.0465 | 0.0907 | +0.022778 | REJECTED_PROSPECTIVE |
| random-control | 0.000 | -0.000461 | -0.010402 | 0.9365 | 0.9365 | -0.003977 | REJECTED_PROSPECTIVE |

Primary outcome: validated discoveries per credit (paired across matched trials). Secondary: distinct useful methods per credit. Negative results are reported as measured.
