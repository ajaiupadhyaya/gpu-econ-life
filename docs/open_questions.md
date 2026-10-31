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
- **GitHub remote not set up.** The private repo creation and push were refused by the permission
  system, so the work exists only on this machine.
- **Host for the daily collector.** Phase 1 finishes only when the owner has confirmed all four
  checks in deploy/README.md. Until then, no daily prices are being collected.
- **Google Cloud price basis.** Rows are treated as accelerator-only. Confirm against Google's
  pricing page before they enter any estimate.
- **Interconnect is mostly empty.** Only AWS reports it. Azure and Lambda values need a sourced
  mapping in Phase 3, or the control must be dropped.
- **Chip memory is partly empty** where vendor documents disagree or were not checked, for example
  L40S (AWS docs say 44 GiB and its offer file says 48 GB). Phase 3 settles these from datasheets.
- **Azure is retiring NCv3,** the main V100 series. Expect those rows to vanish, and treat that as
  survivorship rather than a collector fault. The health check will flag it.
