# Revision notices: drafts for AJ (2026-11-16)

Step 2 of the plan to republish (`docs/finish_plan.md`, "Withdrawal for revision"). The repository
already says this (README and `CITATION.cff`, commit 0b20125). Below is matching text for every
public place outside the repository that still presents v1.0.0–v1.0.3 as current. All of it is
draft text: nothing has been posted or changed. Edit freely; each notice uses the same core wording
so the record stays consistent.

**Core notice (use as is or shorten):**

> **Under revision (November 2026).** This working paper has been withdrawn from SSRN while it is
> revised after an internal review. The versions released so far (v1.0.0–v1.0.3) are superseded
> drafts; please do not cite their results. The revision changes the statistical inference behind
> the headline tables and the claims that depend on it, and will be released as v1.1.0.

---

## 1. GitHub release notes (v1.0.0, v1.0.1, v1.0.2, v1.0.3)

Add the notice at the **top** of each release's notes and keep the existing text below it, so the
history stays readable. On GitHub: Releases → the release → Edit (pencil) → paste above the
current text → Update release.

```markdown
> **Superseded draft, under revision (November 2026).** This working paper has been withdrawn from
> SSRN while it is revised after an internal review; please do not cite the results in this
> release. The revision changes the statistical inference behind the headline tables and the claims
> that depend on it, and will be released as v1.1.0. See the README for the current status.
```

For v1.0.0, also change the last line's site link text if you edit the site entry below (the URL
can stay).

## 2. Zenodo: code record (concept doi:10.5281/zenodo.24143073)

Zenodo lets you edit a published record's metadata without changing its DOI or files: open the
record → Edit → change the description → Publish. Do it at least for the latest version (v1.0.3,
doi:10.5281/zenodo.24181545). Doing it for v1.0.1 and v1.0.2 as well means the notice shows on
whichever version someone lands on.

Put this at the start of the description, before the existing text:

```text
SUPERSEDED DRAFT, UNDER REVISION (November 2026). The working paper in this record has been withdrawn from SSRN while it is revised after an internal review; please do not cite its results. The revision changes the statistical inference behind the headline tables and the claims that depend on it, and will be released as version 1.1.0 of this record. The code, data panel and logs below are unchanged.
```

Optionally, under Related works, remove any link to the SSRN abstract (7692700) if one was added.

## 3. Zenodo: data record (concept doi:10.5281/zenodo.24143179)

The data themselves are not known to be wrong, so this notice is milder. Put it at the start of
the description of doi:10.5281/zenodo.24143180:

```text
NOTE (November 2026): The working paper built on this dataset is under revision and its earlier versions (v1.0.0–v1.0.3) are superseded drafts. The panel in this record is not known to be wrong; a revised dataset version may accompany the revised paper (v1.1.0).
```

## 4. Your site (esnupi): BASIS No. 009 and Work 04

Site files on `main` that present the paper as current. Line numbers are from `origin/main` at
3f8951a.

**a. Essay, `src/content/basis/009-rental-implied-depreciation.mdx`.**

- Add a banner directly after the `meta` block, above the first paragraph:

  ```mdx
  > **Under revision (November 2026).** I have withdrawn this working paper from SSRN while I revise
  > it after an internal review. Some findings below may change, in particular the claim that the
  > shape of the decline flips between spot and list prices (section 2) and the valuation in
  > section 3. The versions released so far are drafts; please don't cite their results yet.
  ```

- Line 10: replace "It is a preprint [on SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7692700), under review there." with "It is a working paper, now under revision."
- Line 67: delete "[SSRN preprint](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7692700), " from the sources line.
- Optional: the `dek` says the shape "flips with the market you read", which the reviewer
  flagged as resting on invalid inference. A safer dek: "Posted GPU rents fall slowly, seven chips
  cannot pin down a rate, and the paper behind this essay is being revised."

**b. Work entry, `src/lib/projectsData.ts` (entry `rental-implied-depreciation`, lines 158-186).**

- `status: "complete"` → `status: "ongoing"` (an existing value in the type).
- Delete line 173, the `{ label: "SSRN", ... }` link.
- Prefix the `blurb` with "Under revision. ".
- Prefix the report `abstract` with "Draft under revision (November 2026); results may change. ".
- The hosted PDF (`/reports/rental-implied-depreciation.pdf`) is the v1.0.3 paper. Either keep it
  and rely on the notice above, or remove the report link until v1.1.0.

**c. `public/llms.txt`, line 14.** Append " (under revision)" to the BASIS No. 009 description.

---

Once you've decided the wording, I can open a site pull request with section 4's changes (as with
esnupi #9-#12) and update the GitHub release notes with `gh release edit`. Both are public, so I'll
only do them on your go-ahead. The Zenodo edits need your sign-in.
