"""Phase 7 cohort restatement of GPU depreciation (proposal Step 4).

For each firm and fiscal year:

    GPU capex_c = capex_c x server_share x gpu_share          (cohort c = purchase fiscal year)

Each cohort enters at its purchase year (year 1 of its life, a full year's charge) and is
depreciated twice:

(a) Book: straight-line over the firm's disclosed server life in effect (config/accounting.yaml
    book_life). A life change at fiscal year T applies to cohorts bought from T on, and
    prospectively to older cohorts: their net book value at the start of T is spread evenly over
    the remaining new life (new life minus years already depreciated); if nothing remains, the
    net book value is charged in T.
(b) Alternative: dep_share by year of life, read from a CSV with columns schedule, year,
    dep_share (Phase 6 market-implied schedules at paper/tables/p6_schedules.csv when that file
    exists, plus the straight-line reference set written to paper/tables/p7_book_schedules.csv).

Reported per firm-year, schedule, server share, GPU share and tax basis: delta depreciation =
alternative - book, delta operating income = -delta depreciation, delta net income = delta
operating income x (1 - tax rate), delta diluted EPS = delta net income / diluted shares. Tax is
the firm-year effective rate from XBRL (IncomeTaxExpenseBenefit / pre-tax income) or the 21%
statutory rate. Every input is an XBRL fact in data/interim/edgar/facts.parquet (listed with its
accession number in paper/tables/p7_facts_used.csv) or a parameter in config/accounting.yaml.

Outputs: paper/tables/p7_restatement.csv, p7_restatement.tex, p7_facts_used.csv,
p7_book_schedules.csv and paper/figures/p7_restatement.png.

Usage: uv run python -m gel.accounting.restate
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import polars as pl
import yaml

CONFIG = Path("config/accounting.yaml")
FACTS = Path("data/interim/edgar/facts.parquet")
OUT_CSV = Path("paper/tables/p7_restatement.csv")
OUT_TEX = Path("paper/tables/p7_restatement.tex")
OUT_FACTS = Path("paper/tables/p7_facts_used.csv")
OUT_FIG = Path("paper/figures/p7_restatement.png")
DOLLAR_VARS = ["capex", "operating_income", "pretax_income", "income_tax", "net_income"]
PER_SHARE_VARS = ["eps_diluted", "shares_diluted"]
CONTEXT_VARS = ["depreciation"]

# ------------------------------------------------------------------ schedules


def straight_line(life: float) -> list[float]:
    """dep_share by year of life for straight-line over `life` years (fractional final year)."""
    full = math.floor(life)
    shares = [1.0 / life] * full
    if life > full:
        shares.append((life - full) / life)
    return shares


def sl_name(life: float) -> str:
    return f"sl_{life:g}y"


def reference_schedules(lives: list[float]) -> pl.DataFrame:
    rows = [
        {"schedule": sl_name(life), "year": i + 1, "dep_share": s}
        for life in lives
        for i, s in enumerate(straight_line(life))
    ]
    return pl.DataFrame(
        rows, schema={"schedule": pl.Utf8, "year": pl.Int64, "dep_share": pl.Float64}
    )


def validate_schedules(df: pl.DataFrame) -> dict[str, list[float]]:
    """schedule -> dep_share list for years 1..N. Shares must be >= 0 and sum to at most 1."""
    missing = {"schedule", "year", "dep_share"} - set(df.columns)
    if missing:
        raise ValueError(f"schedule CSV lacks columns {sorted(missing)}")
    out: dict[str, list[float]] = {}
    for (name,), g in df.sort(["schedule", "year"]).group_by(["schedule"], maintain_order=True):
        years = g["year"].to_list()
        if years != list(range(1, len(years) + 1)):
            raise ValueError(f"schedule {name}: years must run 1..N without gaps, got {years}")
        shares = [float(x) for x in g["dep_share"].to_list()]
        if any(s < 0 for s in shares):
            raise ValueError(f"schedule {name}: negative dep_share")
        if sum(shares) > 1 + 1e-9:
            raise ValueError(f"schedule {name}: dep_share sums to {sum(shares):.6f} > 1")
        out[str(name)] = shares
    return out


def load_schedules(
    cfg: dict, root: Path = Path(".")
) -> tuple[dict[str, list[float]], dict[str, str]]:
    """Reference straight-line set (always written and used) plus Phase 6 schedules if present."""
    sc = cfg["schedules"]
    ref = reference_schedules([float(x) for x in sc["straight_line_years"]])
    ref_path = root / sc["reference_path"]
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref.write_csv(ref_path)
    schedules = validate_schedules(ref)
    source = dict.fromkeys(schedules, "straight_line_reference")
    p6 = root / sc["market_implied_path"]
    if p6.exists():
        market = validate_schedules(pl.read_csv(p6))
        clash = set(market) & set(schedules)
        if clash:
            raise ValueError(f"p6 schedule names clash with the reference set: {sorted(clash)}")
        schedules.update(market)
        source.update(dict.fromkeys(market, "market_implied_p6"))
    return schedules, source


# ------------------------------------------------------------------ depreciation arithmetic


def life_in_effect(life_map: dict[int, float], fy: int) -> float:
    keys = sorted(k for k in life_map if k <= fy)
    if not keys:
        raise ValueError(f"no book life in effect for fiscal year {fy}")
    return float(life_map[keys[-1]])


def book_depreciation(
    cost: float, cohort_fy: int, life_map: dict[int, float], last_fy: int
) -> dict[int, float]:
    """Straight-line with prospective life changes. Returns {fiscal_year: depreciation}."""
    out: dict[int, float] = {}
    nbv = cost
    for age, fy in enumerate(range(cohort_fy, last_fy + 1)):  # age = years already charged
        remaining = life_in_effect(life_map, fy) - age
        if nbv <= 1e-12 * max(abs(cost), 1.0):
            dep = 0.0
        elif remaining <= 1:
            dep = nbv
        else:
            dep = nbv / remaining
        out[fy] = dep
        nbv -= dep
    return out


def schedule_depreciation(
    cost: float, cohort_fy: int, shares: list[float], last_fy: int
) -> dict[int, float]:
    return {
        fy: cost * (shares[fy - cohort_fy] if fy - cohort_fy < len(shares) else 0.0)
        for fy in range(cohort_fy, last_fy + 1)
    }


def fleet_depreciation(capex: dict[int, float], fn, last_fy: int) -> dict[int, float]:
    """Sum a per-cohort depreciation function over cohorts {fy: cost}."""
    total: dict[int, float] = {}
    for c, cost in capex.items():
        for fy, d in fn(cost, c).items():
            if fy <= last_fy:
                total[fy] = total.get(fy, 0.0) + d
    return total


# ------------------------------------------------------------------ XBRL inputs


def firm_facts(facts: pl.DataFrame, firm: str, per_share_basis: str) -> dict[int, dict]:
    """{fiscal_year: {variable: (value, accn, concept, basis)}} from the selected facts."""
    sel = facts.filter((pl.col("ticker") == firm) & pl.col("selected"))
    out: dict[int, dict] = {}
    for r in sel.iter_rows(named=True):
        var = r["variable"]
        if var not in DOLLAR_VARS + PER_SHARE_VARS + CONTEXT_VARS:
            continue
        latest = var in PER_SHARE_VARS and per_share_basis == "latest"
        rec = {
            "value": r["value_latest"] if latest else r["value"],
            "accn": r["accn_latest"] if latest else r["accn"],
            "form": r["form_latest"] if latest else r["form"],
            "filed": r["filed_latest"] if latest else r["filed"],
            "concept": r["concept"],
            "unit": r["unit"],
            "start": r["start"],
            "end": r["end"],
            "basis": "latest_filing" if latest else "original_filing",
        }
        out.setdefault(r["fiscal_year"], {})[var] = rec
    return out


def _v(d: dict, var: str) -> float | None:
    rec = d.get(var)
    return None if rec is None else rec["value"]


def _a(d: dict, var: str) -> str | None:
    rec = d.get(var)
    return None if rec is None else rec["accn"]


# ------------------------------------------------------------------ restatement


def restate_firm(
    firm: str,
    ff: dict[int, dict],
    life_map: dict[int, float],
    schedules: dict[str, list[float]],
    cfg: dict,
    *,
    cohort_start: int,
    book_variant: str,
    schedule_source: dict[str, str],
) -> list[dict]:
    report_from = int(cfg["report_from_fy"])
    years_with_oi = [fy for fy, d in ff.items() if "operating_income" in d and "capex" in d]
    if not years_with_oi:
        return []
    last_fy = max(years_with_oi)
    capex = {fy: d["capex"]["value"] for fy, d in ff.items() if "capex" in d and fy >= cohort_start}
    capex = {fy: v for fy, v in capex.items() if fy <= last_fy}
    # Unit base: depreciation of the whole capex stream (scaled by server x GPU share below).
    book = fleet_depreciation(
        capex, lambda k, c: book_depreciation(k, c, life_map, last_fy), last_fy
    )
    alts = {
        name: fleet_depreciation(
            capex, lambda k, c, s=shares: schedule_depreciation(k, c, s, last_fy), last_fy
        )
        for name, shares in schedules.items()
    }
    statutory = float(cfg["tax"]["statutory_rate"])
    rows: list[dict] = []
    for fy in range(max(report_from, min(ff)), last_fy + 1):
        d = ff.get(fy, {})
        oi = _v(d, "operating_income")
        if oi is None:
            continue
        pretax, pretax_source = _v(d, "pretax_income"), "xbrl"
        if pretax is None and _v(d, "net_income") is not None and _v(d, "income_tax") is not None:
            pretax, pretax_source = (
                _v(d, "net_income") + _v(d, "income_tax"),
                "net_income+income_tax",
            )
        tax = _v(d, "income_tax")
        eff = tax / pretax if (tax is not None and pretax and pretax > 0) else None
        if eff is not None and not 0 <= eff <= 1:
            eff = None
        eps = _v(d, "eps_diluted")
        shares, shares_source = _v(d, "shares_diluted"), "xbrl"
        if shares is None and eps and _v(d, "net_income") is not None:
            shares, shares_source = _v(d, "net_income") / eps, "net_income/eps_diluted"
        dep_rep = _v(d, "depreciation")
        base = {
            "firm": firm,
            "fiscal_year": fy,
            "book_variant": book_variant,
            "gpu_cohort_start_fy": cohort_start,
            "book_life_in_effect": life_in_effect(life_map, fy),
            "capex_usd": _v(d, "capex"),
            "operating_income_usd": oi,
            "pretax_income_usd": pretax,
            "pretax_source": pretax_source,
            "income_tax_usd": tax,
            "depreciation_reported_usd": dep_rep,
            "eps_diluted": eps,
            "shares_diluted": shares,
            "shares_source": shares_source,
            "per_share_basis": cfg.get("per_share_basis", "latest"),
            "capex_accn": _a(d, "capex"),
            "operating_income_accn": _a(d, "operating_income"),
            "pretax_income_accn": _a(d, "pretax_income"),
            "income_tax_accn": _a(d, "income_tax"),
            "net_income_accn": _a(d, "net_income"),
            "depreciation_accn": _a(d, "depreciation"),
            "eps_accn": _a(d, "eps_diluted"),
            "shares_accn": _a(d, "shares_diluted"),
        }
        for name in schedules:
            for s in cfg["server_share"]["grid"]:
                for g in cfg["gpu_share"]["grid"]:
                    k = float(s) * float(g)
                    dep_book = k * book.get(fy, 0.0)
                    dep_alt = k * alts[name].get(fy, 0.0)
                    delta = dep_alt - dep_book
                    for basis, rate in (("effective", eff), ("statutory_21", statutory)):
                        dni = None if rate is None else -delta * (1 - rate)
                        deps = None if (dni is None or not shares) else dni / shares
                        rows.append(
                            {
                                **base,
                                "schedule": name,
                                "schedule_source": schedule_source[name],
                                "server_share": float(s),
                                "gpu_share": float(g),
                                "tax_basis": basis,
                                "tax_rate": rate,
                                "gpu_capex_usd": k * capex[fy] if fy in capex else 0.0,
                                "dep_book_gpu_usd": dep_book,
                                "dep_alt_gpu_usd": dep_alt,
                                "delta_dep_usd": delta,
                                "delta_dep_pct_of_reported": (
                                    100 * delta / dep_rep if dep_rep else None
                                ),
                                "delta_operating_income_usd": -delta,
                                "operating_income_restated_usd": oi - delta,
                                "delta_oi_pct": 100 * -delta / abs(oi) if oi else None,
                                "delta_net_income_usd": dni,
                                "delta_eps": deps,
                                "eps_restated": None
                                if (deps is None or eps is None)
                                else eps + deps,
                            }
                        )
    return rows


COLUMNS = [
    "firm", "fiscal_year", "schedule", "schedule_source", "book_variant", "gpu_cohort_start_fy",
    "server_share", "gpu_share", "tax_basis", "book_life_in_effect", "capex_usd", "gpu_capex_usd",
    "dep_book_gpu_usd", "dep_alt_gpu_usd", "delta_dep_usd", "depreciation_reported_usd",
    "delta_dep_pct_of_reported", "operating_income_usd", "delta_operating_income_usd",
    "operating_income_restated_usd", "delta_oi_pct", "pretax_income_usd", "pretax_source",
    "income_tax_usd", "tax_rate", "delta_net_income_usd", "per_share_basis", "shares_diluted",
    "shares_source", "eps_diluted", "delta_eps", "eps_restated", "capex_accn",
    "operating_income_accn", "pretax_income_accn", "income_tax_accn", "net_income_accn",
    "depreciation_accn", "eps_accn", "shares_accn",
]  # fmt: skip


def run(root: Path = Path(".")) -> pl.DataFrame:
    cfg = yaml.safe_load((root / CONFIG).read_text())
    facts = pl.read_parquet(root / FACTS)
    schedules, source = load_schedules(cfg, root)
    basis = cfg.get("per_share_basis", "latest")
    rows: list[dict] = []
    used: list[dict] = []
    starts = [int(cfg["gpu_cohort_start_fy"]), *map(int, cfg.get("cohort_start_alternatives", []))]
    for firm in cfg["firms"]:
        ff = firm_facts(facts, firm, basis)
        variants = {"disclosed": cfg["book_life"][firm]}
        for name, alt in (cfg.get("book_life_alternatives") or {}).items():
            if alt["firm"] == firm:
                variants[name] = alt["life"]
        for variant, life_map in variants.items():
            life_map = {int(k): float(v) for k, v in life_map.items()}
            for start in starts:
                rows += restate_firm(
                    firm, ff, life_map, schedules, cfg,
                    cohort_start=start, book_variant=variant, schedule_source=source,
                )  # fmt: skip
        first_cohort = min(starts)
        report_from = int(cfg["report_from_fy"])
        for fy, d in sorted(ff.items()):
            for var, rec in d.items():
                if (var == "capex" and fy >= first_cohort) or fy >= report_from:
                    used.append({"firm": firm, "fiscal_year": fy, "variable": var, **rec})
    df = pl.DataFrame(rows, infer_schema_length=None).select(COLUMNS)
    df = df.sort(["firm", "book_variant", "gpu_cohort_start_fy", "schedule", "server_share",
                  "gpu_share", "tax_basis", "fiscal_year"])  # fmt: skip
    (root / OUT_CSV).parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(root / OUT_CSV, float_precision=6)
    used_df = pl.DataFrame(used).rename({"value": "value_used", "basis": "value_basis"})
    last_fy = df.group_by("firm").agg(pl.col("fiscal_year").max().alias("_last"))
    used_df = used_df.join(last_fy, on="firm").filter(pl.col("fiscal_year") <= pl.col("_last"))
    used_df.drop("_last").sort(["firm", "variable", "fiscal_year"]).write_csv(root / OUT_FACTS)
    write_tex(pl.read_csv(root / OUT_CSV, infer_schema_length=None), cfg, root / OUT_TEX)
    plot(pl.read_csv(root / OUT_CSV, infer_schema_length=None), cfg, root / OUT_FIG)
    return df


# ------------------------------------------------------------------ exhibits


def _baseline(df: pl.DataFrame, cfg: dict) -> pl.DataFrame:
    return df.filter(
        (pl.col("book_variant") == "disclosed")
        & (pl.col("gpu_cohort_start_fy") == int(cfg["gpu_cohort_start_fy"]))
        & (pl.col("server_share") == float(cfg["server_share"]["baseline"]))
    )


def _fmt(lo: float | None, hi: float | None, digits: int) -> str:
    if lo is None or hi is None:
        return "n/a"
    return f"{lo:+.{digits}f} to {hi:+.{digits}f}".replace("-", "$-$")


def write_tex(df: pl.DataFrame, cfg: dict, path: Path) -> None:
    """Compact sensitivity table: latest fiscal year per firm, baseline server share."""
    ex = cfg["exhibit"]
    lo_g, hi_g = float(ex["gpu_share_low"]), float(ex["gpu_share_high"])
    base = _baseline(df, cfg).filter(pl.col("tax_basis") == ex["tax_basis"])
    last = base.group_by("firm").agg(pl.col("fiscal_year").max().alias("fy"))
    base = base.join(last, on="firm").filter(pl.col("fiscal_year") == pl.col("fy"))
    names = sorted(base["schedule"].unique().to_list(), key=_schedule_key)
    firms = [f for f in cfg["firms"] if f in set(base["firm"].to_list())]

    def cell(firm: str, sched: str, col: str, scale: float, digits: int) -> str:
        sub = base.filter((pl.col("firm") == firm) & (pl.col("schedule") == sched))
        vals = {}
        for g in (lo_g, hi_g):
            hit = sub.filter((pl.col("gpu_share") - g).abs() < 1e-9)[col].to_list()
            vals[g] = None if not hit or hit[0] is None else hit[0] / scale
        return _fmt(vals[lo_g], vals[hi_g], digits)

    labels = _short_labels(names)
    head = " & ".join(labels[n] for n in names)
    lines = [
        "% Generated by src/gel/accounting/restate.py from paper/tables/p7_restatement.csv;"
        " do not edit.",
        "\\begin{tabular}{ll" + "r" * len(names) + "}",
        "\\hline",
        f"Firm & FY & {head} \\\\",
        "\\hline",
        _panel(len(names), "Panel A: change in operating income, USD bn"),
    ]
    fy_of = dict(zip(last["firm"].to_list(), last["fy"].to_list(), strict=True))
    for f in firms:
        cells = " & ".join(cell(f, n, "delta_operating_income_usd", 1e9, 2) for n in names)
        lines.append(f"{f} & {fy_of[f]} & {cells} \\\\")
    lines.append(
        _panel(len(names), f"Panel B: change in diluted EPS, USD ({ex['tax_basis']} tax rate)")
    )
    for f in firms:
        cells = " & ".join(cell(f, n, "delta_eps", 1.0, 2) for n in names)
        lines.append(f"{f} & {fy_of[f]} & {cells} \\\\")
    lines += [
        "\\hline",
        f"\\multicolumn{{{2 + len(names)}}}{{p{{0.95\\linewidth}}}}{{\\footnotesize Each cell: "
        f"GPU share of server capex {lo_g:g} to {hi_g:g}; server/network share of capex "
        f"{float(cfg['server_share']['baseline']):g} (assumption); cohorts from FY"
        f"{int(cfg['gpu_cohort_start_fy'])}. Change = alternative schedule minus the firm's "
        "disclosed straight-line book life. n/a: effective tax rate undefined (pre-tax loss)."
        + "".join(
            f" {labels[n]}: \\texttt{{{n.replace('_', '\\_')}}} (Phase 6)."
            for n in names
            if not n.startswith("sl_")
        )
        + "} \\\\",
        "\\hline",
        "\\end{tabular}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _panel(n_schedules: int, title: str) -> str:
    return f"\\multicolumn{{{2 + n_schedules}}}{{l}}{{\\textit{{{title}}}}} \\\\"


def _schedule_key(name: str) -> tuple:
    if name.startswith("sl_") and name.endswith("y"):
        return (0, float(name[3:-1]))
    return (1, name)


def _schedule_label(name: str) -> str:
    if name.startswith("sl_") and name.endswith("y"):
        return f"SL {name[3:-1]}y"
    return name


def _short_labels(names: list[str]) -> dict[str, str]:
    """Straight-line schedules as 'SL 5y'; other (Phase 6) schedules as M1, M2, ... in order."""
    out, k = {}, 0
    for n in names:
        if n.startswith("sl_"):
            out[n] = _schedule_label(n)
        else:
            k += 1
            out[n] = f"M{k}"
    return out


def plot(df: pl.DataFrame, cfg: dict, path: Path) -> None:
    from gel.viz import style

    style.apply()
    import matplotlib.pyplot as plt

    ex = cfg["exhibit"]
    lo_g, hi_g = float(ex["gpu_share_low"]), float(ex["gpu_share_high"])
    base = _baseline(df, cfg).filter(pl.col("tax_basis") == ex["tax_basis"])
    firms = [f for f in cfg["firms"] if f in set(base["firm"].to_list())]
    names = sorted(base["schedule"].unique().to_list(), key=_schedule_key)
    market = [n for n in names if not n.startswith("sl_")]
    colored = market or names
    grey = [n for n in names if n not in colored]
    grey_styles = ["-", "--", "-.", ":", (0, (8, 2))]
    ncol = 4
    nrow = math.ceil(len(firms) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(10, 2.6 * nrow), squeeze=False)
    for ax, firm in zip(axes.flat, firms, strict=False):
        sub = base.filter(pl.col("firm") == firm)
        for name in names:
            s = sub.filter(pl.col("schedule") == name).sort("fiscal_year")
            lo = s.filter((pl.col("gpu_share") - lo_g).abs() < 1e-9)
            hi = s.filter((pl.col("gpu_share") - hi_g).abs() < 1e-9)
            x = lo["fiscal_year"].to_list()
            y_lo = (lo["delta_operating_income_usd"] / 1e9).to_list()
            y_hi = (hi["delta_operating_income_usd"] / 1e9).to_list()
            if name in colored:
                color = style.SLOTS[colored.index(name) % len(style.SLOTS)]
                ax.fill_between(x, y_lo, y_hi, color=color, alpha=0.18, linewidth=0)
                ax.plot(x, y_hi, color=color, label=_schedule_label(name))
            else:  # straight-line references in grey when Phase 6 schedules are shown
                ls = grey_styles[grey.index(name) % len(grey_styles)]
                ax.plot(x, y_hi, color=style.INK_2, linewidth=0.9, linestyle=ls,
                        label=_schedule_label(name))  # fmt: skip
        ax.axhline(0, color=style.INK_2, linewidth=0.8)
        ax.set_title(firm)
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True, nbins=4))
    for ax in list(axes.flat)[len(firms) :]:
        ax.axis("off")
    axes[0][0].set_ylabel("Change in operating income (USD bn)")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.98, 0.08), ncol=1, fontsize=8)
    fig.suptitle(
        f"Alternative schedule minus disclosed book life; line = GPU share {hi_g:g}, band to "
        f"{lo_g:g}; server share {float(cfg['server_share']['baseline']):g}",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    df = run()
    src = df["schedule_source"].unique().to_list()
    print(f"wrote {OUT_CSV} ({df.height} rows), {OUT_TEX}, {OUT_FACTS}, {OUT_FIG}")
    print(f"schedule sources: {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
