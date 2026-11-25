from typer.testing import CliRunner

from pipeline_cli.cli import app
from worldbank_pipeline import __version__ as worldbank_version

runner = CliRunner()


def test_worldbank_is_registered_as_a_sub_command() -> None:
    result = runner.invoke(app, ["worldbank", "version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == worldbank_version


def test_help_lists_the_worldbank_pipeline() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "worldbank" in result.stdout
