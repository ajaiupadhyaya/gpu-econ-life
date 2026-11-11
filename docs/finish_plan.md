# Plan to finish gpu-econ-life

Written 2026-11-11. This covers everything from today to a published, public, citable project:
the remaining research, the paper, SSRN and arXiv, the public GitHub release with a Zenodo DOI,
and the write-up on ajaiupadhyaya.com. It follows the original proposal's timeline (working paper
posted by 2027-04-05, ahead of May 2027 graduation) and CLAUDE.md's rules.

## The finish line

The project is finished when all of these exist and link to each other:

1. **Working paper** (25-35 pages, LaTeX), posted to **SSRN** and **arXiv** (q-fin.GN, cross-listed
   to econ.GN), after faculty review.
2. **Public GitHub repository** that rebuilds every table and figure, and the PDF, from raw data with
   one command, with a licence, a citation file and a tagged release.
3. **Dataset on Zenodo** with a DOI: the data we may redistribute (see "What can be published").
4. **Site write-up** on ajaiupadhyaya.com: a BASIS essay plus a Work entry on /publications with
   the house-style PDF, linking to the paper, repository and DOI.
5. **Two-page plain-English summary** for interviews and recruiting.
6. Then, one at a time: a **journal submission** and a **student or conference presentation**.

## Where things stand

- Done: Phases 0-2 (collector live on the `ohcamel` DigitalOcean droplet; 35,733-row historical
  panel) and all nine milestones of the GPU extension (benchmark, price panel, P2, P3,
  triangulation, reproducibility). 432 tests; `make figures` rebuilds 26 outputs in ~50 s.
- Not started: original Phases 3-8, which are the paper's core. Phase 3 builds reference tables,
  Phase 4 the panel and descriptives, Phase 5 the hedonic age profiles and identification (H1-H4),
  Phase 6 asset values and economic life, Phase 7 the firm-by-firm accounting restatement, and
  Phase 8 the paper and replication package.
- Repository: private on GitHub, `main` = `8818634`, in sync.

## Who does what

- **Claude Code** builds code, data, tables and figures, the LaTeX scaffold, verified references,
  the replication package and the site PR. It also drafts a first pass of each section's prose
  (decided 2026-11-11, Decision 17), which you rewrite in your own voice.
- **You** own the hypotheses, the interpretation and the final prose, and you approve new data
  sources (rule 7). You also
  hold the accounts: SSRN, arXiv, Zenodo, GitHub visibility, faculty contact, and the droplet's
  alerts and backups. Every publish step is yours to approve.

## Stages

Each stage ends at a gate: you review before the next starts, as in Phases 0-2. Session counts are
estimates.

### Stage A: infrastructure you need to unblock (this week, your actions)

| Item | Why | Your action |
| --- | --- | --- |
| Contact email for User-Agents | Required by SEC EDGAR (Phase 7) and project rule 5 | Put it in the git-ignored `.env` as `GEL_CONTACT_EMAIL` (never committed) |
| Droplet alerts | The Lambda parse failed silently for 8 days | Choose a notification channel; Claude wires `deploy/alert.sh` |
| Droplet backups | Raw data exists only on the Mac and the droplet | Create S3-compatible storage (~$0-5/month); Claude wires `gel-backup.timer` |
| Keep the collector running to April | Live prices can't be collected later | Nothing; it runs daily |

### Stage B: finish the research (mid-November to end of February)

| Step | Content | Done when | Sessions |
| --- | --- | --- | --- |
| B1 Phase 3, reference tables | Chip specs from Epoch with NVIDIA datasheets as backup (Decision 18), EIA state electricity (file already archived), CPI-U deflator (BLS, no key); no MLPerf index (Decision 20) | Every value has a source; a test fails if one doesn't | done 2026-11-11 (Decisions 19-21) |
| B2 Phase 4, panel and descriptives | Merge live and historical rows into `panel.parquet`, age since availability, real prices, cleaning report, four descriptive figures, plain-English memo | `make data` rebuilds the panel; memo written | done 2026-11-11 (Decision 22); memo awaits your review |
| B3 Phase 5, hedonic models | Chip and month fixed effects; age bins and spline; identification strategies 1-4; contract-type (H3) and sub-period (H4) splits; successor event study (H2); wild-cluster or CR2 inference | `make models` reproduces every table; memo written | done 2026-11-11 (Decision 23); memo awaits your review |
| B4 Adversarial review | A fresh session critiques identification from code and results alone; you answer each point | `docs/review_01.md` answered | 1 |
| B5 Phase 6, asset values | Value curves from the estimated age profiles; folds in the extension's P2 and P3 as a four-way triangulation | Tables and figures rebuild | 2 |
| B6 Phase 7, restatement | EDGAR XBRL for MSFT, GOOGL, AMZN, META, ORCL, CRWV, NBIS; `useful_lives.md` with filing quotes; restated depreciation, operating income and EPS across a GPU-share grid; firm lives replace the generic 4/5/5.5/6 in M8 | Every firm-year number traces to an XBRL fact or a logged assumption | 2 |
| B7 Optional data top-ups | A second hand-recorded price snapshot (e.g. February) to ease the single-week limitation; a B200 run (~$2) for a Blackwell frontier point | Only if you choose | 1 each |

Gate after B4 and after B6: you review before writing starts.

### Stage C: write the paper (March)

| Step | Content | Done when | Sessions |
| --- | --- | --- | --- |
| C1 Scaffold | `paper/main.tex`: Introduction, Background, Data, Methodology, Results (age profiles; benchmark, term structure and retirement model; triangulation), Accounting implications, Robustness, Conclusion. Tables and figures come only from generated files, with bullet notes of key results under each heading | `make paper` builds a PDF | 1 |
| C2 References | `references.bib`: every entry verified (DOI or stable URL, title, authors, year, venue); none invented; unverified ones listed in open_questions | No unverified references remain | 1 |
| C3 Prose | Claude drafts each section from the generated results and bullet notes, citing only verified references and quoting no number that is not in a generated file; you rewrite and approve every section | Complete draft by 2027-03-21 | 2-3 + your editing |
| C4 Faculty review | A VCU finance or accounting reader; also your arXiv endorser | Comments addressed | yours + 1 |
| C5 Two-page summary | Plain English, for recruiting | Done | 1 |

### Stage D: release and publish (late March to early April)

| Step | Content | Done when |
| --- | --- | --- |
| D1 Pre-public audit | Scan full git history for secrets and personal data; check no third-party raw data is tracked; review `research_log.md` (it names Runpod pod ids and the Docker Hub image) | Clean audit written to `docs/release_audit.md` |
| D2 Replication package | `make all` from a clean clone to `paper/main.pdf`, tested in a fresh directory; README updated with runtimes; `LICENSE` (code); `CITATION.cff`; a script that re-fetches sources we cannot redistribute, with checksums | Clean-clone rebuild passes |
| D3 GitHub public | You flip the repository to public; tag `v1.0` | Public, tagged |
| D4 Zenodo DOI | Connect the repo to Zenodo; deposit the redistributable dataset (below) | DOI minted, cited in the paper and README |
| D5 SSRN + arXiv | You submit; arXiv needs the endorsement from C4 | Posted 2027-04-05 |
| D6 Site | BASIS No. 009 essay and Work entry on /publications, with the house-style PDF (reusing `reports-src/report.css` and `chartstyle.py`), built in an esnupi worktree and merged by PR, verified live with Playwright. Links to SSRN, arXiv, GitHub and Zenodo | Live and verified |
| D7 After posting | One journal at a time (shortlist and rules in `docs/venues.md`); a student or conference session; LinkedIn and résumé lines | Submitted |

## What can be published

From `docs/data_sources.md` and the terms read for each source:

- **Fully releasable:** our benchmark measurements (own data); EIA electricity (public domain);
  Epoch AI hardware data (CC BY 4.0, with attribution); getdeploying files (CC BY); SEC EDGAR facts;
  all code, tables and figures.
- **Derived aggregates only:** prices from AWS, Azure, Google Cloud, Lambda, CoreWeave, Paperspace and
  the hand-recorded neocloud panel (monthly medians and the M4 panel's facts, not raw pages or page
  copies); Wayback-derived series (archived pages are third-party content).
- **Do not republish:** SkyPilot catalog history (no licence); the saved page copies; anything from
  Vast.ai, RunPod listings, Oracle, Silicon Data, Ornn or SemiAnalysis; NVIDIA datasheet PDFs.
  The replication package re-fetches these, with checksums, rather than shipping them.

## Timeline

| When | Milestone |
| --- | --- |
| Week of 2026-11-16 | Stage A actions; B1 |
| By 2026-12-06 | B2 (panel and descriptive memo) |
| By 2027-01-10 | B3-B4 (hedonic models, adversarial review), gate |
| Mid-January (optional) | Short reconciliation note to SSRN (decision 2) |
| By 2027-02-07 | B5 (asset values, four-way triangulation) |
| By 2027-02-28 | B6 (restatement), gate |
| By 2027-03-21 | C1-C3 complete draft; C5 summary |
| 2027-03-22 to 04-04 | C4 faculty review; D1-D4 audit, replication, public repo, DOI |
| 2027-04-05 | D5 SSRN and arXiv; D6 site the same week |
| April-May 2027 | D7 journal and conference; collector stops after the final snapshot |

Rough total: 20-25 Claude Code sessions, plus your writing and review time. Expected spend: ~$0-5/month for
backups and $0-4 for optional GPU top-ups; the droplet is already paid for.

## Decisions needed from you

1. ~~**Prose.**~~ Decided 2026-11-11: Claude drafts a first pass of each section; you edit and
   own the final text (Decision 17).
2. **Reconciliation note.** Post a short dated note to SSRN in mid-January to stake the claim
   (the proposal's plan, made because related papers keep appearing), or go straight to the full
   paper in April.
3. ~~**Chip-spec source for Phase 3.**~~ Decided 2026-11-11: Epoch AI (CC BY 4.0) first; an
   NVIDIA datasheet you download by hand only for a value Epoch lacks (Decision 18). Known gaps:
   the L40S is not in Epoch at all; FP8 is missing for the H100 PCIe and the MI300X.
4. **Site timing.** Publish the BASIS essay with the paper (recommended), or a shorter preview
   earlier.
5. **Optional top-ups:** a second price snapshot (B7), a B200 run (B7).
6. **Accounts:** contact email in `.env`; SSRN, arXiv and Zenodo accounts; a faculty reader who
   can also endorse on arXiv; alert channel and backup storage for the droplet.

## Risks

- **Scooping:** related papers keep appearing; the mid-January note (decision 2) is the hedge.
- **Phase 5 identification may disagree across strategies.** The proposal already treats the range
  as a finding.
- **Thin price coverage for older chips.** Report counts, and use the optional second snapshot.
- **Collector or droplet failure before April** (no alerts or backups yet). Stage A fixes this.
- **Time:** the paper's core (Phases 3-7) is still ahead. Keep the gates, and keep scope extras
  (more chips, resale prices) until after the draft exists.

## Status update (2026-11-11, after AJ asked for everything to be finished)

- **Done:** B4 checks with Claude draft responses (Decision 24); B5 Phase 6 (Decision 25); B6
  Phase 7 (Decision 26); C1 scaffold and `make paper`; C2 references (65, all verified);
  C3 first-draft prose for every section, built only from generated number macros; C5 summary;
  D1 audit (`docs/release_audit.md`); D2 replication tooling (`make all`, `make verify-raw`,
  `make dataset`, licence and citation drafts).
- **AJ's, still open:** answers in `docs/review_01.md`; rewriting the prose (Decision 17); the
  logged-spec proposals in Decision 24 (a)-(d); restatement inputs (server share of capex,
  finance leases, Amazon's 2025 subset); a sourced hosting cost; the six audit items; decisions
  2, 4, 5 and 6 above; C4 faculty review; D3-D7 (public repo, Zenodo, SSRN/arXiv, site, journal).

## Release update (2026-11-11)

- **D6 site: done.** BASIS No. 009 ("How fast do GPUs lose value? Nine years of rents") and Work 04
  "Rental-Implied Depreciation" (Esn-0014, esnupi Publications No. 32, 9-page house-style report)
  merged to the esnupi site in ajaiupadhyaya/esnupi#9; Vercel production deployment READY. Report
  source: `~/Documents/esnupi/reports-src/rental-implied-depreciation/` (numbers filled from this
  repository's committed tables).
- **D2 public PDFs:** `make paper-public` builds the paper and summary with the [AJ] marks hidden
  and the author line set.
- **D3 still AJ's:** the repository is pushed but still private; flipping it to public was blocked
  by the session's permission rules. Then tag v1.0.0 and connect Zenodo (D4); SSRN/arXiv (D5)
  need AJ's accounts and, by the plan, faculty review (C4) first.
