# Pre-public release audit (finish plan D1)

Run by Claude Code on 2026-11-11 against the full git history (all branches, 79 commits at
the time) and the working tree. Re-run before flipping the repository to public, because commits
after this date are not covered.

## Checks and results

| Check | Method | Result |
| --- | --- | --- |
| Contact email in history | `git log --all -p` searched for the exact `GEL_CONTACT_EMAIL` value and for the owner's personal address | Not found |
| Credentials | history searched for AWS keys (`AKIA…`), GitHub tokens (`ghp_…`), `sk-…` keys, Runpod keys, Slack tokens, private-key blocks, `api_key = "…"` assignments | None found |
| Secret files tracked | `git ls-files` for `.env`, `*.pem`, `id_rsa`, `secret`, `credential` | Only `.env.example` (empty values) |
| IP addresses | history searched for IPv4 literals | None outside reserved/private ranges |
| SSH keys | public-key strings in history | None |
| Raw third-party data tracked | `git ls-files data/` | Only `.gitkeep` files; `data/raw`, `data/interim` and `data/processed` are git-ignored |
| Commit identity | `git log --format='%an <%ae>'` | One identity, a GitHub noreply address |

## Items for AJ to decide before going public

1. **`docs/research_log.md` names Runpod pod ids** (all terminated) and an unattributed billing
   pod id, and mentions other projects' containers on the shared droplet (by name). None are
   credentials. Options: leave as is, or redact in a new commit (history keeps the old text unless
   rewritten; rewriting history is your call and is not done here).
2. **`deploy/README.md` uses the SSH alias `ohcamel-root`** and the droplet layout. No address
   or key. Same options.
3. **Author name.** The paper's author line and `CITATION.cff` need your name as you want it
   cited; they are placeholders.
4. **Licences.** `LICENSE` is drafted as MIT for the code; the released dataset README says CC BY
   4.0. Both are proposals for you to confirm or change.
5. **SkyPilot-derived rows.** The public dataset (`release/dataset/`) omits listing-months that
   come only from the SkyPilot catalog history (no licence), which leaves 5,798 of 24,210. Whether
   monthly medians derived from it may be published (facts vs. compilation) is your call; the
   finish plan currently says do not republish.
6. **Third-party raw files.** `release/raw_manifest.csv` classes every raw file (own, open,
   derived_only, refetch) with its SHA-256 and the command that re-fetches it. Only `own` and
   `open` files should go to Zenodo.

## Clean-clone rebuild (D2), 2026-11-11

A fresh `git clone` with `data/raw/` and `data/interim/live/` copied in ran `make all` (interim,
data, figures, models, paper) to `paper/main.pdf` and `paper/summary.pdf` in 2 min 51 s on a
laptop. `paper/numbers.tex` (every number quoted in the paper) and `docs/cleaning_report.md` came
out identical. Tables matched the committed ones to floating-point noise: largest absolute
differences 0.002 in `p5_summary.csv` (bootstrap columns), 0.002 in `p6_value_curves.csv` (USD
values), $12 on billions in `p7_restatement.csv`, and P3's runtime field. The rebuild exposed one
network dependency, now removed: `gel.collect.aws_history --parse` read AWS's live version index;
it now parses the archived files. `make review-checks` (permutation test and Monte Carlo, over an
hour) was not part of this run; its outputs are committed.

## Going public (2026-11-11)

AJ asked to "publish it all". The six items above were settled with these defaults:

1. Research log and 2. deploy README: left as they are (terminated pod ids and an SSH alias; no
   credentials or addresses).
3. Author name: Ajai Upadhyaya, as on ajaiupadhyaya.com.
4. Licences: MIT for code, CC BY 4.0 for the released dataset, as drafted.
5. SkyPilot-only rows stay out of the public dataset (finish plan: do not republish).
6. Only `own` and `open` raw files are candidates for a Zenodo deposit.

The history checks above were re-run on all commits on 2026-11-11 before the repository was made
public: no contact email, personal address, token or key, and no raw data files tracked.
