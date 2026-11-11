# P1 and P2 results (M5, M6)

Status 2026-11-11. Every number below is produced by `make figures` from raw data. Tables are in
`paper/tables/`, figures in `paper/figures/`. These are preliminary results for the owner's
write-up, not paper text.

## P1: what older hardware earns per dollar (M5)

Benchmark: Llama 3.1 8B on vLLM 0.32.0, 512 in / 256 out tokens, concurrency 1/8/32/128, three
repeats, on A40, A100 80GB, H100 SXM, L40S and H200 SXM (frontier; the B200 could not be rented).
All 120 windows passed (power covered, no confounds). Tables: `p1_benchmark_summary.csv`,
`fig_p1a.csv`..`fig_p1d.csv`.

- **Throughput (P1-a):** at concurrency 128 the H200 does 8,588 tok/s in BF16 against 1,370 for the
  A40. Scaling from 1 to 128 requests is 39x (A40) to 48x (H100): memory-bound at low load,
  compute-bound at high load.
- **Efficiency (P1-b):** tokens per joule at concurrency 32 rise with each generation: A40 2.45,
  A100 4.85, H100 6.07, H200 7.18 (BF16). Native FP8 adds 40-57% on Hopper and Ada. Ampere's
  weight-only FP8 adds 14-31% at concurrency 32 and loses to BF16 at 128: format obsolescence,
  measured.
- **Cost per token (P1-c):** at neocloud median prices, rental cost per million tokens is almost
  flat across five years of hardware: A100 $0.29, H100 $0.26, L40S $0.30, H200 $0.30 (best
  precision, c=32). The A40, at $0.17, rests on one price. Electricity is $0.003-0.010, 1-4% of
  rental cost.
- **Obsolescence discount (P1-d, primary spec = neocloud median):** against the H200 at c=32, BF16:
  H100 -0.02 (provider range -0.13 to +0.34), A100 -0.00 (-0.21 to +0.20), L40S +0.18 (-0.17 to
  +0.72), A40 -0.37 (one price). Old chips are priced close to their output, not at a discount.
  The paid-price spec (RunPod) makes every old chip look 6-32% cheaper. One provider's price
  misleads.

## P2: what decay the term structure implies (M6)

Tables: `p2_observed_ratios.csv`, `p2_implied_decay.csv` (full r x pi grid), `p2_level4.csv`.

- **Observed ratios (P2-a):** 3-year reserved / on-demand runs 0.36-0.38 for neocloud A100 and H100
  (Lambda, Paperspace), and 0.38-0.50 at hyperscalers. Azure's 5-year H100 is 0.40.
- **Implied constant decay (r 8%, pi 0):** H100 0.46/yr (neocloud) and 0.67 (hyperscaler); A100 0.62
  and 0.95; L40S 0.83 and H200 0.83 (hyperscaler); B200 0.49 (neocloud, thin). Implied half-lives
  run 0.7-1.5 years. A 3%/yr term premium lowers H100 delta to 0.40-0.54.
- **Level 4 (P2-b):** only the hyperscaler H100 has three tenors. Its exact fit puts all decay in
  the first two years and a plateau near 29% of the launch rent, consistent with sticky long-run
  reserved prices. It is illustrative, not an estimate.
- **L_opex (P2-c):** 10-12 years for the H100 across the whole (r, pi) grid, and 6.6-12.3 years for
  the other chips. Rent today is about 20x operating cost, so even fast decay takes about a decade
  to reach opex.

## How P1, P2 and P3 line up (input to M8)

- P1: old chips are priced near output parity today. The market is not visibly penalising them
  beyond their throughput gap.
- P2: term discounts imply fast decay (half-life about 1-1.5 years). That is an upper bound on
  expected obsolescence, because the ratios also carry on-demand list-price premiums and term
  premiums (P3 validation check 2).
- P3: calibrated median economic life 4.1 years, 3.6 under constant power scarcity, 11 with
  abundant power. L_opex (10-12 years) brackets P3's abundant-power case; P3's constrained case
  sits between P2's L_50 and L_opex.
- Hyperscaler book lives (4-6 years) sit inside that range. M8 will make this a table and figure.

## Caveats

- One snapshot week (2026-11-10/11) for prices; the A40 has one price and the A100 two neocloud prices.
- P2 term data are thin for neoclouds: 1-2 providers, and Lambda's 12-month H100 ratio exceeds 1.
- Frontier is the H200 (Hopper), not the B200. Discounts are relative to a refresh, not a new
  architecture.
- Board power only. PUE is applied explicitly; host CPU, memory and network power are not measured.
