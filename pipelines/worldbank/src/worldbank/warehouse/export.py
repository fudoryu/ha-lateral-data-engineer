"""Export: write every report table of the published warehouse to CSV (ADR-0034).

Reads only the published warehouse, so only audited data is exported. Report tables are
discovered from the `reporting` schema, so a new report is exported without code changes. Each
CSV has a header and rows sorted for reading, and is written to a temporary name and renamed.
Report CSVs whose table no longer exists are removed; other files in the folder are left alone.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import duckdb

from worldbank.warehouse.errors import WarehouseError

log = logging.getLogger(__name__)

REPORTING_SCHEMA = "reporting"
REPORT_PREFIX = "rpt_"

# Sort keys, in priority order, used when a report has them: income groups low to high, then
# country, indicator and year. Every report's grain is made of these columns.
SORT_KEYS = ("income_group_sort_order", "country_id", "indicator_id", "observation_year")


class NothingToExport(WarehouseError):
    """There's no published warehouse, or it holds no report tables."""


@dataclass(frozen=True)
class ExportedReport:
    table: str
    path: Path
    rows: int


def export_reports(warehouse: Path, output: Path) -> list[ExportedReport]:
    """Write each report table of `warehouse` to `output/<table>.csv`; return what was written."""
    if not warehouse.is_file():
        raise NothingToExport(f"{warehouse} doesn't exist; publish a build first")
    output.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(warehouse), read_only=True) as con:
        tables = _report_tables(con)
        if not tables:
            raise NothingToExport(f"{warehouse} has no tables in the {REPORTING_SCHEMA} schema")
        exported = [_export(con, table, output) for table in tables]
    _remove_stale(output, {report.path.name for report in exported})
    return exported


def _report_tables(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables"
        " WHERE table_schema = ? AND table_name LIKE ? ORDER BY table_name",
        [REPORTING_SCHEMA, f"{REPORT_PREFIX}%"],
    ).fetchall()
    return [row[0] for row in rows]


def _export(con: duckdb.DuckDBPyConnection, table: str, output: Path) -> ExportedReport:
    columns = {
        row[0]
        for row in con.execute(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = ? AND table_name = ?",
            [REPORTING_SCHEMA, table],
        ).fetchall()
    }
    order = ", ".join(_quoted(key) for key in SORT_KEYS if key in columns) or "ALL"
    relation = f"{_quoted(REPORTING_SCHEMA)}.{_quoted(table)}"
    target = output / f"{table}.csv"
    temporary = target.with_name(f"{target.name}.tmp")
    con.execute(
        f"COPY (SELECT * FROM {relation} ORDER BY {order})"
        f" TO '{_escaped(temporary)}' (FORMAT csv, HEADER)"
    )
    os.replace(temporary, target)
    rows = con.execute(f"SELECT count(*) FROM {relation}").fetchone()
    report = ExportedReport(table=table, path=target, rows=rows[0] if rows else 0)
    log.info("report exported", extra={"table": table, "rows": report.rows, "path": str(target)})
    return report


def _remove_stale(output: Path, current: set[str]) -> None:
    for path in output.glob(f"{REPORT_PREFIX}*.csv"):
        if path.name not in current:
            path.unlink()
            log.info("stale report removed", extra={"path": str(path)})


def _quoted(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _escaped(path: Path) -> str:
    return str(path).replace("'", "''")
