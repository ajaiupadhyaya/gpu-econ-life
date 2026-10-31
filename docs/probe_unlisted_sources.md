# Probe: unlisted free price histories

Exploration only, from `notebooks/probe_unlisted_sources.py`. Nothing here enters the
panel, and none of these sources is adopted until the owner approves it (rule 7).

## Azure Retail Prices API, East US, Linux, today

| Instance | Chip | Kind | $/GPU-h | Effective since |
| --- | --- | --- | --- | --- |
| Standard_NC6s_v3 | V100 | spot | 0.565 | 2026-01-01 |
| Standard_NC6s_v3 | V100 | on-demand | 3.060 | 2026-01-01 |
| Standard_ND96asr_v4 | A100 | spot | 0.738 | 2026-09-01 |
| Standard_ND96asr_v4 | A100 | on-demand | 3.400 | 2021-03-01 |
| Standard_ND96asr_v4 | A100 | reserved 1 Year | 2.354 | 2021-05-01 |
| Standard_ND96asr_v4 | A100 | reserved 3 Years | 1.360 | 2021-05-01 |
| Standard_ND96amsr_A100_v4 | A100-80GB | spot | 1.055 | 2026-09-01 |
| Standard_ND96amsr_A100_v4 | A100-80GB | on-demand | 4.096 | 2021-12-01 |
| Standard_ND96amsr_A100_v4 | A100-80GB | reserved 1 Year | 2.622 | 2021-12-01 |
| Standard_ND96amsr_A100_v4 | A100-80GB | reserved 3 Years | 1.802 | 2021-12-01 |
| Standard_NC24ads_A100_v4 | A100 | spot | 0.679 | 2026-07-01 |
| Standard_NC24ads_A100_v4 | A100 | on-demand | 3.673 | 2022-06-01 |
| Standard_NC24ads_A100_v4 | A100 | reserved 1 Year | 2.401 | 2022-06-01 |
| Standard_NC24ads_A100_v4 | A100 | reserved 3 Years | 1.363 | 2022-06-01 |
| Standard_ND96isr_H100_v5 | H100 | on-demand | 12.290 | 2023-12-01 |
| Standard_ND96isr_H100_v5 | H100 | reserved 1 Year | 7.866 | 2023-12-01 |
| Standard_ND96isr_H100_v5 | H100 | reserved 3 Years | 5.395 | 2023-12-01 |
| Standard_ND96isr_H100_v5 | H100 | reserved 5 Years | 4.916 | 2023-12-01 |
| Standard_ND96isr_H100_v5 | H100 | spot | 2.271 | 2026-01-01 |
| Standard_NC40ads_H100_v5 | H100 | spot | 1.290 | 2026-08-01 |
| Standard_NC40ads_H100_v5 | H100 | on-demand | 6.980 | 2024-03-01 |
| Standard_NC40ads_H100_v5 | H100 | reserved 1 Year | 5.235 | 2024-03-01 |
| Standard_NC40ads_H100_v5 | H100 | reserved 3 Years | 3.839 | 2024-03-01 |

## AWS Price List: EC2 offer-file versions by year

| Year | Versions |
| --- | --- |
| 2015 | 1 |
| 2016 | 5 |
| 2017 | 11 |
| 2018 | 11 |
| 2019 | 12 |
| 2020 | 13 |
| 2021 | 11 |
| 2022 | 12 |
| 2023 | 13 |
| 2024 | 12 |
| 2025 | 12 |
| 2026 | 10 |

First 20151209144527, latest 20261029175634, total 123.

## SkyPilot catalog history, sampled

Median across availability zones where a region has several. Sampled at a few dates,
so a flat run here means no change at those dates, not proof of no change between.

| Provider | Instance | Chip | Date sampled | Commit | On-demand $/GPU-h | Spot $/GPU-h |
| --- | --- | --- | --- | --- | --- | --- |
| aws | p3.2xlarge | V100 | 2022-12-15 | 6fdafaa | 3.06 | 1.143 |
| aws | p3.2xlarge | V100 | 2023-06-15 | 211f580 | 3.06 | 0.918 |
| aws | p3.2xlarge | V100 | 2023-12-15 | 54b68cf | 3.06 | 1.562 |
| aws | p3.2xlarge | V100 | 2024-06-15 | e2a47d6 | 3.06 | 1.5 |
| aws | p3.2xlarge | V100 | 2024-12-13 | 1bfec53 | 3.06 | 0.813 |
| aws | p3.2xlarge | V100 | 2025-05-15 | f126e4e | 3.06 | 0.688 |
| aws | p3.2xlarge | V100 | 2025-10-15 | 9c1b28d | 3.06 | 0.467 |
| aws | p3.2xlarge | V100 | 2026-03-31 | 06be764 | 3.06 | 0.371 |
| aws | p4d.24xlarge | A100 | 2022-12-15 | 6fdafaa | 4.097 | 1.229 |
| aws | p4d.24xlarge | A100 | 2023-06-15 | 211f580 | 4.097 | 1.229 |
| aws | p4d.24xlarge | A100 | 2023-12-15 | 54b68cf | 4.097 | 1.369 |
| aws | p4d.24xlarge | A100 | 2024-06-15 | e2a47d6 | 4.097 | 1.856 |
| aws | p4d.24xlarge | A100 | 2024-12-13 | 1bfec53 | 4.097 | 1.68 |
| aws | p4d.24xlarge | A100 | 2025-05-15 | f126e4e | 4.097 | 0.879 |
| aws | p4d.24xlarge | A100 | 2025-10-15 | 9c1b28d | 2.745 | 1.508 |
| aws | p4d.24xlarge | A100 | 2026-03-31 | 06be764 | 2.745 | 1.237 |
| aws | p4d.24xlarge | A100 | 2026-10-31 | 2f252e9 | 2.745 | 2.205 |
| aws | p5.48xlarge | H100 | 2023-12-15 | 54b68cf | 12.29 | 9.397 |
| aws | p5.48xlarge | H100 | 2024-06-15 | e2a47d6 | 12.29 | 6.819 |
| aws | p5.48xlarge | H100 | 2024-12-13 | 1bfec53 | 12.29 | 5.241 |
| aws | p5.48xlarge | H100 | 2025-05-15 | f126e4e | 12.29 | 3.332 |
| aws | p5.48xlarge | H100 | 2025-10-15 | 9c1b28d | 6.88 | 3.715 |
| aws | p5.48xlarge | H100 | 2026-03-31 | 06be764 | 6.88 | 2.335 |
| aws | p5.48xlarge | H100 | 2026-10-31 | 2f252e9 | 6.88 | 4.049 |
| azure | Standard_NC6s_v3 | V100 | 2022-07-25 | 17e771d | 3.06 | 1.142 |
| azure | Standard_NC6s_v3 | V100 | 2022-12-02 | 16d4b8d | 3.06 | 1.346 |
| azure | Standard_NC6s_v3 | V100 | 2023-12-08 | c2f2f01 | 3.06 | 0.935 |
| azure | Standard_NC6s_v3 | V100 | 2024-08-19 | eefe3a1 | 3.06 | 0.398 |
| azure | Standard_NC6s_v3 | V100 | 2025-09-11 | 0082b04 | 3.06 | 0.398 |
| azure | Standard_ND96asr_v4 | A100 | 2022-07-25 | 17e771d | 3.4 | 1.87 |
| azure | Standard_ND96asr_v4 | A100 | 2022-12-02 | 16d4b8d | 3.4 | 2.04 |
| azure | Standard_ND96asr_v4 | A100 | 2023-12-08 | c2f2f01 | 3.4 | 0.602 |
| azure | Standard_ND96asr_v4 | A100 | 2024-08-19 | eefe3a1 | 3.4 | 0.374 |
| azure | Standard_ND96asr_v4 | A100 | 2025-09-11 | 0082b04 | 3.4 | 0.374 |
| azure | Standard_ND96amsr_A100_v4 | A100-80GB | 2022-07-25 | 17e771d | 4.096 | 2.048 |
| azure | Standard_ND96amsr_A100_v4 | A100-80GB | 2022-12-02 | 16d4b8d | 4.096 | 2.253 |
| azure | Standard_ND96amsr_A100_v4 | A100-80GB | 2023-12-08 | c2f2f01 | 4.096 | 0.721 |
| azure | Standard_ND96amsr_A100_v4 | A100-80GB | 2024-08-19 | eefe3a1 | 4.096 | 0.451 |
| azure | Standard_ND96amsr_A100_v4 | A100-80GB | 2025-09-11 | 0082b04 | 4.096 | 0.451 |
| lambda | gpu_1x_a100_sxm4 | A100 | 2023-06-15 | 329b483 | 1.1 | None |
| lambda | gpu_1x_a100_sxm4 | A100 | 2024-05-29 | 6995272 | 1.29 | None |
| lambda | gpu_1x_a100_sxm4 | A100 | 2024-11-19 | a36e196 | 1.29 | None |
| lambda | gpu_1x_a100_sxm4 | A100 | 2025-05-05 | 4083ed5 | 1.29 | None |
| lambda | gpu_1x_a100_sxm4 | A100 | 2025-10-11 | 9daf03f | 1.29 | None |
| lambda | gpu_1x_a100_sxm4 | A100 | 2026-04-06 | 55906a5 | 1.99 | None |
| lambda | gpu_1x_a100_sxm4 | A100 | 2026-08-03 | 0f40703 | 1.99 | None |
| lambda | gpu_8x_h100_sxm5 | H100 | 2024-05-29 | 6995272 | 3.49 | None |
| lambda | gpu_8x_h100_sxm5 | H100 | 2024-11-19 | a36e196 | 2.99 | None |
| lambda | gpu_8x_h100_sxm5 | H100 | 2025-05-05 | 4083ed5 | 2.99 | None |
| lambda | gpu_8x_h100_sxm5 | H100 | 2025-10-11 | 9daf03f | 2.99 | None |
| lambda | gpu_8x_h100_sxm5 | H100 | 2026-04-06 | 55906a5 | 3.99 | None |
| lambda | gpu_8x_h100_sxm5 | H100 | 2026-08-03 | 0f40703 | 3.99 | None |
