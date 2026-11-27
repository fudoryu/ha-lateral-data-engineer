from pathlib import Path
from typing import Any

import duckdb
import pytest
from typer.testing import CliRunner

from worldbank.cli import app
from worldbank.warehouse.report import NothingToReport, render_report

COLUMNS = {
    "rpt_completeness_by_cell": "country_id VARCHAR, indicator_id VARCHAR, "
    "observation_year INTEGER, value_status VARCHAR",
    "rpt_completeness_by_series": "country_name VARCHAR, indicator_name VARCHAR, "
    "series_status VARCHAR, n_present INTEGER, n_expected INTEGER, n_null_value INTEGER, "
    "n_missing_row INTEGER",
    "rpt_year_over_year": "indicator_name VARCHAR, country_name VARCHAR, observation_year INTEGER, "
    "percent_change DOUBLE, null_change_reason VARCHAR",
    "rpt_latest_year_by_country": "indicator_name VARCHAR, country_name VARCHAR, "
    "rank_in_indicator INTEGER, indicator_value DOUBLE, latest_year INTEGER",
    "rpt_latest_common_year": "indicator_name VARCHAR, country_name VARCHAR, "
    "rank_in_indicator INTEGER, indicator_value DOUBLE, common_year INTEGER",
    "rpt_income_group_by_year": "indicator_name VARCHAR, income_group_name VARCHAR, "
    "income_group_sort_order INTEGER, observation_year INTEGER, average_value DOUBLE, "
    "n_countries INTEGER, n_countries_with_data INTEGER",
}


def warehouse(path: Path, tables: dict[str, list[tuple[Any, ...]]]) -> Path:
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


WITH_GAPS: dict[str, list[tuple[Any, ...]]] = {
    "rpt_completeness_by_cell": [
        ("BRA", "GDP", 2023, "present"),
        ("BRA", "GDP", 2024, "null_value"),
        ("IND", "GDP", 2024, "missing_row"),
    ],
    "rpt_completeness_by_series": [
        ("Brazil", "GDP", "incomplete", 1, 2, 1, 0),
        ("<Côte & co>", "GDP", "missing", 0, 2, 1, 1),
    ],
    "rpt_year_over_year": [
        ("GDP", "Brazil", 2021, None, "prior_out_of_scope"),
        ("GDP", "Brazil", 2022, 12.5, None),
        ("GDP", "Brazil", 2023, -3.25, None),
        ("GDP", "Brazil", 2024, 0.0, None),
        ("GDP", "<Côte & co>", 2021, None, "prior_zero"),
        ("GDP", "<Côte & co>", 2022, None, "current_missing"),
        ("GDP", "<Côte & co>", 2023, None, "prior_missing"),
        ("GDP", "<Côte & co>", 2024, None, "a_new_reason"),
    ],
    "rpt_latest_year_by_country": [
        ("GDP", "Brazil", 1, 2.5e12, 2023),
        ("GDP", "<Côte & co>", None, None, None),
    ],
    "rpt_latest_common_year": [
        ("GDP", "Brazil", None, None, None),
        ("GDP", "<Côte & co>", None, None, None),
    ],
    "rpt_income_group_by_year": [
        ("Population", "High income", 4, 2023, 3.2e9, 5, 5),
        ("Population", "High income", 4, 2024, 4.5e6, 5, 4),
        ("Population", "Low income", 1, 2023, 12.25, 2, 2),
        ("Population", "Low income", 1, 2024, None, 2, 0),
        ("Life expectancy", "High income", 4, 2024, 80.0, 5, 5),
        ("No data", "High income", 4, 2024, None, 5, 0),
    ],
}


def test_the_report_shows_gaps_reasons_and_charts(tmp_path: Path) -> None:
    source = warehouse(tmp_path / "wh.duckdb", WITH_GAPS)

    page = render_report(source, tmp_path / "reports" / "report.html").read_text(encoding="utf-8")

    assert "<b>1</b> present, <b>1</b> returned as null,\n<b>1</b> not returned" in page
    assert "Brazil, GDP: incomplete (1 of 2 years; 1 null, 0 missing)" in page
    assert "&lt;Côte &amp; co&gt;" in page and "<Côte" not in page  # escaped
    for shown in ("first year", "prior was 0", "no value", "no prior value", "a_new_reason"):
        assert shown in page
    assert '<td class="num up">+12.5%</td>' in page
    assert '<td class="num down">-3.2%</td>' in page
    assert '<td class="num ">+0.0%</td>' in page
    assert "2.5 T" in page and "3.2 B" in page and "4.5 M" in page and "12.2" in page
    assert "no year common to all" in page
    assert page.count("<svg") == 2  # Population and Life expectancy; "No data" has none
    assert "No group has data for this indicator." in page
    assert not (tmp_path / "reports" / "report.html.tmp").exists()


def test_a_complete_dataset_says_so_and_compares_on_the_common_year(tmp_path: Path) -> None:
    source = warehouse(
        tmp_path / "wh.duckdb",
        {
            "rpt_completeness_by_cell": [("BRA", "GDP", 2024, "present")],
            "rpt_completeness_by_series": [("Brazil", "GDP", "complete", 1, 1, 0, 0)],
            "rpt_year_over_year": [("GDP", "Brazil", 2024, None, "prior_out_of_scope")],
            "rpt_latest_year_by_country": [("GDP", "Brazil", 1, 10.0, 2024)],
            "rpt_latest_common_year": [("GDP", "Brazil", 1, 10.0, 2024)],
            "rpt_income_group_by_year": [("GDP", "High income", 4, 2024, 10.0, 1, 1)],
        },
    )

    page = render_report(source, tmp_path / "report.html").read_text(encoding="utf-8")

    assert "All 1 series are complete" in page
    assert "value in 2024" in page


def test_nothing_to_report_without_a_published_warehouse(tmp_path: Path) -> None:
    with pytest.raises(NothingToReport, match="publish a build first"):
        render_report(tmp_path / "missing.duckdb", tmp_path / "report.html")


def test_nothing_to_report_without_the_reporting_tables(tmp_path: Path) -> None:
    empty = tmp_path / "wh.duckdb"
    duckdb.connect(str(empty)).close()

    with pytest.raises(NothingToReport, match="lacks a reporting table"):
        render_report(empty, tmp_path / "report.html")


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
