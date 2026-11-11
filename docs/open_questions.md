# Open questions

Unknown values, unreachable sources and anything waiting on a decision.

- **Contact email for the User-Agent (rule 5).** `<YOUR EMAIL>` in CLAUDE.md is still a placeholder.
  The code reads it from `GEL_CONTACT_EMAIL` in a git-ignored `.env`, so it never lands in a repo
  that will go public. Until it is set, requests identify the project but carry no email. SEC
  EDGAR requires a contact in the User-Agent, so this must be set before Phase 7.

- **Written permission from Vast.ai and RunPod (stop condition, 2026-10-31).** Vast.ai's terms ban
  automated collection and any use of its data for an "index, benchmark, pricing-comparison
  service". RunPod bars compiling a database from its site; whether that covers its keyed API is
  unclear. Oracle bans robots on oracle.com. Nothing is collected from these three live until the
  owner decides. See docs/data_sources.md section 2.
- **Do archived copies fall under those terms?** The Wayback copies of Vast, RunPod and Oracle
  pages are not addressed by their terms. A faculty advisor or counsel should weigh in before
  Phase 2 parses them.
- **Bloomberg and WRDS access at VCU.** Unconfirmed, and more valuable now that marketplace data is
  in doubt. Ask the business school library.
- **Unlisted sources awaiting approval under rule 7:** AWS offer files, Azure Retail Prices API,
  SkyPilot catalog history. See docs/proposal_review.md item 10.
- **About 60 items in docs/data_sources.md remain UNVERIFIED** (section 4). The SEC, EIA, FRED and
  BLS APIs were documented but not called, because they need a key or a contact User-Agent.

- **Literature stop condition (2026-10-31).** "First use of vintage-price methods" cannot stand. The
  owner decides whether to reposition; see docs/proposal_review.md, Literature.
- **Two CC BY packages: read 2026-10-31 with the owner's approval.** See docs/related_work.md
  section 5. They were kept outside the repo, so re-download them if either enters the pipeline.
- **Do not run `code/farm_history.py` from Huang's package.** It pulls from an exporter of Vast.ai
  data, which raises the Vast terms and would add a source without approval.
- **CCIR's terms are unknown.** `ccir.io/terms` returned 404. Its series stay out until the owner
  has checked, or asked CCIR. Its archive file is available on request.
- **Huang's working paper** ("Underwriting GPU Depreciation") has not been found. Ask the author.
- **SSRN papers to read in a browser**, since SSRN blocks automated access: 7420380, 7541938,
  7346098, 7270603.
- **Phase 1 is not finished.** The collector runs daily on the OhCamel droplet from 06:10 UTC on
  2026-11-01. Checks 1 and 4 in deploy/README.md passed; checks 2 (backup) and 3 (alert) need the
  owner's accounts. Until then raw data sits on the droplet with no automatic off-server copy, and a
  failed run sends no alert.
- **Contact email is still unset** on the host, so requests carry no email (rule 5).
- **Google Cloud price basis.** Rows are treated as accelerator-only. Confirm against Google's
  pricing page before they enter any estimate.
- **Interconnect is mostly empty.** Only AWS reports it. Azure and Lambda values need a sourced
  mapping in Phase 3, or the control must be dropped.
- **Chip memory is partly empty** where vendor documents disagree or were not checked, for example
  L40S (AWS docs say 44 GiB and its offer file says 48 GB). Phase 3 settles these from datasheets.
- **Azure is retiring NCv3,** the main V100 series. Expect those rows to vanish, and treat that as
  survivorship rather than a collector fault. The health check will flag it.

## From Phase 2

- **Validation sample: passed.** The owner checked all 40 rows in docs/validation_checklist.md and
  found no errors.
- **CoreWeave's JavaScript gap.** www.coreweave.com/pricing has no readable prices from 2021-01 to
  2022-07 (17 snapshots), because the tables are filled by script. Docs pages supply V100 and A100
  for 6 of those months. This partly meets the Phase 2 stop condition.
- **Rows left out because identity is not stated.** Each could be added if the owner accepts the
  inference:
  - Paperspace A100 at $3.09, 29 snapshots from 2021-12: memory unstated. Evidence supports 40 GB.
  - Paperspace docs H100 at $5.95 and x8 at $47.60, 13 snapshots: no form factor. Evidence supports SXM.
  - Paperspace docs multi-GPU rows from 2024-11: no GPU count.
  - CoreWeave A100 40GB NVLINK, 24 snapshots: the page's card shows $2.16 and its desktop view $2.06.
  - CoreWeave docs A100 at $21.60, 7 snapshots: memory unstated.
  - CoreWeave docs "H100 (InfiniBand)" at $49.24, 4 snapshots: no form factor.
  - CoreWeave's "starting at $2.23/hr" banner, 19 snapshots: no term.
- **Azure history is thin:** 11 months, because SkyPilot's Azure file is rarely updated. Daily
  collection now fills this forward, but the history cannot be rebuilt.
- **Pre-2022 market-moving prices remain the weak spot.** Before mid-2022 the panel is list prices
  only: AWS, plus Lambda, Paperspace and CoreWeave. AWS spot history starts in October 2022.

## Extension (Decision 6), 2026-11-10

- **Handoff seed points not yet verified.** The handoff lists two calibration targets for P2:
  Ornn's 5-year/1-month ratios (A100 ≈ 80%, B200 ≈ 54%) as reported by Data Gravity, and a Silicon
  Data H100 index ($2.00 on 2025-12-09 to $2.88 on 2026-10-24) as reported by fourweekmba. Both
  are secondary reports. Neither goes into `external_reference.csv` until checked against Ornn's or
  Silicon Data's own publication, and whether those can be used at all is a rule 7 question.
- **Llama 3.1 access: resolved 2026-11-10.** Meta approved the owner's request. The local token
  now gets HTTP 200 on `config.json` and `model-00001-of-00004.safetensors`. The same token goes
  on the Runpod template as `HF_TOKEN`.
- **Still open from the handoff:** (electricity resolved by Decision 12: national base, Virginia
  scenario; the P1 summary has an EIA-priced column, Decision 16); any private rate cards for `prices_term.csv`. Model,
  frontier GPU (B200, approved) and smoke-test card were settled in Decision 7.
- **Benchmark image not built or pushed.** `bench/Dockerfile` has not been built (it needs a
  linux/amd64 build of a ~10 GB base image and a registry account). The harness logic is proven
  only on stub binaries.
- **Unspecified term in the P3 spec.** Handoff 5.2's opex formula uses `u_power` without defining
  it (power-weighted utilization, or the same `u`?). It needs a definition before P3 is built.
- **vLLM FP8 flag deprecation.** vLLM 0.32.0 calls `--quantization fp8` a deprecated alias for
  `fp8_per_tensor` (online per-tensor FP8). All runs use the same flag, so it is consistent, but
  the paper's methods section should name the actual scheme: per-tensor dynamic FP8 (W8A8 on
  Hopper/Ada/Blackwell, W8A16 Marlin on Ampere).
- **(Resolved 2026-11-10: capex by Decision 10, maintenance by Decision 11, weakly sourced.)** P3 needed three sourced inputs: all-in capex per GPU for
  generation 0 (A100, including its share of server and network), capex growth per generation,
  and maintenance per GPU-month. `config/p3_model.yaml` holds them as null and
  `gel.models.monte_carlo` refuses to run. Candidate sources need the owner's approval (rule 7),
  e.g. Epoch AI's chip price data (docs/related_work.md, row 61) or values from SEC filings.
- **(Resolved 2026-11-11 by Decision 12.)** P3 placeholders awaiting sign-off: sigma_G, cadence probabilities, markup and electricity OU
  parameters, regime transition probabilities and the 60-month annuity term
  (docs/assumptions.md). The Weibull failure default (8 y, shape 1.5) makes failure the most
  common end of life in synthetic runs. It is worth checking against field data before results.
- **(Run 2026-11-11, Decision 12: checks 1 and 3 pass, 2 fails for hyperscalers, 4 reported.)** P3 validation checks 1-4: They need the real inputs. Check 3 (a
  scarcity boom that raises old-chip rents while the efficiency gap widens) also needs a
  transition scenario in which the markup jumps mid-path; the current boom scenario starts high.
- **Term structure vs model (Decision 12, check 2).** Observed reserved/on-demand ratios are
  far below the model's flat-rate ratios for hyperscalers (0.38 vs 0.91 at 36 months). The model's
  rent-decay channel cannot explain them without a 19-38%/yr term premium. Most likely the cause
  is inflated, sticky on-demand list prices. P2's full write-up should model the on-demand premium
  explicitly, or use spot as R0.
- **The markup absorbs provider overhead.** The model's cost has no colocation/facility line, so
  the calibrated markup (0.90) mixes normal margin with scarcity. A facility-cost line with a
  sourced value would separate them.
- **(Deployed 2026-11-11, commit 9273467; host backfilled.)** Deploy the Lambda parser fix to the droplet. The collector has failed on Lambda daily since
  2026-11-03 (unknown plan "NVIDIA HGX H100"). Fixed and backfilled locally (commit c84bd1f);
  the droplet needs `deploy/push.sh` (owner's call), and alerts would have caught this on day one.
- **A40 has a single price** (the RunPod price paid) in the M4 panel; no other in-scope provider
  lists it. Its discount is not robust. Paperspace's archived A40 or the Huang tables could widen it.
- **Crusoe and Voltage Park excluded** by their terms (Decision 13). Written permission would
  restore them.
- **Collector alerts are still not set up.** The Lambda failure ran 8 days unnoticed. `deploy/alert.sh`
  and `gel-alert@.service` exist but need the owner's notification account; backups
  (`gel-backup.timer`) are also still off.
- **Firm-specific useful lives (Phase 7).** M8 compares against the handoff's generic 4/5/5.5/6 years.
  Attributing those to Microsoft, Alphabet, Amazon, Meta, Oracle, CoreWeave and Nebius needs the
  SEC/EDGAR work (contact email required for the EDGAR User-Agent).
- **Chip specs Epoch lacks (Decision 18).** The archived Epoch CSV has no L40S row (only the L40)
  and no FP8 figure for the H100 PCIe or the MI300X. Backup sources: the NVIDIA L40S and H100
  datasheets (AJ downloads by hand). The MI300X is an AMD part, so its backup would be an AMD
  datasheet, which is a new source and needs AJ's approval (rule 7). V100 and A100 have no FP8
  entry because they lack FP8 hardware; Phase 3 should cite that from the datasheet, not leave it
  as an unexplained blank.
- **Phase 3 chip table gaps (Decision 19).** 22 values are missing. The L40S has only a
  hand-recorded announcement date (2023-08-08); its specs need the NVIDIA L40S datasheet. FP8 is
  blank for the H100 PCIe and MI300X (datasheets), and for the V100 and A100 80 GB without an Epoch
  "not supported" note (the A100 40 GB has one). Release prices are blank for the A100 80 GB, H100
  PCIe and B200. Announcement dates are hand-recorded only for the L40S.
- **Check before Phase 4 uses release dates as age zero.** Epoch dates the B200 (2024-11-15) three
  days before the H200 (2024-11-18), and the H100 SXM and PCIe both 2022-09-20. Phase 4 could
  compare these with the first date each chip appears in our price panel as a robustness check.
- **V100's tensor FP16/BF16 figure (125 TFLOP/s)** sits in Epoch's combined FP16/BF16 column. If
  the V100 lacks BF16, the value is its FP16 tensor rate; confirm from the NVIDIA datasheet before
  the paper describes it as BF16.
- **Dense vs sparse throughput.** Epoch's notes state "Listed performance figures are without
  sparsity" for the H100 SXM, H100 PCIe and B200 only. The V100, A100, H200 and MI300X rows carry no
  such note; confirm against their datasheets before comparing across chips.
- **(Resolved 2026-11-11, Decision 21: CPI-U built from BLS flat files.)** **CPI-U waits on the contact email.** BLS asks for a contact-bearing User-Agent and FRED needs
  an API key; `GEL_CONTACT_EMAIL` is not yet in `.env`. Until then the panel has nominal prices
  only.
- **(Decided 2026-11-11, Decision 20: not built; P1 is the throughput measure.)** **MLPerf throughput index (proposal Phase 3 item 2).** Not built: MLCommons' terms of use could
  not be read (data_sources.md 3.12), and P1's own vLLM benchmark already measures throughput per
  chip. AJ to decide whether the paper needs MLPerf as well.
- **Google H100 on-demand in SkyPilot's July 2026 catalog (Decision 22).** The accelerator-only
  price is about $4.20 in 12 of 19 regions (7 in June 2026, none in August), against $10-11
  elsewhere; our parse matches the raw file (`data/raw/skypilot_history/gcp/2026-07-*.csv.gz`). The
  cause is unknown. Phase 5 should show results with and without that snapshot.
- **Pull the droplet's live data before Phase 5.** The local live panel ends 2026-11-10. The
  rsync command in `deploy/README.md` adds new raw files without touching existing ones; the
  interim parse then needs rerunning.
- **Announcement dates for H2 (Decision 23).** The successor event study uses Epoch release dates
  only; a drop priced in at announcement would be missed. Hand-recorded NVIDIA announcement dates
  (as for the L40S in `chip_dates.csv`) would allow the review's announcement-date version.
- **H1 shape result is driven by demand timing? (Phase 5).** Every strategy finds prices falling
  later rather than earlier. Phase 6 and the B4 review should test whether this survives removing
  the 2023-24 H100 and 2025-26 H200 shortage windows, which fall at young ages.
- **Headline inference for Phase 5: WCU or WCR? (AJ, rule 7).** On this design the unrestricted
  wild bootstrap logged in Decision 23 covers 66-73% at nominal 95%; the restricted version covers
  97.5-98.5% (`docs/review_01_checks.md`). Under WCR nothing in the headline table is significant.
- **Hosting cost per kW-month for Phase 6 (Decision 25).** No sourced colocation price could be read
  (the CBRE H2 2025 trends URL returned 404). Phase 6 therefore leaves hosting, network and staff
  out of operating cost, so V(0)/capex is an upper bound and T* never binds within 9 years. A
  named report figure (CBRE, JLL, Cushman & Wakefield or datacenterHawk) would close this.
- **DGX A100 system power scope (Decision 25).** NVIDIA's DGX A100 user guide lists "6.5 kW max."
  under a "Specification for Each Power Supply" header. Phase 6 reads it as the system maximum, as
  the DGX H100 guide's 10.2 kW is; confirm.
- **Venue rules not confirmed (docs/venues.md, 2026-11-11).** Financial Analysts Journal: length
  limit, fee amount and data policy (official pages returned 403/500). Journal of Financial Data
  Science: nothing confirmed. Economics Letters: the USD 125 fee rests on a search snippet. The
  undergraduate pick (Issues in Political Economy): preprint policy and length not stated.
- **Byrne, Corrado and Sichel exists as a 2018 NBER working paper and a 2021 book chapter.** The
  bibliography cites the working paper; AJ to pick one.
- **Outdated web-source titles in the proposal.** The verified titles are in `paper/references.bib`
  (American Compute's page, The Register piece, the KuCoin repost, getdeploying's trends page).
- **Phase 7 (Decision 26).** **Server/network share of capex** has no filing source. Owner decision: keep the 0.4/0.6/0.8 grid, or build a filing proxy from the PP&E notes (change in gross server/network class over change in total gross PP&E; possible for META, ORCL, MSFT FY2026, CRWV, NBIS, not for GOOGL or AMZN whose classes mix servers with buildings or other equipment).
- **Phase 7 (Decision 26).** **GPU cohort start year** (2020 vs 2023) is a judgement; results for both are in the CSV (`gpu_cohort_start_fy`).
- **Phase 7 (Decision 26).** **Finance-lease capex** is excluded: Amazon (2020-2021) and Microsoft acquired large server and data-centre amounts under finance leases, so the GPU base is understated for them. Decide whether to add finance-lease additions (not in companyfacts as a clean annual concept).
- **Phase 7 (Decision 26).** **Amazon 2025 subset**: which servers moved to five years is not disclosed.
- **Phase 7 (Decision 26).** **Loss years**: effective-rate EPS is missing for CRWV (all years), NBIS 2022-2024, AMZN 2022 and ORCL FY2021 (negative tax). The statutory-21% column covers them.
- **Phase 7 (Decision 26).** **Proposal table mismatch** (owner to fix the proposal text): the Nebius row says the effect is "Not quantified in the 20-F or Q1 2026 6-K", but the FY2025 20-F expects about $167.6 million lower FY2026 depreciation and the Q1 2026 6-K reports $43.1 (million) for Q1. All other seven rows match the filings. The table omits earlier changes (AMZN 2020, 2022; MSFT 2020; GOOGL 2021; META 2021-2022; ORCL FY2023); see docs/useful_lives.md.
- **Phase 7 (Decision 26).** **Pre-2021 Meta server life** and **pre-FY2023 Oracle server life** are not stated as single figures in the filings (Oracle's 4 years is implied by "from four years").
- **Phase 7 (Decision 26).** The figure and table use the Phase 6 schedule names as delivered at 23:07 local on 2026-11-10; if Phase 6 renames or adds schedules, re-run `make restate`.
