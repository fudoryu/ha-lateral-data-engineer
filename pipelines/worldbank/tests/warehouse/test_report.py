import re
from pathlib import Path
from typing import Any

import duckdb
import pytest
from typer.testing import CliRunner

from worldbank.cli import app
from worldbank.warehouse.report import NothingToReport, _short_names, render_report

GDP, POP, LIFE = "NY.GDP.MKTP.CD", "SP.POP.TOTL", "SP.DYN.LE00.IN"
NAMES = {GDP: "GDP (current US$)", POP: "Population, total", LIFE: "Life expectancy (years)"}

COLUMNS = {
    "rpt_completeness": "country_id VARCHAR, country_name VARCHAR, indicator_id VARCHAR, "
    "indicator_name VARCHAR, observation_year INTEGER, value_status VARCHAR, "
    "indicator_value DOUBLE, series_status VARCHAR",
    "rpt_year_over_year": "country_id VARCHAR, indicator_id VARCHAR, observation_year INTEGER, "
    "indicator_value DOUBLE, prior_indicator_value DOUBLE, absolute_change DOUBLE, "
    "percent_change DOUBLE, null_change_reason VARCHAR",
    "rpt_latest_year": "country_id VARCHAR, indicator_id VARCHAR, latest_year INTEGER, "
    "latest_value DOUBLE, latest_rank INTEGER, common_year INTEGER, common_value DOUBLE, "
    "common_rank INTEGER",
    "rpt_income_group_by_year": "income_group_id VARCHAR, income_group_name VARCHAR, "
    "indicator_id VARCHAR, observation_year INTEGER, aggregation VARCHAR, group_value DOUBLE, "
    "n_countries INTEGER, n_countries_with_data INTEGER",
}

Rows = dict[str, list[tuple[Any, ...]]]


def warehouse(path: Path, tables: Rows) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as con:
        con.execute("CREATE SCHEMA reporting")
        for table, columns in COLUMNS.items():
            con.execute(f"CREATE TABLE reporting.{table} ({columns})")
            rows = tables.get(table, [])
            if rows:
                marks = ", ".join("?" for _ in rows[0])
                con.executemany(f"INSERT INTO reporting.{table} VALUES ({marks})", rows)
    return path


def cell(
    country: str, name: str, indicator: str, year: int, status: str, value: Any, series: str
) -> tuple[Any, ...]:
    return (country, name, indicator, NAMES[indicator], year, status, value, series)


# Two countries, three indicators, two years: GDP has a null and a missing row; population is
# complete; life expectancy has only a null in 2024 and no 2023 cell at all.
WITH_GAPS: Rows = {
    "rpt_completeness": [
        cell("BRA", "Brazil", GDP, 2023, "present", 2.5e12, "incomplete"),
        cell("BRA", "Brazil", GDP, 2024, "null_value", None, "incomplete"),
        cell("IND", "<Côte & co>", GDP, 2023, "missing_row", None, "incomplete"),
        cell("IND", "<Côte & co>", GDP, 2024, "present", -5.0, "incomplete"),
        cell("BRA", "Brazil", POP, 2023, "present", 200.0, "complete"),
        cell("BRA", "Brazil", POP, 2024, "present", 225.0, "complete"),
        cell("IND", "<Côte & co>", POP, 2023, "present", 1.4e9, "complete"),
        cell("IND", "<Côte & co>", POP, 2024, "present", 1.4e9, "complete"),
        cell("BRA", "Brazil", LIFE, 2024, "null_value", None, "missing"),
    ],
    "rpt_year_over_year": [
        ("BRA", GDP, 2023, 2.5e12, None, None, None, "a_new_reason"),
        ("BRA", GDP, 2024, None, 2.5e12, None, None, "current_missing"),
        ("IND", GDP, 2024, -5.0, None, None, None, "prior_missing"),
        ("BRA", POP, 2023, 200.0, 0.0, 200.0, None, "prior_zero"),
        ("BRA", POP, 2024, 225.0, 200.0, 25.0, 12.5, None),
        ("IND", POP, 2023, 1.4e9, 1.4e9, 0.0, 0.0, None),
        ("IND", POP, 2024, 1.4e9, 1.45e9, -5e7, -3.25, None),
    ],
    "rpt_latest_year": [
        ("BRA", GDP, 2023, 2.5e12, 1, 2023, 2.5e12, 1),
        ("IND", GDP, 2024, -5.0, 2, 2023, None, None),
        ("BRA", POP, 2024, 225.0, 2, 2024, 225.0, 2),
        ("IND", POP, 2024, 1.4e9, 1, 2024, 1.4e9, 1),
        ("BRA", LIFE, None, None, None, None, None, None),
    ],
    "rpt_income_group_by_year": [
        ("HIC", "High income", GDP, 2023, "total", 4e12, 2, 2),
        ("HIC", "High income", GDP, 2024, "total", 4.5e12, 2, 1),
        ("LMC", "Lower middle income", GDP, 2023, "total", 1e9, 1, 1),
        ("HIC", "High income", POP, 2023, "sum", 100.0, 2, 2),
        ("XYZ", "Other income", POP, 2023, "sum", 101.0, 1, 1),
        ("XYZ", "Other income", POP, 2024, "sum", None, 1, 0),
        ("LIC", "Low income", POP, 2023, "sum", None, 1, 0),
        ("LMC", "Lower middle income", POP, 2023, "sum", 0.0, 1, 1),
        ("HIC", "High income", LIFE, 2024, "population-weighted mean", None, 2, 0),
    ],
}


@pytest.fixture
def page(tmp_path: Path) -> str:
    source = warehouse(tmp_path / "wh.duckdb", WITH_GAPS)
    output = render_report(source, tmp_path / "reports" / "report.html")
    assert not (tmp_path / "reports" / "report.html.tmp").exists()
    return output.read_text(encoding="utf-8")


def board(page: str, k: int) -> str:
    return page.split(f'data-ind="{k}"', 2)[2].split('<section class="', 1)[0]


def test_the_header_reports_the_gaps_and_the_filters_list_everything(page: str) -> None:
    assert "6 of 9 expected values present: 2 returned as null, 1 not returned" in page
    assert '<p class="status warn">' in page
    assert "2 countries and\n3 indicators, 2023 to 2024" in page
    tabs = re.findall(r'name="indicator" id="ind-(\d)"( checked)?><span>([^<]+)', page)
    assert tabs == [("0", " checked", "GDP"), ("1", "", "Life expectancy"), ("2", "", "Population")]
    assert page.count('type="checkbox" id="cty-') == 2


def test_filters_are_css_rules_and_the_script_holds_no_data(page: str) -> None:
    css = page.split("@supports selector(:has(*))", 1)[1]
    assert 'body:has(#ind-2:checked) .board[data-ind="2"] { display: block; }' in css
    assert 'body:has(#cty-1:not(:checked)) [data-cty="1"] { display: none; }' in css
    assert '.hoverable:has(.band[data-y="1"]:hover) .ro[data-y="1"]' in css
    script = page.split("<script>", 1)[1].split("</script>", 1)[0]
    assert "Côte" not in script and "Brazil" not in script


def test_every_value_is_escaped(page: str) -> None:
    assert "&lt;Côte &amp; co&gt;" in page and "<Côte" not in page


def test_gaps_show_as_squares_line_breaks_and_reasons(page: str) -> None:
    assert 'class="sq-null"' in page and 'class="sq-missing"' in page
    assert (
        "Brazil, GDP (current US$): incomplete, 1 of 2 years (1 returned as null, 0 not returned)"
    ) in page
    assert "<small>1 null, 0 not returned</small>" in page
    for reason in ("a_new_reason", "no value", "no prior value", "prior was 0", "no change"):
        assert reason in page
    assert "2024, returned as null" in page
    assert "2023, not expected" in page  # life expectancy has no 2023 cell


def test_changes_are_signed_and_shaded(page: str) -> None:
    assert '<td class="u4" title="2024: 225.0, from 200.0 (+25.0)">+12.5%</td>' in page
    assert ">&minus;3.2%</td>" in page and 'class="d2"' in page
    assert '<td class="z" title="2023: 1.4 B, from 1.4 B (0.0)">0.0%</td>' in page
    assert "+12.5% on 2023" in page


def test_rankings_say_whether_the_comparison_is_like_for_like(page: str) -> None:
    assert "Latest years differ by country." in board(page, 0)
    assert "Compare every country in 2023, the latest year they all have" in page
    assert "Every country's latest year is 2024" in board(page, 2)
    assert "No year has a value for every country" in board(page, 1)
    assert 'class="bar neg"' in page and "2.5 T" in page
    assert '<span class="val muted">no value</span>' in page


def test_income_groups_are_ordered_labelled_and_charted(page: str) -> None:
    assert "Income-group value: total." in board(page, 0)
    assert "Income-group value: population-weighted mean." in board(page, 1)
    assert page.count('<svg viewBox="0 0 600 250"') == 2  # life expectancy has no value
    assert "No income group has a value for this indicator." in board(page, 1)
    assert 'class="end-label"' in board(page, 0)
    assert 'class="end-label"' not in board(page, 2)  # on a 0-120 axis, 100 and 101 collide
    legend = board(page, 2).split('class="ig-legend"', 1)[1]
    names = ("Low income", "Lower middle income", "High income", "Other income")
    order = [legend.index(name) for name in names]
    assert order == sorted(order)
    assert "1 of 1 country" in page and "2 of 2 countries" in page


def test_rendering_is_deterministic(tmp_path: Path) -> None:
    source = warehouse(tmp_path / "wh.duckdb", WITH_GAPS)
    first = render_report(source, tmp_path / "a.html").read_bytes()
    assert render_report(source, tmp_path / "b.html").read_bytes() == first


def test_a_complete_dataset_says_so(tmp_path: Path) -> None:
    source = warehouse(
        tmp_path / "wh.duckdb",
        {
            "rpt_completeness": [cell("BRA", "Brazil", GDP, 2024, "present", 10.0, "complete")],
            "rpt_latest_year": [("BRA", GDP, 2024, 10.0, 1, 2024, 10.0, 1)],
        },
    )

    page = render_report(source, tmp_path / "report.html").read_text(encoding="utf-8")

    assert "All 1 expected values are present" in page and '<p class="status ok">' in page
    assert "Nothing is missing: every series has a value for every year." in page
    assert "1 country and" in page and "No income-group value." in page


def test_ambiguous_short_names_fall_back_to_the_full_names() -> None:
    names = [("A", "GDP (current US$)"), ("B", "GDP (constant US$)")]
    assert _short_names(names) == dict(names)
    assert _short_names([("C", "Population, total")]) == {"C": "Population"}


def test_nothing_to_report_without_a_published_warehouse(tmp_path: Path) -> None:
    with pytest.raises(NothingToReport, match="publish a build first"):
        render_report(tmp_path / "missing.duckdb", tmp_path / "report.html")


def test_nothing_to_report_without_the_reporting_tables(tmp_path: Path) -> None:
    empty = tmp_path / "wh.duckdb"
    duckdb.connect(str(empty)).close()

    with pytest.raises(NothingToReport, match="lacks a reporting table"):
        render_report(empty, tmp_path / "report.html")


def test_nothing_to_report_without_expected_values(tmp_path: Path) -> None:
    source = warehouse(tmp_path / "wh.duckdb", {})

    with pytest.raises(NothingToReport, match="no expected values"):
        render_report(source, tmp_path / "report.html")


def test_cli_report_writes_to_reports_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    missing = CliRunner().invoke(app, ["report", "--data-dir", "data"])
    warehouse(tmp_path / "data" / "warehouse" / "worldbank.duckdb", WITH_GAPS)
    written = CliRunner().invoke(app, ["report", "--data-dir", "data"])

    assert missing.exit_code == 1
    assert "report failed" in missing.stderr
    assert written.exit_code == 0, written.output
    assert (tmp_path / "reports" / "report.html").is_file()
