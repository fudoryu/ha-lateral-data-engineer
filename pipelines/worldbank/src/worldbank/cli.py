"""Command-line entry point: `uv run worldbank <command>`."""

import subprocess
from pathlib import Path

import requests
import typer

from worldbank import __version__
from worldbank.client import Client, InconsistentPages, PermanentHTTPError, TransientHTTPError
from worldbank.config import load_config
from worldbank.extract import ScopeViolation
from worldbank.extract import extract as run_extract
from worldbank.models import ApiErrorResponse, UnexpectedResponse

DEFAULT_CONFIG = Path("pipelines/worldbank/config.yml")
DEFAULT_DATA_DIR = Path("data")
SOURCE = "worldbank"

EXTRACT_FAILURES = (
    ApiErrorResponse,
    UnexpectedResponse,
    PermanentHTTPError,
    TransientHTTPError,
    InconsistentPages,
    ScopeViolation,
    requests.RequestException,
)

app = typer.Typer(
    help="World Bank country indicators pipeline.",
    no_args_is_help=True,
    add_completion=False,
)

ConfigOption = typer.Option(DEFAULT_CONFIG, "--config", help="Pipeline configuration file.")
DataDirOption = typer.Option(DEFAULT_DATA_DIR, "--data-dir", help="Root of local data.")


@app.callback()
def main() -> None:
    """World Bank country indicators pipeline."""


@app.command()
def version() -> None:
    """Print the World Bank pipeline version."""
    typer.echo(__version__)


@app.command()
def extract(config: Path = ConfigOption, data_dir: Path = DataDirOption) -> None:
    """Fetch the configured scope from the API and commit it as a landing run."""
    settings = load_config(config)
    landing_root = data_dir / "raw" / SOURCE
    try:
        manifest = run_extract(settings, Client(settings.api), landing_root, git_sha=_git_sha())
    except EXTRACT_FAILURES as exc:
        typer.echo(f"extract failed, nothing committed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    for warning in manifest.warnings:
        typer.echo(f"warning: {warning}", err=True)
    typer.echo(f"committed run {manifest.run_id}: {len(manifest.files)} files in {landing_root}")


def _git_sha() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=5
        )
    except OSError, subprocess.SubprocessError:
        return None
    return result.stdout.strip() or None
