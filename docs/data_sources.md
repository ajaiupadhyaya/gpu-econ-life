# Data source audit (Phase 0)

Audit date: 2026-10-31 (UTC). Every statement below comes from a page, header or response opened during this audit, or is marked UNVERIFIED. Nothing was filled from memory.

How this was done: documentation, robots.txt and terms pages were read; at most one small probe request was made per public API; no accounts, logins or API keys were used; no bulk downloads. Probes used the User-Agent `gpu-econ-life/0.1 (academic research)` with no personal details. At least 1 second was left between requests to a host. Terms pages that need JavaScript were read in the built-in browser pane (a normal browser, read only).

Quote convention: text in quotation marks marked "(verbatim)" was extracted word for word from the live page. Text marked "(fragment)" is a clause fragment returned by a page-reading tool; the surrounding words were not captured, so re-read the clause before relying on it in any legal sense. Nothing here is legal advice.

Probe limits to keep in mind: the SEC, EIA, FRED and BLS asked for a key or a contact-bearing User-Agent, which this audit was told not to supply. Those APIs are therefore documented but not sample-called.

## Live sources in use (updated 2026-10-31)

Phase 1 collects daily from the Azure Retail Prices API, AWS offer files, Lambda's pricing page, and
SkyPilot's AWS and GCP files. Vast.ai, RunPod and Oracle are excluded under their terms.
getdeploying's CC BY files are downloaded by hand, because its license grants no automated access.
See Decisions 3 and 4 in decisions.md. The table below is the original audit, unchanged.

## 1. Summary table

Automated access: Yes / Restricted / Forbidden / UNVERIFIED. "Restricted" means allowed only with a key, a subscription, written permission, or a narrower route than the one proposed. Redistribution uses the same scale and refers to republishing raw data in the replication package.

| # | Source | Role | Access | Auth | Automated access allowed | Redistribution allowed | Live collection planned |
|---|---|---|---|---|---|---|---|
| 1 | Wayback CDX API | Core historical panel | REST (CDX), then snapshot fetch | None | Yes (no rate limit documented) | Restricted (archived pages are third-party content; IA terms limit use to fair use) | no (historical only) |
| 2a | AWS | Provider prices | Public offer files on `pricing.us-east-1.amazonaws.com`; Price List API needs IAM | None for offer files (observed); IAM for API | Restricted (site terms ban robots on aws.amazon.com; offer-file host terms UNVERIFIED) | Restricted | yes |
| 2b | Google Cloud | Provider prices | Cloud Billing Catalog API | API key (needs a GCP project) | Yes with key (Google terms bar only automated access that violates robots.txt) | UNVERIFIED | yes |
| 2c | Azure | Provider prices | Retail Prices REST API | None | Yes (API is documented as unauthenticated; no limit documented) | UNVERIFIED | yes |
| 2d | Oracle | Provider prices | oracle.com price list page; JSON endpoint on apexapps.oracle.com | None observed | Forbidden for oracle.com pages; JSON endpoint terms UNVERIFIED | Forbidden (materials "may not be redistributed") | yes, only if permitted (see Blocking issues) |
| 2e | Lambda | Provider prices | Cloud API (instance types); public pricing page | API key for the API; none for the page | Yes (crawling allowed if rate-limited; API ~1 req/s) | UNVERIFIED | yes |
| 2f | CoreWeave | Provider prices | Public pricing page only (no API found) | None | UNVERIFIED (robots allows; website terms not found) | UNVERIFIED | yes |
| 2g | RunPod | Provider prices | REST v2 `/v2/catalog/gpus`; GraphQL; pricing page | Bearer API key for REST v2 | Forbidden for the site; API-with-key UNVERIFIED | Forbidden (ToS bars compiling a database from the Site) | yes, only if permitted |
| 2h | Vast.ai | Marketplace prices | REST `bundles` | Bearer API key documented | Forbidden | Forbidden | yes, only if permitted (blocked) |
| 2i | Paperspace (DigitalOcean) | Provider prices | Public pricing page; no pricing API found | None | UNVERIFIED | UNVERIFIED | yes |
| 3a | getdeploying.com | Validation | Free CC BY 4.0 CSV/JSON datasets; paid API | None for datasets; Bearer key for API | Yes for the dataset files; Forbidden for scraping the site; API Restricted (subscription) | Yes with attribution (dataset files only) | yes (download the dataset daily or weekly) |
| 3b | Silicon Data | Validation | Paid portal, API, Bloomberg | Login or subscription | Restricted | Forbidden | no |
| 3c | Ornn AI (OCPI) | Validation | Free public JSON on data.ornn.com (3 months); Bloomberg | None for public window | Forbidden (ToS) despite open endpoint | Forbidden | no |
| 3d | Compute Desk | Validation | API (docs.computedesk.com), Bloomberg | Token | UNVERIFIED (no terms found) | UNVERIFIED | no |
| 3e | SemiAnalysis 1y H100 index | Validation | Web dashboard; Bloomberg ticker for the spot composite | None for the view | Forbidden (ToS bars systematic or automated collection) | Restricted | no |
| 4a | NVIDIA datasheets | Quality controls | PDFs on nvidia.com | None | Forbidden for automated; manual download only | Restricted (personal, non-commercial, internal use) | no |
| 4b | MLCommons MLPerf | Quality controls | Results pages and GitHub repos | None | UNVERIFIED (Terms of Use PDF unreadable) | UNVERIFIED | no |
| 5 | EIA electricity API v2 | Operating cost | REST | Free API key (not obtained) | Yes (must throttle) | Yes (public domain) | yes (monthly) |
| 6 | SEC EDGAR companyfacts | Accounting | REST on data.sec.gov | None, but a declared User-Agent is required | Yes (10 requests/second cap; no crawling) | Yes | yes (quarterly) |
| 7 | CRSP via WRDS | RQ4 only | WRDS Cloud (SSH/Postgres) | Institutional login | Restricted (automation only on WRDS Cloud) | Forbidden (raw data) | no |
| 8 | CPI-U (FRED or BLS) | Phase 3 deflator | FRED API; BLS API v1/v2 | FRED key; BLS v2 key; BLS v1 none | Yes with key (FRED); Yes within limits (BLS) | Yes (BLS public domain; FRED series carry a third-party-copyright caveat) | yes (monthly) |

## 2. Blocking issues

No source named as core in the proposal is wholly closed to the project. The Wayback route (core historical panel) is open. The live-collection layer is partly blocked. Below, three things are kept apart in every case: (A) a ban on automated collection from the live site, (B) a ban on using the Wayback copy of the page, (C) a ban on redistributing the data.

### 2.1 Vast.ai: live collection blocked (A and C); Wayback status not addressed (B)

Terms: https://vast.ai/terms, "Terms of Use Agreement, Version Date: September 1, 2026".

(A) Automated access, verbatim: "Using any robot, spider, crawler, scraper, script, browser automation, web scraping, web harvesting, web data extraction, data-mining tool or any other automated method to access, query, copy, download, monitor, collect, cache, store or extract data from the Website or Services, except as expressly authorized in a separate written agreement with Company."

(A) Bulk compilation, verbatim: "Engaging in any bulk, systematic, or automated retrieval, collection, copying, downloading, harvesting, caching, storage or other extraction of data or other content from the Website to create, develop, populate, maintain, or compile, directly or indirectly, a collection, compilation, database, dataset, index, benchmark, or directory without written permission from Company."

(C) Index and redistribution, verbatim: "Using the Company Services or any data or information made available through the Website or Services (i) as part of any effort to compete with Company or to provide services as a service bureau, (ii) to construct, publish, or maintain any index, benchmark, pricing-comparison service, market-data product, or similar product or service, or (iii) to redistribute, resell, sublicense, publish or otherwise make available to any third party any feed, dataset or other substantial portion of such data, except in each case as expressly authorized in a separate written agreement with Company."

(C) Authorized Data, verbatim: "You may use pricing and availability information provided by Company to determine the configuration and pricing of your own offering, but you may not use Authorized Data for any other commercial data product or market-information purpose." A further sentence bars using Authorized Data "as an input to or for the construction, calculation, publication, maintenance, or administration of any index, benchmark, pricing index, price-comparison database, or other product or service that measures, compares, tracks, summarizes or reflects pricing, availability, capacity or market conditions, or to train or improve any machine-learning or artificial-intelligence model for any such purpose, unless Company expressly agrees otherwise in a separate written agreement." (verbatim)

(B) Wayback copy: the ToS does not mention archives. Clause (ii) above covers "any data or information made available through the Website", which could be read to reach archived copies. That is an open interpretation question, not a confirmed ban. Whether a research panel counts as a "pricing index" is also open. Decide with the faculty advisor or counsel, or ask Vast.ai for written permission.

Technical note: an unauthenticated `GET https://console.vast.ai/api/v0/bundles/` returned an `offers` array during this audit, yet the live docs say "All endpoints require `Authorization: Bearer $VAST_API_KEY`" and document `POST /api/v0/bundles`. The unauthenticated GET is therefore undocumented. The ToS clauses above apply regardless of whether an endpoint happens to answer. Do not build a collector on it.

Stop condition: do not start a Vast.ai collector until written permission is obtained or the project accepts a legal reading.

### 2.2 Oracle: live collection of oracle.com pages blocked (A and C)

Terms: https://www.oracle.com/legal/terms/ ("Oracle Web Sites Terms of Use").

(A) verbatim: "You agree not to use any robot, spider, scraper or other automated means to access the Site or any Oracle accounts, computer systems or networks without Oracle's express written permission."

(C) verbatim: "Use of Materials You may download, store, display on your computer, view, listen to, play and print Materials that Oracle publishes or broadcasts on the Site or makes available for download through the Site subject to the following: (a) the Materials may be used solely for your personal, informational, noncommercial purposes; (b) the Materials may not be modified or altered in any way; and (c) the Materials may not be redistributed."

(B) Wayback copy: not addressed in the terms. The price list page `https://www.oracle.com/cloud/price-list/` is plain text with GPU rows (for example "BM.GPU.H100.8 — $10.00 GPU per hour").

Possible alternative: a JSON endpoint on `apexapps.oracle.com/pls/apex/cetools/api/v1/products/` answered a probe without auth, but returned `{"items":null}` for the part number tried, so fields are UNVERIFIED, and no terms covering that host were found. It is not documented on any Oracle page that was opened. Treat as unusable until Oracle's terms for it are found.

### 2.3 RunPod: live collection from the site blocked (A and C); API with a key is unresolved

Terms: https://www.runpod.io/legal/terms-of-service ("Last Updated: March 24, 2026").

(A) verbatim: "Engage in any automated use of the system, such as using scripts to send comments or messages, or using any data mining, robots, or similar data gathering and extraction tools."

(A and C) verbatim: "As a user of the Site, you agree not to: Systematically retrieve data or other content from the Site to create or compile, directly or indirectly, a collection, compilation, database, or directory without written permission from us."

(A) verbatim: "(4) access or use the Site or the Service through automated or non-human means, whether through a bot, script or otherwise;" The list lead-in for item (4) was not captured, so whether it is a prohibition or a representation is UNVERIFIED.

(B) Wayback copy: not addressed.

API: RunPod publishes a REST v2 API, `GET https://api.runpod.io/v2/catalog/gpus`, with `Authorization: Bearer <api_key>` and a per-GPU `price` object (`secure`, `community`, `serverless`, USD per single GPU-hour). Using a documented API with the owner's own key is the product's intended use, but obtaining a key means creating an account, which this audit did not do. Whether the ToS clauses above apply to API calls is UNVERIFIED. robots.txt on www.runpod.io is `Allow: /` with `ai-train=no`.

### 2.4 Not blocking, but restricted

- AWS: the AWS Site Terms bar robots on aws.amazon.com (see section 3.2). Use the public offer files instead. Terms for the offer-file host were not found.
- NVIDIA: automated collection from nvidia.com is barred (section 3.12). Datasheets must be downloaded by hand and the values entered with citations.
- SemiAnalysis, Ornn, Silicon Data: automated collection or redistribution barred or paywalled. They are validation-only, so the project loses nothing core. Do not publish their values in the replication package.
- CRSP: raw data cannot be redistributed. Publish derived aggregates only.

### 2.5 Wayback

No clause found that bans the project's use. IA terms limit use of the collections to "scholarship and research purposes" and fair use. This is not a block.

## 3. Source sections

### 3.1 Internet Archive Wayback Machine, CDX API

- Role: core historical panel.
- Access method: REST (CDX server), then fetch each snapshot.
- Endpoint: `https://web.archive.org/cdx/search/cdx` (the endpoint used in the README examples; the README is marked BETA). Observed working probe: `https://web.archive.org/cdx/search/cdx?url=lambdalabs.com/service/gpu-cloud&output=json&limit=3&from=2020`.
- Parameters (README): `url` (required), `matchType` (exact, prefix, host, domain), `output=json`, `fl`, `filter` (regex), `from`/`to` (1 to 14 digit timestamps), `collapse=field[:N]`, `limit`, `offset`, `page`, `pageSize`, `showNumPages`, `resumeKey`/`showResumeKey`.
- Fields returned by default (README, and confirmed by the probe): `urlkey`, `timestamp`, `original`, `mimetype`, `statuscode`, `digest`, `length`.
- Auth: none for public data. Restricted data needs an API key as cookie `cdx-auth-token` (README); not needed here.
- Rate limits: the README states none. UNVERIFIED. It says "For doing large/bulk queries, the use of the Pagination API is recommended." (verbatim), caps result length at 150000 per query by default, and the archive.org deployment uses a page size of 50. The probe's response headers included `x-rl: 0` and `x-na: 0`; their meaning is not documented on any page opened (UNVERIFIED). Follow the project's 1 second rule and back off on 429.
- robots.txt: `https://web.archive.org/robots.txt` returns 404 (none). The probe response carried `server-timing: exclusion.robots` entries, which suggests the server applies robots-based exclusions to archived content; this is an inference from a header, not a documented statement (UNVERIFIED). Pages whose owners later excluded them may be missing.
- Terms on automated access: `https://archive.org/about/terms` has no bot or scraping clause in the text read. Relevant verbatim sentences: "Access to the Archive's Collections is provided at no cost to you and is granted for scholarship and research purposes only." and "You agree not to interfere with the work of other users or Archive personnel, servers, or resources." The Wayback availability API page (https://archive.org/help/wayback_api.php) states no usage policy.
- Terms on redistribution, verbatim: "In particular, you certify that your use of any part of the Archive's Collections will be limited to noninfringing or fair use under copyright law." The privacy section also says "The Collections are made available to researchers and may be made available on the Site, or provided to third parties, for any use, without limitation." The two statements pull in different directions; treat archived provider pages as the provider's copyrighted content and redistribute derived prices only.
- Earliest available date: UNVERIFIED. The README does not say. The probe returned snapshots from 2020-02-02 for the page tried only because of the `from=2020` filter.
- URLs opened: https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md ; https://archive.org/help/wayback_api.php ; https://archive.org/about/terms ; https://web.archive.org/robots.txt ; the probe URL above.

### 3.2 AWS

- Access: (a) Price List Bulk files at `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/index.json` (probe returned HTTP 206 with the first 600 bytes; `publicationDate` 2026-10-31T16:01:43Z; the file lists `versionIndexUrl`, `currentVersionUrl` and `currentRegionIndexUrl` per offer). (b) Price List Query API (`GetProducts`, `DescribeServices`, `GetAttributeValues`) and a Bulk API (`ListPriceLists`, `GetPriceListFileUrl`) at `https://api.pricing.us-east-1.amazonaws.com` (also eu-central-1 and ap-south-1).
- Auth: the docs say "An AWS Identity and Access Management (IAM) identity, such as a user or role, must have permission to use the Price List Query API or Price List Bulk API." (verbatim, https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/price-changes.html). The static offer files answered without credentials (observed HEAD and ranged GET). The docs page does not state that the static files are public, so their documented status is UNVERIFIED.
- Observed size: `AmazonEC2/current/us-east-1/index.json` has Content-Length 481,649,899 bytes (HEAD, Last-Modified 2026-10-29). Plan for large files; do not fetch every region daily without need.
- Rate limits: token bucket, size 10, refill 5 per second for each of DescribeServices, GetAttributeValues, GetProducts, ListPriceLists, GetPriceListFileUrl (https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/billing-limits.html). No limit documented for the static files.
- Coverage notes from docs: the catalog "doesn't include Amazon Elastic Compute Cloud (Amazon EC2) Spot Instances." (verbatim). Savings Plan prices are not in the Query API. The docs say AWS charges the prices on the service pricing page if the file differs.
- Fields (docs): products indexed by SKU with attributes; terms for OnDemand and Reserved. Exact EC2 GPU attribute names were not sampled (UNVERIFIED).
- robots.txt (https://aws.amazon.com/robots.txt): `User-agent: *` disallows only specific paths (for example `/about-aws/whats-new/200...`, `/pricing/awis/`); EC2 pricing pages are not disallowed. The offer-file host has no robots.txt (404).
- Terms, automated access (verbatim, https://aws.amazon.com/terms/): "This license does not include any resale or commercial use of the AWS Site or its contents; any derivative use of the AWS Site or its contents; any downloading or copying of any other users' account information; or any use of data mining, robots, or similar data gathering and extraction tools."
- Terms, redistribution (verbatim): "The AWS Site or any portion of the AWS Site may not be reproduced, duplicated, copied, sold, resold, visited, or otherwise exploited for any commercial purpose without express written consent or license of AWS."
- Terms covering the offer-file host or the pricing API data: not found. UNVERIFIED.
- Earliest available date: the bulk docs say "To find historical price list files, use the EffectiveDate parameter." (verbatim) The earliest effective date is UNVERIFIED here (another agent covers offer-file history).
- URLs opened: the three docs pages above plus https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-price-list-query-api.html and https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/using-the-aws-price-list-bulk-api.html ; https://aws.amazon.com/terms/ ; https://aws.amazon.com/robots.txt ; the two offer-file URLs.

### 3.3 Google Cloud

- Access: Cloud Billing Catalog. Documented endpoints (https://docs.cloud.google.com/billing/docs/how-to/get-pricing-information-api): `GET https://cloudbilling.googleapis.com/v2beta/skus`, `GET https://cloudbilling.googleapis.com/v1beta/skus/SKU_ID/prices`. Older reference (https://docs.cloud.google.com/billing/docs/reference/rest/v1/services.skus/list): `GET https://cloudbilling.googleapis.com/v1/{parent=services/*}/skus`, example parent `services/6F81-5844-456A` (Compute Engine).
- Auth: the pricing page text says public data needs an API key (fragment: "To get information about public services, SKUs, or prices, you must create an API key."). The v1 reference lists only OAuth scopes and does not say whether a key is enough (UNVERIFIED for v1). Creating a key needs a Google Cloud project, so no sample call was made.
- Rate limits: none documented; pagination is 50 per page for services, up to 5000 per page for SKUs.
- Historical prices: v1 `skus.list` accepts `startTime` and `endTime` (RFC 3339), with the window inside one calendar month in America/Los_Angeles; if omitted, latest pricing is returned. How far back it goes is UNVERIFIED.
- Fields (docs): SKU `name`, `skuId`, `displayName`, `service`, `productTaxonomy`, `geoTaxonomy`; price `currencyCode`, `valueType`, `rate` (tiers with `startAmount`, `listPrice`, `unitInfo`, `aggregationInfo`).
- robots.txt (https://cloud.google.com/robots.txt): the Disallow list names console, landing, walkthroughs and some `/terms/looker/` paths; no compute or pricing path is disallowed. `cloudbilling.googleapis.com/robots.txt` returns 404.
- Terms, automated access, verbatim (fragment via page tool, https://policies.google.com/terms): the terms prohibit "using automated means to access content from any of our services in violation of the machine-readable instructions" on our web pages; the example given is robots.txt files that disallow crawling.
- Terms, redistribution: Google Cloud docs content is "licensed under the Creative Commons Attribution 4.0 License" (verbatim footer on the pricing-API page). Google Cloud Terms of Service section 3.3 bars selling or distributing "the Services", not price data. No clause was found on redistribution of catalog data (UNVERIFIED).
- Earliest available date: UNVERIFIED.
- URLs opened: https://docs.cloud.google.com/billing/docs/how-to/get-pricing-information-api ; https://docs.cloud.google.com/billing/docs/reference/rest/v1/services.skus/list ; https://cloud.google.com/terms ; https://policies.google.com/terms ; https://cloud.google.com/robots.txt ; https://cloudbilling.googleapis.com/robots.txt.

### 3.4 Microsoft Azure

- Access: Azure Retail Prices REST API. Endpoint `https://prices.azure.com/api/retail/prices` (preview `?api-version=2023-01-01-preview` adds savings-plan rates). Docs: https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices.
- Auth: none. Verbatim: "This API gives you an unauthenticated experience to get retail rates for all Azure services."
- Rate limits: none stated in the docs (UNVERIFIED for actual throttling). Pages are capped at 1,000 records with a `NextPageLink`. `prices.azure.com/robots.txt` returns 404.
- Filters: `armRegionName`, `Location`, `meterId`, `meterName`, `productid`, `skuId`, `productName`, `skuName`, `serviceName`, `serviceId`, `serviceFamily`, `priceType`, `armSkuName`. Values are case sensitive in the preview version.
- Probe (one call): `$filter=armSkuName eq 'Standard_ND96isr_H100_v5' and armRegionName eq 'eastus'` returned HTTP 200 and 12 items. Sample: Consumption `retailPrice` 98.32 per "1 Hour", `effectiveStartDate` 2023-12-01T00:00:00Z, product "Virtual Machines NDsr H100 v5 Series".
- Fields: `currencyCode`, `tierMinimumUnits`, `reservationTerm`, `retailPrice`, `unitPrice`, `armRegionName`, `location`, `effectiveStartDate`, `meterId`, `meterName`, `productId`, `skuId`, `productName`, `skuName`, `serviceName`, `serviceId`, `serviceFamily`, `unitOfMeasure`, `type` (Consumption, Reservation, DevTestConsumption), `isPrimaryMeterRegion`, `armSkuName`, `savingsPlan` (preview).
- Caution found in the probe: Reservation rows also show `unitOfMeasure` "1 Hour" but carry values such as 551221.0, 1134310.0 and 1722566.0, which cannot be hourly prices. The docs' own example shows a 1 Year reservation `retailPrice` of 25007.0. Treat reservation `retailPrice` as a term total and convert with the term length. The docs do not say this in words (UNVERIFIED as documentation); it is an observation from the probe and example.
- Terms: the Azure pricing pages sit on azure.microsoft.com, whose robots.txt disallows `/api/`, `/*/search/?q=*` and others but not the pricing details paths. Microsoft Terms of Use (https://www.microsoft.com/en-us/legal/terms-of-use) state (fragment): "You may not use web scraping, web harvesting, or web data extraction methods to extract data from the AI services." That sentence is in the AI services section and does not cover the Retail Prices API. On redistribution (fragment): "You may not modify, copy, distribute, transmit, display, perform, reproduce, publish, license, create derivative works from". No clause specific to Retail Prices API data was found (UNVERIFIED).
- Earliest available date: the API returns current prices with `effectiveStartDate`; sample rows begin 2020-08-01 in the docs examples. A true price history is not offered (another agent covers this).
- URLs opened: the Learn page above; https://azure.microsoft.com/robots.txt ; https://prices.azure.com/robots.txt ; https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/ (the table did not render in the text read, so JavaScript-rendered; UNVERIFIED for scraping) ; the Microsoft terms page.

### 3.5 Oracle Cloud

- Access: the price list page https://www.oracle.com/cloud/price-list/ (server-rendered text; GPU rows found: VM.GPU2.1 P100 $1.275, VM.GPU3.x V100 $2.95, BM.GPU.H200.8 $10.00, BM.GPU.H100.8 $10.00, BM.GPU.L40S-NC.4 $3.50, all per GPU-hour). A JSON endpoint `https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/` was probed once with `?partNumber=B96107` and returned `{"lastUpdated":"2026-10-08T14:38:16.165Z","items":null}`, HTTP 200, no auth. It is not documented on any Oracle page opened; a web search found only third-party descriptions. Fields: UNVERIFIED.
- Auth: none observed for the JSON endpoint; none for the page.
- Rate limits: none found (UNVERIFIED).
- robots.txt (https://www.oracle.com/robots.txt): the generic block disallows `/a/ocom/docs/corporate/pricing/`, `/corporate/contracts/`, `/us` and others; `/cloud/price-list/` is not disallowed. `apexapps.oracle.com/robots.txt` returned an error page (UNVERIFIED).
- Terms, automated access and redistribution: see section 2.2 (verbatim).
- Earliest available date: current prices only; UNVERIFIED for any history.
- URLs opened: https://www.oracle.com/robots.txt ; https://www.oracle.com/legal/terms/ ; https://www.oracle.com/cloud/price-list/ ; the apexapps probe URL. (www.oracle.com/cloud/compute/gpu/ returned HTTP 403 to the page-reading tool.)

### 3.6 Lambda

- Access: Cloud API, base `https://cloud.lambda.ai/api/v1` (https://docs.lambda.ai/api/cloud). The instance-types endpoint `GET /api/v1/instance-types` was probed once without a key and returned HTTP 401, `{"error":{"code":"global/invalid-api-key","message":"No API key was provided."...}}`. Its response fields could not be read from the docs excerpt, so they are UNVERIFIED.
- Public pricing page https://lambda.ai/pricing lists per-GPU-hour on-demand rows in server-rendered text (B200 SXM6 $6.69, H100 SXM $3.99, A100 SXM 80 GB $2.79, A100 SXM 40 GB $1.99, Tesla V100 16 GB $0.79) as read during the audit.
- Auth: API key as `Authorization: Bearer <YOUR-API-KEY>`; the page warns that without it "the request will fail." (fragment). Creating a key requires an account; not done.
- Rate limits, verbatim: "Requests to the API are generally limited to one request per second." Launch requests are limited to "one request per 12 seconds, or five requests per minute."
- robots.txt: https://lambda.ai/robots.txt disallows only `/_hcms/preview/`, `/hs/manage-preferences/`, `/hs/preferences-center/` and two query patterns. https://cloud.lambda.ai/robots.txt is `Disallow:` (empty). https://lambdalabs.com/robots.txt redirects to the same file.
- Terms, automated access (fragment, https://lambda.ai/legal/terms-of-service, "Last updated: August 2025"): the Acceptable Use Policy lists "web crawling which is not restricted to a rate so as not to impair or otherwise disrupt the servers being crawled". Read together, rate-limited crawling is not listed as a violation. No explicit scraping ban on public pages was found.
- Terms, redistribution: no clause on copying pricing found; the site terms say Lambda "retains ownership of all intellectual property rights related to the Sites" (fragment). UNVERIFIED.
- Earliest available date: current prices only from the page and API. Historical pages via Wayback (the probe in 3.1 used lambdalabs.com/service/gpu-cloud).
- URLs opened: https://docs.lambda.ai/api/cloud ; https://lambda.ai/pricing ; https://lambda.ai/legal/terms-of-service ; the robots files above ; the 401 probe.

### 3.7 CoreWeave

- Access: public pricing page https://www.coreweave.com/pricing (instance-hour prices, not per-GPU, North America and Europe, on-demand and spot; as read: H100 8-GPU $49.24 on-demand; reserved rates are "contact sales"). No pricing API found; the page "contains no pricing API, endpoint, or programmatic access information."
- Auth: none for the page.
- Rate limits: none stated.
- robots.txt (https://www.coreweave.com/robots.txt): `User-agent: *` disallows `/blog-categories/` and `/event/` only.
- Terms: https://docs.coreweave.com/policies/terms-of-service ("Last modified: June 30, 2022") is a customer contract; no clause on scraping, robots or redistribution was found in it. A separate website terms-of-use page was not located (https://www.coreweave.com/terms-of-use returned 404). Automated access and redistribution: UNVERIFIED.
- Earliest available date: current prices only.
- URLs opened: pricing page, robots file, the docs terms page, the 404 URL above.

### 3.8 RunPod

- Access: REST v2 `GET https://api.runpod.io/v2/catalog/gpus` (https://docs.runpod.io/api-reference-v2/catalog/list-gpu-types). Response: `gpus` array with `id`, `name`, `pool`, `manufacturer`, `memory`, `secure`, `community`, `price`, `maxCount`; `price` has `secure`, `community`, `serverless`, "List price in USD per hour for a **single** GPU of this type." (fragment). Optional `include=AVAILABILITY`. Legacy GraphQL at `https://api.runpod.io/graphql`: a probe of `{ gpuTypes { id } }` without a key returned HTTP 200 with GPU ids; price fields were not requested, so whether they need a key is UNVERIFIED.
- Public pricing page https://www.runpod.io/pricing shows per-GPU-hour prices (H100 SXM $3.99, A100 SXM $1.79, H200 $5.29, B200 $7.99 as read), with a JSON-LD block giving secure and community cloud prices.
- Auth: REST v2 needs a Bearer key from the console. Account creation not done.
- Rate limits: authenticated responses carry `RateLimit` and `RateLimit-Policy` headers; the spec's example is 180 per minute, 3600 per hour, 43200 per day, "illustrative, not a guaranteed limit"; a 429 includes `Retry-After`. Limits are per user.
- robots.txt (https://www.runpod.io/robots.txt): `Allow: /`; `Content-Signal: search=yes, ai-input=yes, ai-train=no`. `api.runpod.io/robots.txt` returns 404.
- Terms: see section 2.3 (verbatim).
- Earliest available date: current prices only.
- URLs opened: robots, ToS, REST v2 catalog docs, pricing page, probe.

### 3.9 Vast.ai

- Access: documented `POST https://console.vast.ai/api/v0/bundles` (search offers). Returned offer fields named in the docs: `dph_total`, `min_bid`, `gpu_name`, `num_gpus`, `gpu_ram`, `reliability`, `dlperf`, `cpu_cores`, `cpu_ram`, `disk_space`, `inet_down`, `inet_up`, `geolocation`, `verification`, `rentable`, `rented`, `is_bid`, `machine_id`, `host_id`, `id`. The docs state the spec "doesn't formally define these fields" (page-tool paraphrase), so the list may be incomplete.
- Auth: documented as required. Verbatim: "All endpoints require `Authorization: Bearer $VAST_API_KEY`." The undocumented unauthenticated GET behaviour is covered in section 2.1.
- Rate limits: https://docs.vast.ai/api-reference/rate-limits-and-errors says limits apply "per endpoint and per identity" (fragment) and a 429 is returned; "The API does not currently set standard rate-limit headers" (fragment). Per-endpoint numbers are not given.
- robots.txt: https://vast.ai/robots.txt disallows `/admin/`, `/pricing/tables/`, `/tag/`, `/post/` and others for all agents; https://console.vast.ai/robots.txt (served from cloud.vast.ai) is `Allow: /`. `Content-Signal: search=yes, ai-train=no, ai-input=yes`.
- Terms: section 2.1.
- Earliest available date: current offers only.
- URLs opened: robots files, docs pages, https://vast.ai/terms, one unauthenticated probe of the `bundles` GET.

### 3.10 Paperspace (DigitalOcean)

- Access: public pricing page https://www.paperspace.com/pricing (as read: H100 $3.09, H100 HGX $2.24 with a 3-year commitment, A100-80G $1.15 with a 3-year commitment, V100 $2.30; the H100 row lists A100 hardware specs, which may be a page error). No public pricing API found; the Paperspace API uses keys ("Create and revoke Paperspace API keys to authenticate with the Core REST API", fragment, https://docs.digitalocean.com/products/paperspace/).
- Auth: none for the page.
- Rate limits: none found.
- robots.txt (https://www.paperspace.com/robots.txt): lists only a Sitemap line; no Disallow.
- Terms: https://www.paperspace.com/terms returned 404. The DigitalOcean Terms of Service (https://www.digitalocean.com/legal/terms-of-service-agreement, "Last Updated on August 21, 2026") covers "Websites and Services"; no clause on scraping, robots or redistribution of website content was found in it. The acceptable use policy was not read. Automated access and redistribution: UNVERIFIED.
- Earliest available date: current prices only.

### 3.11 Published indices

**getdeploying.com GPU Rental Price Index.** The proposal's link `https://getdeploying.com/gpu-price-index` now redirects (HTTP 301) to `/gpu-price-trends`.
- Access: free datasets at https://getdeploying.com/dataset (CC BY 4.0). `weekly.csv` is one row per GPU model, billing type and week; fields `gpu_slug`, `date`, `billing_type`, `reservation_months`, `min_price`, `max_price`, `median_price`, `provider_median_price`, `provider_count`, `offering_count` (USD per GPU-hour). Cover: 103 GPU models, 92 providers, "53 trailing" weeks per model, 16,490 rows, updated daily as of 2026-10-31. Per-provider rows and longer history are in a paid API (https://getdeploying.com/api): "Price history since 2024", daily since July 2026, "Get API credentials. Pick a plan and request access." The API was not used.
- Auth: none for datasets; Bearer token for the API.
- Rate limits: not stated for datasets. The terms bar circumventing rate limits.
- robots.txt (https://getdeploying.com/robots.txt): `Allow: /`; disallows `/terms`, `/privacy`, `/legal`, `/share`, `/api/`, `/provider-report/`. `/dataset` is not disallowed.
- Terms (https://getdeploying.com/terms, "Last updated: September 16, 2026"), automated access, verbatim: acceptable use bars you from "scrape, extract, or systematically copy content from the Services, including for AI or machine learning training purposes, without our prior written consent".
- Terms, redistribution, verbatim: the dataset files "are licensed under Creative Commons Attribution 4.0 International. That license covers those published files only. It does not cover the Services, their HTML or design, the API or API Data, and it does not permit automated access to the Services beyond what section 5 allows." The dataset page says: "The license covers the published dataset files only and implies no endorsement." The terms define a "Derived Product" (own analysis such as an index, benchmark, report or dashboard) for API Data; those API terms were not read in full (UNVERIFIED).
- Earliest date: about 53 weeks back for the free file (from "53 trailing"); 2024 for the paid API.
- URLs opened: robots, terms, /dataset, /dataset/gpu-prices, /api, /gpu-price-index (HEAD).

**Silicon Data (Bloomberg SDH100RT, SDA100RT, SDB200RT).**
- Access: paid portal ("7-day trial" shown), direct API and partner distribution (Kaiko). Free chart access not stated. Page: https://www.silicondata.com/products/silicon-index?gpu=h100. Bloomberg tickers appear on the page and in search results; the Bloomberg route needs a terminal (not checked).
- Auth: login or subscription; not used. History start: UNVERIFIED (only "90-day historical pricing" for the portal is mentioned). The governance PDF (https://www.silicondata.com/documents/silicon-data-index-governance.pdf, "Governance, Methodology & Control Framework", 10 pages) could not be text-extracted (UNVERIFIED).
- robots.txt: `Allow: /`.
- Terms (https://www.silicondata.com/terms-of-use, fragments): "No Site Content or any part thereof may be modified, reverse-engineered, reproduced or distributed in any form by any means," ... "without the prior written consent of Silicon Derivatives." No scraping clause found.
- Rate limits: UNVERIFIED.

**Ornn AI (OCPI, Bloomberg ORNNH100).**
- Access: public window of three months on https://data.ornn.com/markets/h100-sxm; the page says the index is "served free as JSON by the Ornn Data API with no key required." (fragment); full history needs an account ("Premium adds full daily history"). robots.txt on data.ornn.com allows `/api/public-index/daily-index/all`, `/api/public-index/otpi`, `/api/public-index/gpu/` and disallows the rest of `/api/`.
- Terms (https://www.ornn.com/terms-of-use, fragments): bars "scrape, crawl, harvest, mine, index, copy, cache, download in bulk, extract, record, monitor" "except as expressly authorized by the Company in writing"; "No Company Data may be used for external publication, republication, redistribution, resale, syndication"; bars creating, publishing or distributing "any index, benchmark, reference rate" "or other derivative work using Company Data without the Company's prior express written consent". The data page adds (fragment): "Redistribution and commercial use remain subject to Ornn's terms and any applicable data license."
- Conclusion: the open endpoint conflicts with the terms. Treat as Forbidden unless written consent is obtained. Not a core source.

**Compute Desk (Bloomberg tickers).**
- Access: indices DESKH100, DESKH200, DESKB200, DESKB300 (daily, US, 1-year rental) at https://www.compute-desk.com/ with an "Access via API" button to https://docs.computedesk.com/. The docs page says a token is needed (fragment: "swap your API key for an access token"); price and rate limits not stated. Bloomberg ticker names (CIHOPUS and others) come only from third-party search results, not from Compute Desk's own pages (UNVERIFIED).
- Terms: none found on the pages opened (UNVERIFIED). History start: UNVERIFIED.

**SemiAnalysis.**
- Access: dashboard https://gpu-index.semianalysis.com/ (spot-contract composite for H100, A100, B200; H100 also on Bloomberg as SAH100SC per the page; the earliest value in its table is for 2H 2023; computed and published hourly). The 1-year H100 contract index (monthly survey of 100+ participants, ranges by month) is described in search results and the dashboard's historical table; whether the 1-year series is on this page or elsewhere was not confirmed (UNVERIFIED). Institutional data: "For institutional access to the underlying data, contact sales@semianalysis.com." (fragment)
- Terms (https://www.semianalysis.com/terms-of-service, "Terms and Conditions", last updated January 13, 2026, fragments): bars "conduct any systematic or automated data collection activities on or in relation to our website."; research may not be "quoted, excerpted, attributed or otherwise referenced in any publication, report or other public communication" unless properly sourced and linked.
- Conclusion: Forbidden for automated collection. Any figures used for validation must be read by hand and cited; republishing the series is not permitted without consent.

### 3.12 NVIDIA datasheets and MLCommons MLPerf

**NVIDIA datasheets.**
- Access: PDFs on nvidia.com (product pages). No machine-readable spec feed found. Fields: launch and GA dates, memory, bandwidth, BF16 TFLOPS, TDP (as the proposal lists; not re-verified against datasheets in this audit).
- Auth: none. robots.txt (https://www.nvidia.com/robots.txt): `Allow: /` with gated PDF paths disallowed (`/content/gated-pdfs/*`, `/gated-resources/*`).
- Terms (https://www.nvidia.com/en-us/about-nvidia/terms-of-service/, dated July 15, 2026, fragments): bars use of "any robot, spider, scraper, crawler, data mining tool, data gathering or extraction tool, or any other automatic device" "to access, acquire, copy or monitor any portion of the Site"; permits "download one copy of the software and materials found on the Site" "for your personal, non-commercial internal use only".
- Conclusion: manual download of a small set of datasheets is within the stated personal-use grant; scripted collection is Forbidden. Record values by hand with citations; do not redistribute the PDFs. Earliest date: per document (UNVERIFIED).

**MLCommons MLPerf.**
- Access: results pages on https://mlcommons.org/benchmarks/ and GitHub repos (for example https://github.com/mlcommons/inference_results_v5.0, with `closed/`, `open/` and `summary_results.json`). The repo page shows no LICENSE file and no terms on use of results.
- Auth: none. robots.txt (https://mlcommons.org/robots.txt): `Crawl-delay: 10`, otherwise open. Respect the 10 second delay.
- Terms: the policies page https://mlcommons.org/policies/ links a "Terms of Use" document hosted on Google Drive that could not be read (UNVERIFIED). A web search result says the submission rules state "After publication, code and results are public and free for use under the MLPerf Terms of Use." (secondary, https://github.com/mlcommons/policies/blob/master/submission_rules.adoc; not opened). Use of the MLPerf name with results must follow the MLPerf Results Messaging Guidelines (https://github.com/mlcommons/policies/blob/master/MLPerf_Results_Messaging_Guidelines.adoc; not opened). Automated access and redistribution: UNVERIFIED.

### 3.13 U.S. EIA electricity API

- Access: API v2, base `https://api.eia.gov/v2/`; retail sales route `/v2/electricity/retail-sales/data` with facets `stateid`, `sectorid` (RES, COM, IND, ALL, OTH, TRA); fields `price` (cents per kWh), `sales`, `revenue`, `customers`; `frequency=monthly`, periods `YYYY-MM` (https://www.eia.gov/opendata/documentation.php). The `sales` unit label is inconsistent on the page ("million kilowatthours" and "kilowatthours").
- Auth, verbatim: "To call our API, you must use the unique API key assigned to you." The key goes in the URL as `api_key`; a free key is emailed after registration. A bare request returned `API_KEY_MISSING` with a pointer to https://www.eia.gov/opendata/register.php. No key was requested (account creation is out of scope for this audit), so no fields were sampled.
- Rate limits: no numbers on the page; programs "must throttle the number of the requests they make per second and per hour" and exceeding limits temporarily suspends the key (fragment). JSON responses are capped at 5,000 rows; use `offset` and `length`.
- robots.txt (https://www.eia.gov/robots.txt): `Allow: /` with specific Disallow paths (for example `/archive/`, `/cfapps/`, `/reports/`); `/opendata` is not disallowed. `api.eia.gov/robots.txt` returns the key-missing JSON, so none.
- Terms, redistribution, verbatim (https://www.eia.gov/about/copyrights_reuse.php): "U.S. government publications are in the public domain and are not subject to copyright protection." The page also says "You may use and/or distribute any of our data, files, databases, reports, graphs, charts, and other information products" (fragment) and asks for an acknowledgment such as "Source: U.S. Energy Information Administration (Oct 2008)." No automated-access terms on that page.
- Earliest date: monthly data starts 2001-01 in the docs' example metadata, which the page says may change (not confirmed against live metadata because no key; UNVERIFIED).

### 3.14 SEC EDGAR XBRL companyfacts

- Access: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (all XBRL concepts for one company), plus `submissions`, `companyconcept` and `frames` endpoints, and nightly bulk `companyfacts.zip` and `submissions.zip` (about 3:00 a.m. ET) (https://www.sec.gov/search-filings/edgar-application-programming-interfaces).
- Auth, verbatim: "These APIs do not require any authentication or API keys to access."
- Fair access: "Current max request rate: 10 requests/second." (verbatim, https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data). Clients must "declare your user agent in request headers" (fragment) with company name and contact. Verbatim: "The SEC does not allow botnets or automated tools to crawl the site." https://www.sec.gov/privacy adds: "The SEC does not allow "unclassified" bots or automated tools to crawl the site." and "Current guidelines limit users to a total of no more than 10 requests per second" (fragment), and that after dropping below the threshold for 10 minutes the user may resume. The SEC "cannot provide technical support for developing or debugging scripted downloading processes." CORS is not supported.
- Probe result: a request to `https://www.sec.gov/robots.txt` with this audit's neutral User-Agent returned HTTP 403 with "Request Rate Threshold Exceeded" and "Automated access to our sites must comply with SEC.gov's Privacy and Security Policy." That is expected: the User-Agent had no contact details, which the audit rules forbid. The collector must send the contact User-Agent required by project rule 5. No sample companyfacts call was made; field names beyond the endpoint docs are UNVERIFIED.
- robots.txt: read through a page tool summary (not verbatim): applies to `User-agent: *`, allows `/Archives/edgar/data`, disallows `/cgi-bin`, parts of `/Archives/` and others. `data.sec.gov/robots.txt` returns 404 (none).
- Terms, redistribution, verbatim (https://www.sec.gov/privacy): content "may be copied or further distributed by users of the web site without the SEC's permission" (fragment) and "Please consider appropriate citation to the SEC as the source."
- Update latency: XBRL data typically lags by under a minute.
- Earliest available date: UNVERIFIED (not stated on the pages opened; XBRL filing start is not asserted here).
- 10-K text: the proposal also lists 10-K text. Full-text and filing-index access go through `www.sec.gov/Archives/...`, which falls under the same 10 requests per second and no-crawling rules. Not audited beyond that.

### 3.15 CRSP via WRDS

- Access: WRDS Cloud (programmatic, per WRDS terms "Automation is permitted on the WRDS Cloud server." (fragment)). Whether VCU holds a CRSP subscription is not something a public page can show (UNVERIFIED).
- Auth: institutional username and password; the page states "You must be logged-in to access that page." (fragment), with Duo two-factor. Login required, so this audit stopped here. The Python or SSH interface, table names and start dates are UNVERIFIED because the support pages need a login.
- Rate limits: UNVERIFIED.
- Terms (https://wrds-www.wharton.upenn.edu/users/tou/, fragments): "Users are not permitted to script or otherwise automate the login to the WRDS website"; "You agree not to use any manual or automated device or process to gather or extract data"; "Users may not use data downloaded from the WRDS database for any non-academic or commercial endeavor."; "...you may not reproduce, distribute, modify, adapt, create derivative works of, display, transmit".
- Redistribution: Forbidden for raw CRSP; publish derived aggregates only. A separate Data Download and Analysis Policy exists and was not read (UNVERIFIED). Free fallback (proposal says "else a free price source"): not audited.

### 3.16 CPI-U (FRED or BLS)

- FRED. Series CPIAUCSL ("Consumer Price Index for All Urban Consumers: All Items in U.S. City Average", seasonally adjusted, monthly, index 1982-1984=100): "Data ranges from 1947-01-01 1:00:00 to 2026-09-01 2:00:00." Latest observation Sep 2026 = 336.298, updated Oct 14, 2026, next release Nov 10, 2026 (https://fred.stlouisfed.org/series/CPIAUCSL).
- FRED API: `https://api.stlouisfed.org/fred/series/observations`, `api_key` required (a 32-character key; registration needs a FRED account, not created). Params: `series_id`, `file_type` (xml, json, xlsx, csv), `observation_start`, `observation_end`, `units`, `frequency`, `vintage_dates`, `output_type`, `limit` (up to 100000), `offset`. Response fields per observation: `realtime_start`, `realtime_end`, `date`, `value` (string in JSON). No rate limit stated (https://fred.stlouisfed.org/docs/api/fred/series_observations.html).
- FRED robots: `https://fred.stlouisfed.org/robots.txt` has `Crawl-delay: 1` and disallows some `/graph/` image paths and `/searchresults`; `https://api.stlouisfed.org/robots.txt` has `Crawl-delay: 2` and no Disallow. Use at least 2 seconds between API calls to be safe.
- FRED terms (https://fred.stlouisfed.org/docs/api/terms_of_use.html, fragments): the Bank "may impose limits on certain features and services"; bars "Use an unreasonable amount of bandwidth"; "Data series available through the FRED® API, may be owned by third parties and subject to copyright restrictions."; required notice: "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis." No explicit redistribution clause. CPI itself is a BLS series.
- BLS. Public Data API: v1 is unregistered with "Unregistered users may request up to 25 queries daily" and 25 series per query, 10 years per query; v2 needs registration ("Registration is required for Version 2.0 of the BLS Public Data API.") with 500 queries daily, 50 series per query, 20 years per query; both have a limit of 50 requests per 10 seconds (fragments via page tool, https://www.bls.gov/developers/api_faqs.htm). The endpoint URL and the CPI-U series ids (for example CUUR0000SA0, CUSR0000SA0) were not confirmed on the pages opened (UNVERIFIED).
- BLS robots and access: `https://api.bls.gov/robots.txt` is `User-agent: * / Disallow: /`, which conflicts with the API's purpose; whether it applies to API clients is UNVERIFIED. `https://www.bls.gov/robots.txt` returned an Access Denied page to this audit's User-Agent. BLS policy (fragments, https://www.bls.gov/bls/pss.htm): "BLS also reserves the right to block robots that do not contain information that can be used to contact the owner." and "excessive robot activity on BLS websites is prohibited." A contact-bearing User-Agent is therefore needed for any BLS site access.
- BLS redistribution, verbatim (https://www.bls.gov/opub/copyright-information.htm): "everything that we publish, both in hard copy and electronically, is in the public domain, except for previously copyrighted photographs and illustrations." and "You are free to use our public domain material without specific permission, although we do ask that you cite the Bureau of Labor Statistics as the source."
- Recommendation: FRED CPIAUCSL via the API (the project owner registers a key) is the cleaner route; BLS API v1 needs no key but is capped at 25 queries per day.
- Earliest date: 1947-01-01 (FRED series page). BLS start date UNVERIFIED.

## 4. Items that stayed UNVERIFIED

These are the items tagged UNVERIFIED above, grouped by source, so the owner can decide what to chase.

- Wayback: CDX rate limit; meaning of `x-rl` and `x-na` headers; robots-based exclusion inference; earliest date overall.
- AWS: whether the static offer files are documented as public; terms for the offer-file host; EC2 GPU attribute names; earliest effective date.
- Google Cloud: whether an API key suffices for v1; how far back `startTime` goes; redistribution of catalog data; earliest date.
- Azure: actual throttling; terms specific to Retail Prices API data; reservation price semantics are an observation, not documentation; the VM pricing page table did not render in the text read.
- Oracle: fields, terms and robots for the apexapps endpoint; history; rate limits.
- Lambda: instance-types response fields; redistribution of pricing.
- CoreWeave: website terms (automated access and redistribution).
- RunPod: context of the "(4)" clause; whether GraphQL price fields need a key; whether the site ToS reaches API use.
- Vast.ai: whether the Wayback copy is within clause (ii); whether a research panel is a "pricing index" under the ToS.
- Paperspace: Paperspace-specific terms and the DigitalOcean acceptable use policy; any pricing API.
- Indices: Silicon Data history start, governance PDF, rate limits; Compute Desk terms, price, history and Bloomberg tickers; SemiAnalysis 1-year series location; getdeploying API terms in full.
- MLCommons: Terms of Use text, automated access and redistribution.
- EIA: live earliest date and exact field list (no key).
- SEC: earliest date; companyfacts field list (no sample call).
- WRDS: whether VCU has CRSP, tables, start date, rate limits, Data Download and Analysis Policy.
- CPI: BLS endpoint URL, CPI-U series ids and start date; whether the api.bls.gov robots Disallow applies to API clients.

## Epoch AI machine-learning hardware dataset (added 2026-11-10, Decision 10)

- URL: https://epoch.ai/data/machine-learning-hardware; CSV https://epoch.ai/data/ml_hardware.csv
- Licence: CC BY 4.0. Cite: Epoch AI, 'Data on machine learning hardware'. Published online at
  epoch.ai. No terms-of-use page (`/terms` 404); documentation offers programmatic CSV access.
- Fields used: "Release date", "Release price (USD)" ("Price of the processor when released, in
  nominal US dollars"; "Listed prices do not reflect bulk discounts"), "Source for the price".
- Raw copy: data/raw/indices/epoch/2026-11-10/235424Z-ml_hardware.csv (+ .json sidecar).
- Used by: gel.models.p3_capex (P3 capex anchor, growth, release gaps).
