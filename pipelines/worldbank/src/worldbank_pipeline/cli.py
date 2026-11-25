"""`pipeline worldbank <command>`."""

import typer

from worldbank_pipeline import __version__

app = typer.Typer(help="World Bank country indicators pipeline.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """World Bank country indicators pipeline."""


@app.command()
def version() -> None:
    """Print the World Bank pipeline version."""
    typer.echo(__version__)
