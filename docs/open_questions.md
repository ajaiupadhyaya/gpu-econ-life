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
- **Two CC BY packages to read before deciding** (download needs owner approval):
  `gpu-rental-value-curves-v1.6.1.zip`, 207.6 kB, https://zenodo.org/records/22053861, and
  `ai-gpu-depreciation-v1.3.0.zip`, 1.8 MB, https://zenodo.org/records/21894454.
- **SSRN papers to read in a browser**, since SSRN blocks automated access: 7420380, 7541938,
  7346098, 7270603.
- **GitHub remote not set up.** The private repo creation and push were refused by the permission
  system, so the work exists only on this machine.
