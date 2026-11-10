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
- **Owner's open questions from the handoff (answer before any GPU is rented):** Llama 3.1 8B
  (gated) or Qwen 2.5 7B; H200 or B200 as the frontier point; base-case electricity price and PUE
  (a region such as Northern Virginia, or a national average); any private rate cards for
  `prices_term.csv`.
- **Benchmark image not built or pushed.** `bench/Dockerfile` has not been built (it needs a
  linux/amd64 build of a ~10 GB base image and a registry account). The harness logic is proven
  only on stub binaries.
- **Unspecified term in the P3 spec.** Handoff 5.2's opex formula uses `u_power` without defining
  it (power-weighted utilization, or the same `u`?). It needs a definition before P3 is built.
