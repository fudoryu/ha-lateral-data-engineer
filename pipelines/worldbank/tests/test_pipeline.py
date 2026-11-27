"""End to end, offline: extract → load → dbt build → publish → export → report, as `just run`
chains them after its extract.

The chain is ADR-0022's. Extract runs against the recorded API responses (ADR-0012), crafted
variants of them, or a fake API that answers any scope; dbt runs as its own process, the way the
task runner calls it, with its target and log folders inside the test's temp directory. Every
test reads the exported reports, as a reviewer would.
"""

import csv
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import responses
from fake_api import GDP, LIFE_EXPECTANCY, POP, fake_world_bank
from scenarios import RecordedApi
from typer.testing import CliRunner

from worldbank.cli import app
from worldbank.config import Config
from worldbank.source.client import Client
from worldbank.source.extract import extract

DBT_PROJECT = Path(__file__).parents[1] / "dbt"
DBT = Path(sys.executable).parent / "dbt"
T0 = datetime(2026, 11, 24, tzinfo=UTC)
REPORTS = {
    "rpt_completeness_by_cell",
    "rpt_completeness_by_series",
    "rpt_year_over_year",
    "rpt_latest_year_by_country",
    "rpt_latest_common_year",
    "rpt_income_group_by_year",
}

Report = list[dict[str, str]]


def land(config: Config, data_dir: Path, at: datetime = T0) -> None:
    client = Client(config.api, sleep=lambda _: None)
    extract(config, client, data_dir / "raw" / "worldbank", now=lambda: at)


def build_publish_export(data_dir: Path) -> dict[str, Report]:
    """Run load, dbt build, publish and export on `data_dir`; return each exported report."""
    loaded = CliRunner().invoke(app, ["load", "--data-dir", str(data_dir)])
    assert loaded.exit_code == 0, loaded.output

    built = subprocess.run(
        [
            str(DBT),
            "build",
            *("--project-dir", str(DBT_PROJECT), "--profiles-dir", str(DBT_PROJECT)),
            *(
                "--target-path",
                str(data_dir / "dbt-target"),
                "--log-path",
                str(data_dir / "dbt-logs"),
            ),
        ],
        env={
            **os.environ,
            "WORLDBANK_WAREHOUSE": str(data_dir / "warehouse" / "worldbank.next.duckdb"),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert built.returncode == 0, built.stdout[-3000:]

    for command in ("publish", "export"):
        result = CliRunner().invoke(app, [command, "--data-dir", str(data_dir)])
        assert result.exit_code == 0, result.output
    report = data_dir / "reports" / "report.html"
    rendered = CliRunner().invoke(
        app, ["report", "--data-dir", str(data_dir), "--output", str(report)]
    )
    assert rendered.exit_code == 0, rendered.output
    assert "Indicators across income groups, by year" in report.read_text(encoding="utf-8")

    reports = {}
    for path in (data_dir / "outputs").glob("rpt_*.csv"):
        with path.open(newline="", encoding="utf-8") as file:
            reports[path.stem] = list(csv.DictReader(file))
    return reports


def one(report: Report, **match: Any) -> dict[str, str]:
    [row] = [r for r in report if all(r[key] == str(value) for key, value in match.items())]
    return row


def test_recorded_runs_build_and_publish(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    land(recorded_config, tmp_path)

    reports = build_publish_export(tmp_path)

    scope = recorded_config.scope
    expected = len(scope.countries) * len(scope.indicators) * len(scope.years.as_range())
    with duckdb.connect(str(tmp_path / "warehouse" / "worldbank.duckdb"), read_only=True) as con:
        counts = con.execute(
            "SELECT"
            " (SELECT count(*) FROM staging.stg_worldbank__expected_cells),"
            " (SELECT count(*) FROM staging.stg_worldbank__observations),"
            " (SELECT count(*) FROM staging.stg_worldbank__countries)"
        ).fetchone()
    assert counts == (expected, expected, len(scope.countries))
    assert not (tmp_path / "warehouse" / "worldbank.next.duckdb").exists()
    assert set(reports) == REPORTS
    assert len(reports["rpt_completeness_by_cell"]) == expected


def test_rerunning_with_unchanged_data_gives_identical_reports(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    """NFR-2: a re-run with unchanged source data creates no duplicate analytical records."""
    once, twice = tmp_path / "once", tmp_path / "twice"
    land(recorded_config, once)
    land(recorded_config, twice)
    land(recorded_config, twice, at=T0 + timedelta(hours=1))  # the same data, fetched again

    build_publish_export(once)
    build_publish_export(twice)

    for report in REPORTS:
        assert (twice / "outputs" / f"{report}.csv").read_bytes() == (
            once / "outputs" / f"{report}.csv"
        ).read_bytes(), report


def test_nulls_gaps_zeros_and_revisions_reach_the_reports(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    """Cases live data doesn't show (source-system §6), crafted on the recorded responses."""
    with api.serve():
        land(recorded_config, tmp_path)  # the original release
    api.with_value(POP, "BRA", 2020, None)  # a row with a null value
    api.without_row(GDP, "IND", 2019)  # no row at all
    api.with_value(LIFE_EXPECTANCY, "ZAF", 2021, 0)  # a zero prior value for 2022
    api.with_value(LIFE_EXPECTANCY, "USA", 2022, 79.5)  # a silent revision
    with api.serve():
        land(recorded_config, tmp_path, at=T0 + timedelta(days=1))  # the revised release

    reports = build_publish_export(tmp_path)

    cells, series = reports["rpt_completeness_by_cell"], reports["rpt_completeness_by_series"]
    changes, groups = reports["rpt_year_over_year"], reports["rpt_income_group_by_year"]
    assert one(cells, country_id="BRA", indicator_id=POP, observation_year=2020)[
        "value_status"
    ] == ("null_value")
    assert one(cells, country_id="IND", indicator_id=GDP, observation_year=2019)[
        "value_status"
    ] == ("missing_row")
    assert one(series, country_id="BRA", indicator_id=POP)["series_status"] == "incomplete"
    reasons = {
        (country, indicator, year): one(
            changes, country_id=country, indicator_id=indicator, observation_year=year
        )["null_change_reason"]
        for country, indicator, year in [
            ("BRA", POP, 2020),
            ("BRA", POP, 2021),
            ("ZAF", LIFE_EXPECTANCY, 2022),
            ("BRA", POP, 2018),
        ]
    }
    assert reasons == {
        ("BRA", POP, 2020): "current_missing",
        ("BRA", POP, 2021): "prior_missing",
        ("ZAF", LIFE_EXPECTANCY, 2022): "prior_zero",
        ("BRA", POP, 2018): "prior_out_of_scope",
    }
    india_gdp_2019 = one(groups, income_group_id="LMC", indicator_id=GDP, observation_year=2019)
    assert (india_gdp_2019["group_value"], india_gdp_2019["n_countries_with_data"]) == ("", "0")
    revised = one(cells, country_id="USA", indicator_id=LIFE_EXPECTANCY, observation_year=2022)
    assert float(revised["indicator_value"]) == 79.5  # the latest release wins (ADR-0006)


def test_adding_a_country_and_an_indicator_is_configuration_only(
    recorded_config: Config, tmp_path: Path
) -> None:
    """NFR-4: a later run with a wider scope in configuration extends every report."""
    base_url = str(recorded_config.api.base_url).rstrip("/")
    narrow = recorded_config.model_copy(
        update={
            "scope": recorded_config.scope.model_copy(
                update={"countries": ["BRA", "IND"], "indicators": [POP, GDP]}
            )
        }
    )
    wider = narrow.model_copy(
        update={
            "scope": narrow.scope.model_copy(
                update={
                    "countries": ["BRA", "IND", "ZAF"],
                    "indicators": [POP, GDP, LIFE_EXPECTANCY],
                }
            )
        }
    )
    with fake_world_bank(base_url):
        land(narrow, tmp_path)
        land(wider, tmp_path, at=T0 + timedelta(days=1))

    reports = build_publish_export(tmp_path)

    years = len(wider.scope.years.as_range())
    cells = reports["rpt_completeness_by_cell"]
    assert len(cells) == 3 * 3 * years
    assert {row["country_id"] for row in cells} == {"BRA", "IND", "ZAF"}
    assert {row["indicator_id"] for row in reports["rpt_latest_year_by_country"]} == {
        POP,
        GDP,
        LIFE_EXPECTANCY,
    }
    life_by_group = [
        r for r in reports["rpt_income_group_by_year"] if r["indicator_id"] == LIFE_EXPECTANCY
    ]
    assert life_by_group and all(
        r["aggregation"] == "population-weighted mean" and r["group_value"] for r in life_by_group
    )
