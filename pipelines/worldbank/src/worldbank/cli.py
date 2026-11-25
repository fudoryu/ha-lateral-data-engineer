"""Command-line entry point: `uv run worldbank <command>`."""

import typer

from worldbank import __version__

app = typer.Typer(
    help="World Bank country indicators pipeline.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main() -> None:
    """World Bank country indicators pipeline."""


@app.command()
def version() -> None:
    """Print the World Bank pipeline version."""
    typer.echo(__version__)
