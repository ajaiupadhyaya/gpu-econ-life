"""M8: triangulate P1, P2 and P3 against accounting lives (handoff section 6; Decision 15).

Per generation (A100 80GB, H100 SXM, H200 SXM; the L40S has no P2 neocloud data and its own
product class):
- P1: obsolescence discount D (BF16, c=32, neocloud median; provider min-max) and a P1-implied
  life. P1 is a snapshot, so its implied rent decay is the cross-sectional slope of log
  neocloud rent on chip age along the SXM line (A100 -> H100 -> H200), computed separately with
  each chip's min, median and max neocloud price. L_opex(P1) = age + ln(rent / opex) / delta_cs.
- P2: L_opex over the (r, pi) grid, neocloud and hyperscaler (Decision 14).
- P3: median retirement age with P10-P90 (base), plus always-constrained and power-abundant
  medians. P3 is generation-generic (calibrated on the H100), so one row serves all chips.
- Accounting lives compared: 4, 5, 5.5, 6 years (the handoff's set; firm-specific lives are
  Phase 7's).
- Attribution: P3 with no scarcity markup vs base; markup share of today's rent = m / (1 + m).
- Blended fleet: 1 / (s / L_gpu + (1 - s) / L_other), s in {0.3, 0.5, 0.7}, L_other in {6, 7}.

Outputs: paper/tables/m8_triangulation.csv, m8_blended_fleet.csv, m8_attribution.csv,
paper/figures/t1_triangulation.png
Usage: uv run python -m gel.models.triangulate
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

TABLES, FIGURES = Path("paper/tables"), Path("paper/figures")
CHIPS = {"a100_80gb": "A100 80GB", "h100_sxm": "H100 SXM", "h200": "H200 SXM"}
LABEL = {"a100_80gb": "A100_SXM", "h100_sxm": "H100_SXM", "h200": "H200_SXM"}
BOOK_LIVES = (4.0, 5.0, 5.5, 6.0)
SHARES = (0.3, 0.5, 0.7)
L_OTHER = (6.0, 7.0)


def blended_life(s: float, l_gpu: float, l_other: float) -> float:
    return 1.0 / (s / l_gpu + (1.0 - s) / l_other)


def cross_section_delta(ages, prices) -> float:
    """-slope of OLS ln(price) on age; NaN unless rents fall with age."""
    a = np.asarray(ages, dtype=float)
    y = np.log(np.asarray(prices, dtype=float))
    slope = np.polyfit(a, y, 1)[0]
    return float(-slope) if slope < 0 else math.nan


def markup_share(m: float) -> float:
    return m / (1.0 + m)


def p1_block(inputs: dict) -> tuple[dict, dict]:
    panel = pl.read_parquet("data/processed/spot_panel.parquet").filter(
        (pl.col("billing") == "on_demand") & (pl.col("provider_type") == "neocloud")
    )
    d = pl.read_csv(TABLES / "fig_p1d.csv")
    stats = {}
    for chip in CHIPS:
        p = panel.filter(pl.col("chip_id") == chip)["price_per_gpu_hr"]
        stats[chip] = {"min": float(p.min()), "median": float(p.median()), "max": float(p.max())}
    ages = [inputs[c]["age_now"] for c in CHIPS]
    deltas = {
        spec: cross_section_delta(ages, [stats[c][spec] for c in CHIPS])
        for spec in ("min", "median", "max")
    }
    out = {}
    for chip in CHIPS:
        row = d.filter(pl.col("gpu_label") == LABEL[chip])
        lives = []
        for spec, dl in deltas.items():
            if dl == dl:
                lives.append(
                    inputs[chip]["age_now"]
                    + math.log(stats[chip][spec] / inputs[chip]["opex_hr"]) / dl
                )
        out[chip] = {
            "p1_D_median": row["discount_median"][0] if row.height else 0.0,
            "p1_D_low": row["discount_low"][0] if row.height else 0.0,
            "p1_D_high": row["discount_high"][0] if row.height else 0.0,
            "p1_Lopex_low": min(lives) if lives else math.nan,
            "p1_Lopex_high": max(lives) if lives else math.nan,
        }
    return out, deltas


def p2_block() -> dict:
    t = pl.read_csv(TABLES / "p2_implied_decay.csv")
    out = {}
    for chip in CHIPS:
        g = t.filter((pl.col("chip") == chip) & pl.col("L_opex_y").is_finite())
        out[chip] = {
            "p2_Lopex_low": float(g["L_opex_y"].min()) if g.height else math.nan,
            "p2_Lopex_high": float(g["L_opex_y"].max()) if g.height else math.nan,
            "p2_L50_low": float(g["L50_y"].min()) if g.height else math.nan,
            "p2_L50_high": float(g["L50_y"].max()) if g.height else math.nan,
            "p2_provider_types": ",".join(sorted(g["provider_type"].unique().to_list())),
        }
    return out


def p3_block() -> dict:
    s = {r["scenario"]: r for r in json.loads((TABLES / "p3_summary.json").read_text())}
    b = s["base"]
    return {
        "p3_median": b["retire_age_p50_y"],
        "p3_p10": b["retire_age_p10_y"],
        "p3_p90": b["retire_age_p90_y"],
        "p3_constrained_median": s["always_constrained"]["retire_age_p50_y"],
        "p3_abundant_median": s["power_abundant"]["retire_age_p50_y"],
        "p3_no_scarcity_median": s["no_scarcity"]["retire_age_p50_y"],
        "p3_boom_median": s["scarcity_boom"]["retire_age_p50_y"],
    }


def build() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, dict]:
    from gel.models.p2_term import chip_inputs

    inputs = chip_inputs()
    p1, deltas = p1_block(inputs)
    p2 = p2_block()
    p3 = p3_block()
    rows = []
    for chip, name in CHIPS.items():
        rows.append(
            {
                "generation": name,
                "chip": chip,
                "age_now_y": inputs[chip]["age_now"],
                **p1[chip],
                **p2[chip],
                **p3,
                "book_lives_y": "/".join(f"{x:g}" for x in BOOK_LIVES),
            }
        )
    tri = pl.DataFrame(rows)

    market = json.loads(Path("data/processed/p3_market.json").read_text())["markup"]
    attribution = pl.DataFrame(
        [
            {
                "quantity": "P3 median life, no scarcity markup (y)",
                "value": p3["p3_no_scarcity_median"],
            },
            {"quantity": "P3 median life, base markup (y)", "value": p3["p3_median"]},
            {"quantity": "P3 median life, 2026 boom markup (y)", "value": p3["p3_boom_median"]},
            {
                "quantity": "Life shortened by scarcity, base (y)",
                "value": p3["p3_no_scarcity_median"] - p3["p3_median"],
            },
            {
                "quantity": "Markup share of rent, base (m/(1+m))",
                "value": markup_share(market["mean"]),
            },
            {
                "quantity": "Markup share of rent, 2026 boom",
                "value": markup_share(market["boom_mean"]),
            },
            {
                "quantity": "P1 cross-sectional rent decay, median prices (/y)",
                "value": deltas["median"],
            },
        ]
    )

    gpu_lives = {
        "P3 base median": p3["p3_median"],
        "P3 always constrained": p3["p3_constrained_median"],
        "P3 power abundant": p3["p3_abundant_median"],
        "P2 H100 L_opex (low)": p2["h100_sxm"]["p2_Lopex_low"],
        "P1 H100 L_opex (low)": p1["h100_sxm"]["p1_Lopex_low"],
    }
    blend = pl.DataFrame(
        [
            {
                "gpu_life_source": k,
                "L_gpu_y": v,
                "gpu_share_s": s,
                "L_other_y": lo,
                "blended_life_y": blended_life(s, v, lo),
            }
            for k, v in gpu_lives.items()
            for s in SHARES
            for lo in L_OTHER
        ]
    )
    return tri, blend, attribution, deltas


def main() -> int:
    from gel.viz import triangulation_figure

    tri, blend, attribution, deltas = build()
    TABLES.mkdir(parents=True, exist_ok=True)
    tri.write_csv(TABLES / "m8_triangulation.csv")
    blend.write_csv(TABLES / "m8_blended_fleet.csv")
    attribution.write_csv(TABLES / "m8_attribution.csv")
    triangulation_figure.render(tri)
    pl.Config.set_tbl_width_chars(230)
    pl.Config.set_tbl_rows(40)
    print(
        tri.select(
            "generation",
            pl.col("age_now_y").round(1),
            pl.col("p1_D_median").round(3),
            pl.col("p1_Lopex_low").round(1),
            pl.col("p1_Lopex_high").round(1),
            pl.col("p2_Lopex_low").round(1),
            pl.col("p2_Lopex_high").round(1),
            pl.col("p2_L50_low").round(2),
            pl.col("p2_L50_high").round(2),
            pl.col("p3_median").round(2),
            pl.col("p3_p10").round(2),
            pl.col("p3_p90").round(2),
        )
    )
    print(attribution.with_columns(pl.col("value").round(3)))
    print(
        blend.filter(pl.col("L_other_y") == 6.0)
        .pivot(on="gpu_share_s", index="gpu_life_source", values="blended_life_y")
        .with_columns(pl.col(pl.Float64).round(2))
    )
    print("P1 cross-sectional deltas:", {k: round(v, 3) for k, v in deltas.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
