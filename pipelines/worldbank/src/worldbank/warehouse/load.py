"""Load: rebuild the warehouse's raw layer from every committed landing run (ADR-0003, ADR-0006).

The warehouse is a rebuildable cache, so loading always starts from an empty database file, and
never the live one: it writes the next file (`<name>.next.duckdb`), which dbt then builds and
tests, and which only `publish` makes live (ADR-0007, ADR-0022). A point-in-time load (`as_of`)
writes a file of its own and is never published.

Before anything is inserted, each landed file is checked against the sha256 in its run's manifest,
so an edited or corrupted landing file can't silently change the data. Response contracts are
enforced once, at extract time: a matching hash proves the bytes are the ones validated then
(ADR-0020).

Raw tables, defined in `schema.sql` (one row per landing run, request, and response page; never
deduplicated):
    raw.landing_runs    run metadata, including the configuration the run was extracted with
    raw.api_requests    one row per API request (pages, total, lastupdated)
    raw.api_responses   one row per page, with the exact response text as JSON
Timestamps are stored in UTC.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

import duckdb

from worldbank.storage.read import CommittedRun, committed_runs

SCHEMA = resources.files("worldbank.warehouse").joinpath("schema.sql").read_text(encoding="utf-8")


class UnknownRun(Exception):
    """`as_of` names no committed run."""


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

    With `as_of`, only the runs up to and including that run are loaded, so the latest run (and
    with it every mart) is as of that run (ADR-0006).
    """
    runs = committed_runs(landing_root)
    if as_of is not None:
        run_ids = [run.manifest.run_id for run in runs]
        if as_of not in run_ids:
            raise UnknownRun(f"no committed run {as_of} under {landing_root}")
        runs = runs[: run_ids.index(as_of) + 1]
    bodies = {run.manifest.run_id: run.read_files() for run in runs}

    warehouse.parent.mkdir(parents=True, exist_ok=True)
    warehouse.unlink(missing_ok=True)
    with duckdb.connect(str(warehouse)) as con:
        con.execute(SCHEMA)
        for run in runs:
            _insert_run(con, run, bodies[run.manifest.run_id])
    return LoadSummary(runs=len(runs), responses=sum(len(b) for b in bodies.values()))


def _insert_run(
    con: duckdb.DuckDBPyConnection, run: CommittedRun, bodies: dict[str, bytes]
) -> None:
    m = run.manifest
    con.execute(
        "insert into raw.landing_runs values (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            m.run_id,
            _utc(m.started_at),
            _utc(m.committed_at),
            m.pipeline_version,
            m.git_sha,
            m.config_hash,
            json.dumps(m.config),
            json.dumps(m.warnings),
        ],
    )
    _insert_many(
        con,
        "insert into raw.api_requests values (?, ?, ?, ?, ?, ?)",
        [[m.run_id, r.endpoint, r.key, r.pages, r.total, r.lastupdated] for r in m.requests],
    )
    _insert_many(
        con,
        "insert into raw.api_responses values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            [
                f.response_id,
                m.run_id,
                f.endpoint,
                f.key,
                f.page,
                f.url,
                _utc(f.fetched_at),
                f.sha256,
                bodies[f.response_id].decode("utf-8"),
            ]
            for f in m.files
        ],
    )


def _insert_many(con: duckdb.DuckDBPyConnection, sql: str, rows: list[list[object]]) -> None:
    if rows:  # DuckDB rejects executemany with no rows; a run may have no requests or files
        con.executemany(sql, rows)


def _utc(moment: datetime) -> datetime:
    return moment.astimezone(UTC).replace(tzinfo=None)
