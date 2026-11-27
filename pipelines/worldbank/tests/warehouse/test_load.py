from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pytest
import responses

from worldbank.config import Config
from worldbank.source.client import Client
from worldbank.source.extract import extract
from worldbank.storage.manifest import Manifest
from worldbank.storage.runs import IntegrityError, RunWriter
from worldbank.warehouse.load import load_raw


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
    page.write_bytes(page.read_bytes().replace(b'"value":', b'"value" :', 1))

    with pytest.raises(IntegrityError, match="sha256"):
        load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")


def test_a_missing_landing_file_fails_the_load(
    recorded_api: responses.RequestsMock, recorded_config: Config, tmp_path: Path
) -> None:
    extract_recorded(recorded_config, tmp_path / "raw", datetime(2026, 11, 24, tzinfo=UTC))
    _first_observation_page(tmp_path / "raw").unlink()

    with pytest.raises(IntegrityError, match="missing"):
        load_raw(tmp_path / "raw", tmp_path / "wh.duckdb")
