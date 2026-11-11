# Server and network-equipment useful lives, 2020 onward

Every quote below is copied from the visible text of a filing document fetched from EDGAR
Archives and stored, with a `.json` sidecar (source URL, UTC retrieval time, HTTP status), under
`data/raw/edgar/filings/{ticker}/{accession}/`. Fetched on 2026-11-11 (UTC) by
`uv run python -m gel.collect.edgar filings`. Text is extracted by `gel.parse.edgar.html_to_text`
(inline-XBRL header removed, whitespace collapsed). Every `Quote:` line is checked against its raw
file by `uv run python -m gel.parse.edgar verify` (0 problems on 2026-11-11). Nothing inside
quotation marks is paraphrased; text outside quotation marks is my summary.

URL pattern: `https://www.sec.gov/Archives/edgar/data/{CIK}/{accession without dashes}/{document}`.
CIKs come from SEC's `company_tickers.json` (raw copy in `data/raw/edgar/2026-11-11/`).

The life history used by the restatement is in `config/accounting.yaml` (`book_life`).

## Summary of changes (server lives; network equipment noted where it differs)

| Effective | Firm | Change | Reported effect (filing) |
| --- | --- | --- | --- |
| Jan 2020 | Amazon | servers 3 → 4 years | $2.3B anticipated 2020 operating income (FY2019 10-K) |
| Jul 2020 (FY2021) | Microsoft | servers 3 → 4, network 2 → 4 years | $2.7B FY2021 operating income (FY2021 10-K) |
| Jan 2021 | Alphabet | servers 3 → 4, certain network 3 → 5 years | $2.6B less 2021 depreciation (FY2021 10-K) |
| 2021 and earlier | Meta | selected server and network cohorts 3 → 4 years | $620M less 2021 depreciation (FY2021 10-K) |
| Jan 2022 | Amazon | servers 4 → 5, networking 5 → 6 years | $3.6B less 2022 D&A (FY2022 10-K) |
| Q2 and Q4 2022 | Meta | majority of servers and network 4 → 4.5 → 5 years | $860M less 2022 depreciation (FY2022 10-K) |
| Jun 2022 (FY2023) | Oracle | servers 4 → 5 years | $434M lower FY2023 operating expenses (FY2023 10-K) |
| Jul 2022 (FY2023) | Microsoft | servers and network 4 → 6 years | $3.7B FY2023 operating income (FY2023 10-K) |
| Jan 2023 | Alphabet | servers 4 → 6, certain network 5 → 6 years | $3.9B less 2023 depreciation (FY2023 10-K) |
| Jan 2023 | CoreWeave | computing equipment 5 → 6 years | $20M lower 2023 total expenses (424B4; FY2025 10-K) |
| Jan 2024 | Amazon | servers 5 → 6 years | $3.2B less 2024 D&A (FY2024 10-K) |
| Jun 2024 (FY2025) | Oracle | servers and networking 5 → 6 years | $733M lower FY2025 operating expenses (FY2025 10-K) |
| Jan 2025 | Amazon | a subset of servers and networking 6 → 5 years | $1.4B more 2025 D&A (FY2025 10-K) |
| Jan 2025 | Meta | most servers and network to 5.5 years | $2.92B less 2025 depreciation (FY2025 10-K) |
| Jan 2026 | Nebius | servers and network 4 → 5 years | ~$167.6M expected less 2026 depreciation (FY2025 20-F); $43.1M Q1 2026 (6-K) |

## Cross-check against the proposal's useful-life table (docs/proposal.md, Motivation)

The proposal's table (sourced to an American Compute compilation, not to the filings) has eight
rows. Each was checked against the filing text below.

| Proposal row | Filing check | Status |
| --- | --- | --- |
| Jan 2026, Nebius, 4 → 5, "Not quantified in the 20-F or Q1 2026 6-K" | Change confirmed. The effect IS quantified: the FY2025 20-F expects about $167.6 million lower FY2026 depreciation, and the Q1 2026 6-K (Exhibit 99.2) reports a $43.1 (USD millions) reduction for Q1 2026 | **MISMATCH (effect column)** |
| Jan 2025, Amazon (subset), 6 → 5, $1.4B more 2025 depreciation | Confirmed (FY2025 10-K). The FY2024 10-K had anticipated about $0.7 billion lower 2025 operating income for assets on hand at Dec 31, 2024 | Match (note the ex-ante figure differs) |
| Jan 2025, Meta, 5 → 5.5, $2.92B less 2025 depreciation | Confirmed: "most servers and network assets to 5.5 years"; prior range "Four to Five years" | Match |
| Jan 2024, Amazon, 5 → 6, $3.2B less 2024 depreciation | Confirmed (reduction in depreciation and amortization of $3.2 billion) | Match |
| Jun 2024 (FY2025), Oracle, 5 → 6, $733M lower FY2025 operating expenses | Confirmed; the change covers servers and networking equipment | Match |
| Jan 2023, Alphabet, 4 → 6, $3.9B less 2023 depreciation | Confirmed for servers; certain network equipment went 5 → 6 | Match |
| Jan 2023, CoreWeave, 5 → 6, $20M lower 2023 expenses | Confirmed ("computing equipment utilized in data centers"; "reduction in total expenses of $20 million") | Match |
| Jul 2022 (FY2023), Microsoft, 4 → 6, $3.7B higher FY2023 operating income | Confirmed | Match |

Changes since 2020 that the proposal's table omits (it is labelled "Selected", so these are
omissions, not errors): Amazon Jan 2020 (3 → 4) and Jan 2022 (4 → 5); Microsoft Jul 2020
(3 → 4); Alphabet Jan 2021 (3 → 4); Meta 2021 (selected cohorts 3 → 4) and 2022 (4 → 4.5 → 5);
Oracle FY2023 (4 → 5). The proposal's prose ("From 2020 to 2024, Microsoft, Alphabet and Amazon
stretched server lives to 6 years. Meta reached 5.5 in 2025.") is consistent with the filings.

## Amazon (AMZN, CIK 1018724)

### AMZN FY2019 10-K (accession 0001018724-20-000004, filed 2020-01-31)
- URL: https://www.sec.gov/Archives/edgar/data/1018724/000101872420000004/amzn-20191231x10k.htm
- Raw file: `data/raw/edgar/filings/AMZN/0001018724-20-000004/amzn-20191231x10k.htm`
- Quote: "Depreciation and amortization is recorded on a straight-line basis over the estimated useful lives of the assets (generally the lesser of 40 years or the remaining life of the underlying building, three years for our servers, five years for networking equipment, ten years for heavy equipment, and three to seven years for other fulfillment equipment)."
- Quote: "For example, in Q4 2019 we completed a useful life study for our servers and are increasing the useful life from three years to four years for servers in January 2020, which, based on servers that are included in “Property and equipment, net” as of December 31, 2019, will have an anticipated impact to our 2020 operating income of $2.3 billion."

### AMZN Q1 2020 10-Q (accession 0001018724-20-000010, filed 2020-05-01)
- URL: https://www.sec.gov/Archives/edgar/data/1018724/000101872420000010/amzn-20200331x10q.htm
- Raw file: `data/raw/edgar/filings/AMZN/0001018724-20-000010/amzn-20200331x10q.htm`
- Quote: "We review the useful lives of equipment on an ongoing basis, and effective January 1, 2020 we changed our estimate of the useful life for our servers from three to four years."

### AMZN FY2021 10-K (accession 0001018724-22-000005, filed 2022-02-04)
- URL: https://www.sec.gov/Archives/edgar/data/1018724/000101872422000005/amzn-20211231.htm
- Raw file: `data/raw/edgar/filings/AMZN/0001018724-22-000005/amzn-20211231.htm`
- Quote: "For example, in Q4 2021 we completed a useful life study for our servers and networking equipment and are increasing the useful lives from four years to five years for servers and from five years to six years for networking equipment in January 2022, which, based on servers and networking equipment that are included in “Property and equipment, net” as of December 31, 2021, will have an anticipated impact to our 2022 operating income of $3.1 billion."

### AMZN FY2022 10-K (accession 0001018724-23-000004, filed 2023-02-03)
- URL: https://www.sec.gov/Archives/edgar/data/1018724/000101872423000004/amzn-20221231.htm
- Raw file: `data/raw/edgar/filings/AMZN/0001018724-23-000004/amzn-20221231.htm`
- Quote: "We review the useful lives of equipment on an ongoing basis, and effective January 1, 2022 we changed our estimate of the useful lives for our servers from four years to five years and for our networking equipment from five years to six years."
- Quote: "The effect of this change in estimate for the year ended December 31, 2022, based on servers and networking equipment that were included in “Property and equipment, net” as of December 31, 2021 and those acquired during the year ended December 31, 2022, was a reduction in depreciation and amortization expense of $3.6 billion and a benefit to net loss of $2.8 billion, or $0.28 per basic share and $0.28 per diluted share."

### AMZN FY2023 10-K (accession 0001018724-24-000008, filed 2024-02-02)
- URL: https://www.sec.gov/Archives/edgar/data/1018724/000101872424000008/amzn-20231231.htm
- Raw file: `data/raw/edgar/filings/AMZN/0001018724-24-000008/amzn-20231231.htm`
- Quote: "For example, in Q4 2023 we completed a useful life study for our servers and are increasing the useful life from five years to six years in January 2024, which, based on servers that are included in “Property and equipment, net” as of December 31, 2023, will have an anticipated impact to our 2024 operating income of $3.1 billion."

### AMZN FY2024 10-K (accession 0001018724-25-000004, filed 2025-02-07)
- URL: https://www.sec.gov/Archives/edgar/data/1018724/000101872425000004/amzn-20241231.htm
- Raw file: `data/raw/edgar/filings/AMZN/0001018724-25-000004/amzn-20241231.htm`
- Quote: "The effect of this change for the year ended December 31, 2024, based on servers that were included in “Property and equipment, 41 Table of Contents net” as of December 31, 2023 and those acquired during the year ended December 31, 2024, was a reduction in depreciation and amortization expense of $3.2 billion and a benefit to net income of $2.5 billion, or $0.23 per basic share and $0.23 per diluted share."
- Quote: "We completed our most recent servers and networking equipment useful life study in Q4 2024, and are changing the useful lives of a subset of our servers and networking equipment, effective January 1, 2025, from six years to five years."
- Quote: "For those assets included in “Property and equipment, net” as of December 31, 2024, whose useful life will change from six years to five years, we anticipate a decrease in 2025 operating income of approximately $0.7 billion."
- Quote: "These server and networking equipment useful life changes primarily impact our AWS segment."
- Note: the first quote contains a page break ("41 Table of Contents") inside the sentence, as in the filing.

### AMZN FY2025 10-K (accession 0001018724-26-000004, filed 2026-02-06)
- URL: https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm
- Raw file: `data/raw/edgar/filings/AMZN/0001018724-26-000004/amzn-20251231.htm`
- Quote: "Effective January 1, 2025 we changed our estimate of the useful lives of a subset of our servers and networking equipment from six years to five years."
- Quote: "The effect of this change in estimate for the year ended December 31, 2025, based on servers and networking equipment that were included in “Property and equipment, net” as of December 31, 2024 and those acquired during the year ended December 31, 2025, was an increase in depreciation and amortization expense of $1.4 billion and a reduction in net income of $1.0 billion, or $0.10 per basic share and $0.10 per diluted share, which primarily impacted our AWS segment."
- Note: the filing does not say which servers form the "subset". The restatement assumes GPU servers are in it (`book_life.AMZN`), with the alternative that they stay at six years (`book_life_alternatives.AMZN_gpu_not_in_subset`).

## Microsoft (MSFT, CIK 789019; fiscal year ends June 30)

### MSFT FY2020 10-K (accession 0001564590-20-034944, filed 2020-07-30)
- URL: https://www.sec.gov/Archives/edgar/data/789019/000156459020034944/msft-10k_20200630.htm
- Raw file: `data/raw/edgar/filings/MSFT/0001564590-20-034944/msft-10k_20200630.htm`
- Quote: "In July 2020, we completed an assessment of the useful lives of our server and network equipment and determined we should increase the estimated useful life of server equipment from three years to four years and increase the estimated useful life of network equipment from two years to four years."
- Quote: "The estimated useful lives of our property and equipment are generally as follows: computer software developed or acquired for internal use, three to seven years; computer equipment, two to three years; buildings and improvements, five to 15 years; leasehold improvements, three to 20 years; and furniture and equipment, one to 10 years."

### MSFT FY2021 10-K (accession 0001564590-21-039151, filed 2021-07-29)
- URL: https://www.sec.gov/Archives/edgar/data/789019/000156459021039151/msft-10k_20210630.htm
- Raw file: `data/raw/edgar/filings/MSFT/0001564590-21-039151/msft-10k_20210630.htm`
- Quote: "Based on the carrying amount of server and network equipment included in property and equipment, net as of June 30, 2020, the effect of this change in estimate for fiscal year 2021 was an increase in operating income of $2.7 billion and net income of $2.3 billion, or $0.30 per both basic and diluted share."

### MSFT FY2022 10-K (accession 0001564590-22-026876, filed 2022-07-28)
- URL: https://www.sec.gov/Archives/edgar/data/789019/000156459022026876/msft-10k_20220630.htm
- Raw file: `data/raw/edgar/filings/MSFT/0001564590-22-026876/msft-10k_20220630.htm`
- Quote: "Due to investments in software that increased efficiencies in how we operate our server and network equipment, as well as advances in technology, we determined we should increase the estimated useful lives of both server and network equipment from four years to six years."
- Quote: "Based on the carrying amount of server and network equipment included in property and equipment, net as of June 30, 2022, it is estimated this change will increase our fiscal year 2023 operating income by $3.7 billion."

### MSFT FY2023 10-K (accession 0000950170-23-035122, filed 2023-07-27)
- URL: https://www.sec.gov/Archives/edgar/data/789019/000095017023035122/msft-20230630.htm
- Raw file: `data/raw/edgar/filings/MSFT/0000950170-23-035122/msft-20230630.htm`
- Quote: "Based on the carrying amount of server and network equipment included in property and equipment, net as of June 30, 2022, the effect of this change in estimate for fiscal year 2023 was an increase in operating income of $3.7 billion and net income of $3.0 billion, or $0.40 per both basic and diluted share."
- Quote: "The estimated useful lives of our property and equipment are generally as follows: computer software developed or acquired for internal use, three years; computer equipment, two to six years; buildings and improvements, five to 15 years; leasehold improvements, three to 20 years; and furniture and equipment, one to 10 years."

### MSFT FY2026 10-K (accession 0001193125-26-323660, filed 2026-07-29)
- URL: https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm
- Raw file: `data/raw/edgar/filings/MSFT/0001193125-26-323660/msft-20260630.htm`
- Quote: "The estimated useful lives of our property and equipment are generally as follows: software developed or acquired for internal use, three years; servers and network equipment, two to six years; buildings and improvements, five to 15 years; leasehold improvements, three to 15 years; and furniture and equipment, one to 10 years."
- Note: no change after July 2022 was found in the FY2024-FY2026 10-Ks or the first 10-Q of each fiscal year.

## Alphabet (GOOGL, CIK 1652044)

### GOOGL FY2019 10-K (accession 0001652044-20-000008, filed 2020-02-04)
- URL: https://www.sec.gov/Archives/edgar/data/1652044/000165204420000008/goog10-k2019.htm
- Raw file: `data/raw/edgar/filings/GOOGL/0001652044-20-000008/goog10-k2019.htm`
- Quote: "We depreciate information technology assets generally over periods of three to five years (specifically, three years for servers and three to five years for network equipment)."

### GOOGL FY2020 10-K (accession 0001652044-21-000010, filed 2021-02-03)
- URL: https://www.sec.gov/Archives/edgar/data/1652044/000165204421000010/goog-20201231.htm
- Raw file: `data/raw/edgar/filings/GOOGL/0001652044-21-000010/goog-20201231.htm`
- Quote: "In January 2021, we completed an assessment of the useful lives of our servers and network equipment and determined we should adjust the estimated useful life of our servers from three years to four years and the estimated useful life of certain network equipment from three years to five years."
- Quote: "For assets that are in-service as of December 31, 2020, we expect operating results to be favorably impacted by approximately $2.1 billion for the full fiscal year 2021."

### GOOGL FY2021 10-K (accession 0001652044-22-000019, filed 2022-02-02)
- URL: https://www.sec.gov/Archives/edgar/data/1652044/000165204422000019/goog-20211231.htm
- Raw file: `data/raw/edgar/filings/GOOGL/0001652044-22-000019/goog-20211231.htm`
- Quote: "Based on the carrying value of servers and certain network equipment as of December 31, 2020 and those acquired during the year ended December 31, 2021, the effect of this change in estimate was a reduction in depreciation expense of $2.6 billion and an increase in net income of $2.0 billion, or $3.02 per basic share and $2.98 per diluted share, for the year ended December 31, 2021."

### GOOGL FY2022 10-K (accession 0001652044-23-000016, filed 2023-02-03)
- URL: https://www.sec.gov/Archives/edgar/data/1652044/000165204423000016/goog-20221231.htm
- Raw file: `data/raw/edgar/filings/GOOGL/0001652044-23-000016/goog-20221231.htm`
- Quote: "In January 2023, we completed an assessment of the useful lives of our servers and network equipment and adjusted the estimated useful life of our servers from four years to six years and the estimated useful life of certain network equipment from five years to six years."
- Quote: "We depreciate information technology assets generally over periods of four to five years (generally, four years for servers and five years for network equipment)."

### GOOGL FY2023 10-K (accession 0001652044-24-000022, filed 2024-01-31)
- URL: https://www.sec.gov/Archives/edgar/data/1652044/000165204424000022/goog-20231231.htm
- Raw file: `data/raw/edgar/filings/GOOGL/0001652044-24-000022/goog-20231231.htm`
- Quote: "Based on the carrying value of servers and certain network equipment as of December 31, 2022, and those placed in service during the year ended December 31, 2023, the effect of this change in estimate was a reduction in depreciation expense of $3.9 billion and an increase in net income of $3.0 billion, or $0.24 per basic and $0.24 per diluted share, for the year ended December 31, 2023."

### GOOGL FY2025 10-K (accession 0001652044-26-000018, filed 2026-02-05)
- URL: https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm
- Raw file: `data/raw/edgar/filings/GOOGL/0001652044-26-000018/goog-20251231.htm`
- Quote: "We depreciate servers and network equipment generally over a period of six years."
- Note: the same sentence appears in the FY2024 10-K (accession 0001652044-25-000014). No change after January 2023 was found.

## Meta (META, CIK 1326801)

### META FY2020 10-K (accession 0001326801-21-000014, filed 2021-01-28)
- URL: https://www.sec.gov/Archives/edgar/data/1326801/000132680121000014/fb-20201231.htm
- Raw file: `data/raw/edgar/filings/META/0001326801-21-000014/fb-20201231.htm`
- Quote: "The estimated useful lives of property and equipment are described below: Property and Equipment Useful Life Network equipment Three to 20 years Buildings Three to 30 years Computer software, office equipment and other Two to five years Finance lease right-of-use assets Three to 20 years Leasehold improvements Lesser of estimated useful life or remaining lease term The useful lives of our property and equipment are determined by management when those assets are initially recognized and are routinely reviewed for the remaining estimated useful lives."
- Note: the FY2019 and FY2020 10-Ks give no server-specific life (servers sit in "Network equipment, three to 20 years"). Server life before 2021: not found as a single figure.

### META FY2021 10-K (accession 0001326801-22-000018, filed 2022-02-03)
- URL: https://www.sec.gov/Archives/edgar/data/1326801/000132680122000018/fb-20211231.htm
- Raw file: `data/raw/edgar/filings/META/0001326801-22-000018/fb-20211231.htm`
- Quote: "In connection with our periodic reviews of the estimated useful lives of property and equipment, we extended the estimated average useful lives of selected cohorts of servers and network assets from three years to four years in prior years as well as in 2021 as a result of longer refresh cycles in our data centers."
- Quote: "The effect of the 2021 changes was a reduction in depreciation expense of $620 million and an increase in net income of $516 million, or $0.18 per diluted share for the year ended December 31, 2021."

### META FY2022 10-K (accession 0001326801-23-000013, filed 2023-02-02)
- URL: https://www.sec.gov/Archives/edgar/data/1326801/000132680123000013/meta-20221231.htm
- Raw file: `data/raw/edgar/filings/META/0001326801-23-000013/meta-20221231.htm`
- Quote: "In connection with our periodic reviews of the estimated useful lives of property and equipment, we extended the estimated average useful lives of a majority of the servers and network assets from four years to 4.5 years, effective the second quarter of 2022, and further extended the useful lives to five years effective the fourth quarter of 2022."
- Quote: "The impact from the changes in our estimates was calculated based on the servers and network assets existing as of the effective dates of the changes and applying the revised estimated useful lives prospectively."
- Quote: "The financial impact of the changes in estimates was a reduction in depreciation expense of $860 million and an increase in net income of $693 million, or $0.26 per diluted share for the year ended December 31, 2022."

### META FY2024 10-K (accession 0001326801-25-000017, filed 2025-01-30)
- URL: https://www.sec.gov/Archives/edgar/data/1326801/000132680125000017/meta-20241231.htm
- Raw file: `data/raw/edgar/filings/META/0001326801-25-000017/meta-20241231.htm`
- Quote: "In January 2025, we completed an assessment of the useful lives of certain servers and network assets, and determined we should extend the estimated useful lives to 5.5 years."

### META FY2025 10-K (accession 0001628280-26-003942, filed 2026-01-29)
- URL: https://www.sec.gov/Archives/edgar/data/1326801/000162828026003942/meta-20251231.htm
- Raw file: `data/raw/edgar/filings/META/0001628280-26-003942/meta-20251231.htm`
- Quote: "In January 2025, we completed an assessment of the useful lives of property and equipment, which resulted in an increase in the estimated useful lives of most servers and network assets to 5.5 years, effective January 1, 2025."
- Quote: "Based on the servers and network assets placed in service as of December 31, 2024, the financial impact of this change in estimate included a reduction in depreciation expense of $2.92 billion and an increase in net income of $2.59 billion, or $1.00 per diluted share, for the year ended December 31, 2025."

## Oracle (ORCL, CIK 1341439; fiscal year ends May 31)

### ORCL FY2022 10-K (accession 0001564590-22-023675, filed 2022-06-21)
- URL: https://www.sec.gov/Archives/edgar/data/1341439/000156459022023675/orcl-10k_20220531.htm
- Raw file: `data/raw/edgar/filings/ORCL/0001564590-22-023675/orcl-10k_20220531.htm`
- Note: the PP&E note gives "Computer, network, machinery and equipment" a 1-5 year range; no server-specific life before FY2023 was found other than the "from four years" in the FY2023 change below.

### ORCL FY2023 10-K (accession 0000950170-23-028914, filed 2023-06-20)
- URL: https://www.sec.gov/Archives/edgar/data/1341439/000095017023028914/orcl-20230531.htm
- Raw file: `data/raw/edgar/filings/ORCL/0000950170-23-028914/orcl-20230531.htm`
- Quote: "During the first quarter of fiscal 2023, we completed an assessment of the useful lives of our servers and increased the estimate of the useful lives from four years to five years effective at the beginning of fiscal 2023."
- Quote: "Based on the carrying value of our servers as of May 31, 2022, this change in accounting estimate decreased our total operating expenses by $434 million during fiscal 2023."

### ORCL Q1 FY2025 10-Q (accession 0000950170-24-104905, filed 2024-09-10)
- URL: https://www.sec.gov/Archives/edgar/data/1341439/000095017024104905/orcl-20240831.htm
- Raw file: `data/raw/edgar/filings/ORCL/0000950170-24-104905/orcl-20240831.htm`
- Quote: "During the first quarter of fiscal 2025, we completed an assessment of the useful lives of our servers and networking equipment and increased the estimate of the useful lives from five years to six years, effective at the beginning of fiscal 2025."

### ORCL FY2025 10-K (accession 0000950170-25-087926, filed 2025-06-18)
- URL: https://www.sec.gov/Archives/edgar/data/1341439/000095017025087926/orcl-20250531.htm
- Raw file: `data/raw/edgar/filings/ORCL/0000950170-25-087926/orcl-20250531.htm`
- Quote: "Based on the carrying value of our servers and networking equipment as of May 31, 2024, this change in accounting estimate decreased our total operating expenses by $733 million and increased our net income by $573 million, or $0.21 per basic and $0.20 per diluted share, during fiscal 2025."

### ORCL FY2026 10-K (accession 0001193125-26-277521, filed 2026-06-22)
- URL: https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm
- Raw file: `data/raw/edgar/filings/ORCL/0001193125-26-277521/orcl-20260531.htm`
- Quote: "Comprised primarily of servers and networking equipment with estimated useful life of six years."

## CoreWeave (CRWV, CIK 1769628)

CoreWeave's first 10-K covers FY2025, so the 2023 change is first quoted from the IPO prospectus
(Form 424B4, an EDGAR filing outside the 10-K/10-Q/6-K set; fetched by accession).

### CRWV 424B4 prospectus (accession 0001193125-25-067651, filed 2025-03-31)
- URL: https://www.sec.gov/Archives/edgar/data/1769628/000119312525067651/d899798d424b4.htm
- Raw file: `data/raw/edgar/filings/CRWV/0001193125-25-067651/d899798d424b4.htm`
- Quote: "Effective January 1, 2023, the Company changed its estimate of the useful life for its computing equipment utilized in data centers from five to six years, reflecting continuous advancements in hardware performance, software optimization, and data center design improvements."
- Quote: "The effects of this change in estimate for the year ended December 31, 2023 on computing equipment that was included in property and equipment, net on the consolidated balance sheets as of December 31, 2023 was a reduction in total expenses of $20 million."

### CRWV FY2025 10-K (accession 0001769628-26-000104, filed 2026-03-02)
- URL: https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/crwv-20251231.htm
- Raw file: `data/raw/edgar/filings/CRWV/0001769628-26-000104/crwv-20251231.htm`
- Quote: "Effective January 1, 2023, the Company changed its estimate of the useful life for its computing equipment utilized in data centers from five to six years, reflecting continuous advancements in hardware performance, software optimization, and data center design improvements."
- Quote: "The per share impact of the change in estimate was a $0.10 increase for the year ended December 31, 2023."

## Nebius (NBIS, formerly Yandex N.V., CIK 1513845; files 20-F and 6-K)

### NBIS (Yandex) FY2021 20-F (accession 0001558370-22-005654, filed 2022-04-20)
- URL: https://www.sec.gov/Archives/edgar/data/1513845/000155837022005654/yndx-20211231x20f.htm
- Raw file: `data/raw/edgar/filings/NBIS/0001558370-22-005654/yndx-20211231x20f.htm`
- Quote: "Depreciation is computed under the straight-line method using estimated useful lives as follows: Estimated useful lives Servers and network equipment 4.0 years Infrastructure systems 3.0-10.0 years Office furniture and equipment 1.0 - 3.0 years Buildings 10.0-20.0 years Land rights 50.0 years Leasehold improvements the shorter of 5.0 years or the remaining period of the lease term Other equipment 2.0‑10.0 years Land is not depreciated."
- Note: the FY2019 and FY2020 20-Fs give "Servers and network equipment 3.0-4.0 years". The FY2023 20-F table has no server line. These are Yandex group policies, before the 2024 divestment.

### NBIS FY2024 20-F (accession 0001558370-25-005991, filed 2025-04-30)
- URL: https://www.sec.gov/Archives/edgar/data/1513845/000155837025005991/nbis-20241231x20f.htm
- Raw file: `data/raw/edgar/filings/NBIS/0001558370-25-005991/nbis-20241231x20f.htm`
- Quote: "Depreciation is computed under the straight-line method using estimated useful lives as follows: Estimated useful lives Server and network equipment 4.0 years Infrastructure systems and equipment 3.0-10.0 years Office furniture and equipment 3.0 years Buildings 20.0 years Other property and equipment 2.0-5.0 years Land is not depreciated."

### NBIS FY2025 20-F (accession 0001104659-26-052948, filed 2026-04-30)
- URL: https://www.sec.gov/Archives/edgar/data/1513845/000110465926052948/nbis-20251231x20f.htm
- Raw file: `data/raw/edgar/filings/NBIS/0001104659-26-052948/nbis-20251231x20f.htm`
- Quote: "In January 2026, the Company completed an assessment of the useful lives of servers and network equipment based on updated information and usage patterns obtained subsequent to year-end and concluded that the estimated useful lives of such assets should be extended from four to five years."
- Quote: "Management is considering the application of this change in accounting estimate prospectively beginning January 1, 2026."
- Quote: "Based on the servers and network equipment placed in service as of December 31, 2025, we expect this change in accounting estimate will reduce the depreciation expenses for fiscal year 2026 by approximately $167.6 million."

### NBIS Q1 2026 6-K, Exhibit 99.2 (accession 0001104659-26-064092, filed 2026-05-20)
- URL: https://www.sec.gov/Archives/edgar/data/1513845/000110465926064092/nbis-20260331xex99d2.htm
- Raw file: `data/raw/edgar/filings/NBIS/0001104659-26-064092/nbis-20260331xex99d2.htm`
- Quote: "Management applied this change in accounting estimate prospectively beginning January 1, 2026."
- Quote: "Based on the servers and network equipment placed in service as of December 31, 2025, the financial impact of this change in estimate included a reduction in depreciation expense of $43.1 and an increase in net income of $41.6, for the three months ended March 31, 2026."
- Quote: "In millions of U.S. dollars (“$”), except share and per share data)"
- Note: the sentence above carries no unit; the exhibit's statements are headed with the unit just quoted, so the amounts read as USD 43.1 million and USD 41.6 million.

### NBIS Q1 2026 6-K, Exhibit 99.1 (accession 0001104659-26-064092, filed 2026-05-20)
- URL: https://www.sec.gov/Archives/edgar/data/1513845/000110465926064092/nbis-20260331xex99d1.htm
- Raw file: `data/raw/edgar/filings/NBIS/0001104659-26-064092/nbis-20260331xex99d1.htm`
- Quote: "Starting the first quarter of 2026, we revised the useful life for our server and network equipment from four years to five years to reflect usage patterns and current utilization commitments."

## Open items

1. Share of capex that is servers and network equipment: not disclosed by any of the seven firms
   in the filings searched (latest 10-K/20-F of each). The restatement uses an assumption grid
   (0.4, 0.6, 0.8; baseline 0.6). A filing-based proxy (change in the gross server/network PP&E
   class over change in total gross PP&E, from the PP&E notes) is possible for Meta, Oracle,
   Microsoft (FY2026), CoreWeave and Nebius but not built.
2. Which Amazon servers form the 2025 "subset" moved from six to five years: not found.
3. Meta server life before 2021 as a single figure: not found (servers were inside "Network
   equipment, three to 20 years").
4. Oracle server life before FY2023: only implied by "from four years" in the FY2023 change.
5. Meta's Q2 2022 and Q4 2022 changes were first reported in the Q2 and Q4 2022 filings, which
   were not fetched; the FY2022 10-K quote above covers both.
6. NBIS Exhibit 99.2 amounts ($43.1, $41.6) carry no unit in the quoted sentence; read as USD
   millions from the statement headings (inference, flagged).
