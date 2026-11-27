"""End to end, offline: extract → load → dbt build → publish → export, as `just build` and
`just export` chain them.

The chain is ADR-0022's. Extract runs against the recorded API responses (ADR-0012), and dbt runs
as its own process, the way the task runner calls it, with its target and log folders inside the
test's temp directory.
"""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import responses
from typer.testing import CliRunner

from worldbank.cli import app
from worldbank.config import Config
from worldbank.source.client import Client
from worldbank.source.extract import extract

DBT_PROJECT = Path(__file__).parents[1] / "dbt"
DBT = Path(sys.executable).parent / "dbt"


def dbt_build(warehouse: Path, work: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(DBT),
            "build",
            *("--project-dir", str(DBT_PROJECT), "--profiles-dir", str(DBT_PROJECT)),
            *("--target-path", str(work / "target"), "--log-path", str(work / "logs")),
        ],
        env={**os.environ, "WORLDBANK_WAREHOUSE": str(warehouse)},
        capture_output=True,
        text=True,
        check=False,
    )


def test_recorded_runs_build_and_publish(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    client = Client(recorded_config.api, sleep=lambda _: None)
    extract(
        recorded_config,
        client,
        tmp_path / "raw" / "worldbank",
        now=lambda: datetime(2026, 11, 24, tzinfo=UTC),
    )
    warehouse = tmp_path / "warehouse"

    loaded = CliRunner().invoke(app, ["load", "--data-dir", str(tmp_path)])
    assert loaded.exit_code == 0, loaded.output

    built = dbt_build(warehouse / "worldbank.next.duckdb", tmp_path / "dbt")
    assert built.returncode == 0, built.stdout[-3000:]

    published = CliRunner().invoke(app, ["publish", "--data-dir", str(tmp_path)])
    assert published.exit_code == 0, published.output

    scope = recorded_config.scope
    expected = len(scope.countries) * len(scope.indicators) * len(scope.years.as_range())
    with duckdb.connect(str(warehouse / "worldbank.duckdb"), read_only=True) as con:
        counts = con.execute(
            "select"
            " (select count(*) from staging.stg_worldbank__expected_cells),"
            " (select count(*) from staging.stg_worldbank__observations),"
            " (select count(*) from staging.stg_worldbank__countries)"
        ).fetchone()
    assert counts == (expected, expected, len(scope.countries))
    assert not (warehouse / "worldbank.next.duckdb").exists()

    exported = CliRunner().invoke(app, ["export", "--data-dir", str(tmp_path)])
    assert exported.exit_code == 0, exported.output
    reports = {path.stem: path for path in (tmp_path / "outputs").glob("rpt_*.csv")}
    assert set(reports) == {
        "rpt_completeness_by_cell",
        "rpt_completeness_by_series",
        "rpt_year_over_year",
        "rpt_latest_year_by_country",
        "rpt_latest_common_year",
        "rpt_income_group_by_year",
    }
    lines = reports["rpt_completeness_by_cell"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == expected + 1  # header + one row per expected cell
