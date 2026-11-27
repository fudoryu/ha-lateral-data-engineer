"""Command-line entry point: `uv run worldbank <command>`.

The CLI is the only place that configures logging (ADR-0024): one handler on the `worldbank`
logger, on stderr, as text or JSON. stdout carries only each command's one-line result.
"""

import json
import logging
import subprocess
import sys
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import typer
import yaml
from pydantic import ValidationError

from worldbank import __version__
from worldbank.config import Config, load_config
from worldbank.source.client import Client
from worldbank.source.errors import ExtractError
from worldbank.source.extract import extract as run_extract
from worldbank.storage.errors import StorageError
from worldbank.warehouse.errors import WarehouseError
from worldbank.warehouse.load import as_of_path, load_raw, next_path
from worldbank.warehouse.publish import publish as publish_build

DEFAULT_CONFIG = Path("pipelines/worldbank/config.yml")
DEFAULT_DATA_DIR = Path("data")
SOURCE = "worldbank"


log = logging.getLogger(__name__)


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


app = typer.Typer(
    help="World Bank country indicators pipeline.",
    no_args_is_help=True,
    add_completion=False,
)

ConfigOption = typer.Option(DEFAULT_CONFIG, "--config", help="Pipeline configuration file.")
DataDirOption = typer.Option(DEFAULT_DATA_DIR, "--data-dir", help="Root of local data.")
LogLevelOption = typer.Option(
    LogLevel.INFO, "--log-level", envvar="WORLDBANK_LOG_LEVEL", help="Lowest level logged."
)
LogFormatOption = typer.Option(
    LogFormat.TEXT, "--log-format", envvar="WORLDBANK_LOG_FORMAT", help="Log line format."
)


@app.callback()
def main(log_level: LogLevel = LogLevelOption, log_format: LogFormat = LogFormatOption) -> None:
    """World Bank country indicators pipeline."""
    configure_logging(log_level, log_format)


@app.command()
def version() -> None:
    """Print the World Bank pipeline version."""
    typer.echo(__version__)


@app.command()
def extract(config: Path = ConfigOption, data_dir: Path = DataDirOption) -> None:
    """Fetch the configured scope from the API and commit it as a landing run."""
    settings = _load_config_or_exit(config)
    landing_root = _landing_root(data_dir)
    try:
        manifest = run_extract(settings, Client(settings.api), landing_root, git_sha=_git_sha())
    except ExtractError as exc:
        log.error("extract failed, nothing committed: %s", exc)
        raise typer.Exit(code=1) from exc
    typer.echo(f"committed run {manifest.run_id}: {len(manifest.files)} files in {landing_root}")


@app.command()
def load(
    data_dir: Path = DataDirOption,
    as_of: str | None = typer.Option(
        None, "--as-of", help="Load only the runs up to this run ID, into a file of its own."
    ),
) -> None:
    """Load committed landing runs into a new warehouse file; the live one is never touched."""
    live = _live_warehouse(data_dir)
    target = next_path(live) if as_of is None else as_of_path(live, as_of)
    try:
        summary = load_raw(_landing_root(data_dir), target, as_of=as_of)
    except (StorageError, WarehouseError) as exc:
        log.error("load failed, no build written: %s", exc)
        raise typer.Exit(code=1) from exc
    typer.echo(f"loaded {summary.runs} runs ({summary.responses} responses) into {target}")


@app.command()
def publish(data_dir: Path = DataDirOption) -> None:
    """Make the audited build live: atomically replace the live warehouse with the next file.

    Run it only after a successful full `dbt build` on the next file; `just build` guarantees that
    order (ADR-0023).
    """
    try:
        live = publish_build(_live_warehouse(data_dir))
    except (WarehouseError, OSError) as exc:
        log.error("publish failed, live warehouse unchanged: %s", exc)
        raise typer.Exit(code=1) from exc
    typer.echo(f"published {live}")


def _landing_root(data_dir: Path) -> Path:
    return data_dir / "raw" / SOURCE


def _live_warehouse(data_dir: Path) -> Path:
    return data_dir / "warehouse" / f"{SOURCE}.duckdb"


def _load_config_or_exit(path: Path) -> Config:
    try:
        return load_config(path)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        log.error("invalid configuration %s: %s", path, exc)
        raise typer.Exit(code=2) from exc


def _git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=5
        )
    except OSError, subprocess.SubprocessError:
        return None
    return result.stdout.strip() or None


def configure_logging(level: str, log_format: str) -> None:
    """Send the `worldbank` loggers to stderr at `level`, as text or JSON (ADR-0024)."""
    logger = logging.getLogger("worldbank")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter() if log_format == LogFormat.JSON else TextFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)


# Attributes every LogRecord has; anything else on a record came from `extra=` and is a field.
_RECORD_ATTRIBUTES = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


def _fields(record: logging.LogRecord) -> dict[str, object]:
    return {k: v for k, v in vars(record).items() if k not in _RECORD_ATTRIBUTES}


def _timestamp(record: logging.LogRecord) -> str:
    moment = datetime.fromtimestamp(record.created, UTC)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


class TextFormatter(logging.Formatter):
    """`2026-11-26T21:40:00.123Z INFO    worldbank.source.client request fetched path=… rows=63`"""

    def format(self, record: logging.LogRecord) -> str:
        fields = " ".join(f"{key}={_text(value)}" for key, value in _fields(record).items())
        line = f"{_timestamp(record)} {record.levelname:<7} {record.name} {record.getMessage()}"
        if fields:
            line += f" {fields}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class JsonFormatter(logging.Formatter):
    """One JSON object per line, with the event's fields as top-level keys."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "ts": _timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **_fields(record),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def _text(value: object) -> str:
    text = str(value)
    return json.dumps(text) if not text or any(c.isspace() for c in text) else text
