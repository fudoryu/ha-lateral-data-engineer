"""Load: rebuild the warehouse's raw layer from every committed landing run (ADR-0003, ADR-0006).

The warehouse is a rebuildable cache, so loading always starts from an empty database file.
Before anything is inserted, each landed file is checked against the sha256 in its run's manifest,
so an edited or corrupted landing file can't silently change the data. Response contracts are
enforced once, at extract time: a matching hash proves the bytes are the ones validated then
(ADR-0020).

Raw tables (one row per landing run, request, and response page; never deduplicated):
    raw.landing_runs    run metadata, including the configuration the run was extracted with
    raw.api_requests    one row per API request (pages, total, lastupdated)
    raw.api_responses   one row per page, with the exact response text as JSON
Timestamps are stored in UTC.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from worldbank.storage.runs import CommittedRun, committed_runs

DDL = """
create schema raw;

create table raw.landing_runs (
    run_id varchar primary key,
    started_at timestamp not null,
    committed_at timestamp not null,
    pipeline_version varchar not null,
    git_sha varchar,
    config_hash varchar not null,
    config json not null,
    warnings json not null
);

create table raw.api_requests (
    run_id varchar not null,
    endpoint varchar not null,
    key varchar,
    pages integer not null,
    total integer not null,
    lastupdated date
);

create table raw.api_responses (
    response_id varchar primary key,
    run_id varchar not null,
    endpoint varchar not null,
    key varchar,
    page integer not null,
    url varchar not null,
    fetched_at timestamp not null,
    sha256 varchar not null,
    payload json not null
);
"""


@dataclass(frozen=True)
class LoadSummary:
    runs: int
    responses: int


def load_raw(landing_root: Path, warehouse: Path) -> LoadSummary:
    """Build a fresh warehouse file at `warehouse` from all committed runs under `landing_root`."""
    runs = committed_runs(landing_root)
    bodies = {run.manifest.run_id: run.read_files() for run in runs}

    warehouse.parent.mkdir(parents=True, exist_ok=True)
    warehouse.unlink(missing_ok=True)
    with duckdb.connect(str(warehouse)) as con:
        con.execute(DDL)
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
