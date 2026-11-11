# Assumptions

Every assumption with its value and source.

| Assumption | Value | Source | Used in |
| --- | --- | --- | --- |
| P3 operating concurrency | 32 | Handoff 5.2 default | p3_calibration |
| P3 utilisation u | 0.70 | Handoff 5.2 default | P3 economics |
| PUE | 1.3 | Handoff 3.5 / 5.2 default | P1 energy cost, P3 opex |
| Electricity price | $0.089/kWh US industrial (VA $0.100 scenario); P1 tables still use $0.08 | EIA-861M last 12 months (Decision 12) | P3 opex |
| Discount rate | 8%/yr | Handoff 5.2 default (neocloud cost of capital) | P3 annuity and valuation |
| Capex annuity term | 60 months (tornado 48/72) | Judgement: midpoint of 4-6 y book lives (Decision 12) | P3 frontier annuity |
| Retirement hold | 3 months | Handoff 5.2 | P3 rules |
| Physical failure | constant 2%/yr permanent loss (0.5% / 11.1% scenarios; handoff 8 y/1.5 kept as scenario) | Judgement on field data: Llama 3, Delta, Titan (Decision 12) | P3 failure channel |
| Generation step mu_G | 0.459 (x1.58 tokens/J) | Measured, P1 A100->H100 at c=32, best precision (Decision 9) | P3 frontier progression |
| Generation step sigma_G | 0.086 | Epoch: sd of log FLOP/W steps V100->B200 (Decision 12) | P3 frontier progression |
| Power step per generation | x1.43 | Measured, P1 A100->H100 board power at c=32 | P3 hardware path |
| Idle share of loaded power | 0.21 (H100, gen 0) | Measured, P1 idle window vs c=32 load (A100 0.24) | P3 opex (Decision 8) |
| Release cadence | 18/24/30 mo w.p. 0.25/0.50/0.25 (mean 24) | Handoff base design; Epoch gaps 26/28/34 in empirical_cadence (Decision 12) | P3 base scenario |
| Scarcity markup m(t) | log-OU, mean 0.90, kappa 0.98, sigma 1.09, floor -0.5, stationary start | Lambda H100 on-demand level; AWS spot H100 dynamics (Decision 12) | P3 token price |
| Scarcity boom | m mean 1.57 | Lambda H100 $4.14 in 2026 (Decision 12) | P3 scenario |
| Electricity OU | kappa 0.43, sigma $0.0096, floor $0.02 | EIA-861M AR(1), deseasonalised (Decision 12) | P3 opex |
| Power regime | stay 0.979 constrained / 0.958 unconstrained; start constrained | LBNL Queued Up 2025 (>4 y queue) + judgement (Decision 12) | P3 base scenario |
| Capex per GPU (gen 0, H100) | $33,600 all-in (sensitivity $24,400) | Epoch AI hardware data (CC BY 4.0), citing SemiAnalysis DGX H100 $269k/8 (Decision 10) | P3 |
| Capex growth per generation | 1.63x (sensitivity 1.0x) | Epoch: H100 GPU+baseboard $24.4k / A100 40GB card $15,000 (Decision 10) | P3 |
| Maintenance per GPU-month | 4% of capex/yr (~$112 for H100); sensitivity 12.5% | CloudRift blog 2026-01-21 (weak, vendor); GMI Cloud 10-15% (Decision 11) | P3 opex |
