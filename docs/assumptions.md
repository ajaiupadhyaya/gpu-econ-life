# Assumptions

Every assumption with its value and source.

| Assumption | Value | Source | Used in |
| --- | --- | --- | --- |
| P3 operating concurrency | 32 | Handoff 5.2 default | p3_calibration |
| P3 utilisation u | 0.70 | Handoff 5.2 default | P3 economics |
| PUE | 1.3 | Handoff 3.5 / 5.2 default | P1 energy cost, P3 opex |
| Electricity price | $0.08/kWh (OU mean) | Handoff default; region vs national is the owner's open question 3 | P1 energy cost, P3 opex |
| Discount rate | 8%/yr | Handoff 5.2 default (neocloud cost of capital) | P3 annuity and valuation |
| Capex annuity term | 60 months | Placeholder (Claude Code); handoff gives no n | P3 frontier annuity |
| Retirement hold | 3 months | Handoff 5.2 | P3 rules |
| Weibull failure | scale 8 y, shape 1.5 | Handoff 5.2 default; drives ~half of retirements in synthetic runs, needs review | P3 failure channel |
| Generation step mu_G | 0.459 (x1.58 tokens/J) | Measured, P1 A100->H100 at c=32, best precision (Decision 9) | P3 frontier progression |
| Generation step sigma_G | 0.15 | Placeholder: not identifiable from one measured step | P3 frontier progression |
| Power step per generation | x1.43 | Measured, P1 A100->H100 board power at c=32 | P3 hardware path |
| Idle share of loaded power | 0.21 (H100, gen 0) | Measured, P1 idle window vs c=32 load (A100 0.24) | P3 opex (Decision 8) |
| Release cadence | 18/24/30/36 mo w.p. 0.25/0.50/0.25/0 | Support from handoff; probabilities are a placeholder (mean 24 mo) | P3 base scenario |
| Scarcity markup m(t) | OU mean 0.20, kappa 1.0, sigma 0.30, floor -0.5 | Floor from handoff; the rest placeholders | P3 token price |
| Scarcity boom | m mean 1.0, start 1.0 | Placeholder for the handoff's 'high m-bar (2026-like)' | P3 scenario |
| Electricity OU | kappa 1.0, sigma $0.02, floor $0.02 | Floor from handoff; kappa, sigma placeholders | P3 opex |
| Power regime | monthly stay prob. 0.97 each, start constrained | Placeholder | P3 base scenario |
| Capex per GPU (gen 0, H100) | $33,600 all-in (sensitivity $24,400) | Epoch AI hardware data (CC BY 4.0), citing SemiAnalysis DGX H100 $269k/8 (Decision 10) | P3 |
| Capex growth per generation | 1.63x (sensitivity 1.0x) | Epoch: H100 GPU+baseboard $24.4k / A100 40GB card $15,000 (Decision 10) | P3 |
| Maintenance per GPU-month | NO SOURCE (null) | Needed; model refuses to run | P3 |
