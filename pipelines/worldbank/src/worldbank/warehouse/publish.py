"""Publish: make an audited warehouse build live (ADR-0007, ADR-0022).

`just build` runs load, `dbt build` and publish in that order and stops at the first failure, so
publish only ever sees a next file that dbt built and tested. One atomic rename then replaces the
live file: readers see the old warehouse or the new one, never a mix.

DuckDB keeps recent writes in a `<file>.wal` until it checkpoints. A WAL next to the build means a
connection is still open or a write didn't finish; a WAL next to the live file would be replayed
against the new file. Either way publishing is refused.
"""

import os
from pathlib import Path

from worldbank.warehouse.errors import WarehouseError
from worldbank.warehouse.load import next_path


class NothingToPublish(WarehouseError):
    """There is no next file: load and dbt build haven't produced one."""


class UnsafeToPublish(WarehouseError):
    """A write-ahead log shows an open connection or an unfinished write."""


def publish(live: Path) -> Path:
    """Atomically replace `live` with its next file, and return the live path."""
    build = next_path(live)
    if not build.is_file():
        raise NothingToPublish(f"{build} doesn't exist; run `worldbank load` and `dbt build` first")
    for database in (build, live):
        wal = database.with_name(f"{database.name}.wal")
        if wal.exists():
            raise UnsafeToPublish(f"{wal} exists: close open connections, then rebuild")
    os.replace(build, live)  # atomic within one directory
    return live
