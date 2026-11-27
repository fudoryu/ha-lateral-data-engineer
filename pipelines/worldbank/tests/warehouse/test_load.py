from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pytest
import responses
from typer.testing import CliRunner

from worldbank.cli import app
from worldbank.config import Config
from worldbank.source.client import Client
from worldbank.source.extract import extract
from worldbank.storage.manifest import Manifest
from worldbank.storage.read import IntegrityError
from worldbank.storage.write import RunWriter
from worldbank.warehouse.load import LoadFailed, UnknownRun, as_of_path, load_raw, next_path


def extract_recorded(config: Config, root: Path, at: datetime) -> Manifest:
    return extract(config, Client(config.api, sleep=lambda _: None), root, now=lambda: at)


def scalar(warehouse: Path, sql: str) -> object:
    with duckdb.connect(str(warehouse), read_only=True) as con:
        row = con.execute(sql).fetchone()
    assert row is not None
    return row[0]


def test_loads_one_row_per_run_request_and_page(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    manifest = extract_recorded(
        recorded_config, tmp_path / "raw", datetime(2026, 11, 24, tzinfo=UTC)
    )

    summary = load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")

    assert (summary.runs, summary.responses) == (1, len(manifest.files))
    wh = tmp_path / "wh.duckdb"
    assert scalar(wh, "select count(*) from raw.landing_runs") == 1
    assert scalar(wh, "select count(*) from raw.api_requests") == len(manifest.requests)
    assert scalar(wh, "select count(*) from raw.api_responses") == len(manifest.files)


def test_payload_is_the_exact_response_and_queryable_as_json(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    extract_recorded(recorded_config, tmp_path / "raw", datetime(2026, 11, 24, tzinfo=UTC))
    load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")

    total = scalar(
        tmp_path / "wh.duckdb",
        "select sum(json_array_length(payload -> 1)) from raw.api_responses"
        " where endpoint = 'observations'",
    )
    rows_per_indicator = len(recorded_config.scope.countries) * len(
        recorded_config.scope.years.as_range()
    )
    assert total == rows_per_indicator * len(recorded_config.scope.indicators)
    config_countries = scalar(
        tmp_path / "wh.duckdb", "select config -> 'scope' ->> 'countries' from raw.landing_runs"
    )
    assert "BRA" in str(config_countries)


def test_every_committed_run_is_loaded_and_incomplete_runs_are_not(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    extract_recorded(recorded_config, tmp_path / "raw", datetime(2026, 11, 24, tzinfo=UTC))
    extract_recorded(recorded_config, tmp_path / "raw", datetime(2026, 11, 25, tzinfo=UTC))
    RunWriter.start(tmp_path / "raw", datetime(2026, 11, 26, tzinfo=UTC))  # never committed

    summary = load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")

    assert summary.runs == 2


def test_load_always_starts_from_an_empty_warehouse(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    extract_recorded(recorded_config, tmp_path / "raw", datetime(2026, 11, 24, tzinfo=UTC))
    load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")
    load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")

    assert scalar(tmp_path / "wh.duckdb", "select count(*) from raw.landing_runs") == 1


def test_no_runs_gives_empty_raw_tables(tmp_path: Path) -> None:
    summary = load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")

    assert summary.runs == 0
    assert scalar(tmp_path / "wh.duckdb", "select count(*) from raw.api_responses") == 0


def _first_observation_page(root: Path) -> Path:
    return next(root.glob("run_id=*/endpoint=observations/*/page=1.json"))


def test_a_tampered_landing_file_fails_the_load(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    extract_recorded(recorded_config, tmp_path / "raw", datetime(2026, 11, 24, tzinfo=UTC))
    page = _first_observation_page(tmp_path / "raw")
    page.write_bytes(page.read_bytes().replace(b'"value":', b'"VALUE":', 1))  # same size

    with pytest.raises(IntegrityError, match="sha256"):
        load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")


def test_a_missing_landing_file_fails_the_load(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    extract_recorded(recorded_config, tmp_path / "raw", datetime(2026, 11, 24, tzinfo=UTC))
    _first_observation_page(tmp_path / "raw").unlink()

    with pytest.raises(IntegrityError, match="missing"):
        load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")


def test_a_run_without_requests_or_files_loads(tmp_path: Path) -> None:
    RunWriter.start(tmp_path / "raw", datetime(2026, 11, 24, tzinfo=UTC)).commit(
        committed_at=datetime(2026, 11, 24, 0, 1, tzinfo=UTC),
        pipeline_version="0.1.0",
        git_sha=None,
        config={},
        warnings=[],
    )

    summary = load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")

    assert (summary.runs, summary.responses) == (1, 0)


def two_runs(root: Path) -> None:
    for day in (24, 25):
        RunWriter.start(root, datetime(2026, 11, day, tzinfo=UTC)).commit(
            committed_at=datetime(2026, 11, day, 0, 1, tzinfo=UTC),
            pipeline_version="0.1.0",
            git_sha=None,
            config={},
            warnings=[],
        )


def test_as_of_loads_the_runs_up_to_that_run(tmp_path: Path) -> None:
    two_runs(tmp_path / "raw")

    summary = load_raw(tmp_path / "raw", tmp_path / "wh.duckdb", as_of="2026-11-24T00-00-00Z")

    assert summary.runs == 1
    assert scalar(tmp_path / "wh.duckdb", "select max(run_id) from raw.landing_runs") == (
        "2026-11-24T00-00-00Z"
    )


def test_as_of_cuts_runs_by_commit_time_not_start_time(tmp_path: Path) -> None:
    root = tmp_path / "raw"
    for started, committed in ((5, 30), (10, 15)):  # the earlier start commits later
        RunWriter.start(root, datetime(2026, 11, 24, 0, started, tzinfo=UTC)).commit(
            committed_at=datetime(2026, 11, 24, 0, committed, tzinfo=UTC),
            pipeline_version="0.1.0",
            git_sha=None,
            config={},
            warnings=[],
        )

    # As of the run that started at 00:10 and committed at 00:15, the run that started first but
    # committed at 00:30 hadn't happened yet.
    summary = load_raw(root, tmp_path / "wh.duckdb", as_of="2026-11-24T00-10-00Z")

    assert summary.runs == 1
    assert scalar(tmp_path / "wh.duckdb", "select max(run_id) from raw.landing_runs") == (
        "2026-11-24T00-10-00Z"
    )


def test_as_of_an_unknown_run_fails_before_writing(tmp_path: Path) -> None:
    two_runs(tmp_path / "raw")

    with pytest.raises(UnknownRun, match="2026-01-01T00-00-00Z"):
        load_raw(tmp_path / "raw", tmp_path / "wh.duckdb", as_of="2026-01-01T00-00-00Z")
    assert not (tmp_path / "wh.duckdb").exists()


def test_build_files_sit_next_to_the_live_warehouse() -> None:
    live = Path("data/warehouse/worldbank.duckdb")

    assert next_path(live) == Path("data/warehouse/worldbank.next.duckdb")
    assert as_of_path(live, "2026-11-24T00-00-00Z") == Path(
        "data/warehouse/worldbank.as-of-2026-11-24T00-00-00Z.duckdb"
    )


def test_cli_load_writes_the_next_file_never_the_live_one(tmp_path: Path) -> None:
    two_runs(tmp_path / "raw" / "worldbank")

    result = CliRunner().invoke(app, ["load", "--data-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "loaded 2 runs" in result.stdout
    assert (tmp_path / "warehouse" / "worldbank.next.duckdb").is_file()
    assert not (tmp_path / "warehouse" / "worldbank.duckdb").exists()


def test_cli_load_as_of_writes_a_file_of_its_own(tmp_path: Path) -> None:
    two_runs(tmp_path / "raw" / "worldbank")

    result = CliRunner().invoke(
        app, ["load", "--data-dir", str(tmp_path), "--as-of", "2026-11-24T00-00-00Z"]
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "warehouse" / "worldbank.as-of-2026-11-24T00-00-00Z.duckdb").is_file()
    assert not (tmp_path / "warehouse" / "worldbank.next.duckdb").exists()


def test_cli_load_reports_failures_with_exit_code_1(tmp_path: Path) -> None:
    two_runs(tmp_path / "raw" / "worldbank")

    result = CliRunner().invoke(
        app, ["load", "--data-dir", str(tmp_path), "--as-of", "2026-01-01T00-00-00Z"]
    )

    assert result.exit_code == 1
    assert "load failed, no build written: no committed run 2026-01-01T00-00-00Z" in result.stderr


def test_timestamps_with_any_offset_are_stored_as_utc(tmp_path: Path) -> None:
    plus_two = timezone(timedelta(hours=2))
    RunWriter.start(tmp_path / "raw", datetime(2026, 11, 24, 12, 0, tzinfo=plus_two)).commit(
        committed_at=datetime(2026, 11, 24, 12, 1, tzinfo=plus_two),
        pipeline_version="0.1.0",
        git_sha=None,
        config={},
        warnings=[],
    )

    load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")

    assert scalar(tmp_path / "wh.duckdb", "select started_at from raw.landing_runs") == datetime(
        2026, 11, 24, 10, 0
    )


def test_a_failed_load_removes_the_previous_build(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    extract_recorded(recorded_config, tmp_path / "raw", datetime(2026, 11, 24, tzinfo=UTC))
    (tmp_path / "wh.duckdb").write_bytes(b"previous build")
    _first_observation_page(tmp_path / "raw").write_bytes(b"tampered")

    with pytest.raises(IntegrityError):
        load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")
    assert not (tmp_path / "wh.duckdb").exists()


def test_a_load_that_fails_midway_leaves_no_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    two_runs(tmp_path / "raw")
    monkeypatch.setattr("worldbank.warehouse.load.LOAD", "select * from no_such_table")

    with pytest.raises(LoadFailed):
        load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")
    assert not (tmp_path / "wh.duckdb").exists()
    assert (tmp_path / "wh.duckdb.loading").exists()  # kept for debugging


def test_cli_load_reports_a_failing_load_sql(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    two_runs(tmp_path / "raw" / "worldbank")
    monkeypatch.setattr("worldbank.warehouse.load.LOAD", "select * from no_such_table")

    result = CliRunner().invoke(app, ["load", "--data-dir", str(tmp_path)])

    assert result.exit_code == 1
    assert "load failed, no build written" in result.stderr
