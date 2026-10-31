"""Exploration only: do free dated price histories exist that the proposal does not list?

Samples the git history of the public SkyPilot catalog at a few dates and prints on-demand and spot
$/GPU-hour for a handful of instances. Nothing here enters the panel, and none of these sources is
adopted until the owner approves them (CLAUDE.md rule 7). Run from the repo root:

    uv run python notebooks/probe_unlisted_sources.py
"""

import csv
import io
import json
import statistics
import subprocess

import httpx

from gel.collect.http import Throttle, get_with_backoff, user_agent

REPO = "skypilot-org/skypilot-catalog"
RAW = "https://raw.githubusercontent.com/" + REPO
TARGETS = {
    "aws": {
        "paths": [
            ("2025-06-30", "catalogs/v5/aws/vms.csv"),
            ("2099-01-01", "catalogs/v8/aws/vms.csv"),
        ],
        "region": "us-east-1",
        "instances": {"p3.2xlarge": "V100", "p4d.24xlarge": "A100", "p5.48xlarge": "H100"},
    },
    "azure": {
        "paths": [
            ("2022-08-30", "catalogs/v1/azure.csv"),
            ("2022-11-01", "catalogs/v3/azure.csv"),
            ("2025-04-01", "catalogs/v5/azure/vms.csv"),
            ("2099-01-01", "catalogs/v8/azure/vms.csv"),
        ],
        "region": "eastus",
        "instances": {
            "Standard_NC6s_v3": "V100",
            "Standard_ND96asr_v4": "A100",
            "Standard_ND96amsr_A100_v4": "A100-80GB",
        },
    },
    "lambda": {
        "paths": [
            ("2025-06-30", "catalogs/v5/lambda/vms.csv"),
            ("2099-01-01", "catalogs/v8/lambda/vms.csv"),
        ],
        "region": "us-east-1",
        "instances": {"gpu_1x_a100_sxm4": "A100", "gpu_8x_h100_sxm5": "H100"},
    },
}
DATES = [
    "2022-08-01", "2022-12-15", "2023-06-15", "2023-12-15", "2024-06-15", "2024-12-15",
    "2025-05-15", "2025-10-15", "2026-04-15", "2026-10-31",
]  # fmt: skip


def commit_before(path: str, date: str) -> dict | None:
    out = subprocess.run(
        ["gh", "api", f"repos/{REPO}/commits?path={path}&until={date}T23:59:59Z&per_page=1"],
        capture_output=True,
        text=True,
    )
    rows = json.loads(out.stdout or "[]")
    if not rows or not isinstance(rows, list):
        return None
    return {"sha": rows[0]["sha"], "date": rows[0]["commit"]["committer"]["date"][:10]}


def path_for(cfg: dict, date: str) -> str | None:
    for upto, path in cfg["paths"]:
        if date <= upto:
            return path
    return None


def per_gpu(rows: list[dict], column: str) -> float | None:
    values = [float(r[column]) / float(r["AcceleratorCount"]) for r in rows if r.get(column)]
    return round(statistics.median(values), 3) if values else None


AZURE_SKUS = {
    "Standard_NC6s_v3": ("V100", 1),
    "Standard_ND96asr_v4": ("A100", 8),
    "Standard_ND96amsr_A100_v4": ("A100-80GB", 8),
    "Standard_NC24ads_A100_v4": ("A100", 1),
    "Standard_ND96isr_H100_v5": ("H100", 8),
    "Standard_NC40ads_H100_v5": ("H100", 1),
}
TERM_HOURS = {"1 Year": 8760, "3 Years": 26280, "5 Years": 43800}


def azure_current() -> None:
    """Azure Retail Prices: today's East US Linux prices and the date each took effect.

    Reservation rows hold the whole-term price even though the unit field says "1 Hour".
    """
    print("## Azure Retail Prices API, East US, Linux, today\n")
    print("| Instance | Chip | Kind | $/GPU-h | Effective since |")
    print("| --- | --- | --- | --- | --- |")
    throttle = Throttle(min_interval=1.2)
    url = "https://prices.azure.com/api/retail/prices"
    with httpx.Client(headers={"User-Agent": user_agent()}, timeout=60) as client:
        for sku, (chip, gpus) in AZURE_SKUS.items():
            throttle.wait("prices.azure.com")
            flt = f"armSkuName eq '{sku}' and armRegionName eq 'eastus'"
            items = get_with_backoff(client, url, params={"$filter": flt}).json()["Items"]
            for item in items:
                name = item["skuName"]
                if "Windows" in item["productName"] or "Low Priority" in name:
                    continue
                term = item.get("reservationTerm")
                if item["type"] == "Reservation" and term:
                    kind, price = f"reserved {term}", item["retailPrice"] / TERM_HOURS[term]
                elif item["type"] == "Consumption":
                    kind, price = ("spot" if "Spot" in name else "on-demand"), item["retailPrice"]
                else:
                    continue
                since = item["effectiveStartDate"][:10]
                print(f"| {sku} | {chip} | {kind} | {price / gpus:.3f} | {since} |")
    print()


def aws_offer_versions() -> None:
    print("## AWS Price List: EC2 offer-file versions by year\n")
    url = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/index.json"
    with httpx.Client(headers={"User-Agent": user_agent()}, timeout=60) as client:
        versions = sorted(client.get(url).json()["versions"])
    years = sorted({v[:4] for v in versions})
    print("| Year | Versions |\n| --- | --- |")
    for year in years:
        print(f"| {year} | {sum(v[:4] == year for v in versions)} |")
    print(f"\nFirst {versions[0]}, latest {versions[-1]}, total {len(versions)}.\n")


def main() -> None:
    print("# Probe: unlisted free price histories\n")
    print("Exploration only, from `notebooks/probe_unlisted_sources.py`. Nothing here enters the")
    print("panel, and none of these sources is adopted until the owner approves it (rule 7).\n")
    azure_current()
    aws_offer_versions()
    print("## SkyPilot catalog history, sampled\n")
    print("Median across availability zones where a region has several. Sampled at a few dates,")
    print("so a flat run here means no change at those dates, not proof of no change between.\n")
    print(
        "| Provider | Instance | Chip | Date sampled | Commit | On-demand $/GPU-h | Spot $/GPU-h |"
    )
    print("| --- | --- | --- | --- | --- | --- | --- |")
    cache: dict[tuple[str, str], list[dict]] = {}
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        for provider, cfg in TARGETS.items():
            for instance, chip in cfg["instances"].items():
                seen = set()
                for date in DATES:
                    path = path_for(cfg, date)
                    commit = commit_before(path, date) if path else None
                    if not commit or commit["sha"] in seen:
                        continue
                    seen.add(commit["sha"])
                    key = (commit["sha"], path)
                    if key not in cache:
                        text = client.get(f"{RAW}/{commit['sha']}/{path}").text
                        cache[key] = list(csv.DictReader(io.StringIO(text)))
                    rows = [
                        r
                        for r in cache[key]
                        if r["InstanceType"] == instance and r.get("Region") == cfg["region"]
                    ]
                    if rows:
                        print(
                            f"| {provider} | {instance} | {chip} | {commit['date']} | "
                            f"{commit['sha'][:7]} | {per_gpu(rows, 'Price')} | "
                            f"{per_gpu(rows, 'SpotPrice')} |"
                        )


if __name__ == "__main__":
    main()
