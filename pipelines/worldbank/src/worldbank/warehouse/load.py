"""Load: rebuild the warehouse's raw layer from every committed landing run (ADR-0003, ADR-0006).

The warehouse is a rebuildable cache, so loading always starts from an empty database file, and
never the live one: it writes the next file (`<name>.next.duckdb`), which dbt then builds and
tests, and which only `publish` makes live (ADR-0007, ADR-0022). A point-in-time load (`as_of`)
writes a file of its own and is never published.

Before anything is loaded, each landed file is checked against the sha256 in its run's manifest,
so an edited or corrupted landing file can't silently change the data. Python then hands DuckDB
the verified file lists, and `load.sql` copies them in set-based, the local equivalent of
`COPY INTO` with an explicit file list. Response contracts are
enforced once, at extract time: a matching hash proves the bytes are the ones validated then
(ADR-0020).

Raw tables, defined in `schema.sql` (one row per landing run, request, and response page; never
deduplicated):
    raw.landing_runs    run metadata, including the configuration the run was extracted with
    raw.api_requests    one row per API request (pages, total, lastupdated)
    raw.api_responses   one row per page, with the exact response text as JSON
Timestamps are stored in UTC.
"""

import logging
import os
import time
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import duckdb

from worldbank.storage.read import committed_runs
from worldbank.warehouse.errors import WarehouseError

log = logging.getLogger(__name__)


def _sql(name: str) -> str:
    return resources.files("worldbank.warehouse").joinpath(name).read_text(encoding="utf-8")


SCHEMA = _sql("schema.sql")  # the raw tables
LOAD = _sql("load.sql")  # committed runs into those tables, set-based


class UnknownRun(WarehouseError):
    """`as_of` names no committed run."""


class LoadFailed(WarehouseError):
    """The load SQL failed; no build was written."""


@dataclass(frozen=True)
class LoadSummary:
    runs: int
    responses: int


def next_path(live: Path) -> Path:
    """The file a build writes before publishing: `x.duckdb` → `x.next.duckdb`."""
    return live.with_name(f"{live.stem}.next{live.suffix}")


def as_of_path(live: Path, run_id: str) -> Path:
    """The file of a point-in-time build, which is never published."""
    return live.with_name(f"{live.stem}.as-of-{run_id}{live.suffix}")


def load_raw(landing_root: Path, warehouse: Path, *, as_of: str | None = None) -> LoadSummary:
    """Build a fresh warehouse file at `warehouse` from the committed runs under `landing_root`.

    With `as_of`, only the runs committed up to and including that run are loaded, so the latest
    run (and with it every mart) is as of that run (ADR-0006). Runs are cut by commit time, the
    order dbt uses to pick the latest run, since a run that started earlier can commit later.

    The file appears only once it's complete: any previous build at `warehouse` is removed first,
    the load writes `<warehouse>.loading`, and a rename gives it its final name. A failed load
    leaves no build behind, only the `.loading` file for debugging.
    """
    for stale in (warehouse, _wal(warehouse)):
        stale.unlink(missing_ok=True)
    runs = committed_runs(landing_root)
    if as_of is not None:
        target = next((run for run in runs if run.manifest.run_id == as_of), None)
        if target is None:
            raise UnknownRun(f"no committed run {as_of} under {landing_root}")
        runs = [run for run in runs if run.manifest.committed_at <= target.manifest.committed_at]
    started = time.monotonic()
    log.info("load started", extra={"runs": len(runs), "as_of": as_of, "target": str(warehouse)})
    manifests = [str(run.manifest_path.resolve()) for run in runs]
    pages = [str(path.resolve()) for run in runs for path in run.verified_files()]

    loading = warehouse.with_name(f"{warehouse.name}.loading")
    for stale in (loading, _wal(loading)):
        stale.unlink(missing_ok=True)
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(loading)) as con:
        con.execute("SET TimeZone = 'UTC'")
        con.execute(SCHEMA)
        con.execute(
            "CREATE TEMP TABLE landed_manifest AS"
            " SELECT content::JSON AS manifest FROM read_text($files)",
            {"files": manifests},
        )
        con.execute(
            "CREATE TEMP TABLE landed_page AS"
            " SELECT substr(filename, length($root) + 2) AS response_id, content"
            " FROM read_text($files)",
            {"files": pages, "root": str(landing_root.resolve())},
        )
        try:
            con.execute(LOAD)
        except duckdb.Error as exc:
            raise LoadFailed(f"loading {warehouse.name} failed: {exc}") from exc
    os.replace(loading, warehouse)  # closing the connection checkpointed it: no .wal is left
    log.info(
        "load finished",
        extra={
            "runs": len(runs),
            "responses": len(pages),
            "target": str(warehouse),
            "duration_ms": round((time.monotonic() - started) * 1000),
        },
    )
    return LoadSummary(runs=len(runs), responses=len(pages))


def _wal(database: Path) -> Path:
    return database.with_name(f"{database.name}.wal")
