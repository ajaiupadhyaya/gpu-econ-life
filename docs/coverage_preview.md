# Wayback coverage preview

Generated 2026-10-31T20:08:32Z by `make coverage-preview` from the CDX index. No page contents were downloaded.

**Stop test:** 6 of 9 providers have at least 6 usable snapshots in each of 2020–2022.

Do not read these counts as price coverage. A capture can be an empty JavaScript shell, so a page can pass this test and still hold no readable prices.

## Provider gate

Usable snapshots summed across each provider's candidate pages.

| Provider | Type | 2020 | 2021 | 2022 | Passes |
| --- | --- | --- | --- | --- | --- |
| aws | hyperscaler | 170 | 252 | 334 | yes |
| google_cloud | hyperscaler | 128 | 91 | 131 | yes |
| azure | hyperscaler | 65 | 46 | 104 | yes |
| oracle | hyperscaler | 0 | 0 | 97 | no |
| lambda | neocloud | 14 | 22 | 53 | yes |
| coreweave | neocloud | 4 | 21 | 27 | no |
| runpod | neocloud | 0 | 0 | 13 | no |
| vast | marketplace | 35 | 41 | 86 | yes |
| paperspace | neocloud | 8 | 19 | 45 | yes |

## Per page

Each cell: usable snapshots / distinct months / distinct content versions (by digest). `·` means none. A version count of 1 across a year means the page bytes never changed.

| Provider | URL | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| aws | https://aws.amazon.com/ec2/pricing/on-demand/ | 98 / 12m / 38v | 74 / 12m / 30v | 109 / 12m / 36v | 164 / 12m / 45v | 78 / 12m / 38v | 139 / 12m / 119v | 248 / 12m / 248v | 1119 / 10m / 1119v |
| aws | https://aws.amazon.com/ec2/spot/pricing/ | 9 / 7m / 8v | 16 / 8m / 12v | 21 / 10m / 13v | 22 / 10m / 17v | 16 / 8m / 8v | 45 / 11m / 43v | 57 / 12m / 57v | 41 / 10m / 41v |
| aws | https://aws.amazon.com/ec2/instance-types/p3/ | 58 / 12m / 26v | 63 / 11m / 22v | 62 / 12m / 15v | 88 / 12m / 21v | 67 / 12m / 32v | 39 / 12m / 38v | · | · |
| aws | https://aws.amazon.com/ec2/instance-types/p4/ | · | 17 / 2m / 6v | 60 / 12m / 23v | 60 / 11m / 21v | 19 / 8m / 13v | 37 / 9m / 37v | 54 / 11m / 54v | 55 / 10m / 55v |
| aws | https://aws.amazon.com/ec2/instance-types/p5/ | · | · | · | · | 29 / 5m / 16v | 48 / 11m / 41v | 87 / 12m / 87v | 51 / 10m / 51v |
| aws | https://aws.amazon.com/ec2/capacityblocks/pricing/ | · | · | · | · | 6 / 2m / 5v | 37 / 11m / 36v | 32 / 10m / 32v | 30 / 10m / 30v |
| google_cloud | https://cloud.google.com/compute/gpus-pricing | 4 / 3m / 4v | 17 / 10m / 17v | 16 / 10m / 15v | 29 / 10m / 28v | 15 / 6m / 15v | 17 / 8m / 17v | 49 / 11m / 49v | 34 / 6m / 34v |
| google_cloud | https://cloud.google.com/compute/all-pricing | 76 / 6m / 76v | 58 / 12m / 56v | 32 / 11m / 32v | 45 / 12m / 44v | 95 / 12m / 95v | 150 / 12m / 150v | 132 / 12m / 132v | 15 / 3m / 15v |
| google_cloud | https://cloud.google.com/compute/vm-instance-pricing | 7 / 3m / 7v | 13 / 8m / 13v | 22 / 10m / 21v | 31 / 12m / 31v | 19 / 9m / 19v | 37 / 11m / 37v | 95 / 12m / 95v | 18 / 3m / 18v |
| google_cloud | https://cloud.google.com/compute/docs/gpus | 61 / 11m / 61v | 40 / 10m / 40v | 21 / 10m / 21v | 26 / 11m / 26v | 22 / 9m / 22v | 42 / 11m / 42v | 97 / 11m / 97v | · |
| azure | https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/ | 48 / 11m / 48v | 58 / 11m / 58v | 39 / 11m / 39v | 94 / 12m / 93v | 35 / 10m / 35v | 65 / 12m / 65v | 54 / 11m / 54v | 116 / 10m / 116v |
| azure | https://azure.microsoft.com/en-us/pricing/details/virtual-machines/series/ | 15 / 8m / 15v | 7 / 5m / 7v | 7 / 6m / 7v | 10 / 8m / 10v | 15 / 7m / 14v | 18 / 10m / 18v | 23 / 10m / 23v | 13 / 9m / 13v |
| oracle | https://www.oracle.com/cloud/compute/pricing/ | · | · | · | 6 / 3m / 6v | 15 / 8m / 15v | 16 / 10m / 16v | 12 / 8m / 12v | 2 / 2m / 2v |
| oracle | https://www.oracle.com/cloud/price-list/ | · | · | · | 12 / 5m / 12v | 33 / 10m / 33v | 27 / 12m / 27v | 35 / 12m / 35v | 104 / 10m / 104v |
| oracle | https://www.oracle.com/cloud/compute/gpu/ | · | · | · | 79 / 10m / 79v | 59 / 12m / 50v | 36 / 12m / 36v | 33 / 12m / 33v | 10 / 5m / 10v |
| lambda | https://lambdalabs.com/service/gpu-cloud | 21 / 8m / 11v | 14 / 9m / 14v | 17 / 9m / 16v | 34 / 10m / 33v | 54 / 12m / 43v | 45 / 11m / 42v | 20 / 3m / 16v | · |
| lambda | https://lambdalabs.com/service/gpu-cloud/pricing | · | · | 5 / 3m / 5v | 9 / 6m / 7v | 10 / 6m / 9v | 1 / 1m / 1v | · | · |
| lambda | https://lambdalabs.com/service/gpu-cloud/reserved | · | · | · | 10 / 6m / 10v | 22 / 11m / 19v | 10 / 7m / 10v | · | · |
| lambda | https://lambda.ai/pricing | · | · | · | · | · | · | 27 / 7m / 27v | 75 / 10m / 74v |
| lambda | https://lambda.ai/service/gpu-cloud | · | · | · | · | · | · | 28 / 9m / 28v | · |
| coreweave | https://www.coreweave.com/pricing | · | 4 / 1m / 4v | 17 / 12m / 16v | 10 / 5m / 10v | 1 / 1m / 1v | · | 57 / 12m / 54v | 69 / 10m / 69v |
| coreweave | https://www.coreweave.com/gpu-cloud-pricing | · | · | · | 10 / 5m / 10v | 33 / 11m / 33v | 45 / 12m / 45v | 1 / 1m / 1v | · |
| coreweave | https://docs.coreweave.com/resources/resource-based-pricing | · | · | 4 / 4m / 4v | 7 / 4m / 7v | 13 / 7m / 13v | · | · | · |
| coreweave | https://docs.coreweave.com/docs/pricing/pricing-instances | · | · | · | · | · | · | 10 / 8m / 9v | 5 / 1m / 5v |
| runpod | https://www.runpod.io/pricing | · | · | · | · | · | 19 / 6m / 19v | 52 / 12m / 48v | 68 / 10m / 66v |
| runpod | https://www.runpod.io/gpu-instance/pricing | · | · | · | 8 / 6m / 7v | 16 / 9m / 15v | 14 / 5m / 14v | · | · |
| runpod | https://www.runpod.io/console/gpu-cloud | · | · | · | 5 / 3m / 5v | 53 / 9m / 30v | 21 / 3m / 15v | · | · |
| vast | https://vast.ai/pricing | · | · | · | · | 5 / 4m / 5v | 23 / 10m / 23v | 27 / 11m / 25v | 62 / 10m / 52v |
| vast | https://vast.ai/ | 22 / 10m / 15v | 22 / 10m / 20v | 21 / 10m / 20v | 64 / 12m / 52v | 86 / 12m / 57v | 161 / 12m / 81v | 159 / 12m / 99v | 124 / 10m / 93v |
| vast | https://cloud.vast.ai/create/ | · | · | · | · | 31 / 9m / 29v | 54 / 12m / 43v | 50 / 12m / 36v | 85 / 10m / 36v |
| vast | https://vast.ai/console/create/ | 13 / 9m / 12v | 13 / 6m / 13v | 20 / 10m / 17v | 22 / 11m / 22v | · | · | · | · |
| paperspace | https://www.paperspace.com/pricing | 35 / 10m / 35v | 8 / 5m / 7v | 16 / 9m / 12v | 22 / 9m / 17v | 25 / 11m / 20v | 68 / 12m / 34v | 23 / 11m / 5v | 17 / 8m / 5v |
| paperspace | https://www.paperspace.com/gpu-cloud | · | · | 3 / 2m / 3v | 11 / 8m / 9v | 12 / 8m / 10v | 16 / 10m / 11v | 7 / 6m / 3v | 6 / 6m / 3v |
| paperspace | https://www.paperspace.com/gradient/pricing | · | · | · | 12 / 5m / 9v | 18 / 7m / 9v | 13 / 7m / 10v | 5 / 5m / 4v | 3 / 3m / 2v |
| paperspace | https://docs.digitalocean.com/products/paperspace/machines/details/pricing/ | · | · | · | · | · | 9 / 6m / 9v | 9 / 7m / 8v | 2 / 2m / 2v |
