"""Logging (ADR-0024): formats, options, and the events that tell a run's story."""

import json
import logging
import sys
from pathlib import Path

import pytest
import responses
from landed import write_and_commit
from typer.testing import CliRunner

from worldbank.cli import JsonFormatter, TextFormatter, app
from worldbank.config import Config
from worldbank.source.client import Client
from worldbank.source.contracts import Country
from worldbank.storage.read import committed_runs
from worldbank.storage.write import RunWriter


def record(message: str = "request fetched", **fields: object) -> logging.LogRecord:
    entry = logging.LogRecord("worldbank.test", logging.INFO, __file__, 1, message, None, None)
    entry.__dict__.update(fields)
    return entry


def test_text_lines_carry_level_logger_message_and_fields() -> None:
    line = TextFormatter().format(record(path="country/BRA", rows=63, reason="read timed out"))

    assert line.endswith(
        'INFO    worldbank.test request fetched path=country/BRA rows=63 reason="read timed out"'
    )
    assert line[:24].endswith("Z")  # UTC timestamp, milliseconds


def test_json_lines_are_one_object_with_fields_as_keys() -> None:
    entry = json.loads(JsonFormatter().format(record(rows=63, run_id="2026-11-24T18-30-00Z")))

    assert entry["level"] == "INFO"
    assert entry["logger"] == "worldbank.test"
    assert entry["message"] == "request fetched"
    assert (entry["rows"], entry["run_id"]) == (63, "2026-11-24T18-30-00Z")


@pytest.mark.parametrize("formatter", [TextFormatter(), JsonFormatter()])
def test_exceptions_keep_their_traceback(formatter: logging.Formatter) -> None:
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        entry = record("unexpected failure")
        entry.exc_info = sys.exc_info()

    assert "RuntimeError: boom" in formatter.format(entry)


def test_cli_logs_json_to_stderr_and_results_to_stdout(tmp_path: Path) -> None:
    write_and_commit(tmp_path / "raw" / "worldbank")

    result = CliRunner().invoke(app, ["--log-format", "json", "load", "--data-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    events = [json.loads(line) for line in result.stderr.splitlines()]
    finished = next(e for e in events if e["message"] == "load finished")
    assert (finished["runs"], finished["responses"]) == (1, 1)
    assert result.stdout.startswith("loaded 1 runs")


def test_the_log_level_comes_from_the_environment(tmp_path: Path) -> None:
    write_and_commit(tmp_path / "raw" / "worldbank")

    result = CliRunner().invoke(
        app, ["load", "--data-dir", str(tmp_path)], env={"WORLDBANK_LOG_LEVEL": "WARNING"}
    )

    assert result.exit_code == 0, result.output
    assert result.stderr == ""


def test_failures_are_logged_once_as_errors(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["publish", "--data-dir", str(tmp_path)])

    assert result.exit_code == 1
    [line] = result.stderr.splitlines()
    assert "ERROR   worldbank.cli publish failed, live warehouse unchanged" in line


def test_skipped_incomplete_runs_are_warned_about(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    RunWriter.start(tmp_path, write_and_commit(tmp_path).started_at.replace(year=2027))

    with caplog.at_level(logging.WARNING, logger="worldbank"):
        assert len(committed_runs(tmp_path)) == 1
    assert [r.getMessage() for r in caplog.records] == ["skipping incomplete run: no manifest"]


def test_retries_are_warned_about_with_their_reason(
    recorded_config: Config, caplog: pytest.LogCaptureFixture
) -> None:
    url = f"{recorded_config.api.base_url}/country/BRA"
    with responses.RequestsMock() as mock:
        mock.add(responses.GET, url, status=503)
        mock.add(responses.GET, url, json=[{"page": 1, "pages": 1, "per_page": 50, "total": 0}, []])
        with caplog.at_level(logging.WARNING, logger="worldbank"):
            Client(recorded_config.api, sleep=lambda _: None).fetch("country/BRA", Country)

    [retry] = caplog.records
    assert retry.getMessage() == "retrying request"
    assert retry.__dict__["attempt"] == 1
    assert "HTTP 503" in retry.__dict__["reason"]
