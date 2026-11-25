import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import responses
import yaml
from typer.testing import CliRunner

from worldbank.cli import app
from worldbank.client import Client
from worldbank.config import Config
from worldbank.extract import ScopeViolation, extract
from worldbank.landing import committed_runs
from worldbank.models import ApiErrorResponse

BASE = "https://api.worldbank.org/v2"
RAW: dict[str, Any] = {
    "api": {
        "base_url": BASE,
        "source": 2,
        "per_page": 1000,
        "timeout": {"connect_seconds": 1, "read_seconds": 1},
        "retry": {"attempts": 1, "initial_backoff_seconds": 0, "max_backoff_seconds": 0},
    },
    "scope": {
        "countries": ["BRA", "IND"],
        "indicators": ["SP.POP.TOTL"],
        "years": {"start": 2023, "end": 2024},
    },
}
CONFIG = Config.model_validate(RAW)
NOW = datetime(2026, 11, 24, 18, 30, tzinfo=UTC)


def meta(total: int, **extra: Any) -> dict[str, Any]:
    return {
        "page": 1,
        "pages": 1,
        "per_page": 1000,
        "total": total,
        "lastupdated": "2026-11-11",
        **extra,
    }


def country(code: str) -> dict[str, Any]:
    ref = {"id": "X", "iso2code": "X", "value": "X"}
    return {"id": code, "iso2Code": code[:2], "name": code, "region": ref, "incomeLevel": ref}


def indicator(code: str) -> dict[str, Any]:
    return {"id": code, "name": code, "unit": "", "source": {"id": "2", "value": "WDI"}}


def observation(code: str, iso3: str, year: int, value: float | None = 1.0) -> dict[str, Any]:
    return {
        "indicator": {"id": code, "value": code},
        "country": {"id": iso3[:2], "value": iso3},
        "countryiso3code": iso3,
        "date": str(year),
        "value": value,
    }


def default_observations() -> list[dict[str, Any]]:
    return [observation("SP.POP.TOTL", c, y) for c in ("BRA", "IND") for y in (2023, 2024)]


def mock_api(
    countries: list[str] | None = None,
    observations: list[dict[str, Any]] | None = None,
    observation_meta: dict[str, Any] | None = None,
) -> None:
    returned = ["BRA", "IND"] if countries is None else countries
    rows = default_observations() if observations is None else observations
    responses.add(
        responses.GET,
        f"{BASE}/country/BRA;IND",
        json=[meta(len(returned)), [country(c) for c in returned]],
    )
    responses.add(
        responses.GET, f"{BASE}/indicator/SP.POP.TOTL", json=[meta(1), [indicator("SP.POP.TOTL")]]
    )
    responses.add(
        responses.GET,
        f"{BASE}/country/BRA;IND/indicator/SP.POP.TOTL",
        json=[observation_meta or meta(len(rows)), rows],
    )


def run(tmp_path: Path) -> Any:
    return extract(
        CONFIG, Client(CONFIG.api, sleep=lambda _: None), tmp_path, git_sha="abc", now=lambda: NOW
    )


@responses.activate
def test_extract_commits_a_run_with_every_page(tmp_path: Path) -> None:
    mock_api()

    manifest = run(tmp_path)

    assert [r.manifest.run_id for r in committed_runs(tmp_path)] == [manifest.run_id]
    assert [(f.endpoint, f.key) for f in manifest.files] == [
        ("countries", None),
        ("indicators", "SP.POP.TOTL"),
        ("observations", "SP.POP.TOTL"),
    ]
    assert manifest.requests[2].total == 4
    assert manifest.config["scope"]["countries"] == ["BRA", "IND"]
    assert manifest.git_sha == "abc"
    observations_query = str(responses.calls[2].request.url)
    assert "date=2023%3A2024" in observations_query and "source=2" in observations_query


@responses.activate
def test_unknown_country_fails_before_observations(tmp_path: Path) -> None:
    mock_api(countries=["BRA"])

    with pytest.raises(ScopeViolation, match="unknown country codes in config: IND"):
        run(tmp_path)
    assert committed_runs(tmp_path) == []
    assert len(responses.calls) == 1


@responses.activate
def test_api_error_body_leaves_nothing_committed(tmp_path: Path) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/country/BRA;IND",
        json=[{"message": [{"id": "120", "key": "Invalid value", "value": "bad"}]}],
    )

    with pytest.raises(ApiErrorResponse):
        run(tmp_path)
    assert committed_runs(tmp_path) == []


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([observation("SP.POP.TOTL", "BRA", 1999)], "years outside the request: \\[1999\\]"),
        ([observation("SP.POP.TOTL", "USA", 2024)], "countries outside the request"),
        ([observation("NY.GDP.MKTP.CD", "BRA", 2024)], "other indicators"),
        ([observation("SP.POP.TOTL", "BRA", 2024)] * 2, "duplicate country-years"),
    ],
)
@responses.activate
def test_observations_outside_the_request_fail(
    tmp_path: Path, rows: list[dict[str, Any]], message: str
) -> None:
    mock_api(observations=rows)

    with pytest.raises(ScopeViolation, match=message):
        run(tmp_path)
    assert committed_runs(tmp_path) == []


@responses.activate
def test_missing_values_are_landed_not_rejected(tmp_path: Path) -> None:
    mock_api(observations=[observation("SP.POP.TOTL", "BRA", 2024, value=None)])

    manifest = run(tmp_path)

    assert manifest.requests[2].total == 1


@responses.activate
def test_unknown_fields_are_recorded_as_warnings(tmp_path: Path) -> None:
    mock_api(observation_meta=meta(4, brand_new="x"))

    manifest = run(tmp_path)

    assert manifest.warnings == ["unknown field in response: Meta.brand_new"]


@responses.activate
def test_cli_extract_reports_the_committed_run(tmp_path: Path) -> None:
    mock_api()
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.safe_dump(RAW))

    result = CliRunner().invoke(
        app, ["extract", "--config", str(config_path), "--data-dir", str(tmp_path / "data")]
    )

    assert result.exit_code == 0, result.output
    assert "committed run" in result.stdout
    assert len(committed_runs(tmp_path / "data" / "raw" / "worldbank")) == 1


@responses.activate
def test_cli_extract_fails_with_exit_code_and_no_commit(tmp_path: Path) -> None:
    mock_api(countries=["BRA"])
    config_path = tmp_path / "config.yml"
    config_path.write_text(json.dumps(RAW))

    result = CliRunner().invoke(
        app, ["extract", "--config", str(config_path), "--data-dir", str(tmp_path / "data")]
    )

    assert result.exit_code == 1
    assert "extract failed, nothing committed" in result.output
    assert committed_runs(tmp_path / "data" / "raw" / "worldbank") == []


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "No such file"),
        ("scope: [", "invalid configuration"),
        ("api: {}\nscope: {}\n", "validation error"),
    ],
)
def test_cli_reports_configuration_problems(
    tmp_path: Path, content: str | None, message: str
) -> None:
    config_path = tmp_path / "config.yml"
    if content is not None:
        config_path.write_text(content)

    result = CliRunner().invoke(
        app, ["extract", "--config", str(config_path), "--data-dir", str(tmp_path)]
    )

    assert result.exit_code == 2
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert message in result.output


@responses.activate
def test_cli_reports_a_run_id_collision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two extracts in the same second would share a run folder; the second must fail cleanly."""
    mock_api()
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.safe_dump(RAW))
    (tmp_path / "data" / "raw" / "worldbank" / "run_id=2026-11-24T18-30-00Z").mkdir(parents=True)

    def extract_at_now(*args: Any, **kwargs: Any) -> Any:
        return extract(*args, **{**kwargs, "now": lambda: NOW})

    monkeypatch.setattr("worldbank.cli.run_extract", extract_at_now)

    result = CliRunner().invoke(
        app, ["extract", "--config", str(config_path), "--data-dir", str(tmp_path / "data")]
    )

    assert result.exit_code == 1
    assert "extract failed, nothing committed" in result.output
