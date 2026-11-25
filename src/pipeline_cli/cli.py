"""Command-line entry point: `uv run pipeline <source> <command>`."""

import typer

from worldbank_pipeline.cli import app as worldbank_app

app = typer.Typer(
    help="Data pipelines. Each source is a sub-command.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(worldbank_app, name="worldbank")
