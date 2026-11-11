"""Phase 7 restatement arithmetic, checked by hand."""

import polars as pl
import pytest

from gel.accounting import restate as r


def approx(d: dict, expected: dict) -> None:
    assert d.keys() == expected.keys()
    for k, v in expected.items():
        assert d[k] == pytest.approx(v), k


# ------------------------------------------------------------------ schedules


def test_straight_line_fractional_life():
    assert r.straight_line(4) == [0.25] * 4
    shares = r.straight_line(5.5)
    assert shares == pytest.approx([1 / 5.5] * 5 + [0.5 / 5.5])
    assert sum(shares) == pytest.approx(1.0)


def test_reference_schedule_names_and_columns():
    df = r.reference_schedules([3, 5.5])
    assert df.columns == ["schedule", "year", "dep_share"]
    assert df["schedule"].unique().sort().to_list() == ["sl_3y", "sl_5.5y"]


@pytest.mark.parametrize(
    "rows, msg",
    [
        ([("a", 1, 0.6), ("a", 2, 0.6)], "sums to"),
        ([("a", 1, 0.5), ("a", 3, 0.5)], "without gaps"),
        ([("a", 1, -0.1)], "negative"),
    ],
)
def test_validate_schedules_rejects_bad_input(rows, msg):
    df = pl.DataFrame(rows, schema=["schedule", "year", "dep_share"], orient="row")
    with pytest.raises(ValueError, match=msg):
        r.validate_schedules(df)


def test_validate_schedules_allows_residual_value():
    df = pl.DataFrame([("a", 1, 0.5), ("a", 2, 0.3)], schema=["schedule", "year", "dep_share"],
                      orient="row")  # fmt: skip
    assert r.validate_schedules(df) == {"a": [0.5, 0.3]}


def test_load_schedules_picks_up_p6_when_present(tmp_path):
    cfg = {
        "schedules": {
            "market_implied_path": "p6.csv",
            "reference_path": "out/ref.csv",
            "straight_line_years": [4],
        }
    }
    sched, src = r.load_schedules(cfg, tmp_path)
    assert set(sched) == {"sl_4y"} and (tmp_path / "out/ref.csv").exists()
    (tmp_path / "p6.csv").write_text("schedule,year,dep_share\nmkt,1,0.7\nmkt,2,0.3\n")
    sched, src = r.load_schedules(cfg, tmp_path)
    assert sched["mkt"] == [0.7, 0.3] and src["mkt"] == "market_implied_p6"
    assert src["sl_4y"] == "straight_line_reference"


# ------------------------------------------------------------------ book depreciation


def test_single_cohort_straight_line():
    dep = r.book_depreciation(100.0, 2020, {2015: 4}, 2025)
    approx(dep, {2020: 25, 2021: 25, 2022: 25, 2023: 25, 2024: 0, 2025: 0})


def test_fractional_life_ends_with_half_year():
    dep = r.book_depreciation(110.0, 2020, {2015: 5.5}, 2026)
    approx(dep, {2020: 20, 2021: 20, 2022: 20, 2023: 20, 2024: 20, 2025: 10, 2026: 0})


def test_life_extension_applied_prospectively():
    # Bought 2020 on a 4-year life; life becomes 6 years from 2022 (age 2, NBV 50).
    # Remaining NBV 50 over the remaining 6 - 2 = 4 years: 12.5 a year.
    dep = r.book_depreciation(100.0, 2020, {2015: 4, 2022: 6}, 2026)
    approx(dep, {2020: 25, 2021: 25, 2022: 12.5, 2023: 12.5, 2024: 12.5, 2025: 12.5, 2026: 0})
    # A cohort bought after the change depreciates over 6 years from the start.
    dep = r.book_depreciation(60.0, 2023, {2015: 4, 2022: 6}, 2023)
    approx(dep, {2023: 10})


def test_life_shortening_charges_remaining_nbv():
    # Bought 2020 on 6 years; life cut to 5 from 2024 (age 4, NBV 100/3).
    # Remaining 5 - 4 = 1 year, so the whole NBV is charged in 2024.
    dep = r.book_depreciation(100.0, 2020, {2015: 6, 2024: 5}, 2025)
    approx(dep, {2020: 100 / 6, 2021: 100 / 6, 2022: 100 / 6, 2023: 100 / 6, 2024: 100 / 3,
                 2025: 0})  # fmt: skip
    # Cut to 3 from 2024 (age 4 > new life): NBV still charged in 2024.
    dep = r.book_depreciation(100.0, 2020, {2015: 6, 2024: 3}, 2024)
    assert dep[2024] == pytest.approx(100 / 3)
    assert sum(dep.values()) == pytest.approx(100.0)


def test_schedule_depreciation_and_fleet_sum():
    dep = r.schedule_depreciation(100.0, 2020, [0.5, 0.3, 0.2], 2023)
    approx(dep, {2020: 50, 2021: 30, 2022: 20, 2023: 0})
    fleet = r.fleet_depreciation(
        {2020: 100.0, 2021: 200.0},
        lambda k, c: r.schedule_depreciation(k, c, [0.5, 0.5], 2022),
        2022,
    )
    approx(fleet, {2020: 50, 2021: 150, 2022: 100})


# ------------------------------------------------------------------ firm-year restatement


def fact(v, accn="a"):
    return {"value": v, "accn": accn}


CFG = {
    "report_from_fy": 2020,
    "server_share": {"grid": [0.5], "baseline": 0.5},
    "gpu_share": {"grid": [0.4]},
    "tax": {"statutory_rate": 0.21},
    "per_share_basis": "latest",
}


def test_restate_firm_by_hand():
    # One cohort: capex 1,000 in 2020; GPU base = 1000 x 0.5 x 0.4 = 200.
    # Book life 4 years -> 50 a year. Alternative: 3-year straight line -> 66.67 a year.
    ff = {
        2020: {
            "capex": fact(1000.0, "c20"),
            "operating_income": fact(500.0),
            "pretax_income": fact(400.0),
            "income_tax": fact(100.0),  # effective rate 25%
            "eps_diluted": fact(2.0),
            "shares_diluted": fact(150.0),
            "depreciation": fact(80.0),
        },
        2021: {
            "capex": fact(0.0),
            "operating_income": fact(600.0),
            "pretax_income": fact(-10.0),  # loss: effective rate undefined
            "income_tax": fact(1.0),
            "eps_diluted": fact(3.0),
            "net_income": fact(300.0),  # no shares fact: derived as 300 / 3 = 100
        },
    }
    rows = r.restate_firm(
        "X", ff, {2015: 4.0}, {"sl_3y": r.straight_line(3)}, CFG,
        cohort_start=2020, book_variant="disclosed", schedule_source={"sl_3y": "ref"},
    )  # fmt: skip
    got = {(x["fiscal_year"], x["tax_basis"]): x for x in rows}
    e20 = got[(2020, "effective")]
    assert e20["gpu_capex_usd"] == pytest.approx(200)
    assert e20["dep_book_gpu_usd"] == pytest.approx(50)
    assert e20["dep_alt_gpu_usd"] == pytest.approx(200 / 3)
    delta = 200 / 3 - 50
    assert e20["delta_dep_usd"] == pytest.approx(delta)
    assert e20["delta_operating_income_usd"] == pytest.approx(-delta)
    assert e20["operating_income_restated_usd"] == pytest.approx(500 - delta)
    assert e20["tax_rate"] == pytest.approx(0.25)
    assert e20["delta_eps"] == pytest.approx(-delta * 0.75 / 150)
    assert e20["eps_restated"] == pytest.approx(2.0 - delta * 0.75 / 150)
    assert e20["delta_dep_pct_of_reported"] == pytest.approx(100 * delta / 80)
    assert e20["capex_accn"] == "c20"
    s20 = got[(2020, "statutory_21")]
    assert s20["delta_eps"] == pytest.approx(-delta * 0.79 / 150)
    e21 = got[(2021, "effective")]
    assert e21["tax_rate"] is None and e21["delta_eps"] is None
    s21 = got[(2021, "statutory_21")]
    assert s21["shares_source"] == "net_income/eps_diluted"
    assert s21["delta_eps"] == pytest.approx(-delta * 0.79 / 100)


def test_restate_firm_cohort_start_excludes_earlier_capex():
    ff = {
        2020: {"capex": fact(1000.0), "operating_income": fact(1.0)},
        2021: {"capex": fact(500.0), "operating_income": fact(1.0)},
    }
    rows = r.restate_firm(
        "X", ff, {2015: 2.0}, {"sl_1y": [1.0]}, CFG,
        cohort_start=2021, book_variant="disclosed", schedule_source={"sl_1y": "ref"},
    )  # fmt: skip
    got = {(x["fiscal_year"], x["tax_basis"]): x for x in rows}
    # Only the 2021 cohort counts: base 500 x 0.2 = 100; book 50 vs alternative 100.
    assert got[(2020, "statutory_21")]["delta_dep_usd"] == pytest.approx(0)
    assert got[(2021, "statutory_21")]["delta_dep_usd"] == pytest.approx(50)


def test_pretax_derived_from_net_income_plus_tax():
    ff = {2020: {"capex": fact(10.0), "operating_income": fact(5.0), "net_income": fact(80.0),
                 "income_tax": fact(20.0), "eps_diluted": fact(1.0)}}  # fmt: skip
    rows = r.restate_firm(
        "X", ff, {2015: 1.0}, {"sl_1y": [1.0]}, CFG,
        cohort_start=2020, book_variant="disclosed", schedule_source={"sl_1y": "ref"},
    )  # fmt: skip
    eff = next(x for x in rows if x["tax_basis"] == "effective")
    assert eff["pretax_source"] == "net_income+income_tax"
    assert eff["tax_rate"] == pytest.approx(0.2)
