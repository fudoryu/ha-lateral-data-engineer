"""Extract under crafted scenarios built from real recorded responses (ADR-0012).

Each test is "the real API, except ...": one change to the recorded data or one injected failure,
and an assertion about what gets committed (or that nothing does).
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from scenarios import RecordedApi, connection_error

from worldbank.config import Config
from worldbank.source.client import (
    Client,
    InconsistentPages,
    PermanentHTTPError,
    TransientHTTPError,
)
from worldbank.source.contracts import ApiErrorResponse, UnexpectedResponse
from worldbank.source.extract import ScopeViolation, extract
from worldbank.storage.manifest import Manifest
from worldbank.storage.read import committed_runs

T0 = datetime(2026, 11, 24, 18, 0, tzinfo=UTC)
POP, GDP, LE = "SP.POP.TOTL", "NY.GDP.MKTP.CD", "SP.DYN.LE00.IN"


def run(api: RecordedApi, config: Config, root: Path, at: datetime = T0) -> Manifest:
    with api.serve():
        return extract(config, Client(config.api, sleep=lambda _: None), root, now=lambda: at)


def landed_rows(root: Path, manifest: Manifest, indicator: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for f in manifest.files:
        if f.endpoint == "observations" and f.key == indicator:
            rows.extend(json.loads((root / f.response_id).read_bytes())[1] or [])
    return rows


def expected_rows(config: Config) -> int:
    return len(config.scope.countries) * len(config.scope.years.as_range())


def row(api: RecordedApi, indicator: str, iso3: str, year: int) -> dict[str, Any]:
    [match] = [
        r for r in api.rows(indicator) if r["countryiso3code"] == iso3 and r["date"] == str(year)
    ]
    return match


# --- baseline ------------------------------------------------------------------------------------


def test_real_data_lands_byte_for_byte(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    manifest = run(api, recorded_config, tmp_path)

    for f in manifest.files:
        assert (tmp_path / f.response_id).read_bytes() == api.body(f.response_id.split("/", 1)[1])
    assert all(
        len(landed_rows(tmp_path, manifest, code)) == expected_rows(recorded_config)
        for code in (POP, GDP, LE)
    )


# --- missing data is landed, not rejected (NFR-3) ------------------------------------------------


def test_null_value_is_landed_as_null(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.with_value(LE, "IND", 2024, None)

    manifest = run(api, recorded_config, tmp_path)

    [landed] = [
        r
        for r in landed_rows(tmp_path, manifest, LE)
        if r["countryiso3code"] == "IND" and r["date"] == "2024"
    ]
    assert landed["value"] is None


def test_missing_row_is_landed_as_absent(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.without_row(GDP, "ZAF", 2018)

    manifest = run(api, recorded_config, tmp_path)

    rows = landed_rows(tmp_path, manifest, GDP)
    assert len(rows) == expected_rows(recorded_config) - 1
    assert not any(r["countryiso3code"] == "ZAF" and r["date"] == "2018" for r in rows)


# --- responses that don't match the request -------------------------------------------------------


def test_rows_not_adding_up_to_total_fail(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.without_row(GDP, "ZAF", 2018, adjust_total=False)

    with pytest.raises(InconsistentPages, match="API reported"):
        run(api, recorded_config, tmp_path)
    assert committed_runs(tmp_path) == []


def test_out_of_range_year_fails(api: RecordedApi, recorded_config: Config, tmp_path: Path) -> None:
    """The API ignores unsatisfiable date filters (source-system §4); extract must notice."""
    api.with_extra_row(POP, {**row(api, POP, "BRA", 2024), "date": "2025"})

    with pytest.raises(ScopeViolation, match=r"years outside the request: \[2025\]"):
        run(api, recorded_config, tmp_path)


def test_country_outside_scope_fails(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.with_extra_row(POP, {**row(api, POP, "BRA", 2024), "countryiso3code": "FRA"})

    with pytest.raises(ScopeViolation, match="countries outside the request"):
        run(api, recorded_config, tmp_path)


def test_duplicate_country_year_fails(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.with_extra_row(POP, row(api, POP, "BRA", 2024))

    with pytest.raises(ScopeViolation, match="duplicate country-years"):
        run(api, recorded_config, tmp_path)


def test_wrong_indicator_in_response_fails(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.with_value(POP, "BRA", 2024, 1.0)
    api.edit_rows(POP, "BRA", 2024, lambda r: {**r, "indicator": {"id": GDP, "value": "GDP"}})

    with pytest.raises(ScopeViolation, match="other indicators"):
        run(api, recorded_config, tmp_path)


def test_configured_country_missing_from_metadata_fails(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    meta, countries = api.payload("endpoint=countries/page=1.json")
    api.set_payload(
        "endpoint=countries/page=1.json",
        [{**meta, "total": meta["total"] - 1}, [c for c in countries if c["id"] != "ZAF"]],
    )

    with pytest.raises(ScopeViolation, match="unknown country codes in config: ZAF"):
        run(api, recorded_config, tmp_path)


def test_unrequested_country_in_metadata_fails(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    meta, countries = api.payload("endpoint=countries/page=1.json")
    extra = {**countries[0], "id": "FRA", "iso2Code": "FR", "name": "France"}
    api.set_payload(
        "endpoint=countries/page=1.json",
        [{**meta, "total": meta["total"] + 1}, [*countries, extra]],
    )

    with pytest.raises(ScopeViolation, match="country metadata outside the request: FRA"):
        run(api, recorded_config, tmp_path)


def test_empty_indicator_metadata_fails(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    file = f"endpoint=indicators/{GDP}/page=1.json"
    meta, _ = api.payload(file)
    api.set_payload(file, [{**meta, "total": 0}, None])

    with pytest.raises(ScopeViolation, match=f"unknown indicator code in config: {GDP}"):
        run(api, recorded_config, tmp_path)


# --- contract violations --------------------------------------------------------------------------


@pytest.mark.parametrize("bad", ["N/A", "", "1234"])
def test_non_numeric_value_fails(
    api: RecordedApi, recorded_config: Config, tmp_path: Path, bad: str
) -> None:
    api.with_value(POP, "MEX", 2020, bad)

    with pytest.raises(UnexpectedResponse, match="Observation contract"):
        run(api, recorded_config, tmp_path)


def test_missing_required_field_fails(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    meta, countries = api.payload("endpoint=countries/page=1.json")
    del countries[0]["incomeLevel"]
    api.set_payload("endpoint=countries/page=1.json", [meta, countries])

    with pytest.raises(UnexpectedResponse, match="Country contract"):
        run(api, recorded_config, tmp_path)


def test_html_maintenance_page_fails(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.set_body(api.observation_pages(LE)[1], b"<html><body>Down for maintenance</body></html>")

    with pytest.raises(UnexpectedResponse, match="not valid JSON"):
        run(api, recorded_config, tmp_path)


def test_new_field_is_a_warning_not_a_failure(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.edit_rows(POP, "JPN", 2022, lambda r: {**r, "footnote": "estimate"})

    manifest = run(api, recorded_config, tmp_path)

    assert manifest.warnings == ["unknown field in response: Observation.footnote"]


# --- API and network failures ---------------------------------------------------------------------


def test_api_error_body_fails_without_retry(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    error = [{"message": [{"id": "120", "key": "Invalid value", "value": "not valid"}]}]
    first_gdp_page = api.observation_pages(GDP)[0]
    api.set_payload(first_gdp_page, error)
    client = Client(recorded_config.api, sleep=lambda _: None)

    with api.serve() as mock:
        with pytest.raises(ApiErrorResponse):
            extract(recorded_config, client, tmp_path, now=lambda: T0)
        gdp_calls = [
            c
            for c in mock.calls
            if f"country/BRA;CAN;DEU;GBR;IND;JPN;MEX;USA;ZAF/indicator/{GDP}" in str(c.request.url)
        ]

    assert len(gdp_calls) == 1
    assert committed_runs(tmp_path) == []


def test_server_error_mid_paging_is_retried(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.fail(api.observation_pages(POP)[1], 503, 502)

    manifest = run(api, recorded_config, tmp_path)

    assert len(landed_rows(tmp_path, manifest, POP)) == expected_rows(recorded_config)


def test_connection_error_on_last_page_is_retried(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.fail(api.observation_pages(LE)[-1], connection_error())

    assert len(committed_runs(tmp_path)) == 0
    run(api, recorded_config, tmp_path)
    assert len(committed_runs(tmp_path)) == 1


def test_rate_limiting_is_retried(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.fail("endpoint=countries/page=1.json", 429, 429)

    run(api, recorded_config, tmp_path)

    assert len(committed_runs(tmp_path)) == 1


def test_exhausted_retries_commit_nothing_and_keep_earlier_runs(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    first = run(api, recorded_config, tmp_path, at=T0)
    attempts = recorded_config.api.retry.attempts
    api.fail(api.observation_pages(LE)[-1], *([503] * attempts))

    with pytest.raises(TransientHTTPError):
        run(api, recorded_config, tmp_path, at=T0 + timedelta(days=1))

    assert [r.manifest.run_id for r in committed_runs(tmp_path)] == [first.run_id]
    incomplete = [p for p in tmp_path.glob("run_id=*") if not (p / "manifest.json").exists()]
    assert len(incomplete) == 1  # left on disk for debugging, ignored by readers


def test_client_error_is_not_retried(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    api.fail(f"endpoint=indicators/{LE}/page=1.json", 404)

    with pytest.raises(PermanentHTTPError, match="404"):
        run(api, recorded_config, tmp_path)


# --- pagination consistency -----------------------------------------------------------------------


def _torn(api: RecordedApi, file: str) -> bytes:
    meta, rows = api.payload(file)
    return json.dumps([{**meta, "lastupdated": "2026-12-01"}, rows]).encode()


def test_torn_pages_are_refetched_once(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    last = api.observation_pages(GDP)[-1]
    api.fail(last, _torn(api, last))  # first fetch sees a newer release; the refetch is consistent

    manifest = run(api, recorded_config, tmp_path)

    assert len(landed_rows(tmp_path, manifest, GDP)) == expected_rows(recorded_config)


def test_persistently_torn_pages_fail(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    last = api.observation_pages(GDP)[-1]
    api.set_body(last, _torn(api, last))

    with pytest.raises(InconsistentPages, match="disagree"):
        run(api, recorded_config, tmp_path)


# --- silent revisions across runs (ADR-0006) ------------------------------------------------------


def test_revisions_create_a_new_run_and_never_touch_the_old_one(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    first = run(api, recorded_config, tmp_path, at=T0)
    old_value = row(api, POP, "IND", 2019)["value"]
    api.with_value(POP, "IND", 2019, old_value + 22_613_000)  # the real 2021 -> 2025 revision size

    second = run(api, recorded_config, tmp_path, at=T0 + timedelta(days=30))

    assert [r.manifest.run_id for r in committed_runs(tmp_path)] == [first.run_id, second.run_id]
    for f in first.files:  # the first run is untouched, byte for byte
        assert hashlib.sha256((tmp_path / f.response_id).read_bytes()).hexdigest() == f.sha256
    [revised] = [
        r
        for r in landed_rows(tmp_path, second, POP)
        if r["countryiso3code"] == "IND" and r["date"] == "2019"
    ]
    assert revised["value"] == old_value + 22_613_000


def test_identical_reruns_land_identical_bytes(
    api: RecordedApi, recorded_config: Config, tmp_path: Path
) -> None:
    first = run(api, recorded_config, tmp_path, at=T0)
    second = run(api, recorded_config, tmp_path, at=T0 + timedelta(hours=1))

    assert [f.sha256 for f in first.files] == [f.sha256 for f in second.files]
    assert first.config_hash == second.config_hash
