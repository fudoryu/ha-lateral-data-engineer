import csv
from pathlib import Path

import duckdb
import pytest
from typer.testing import CliRunner

from worldbank.cli import app
from worldbank.warehouse.export import NothingToExport, export_reports


def published(path: Path, *statements: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as con:
        con.execute("CREATE SCHEMA reporting")
        for statement in statements:
            con.execute(statement)
    return path


REPORTS = (
    "CREATE TABLE reporting.rpt_by_year AS SELECT * FROM (VALUES"
    " ('IND', 'POP', 2024, 3.5), ('BRA', 'POP', 2024, 1.5), ('BRA', 'POP', 2023, NULL))"
    " AS t (country_id, indicator_id, observation_year, indicator_value)",
    "CREATE TABLE reporting.rpt_by_group AS SELECT * FROM (VALUES"
    " ('LMC', 'POP'), ('HIC', 'POP'))"
    " AS t (income_group_id, indicator_id)",
)


def rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.reader(file))


def test_every_report_is_written_sorted_with_a_header(tmp_path: Path) -> None:
    warehouse = published(tmp_path / "wh.duckdb", *REPORTS)

    reports = export_reports(warehouse, tmp_path / "outputs")

    assert [(r.table, r.rows) for r in reports] == [("rpt_by_group", 2), ("rpt_by_year", 3)]
    assert rows(tmp_path / "outputs" / "rpt_by_year.csv") == [
        ["country_id", "indicator_id", "observation_year", "indicator_value"],
        ["BRA", "POP", "2023", ""],
        ["BRA", "POP", "2024", "1.5"],
        ["IND", "POP", "2024", "3.5"],
    ]
    assert [row[0] for row in rows(tmp_path / "outputs" / "rpt_by_group.csv")[1:]] == ["HIC", "LMC"]
    assert not list((tmp_path / "outputs").glob("*.tmp"))


def test_reports_without_sort_keys_are_sorted_by_every_column(tmp_path: Path) -> None:
    warehouse = published(
        tmp_path / "wh.duckdb",
        "CREATE TABLE reporting.rpt_other AS SELECT * FROM (VALUES ('b'), ('a')) AS t (name)",
    )

    export_reports(warehouse, tmp_path / "outputs")

    assert rows(tmp_path / "outputs" / "rpt_other.csv") == [["name"], ["a"], ["b"]]


def test_stale_report_files_are_removed_and_others_kept(tmp_path: Path) -> None:
    warehouse = published(tmp_path / "wh.duckdb", *REPORTS)
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "rpt_renamed_away.csv").write_text("old")
    (outputs / "notes.md").write_text("keep me")

    export_reports(warehouse, outputs)

    assert not (outputs / "rpt_renamed_away.csv").exists()
    assert (outputs / "notes.md").read_text() == "keep me"


def test_nothing_to_export_without_a_published_warehouse(tmp_path: Path) -> None:
    with pytest.raises(NothingToExport, match="publish a build first"):
        export_reports(tmp_path / "missing.duckdb", tmp_path / "outputs")


def test_nothing_to_export_without_report_tables(tmp_path: Path) -> None:
    warehouse = published(tmp_path / "wh.duckdb")

    with pytest.raises(NothingToExport, match="no tables"):
        export_reports(warehouse, tmp_path / "outputs")


def test_cli_export_writes_to_data_outputs_by_default(tmp_path: Path) -> None:
    published(tmp_path / "warehouse" / "worldbank.duckdb", *REPORTS)

    result = CliRunner().invoke(app, ["export", "--data-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "exported 2 reports" in result.stdout
    assert (tmp_path / "outputs" / "rpt_by_year.csv").is_file()


def test_cli_export_honours_output_and_reports_failures(tmp_path: Path) -> None:
    missing = CliRunner().invoke(app, ["export", "--data-dir", str(tmp_path)])
    published(tmp_path / "warehouse" / "worldbank.duckdb", *REPORTS)
    elsewhere = CliRunner().invoke(
        app, ["export", "--data-dir", str(tmp_path), "--output", str(tmp_path / "sample")]
    )

    assert missing.exit_code == 1
    assert "export failed" in missing.stderr
    assert elsewhere.exit_code == 0
    assert (tmp_path / "sample" / "rpt_by_group.csv").is_file()
