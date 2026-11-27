"""Test helper: a small committed run in a temporary landing root (ADR-0004)."""

from datetime import UTC, date, datetime
from pathlib import Path

from worldbank.storage.manifest import RequestRecord
from worldbank.storage.write import RunWriter

STARTED = datetime(2026, 11, 24, 18, 30, 0, tzinfo=UTC)
COMMITTED = datetime(2026, 11, 24, 18, 30, 5, tzinfo=UTC)
BODY = b'[{"page":1},[]]'  # no trailing newline: bytes must be kept exactly


def write_and_commit(root: Path, started: datetime = STARTED) -> RunWriter:
    run = RunWriter.start(root, started)
    run.write_page(
        endpoint="observations",
        key="SP.POP.TOTL",
        page=1,
        body=BODY,
        url="https://api.worldbank.org/v2/x?page=1",
        fetched_at=started,
    )
    run.record_request(
        RequestRecord(
            endpoint="observations",
            key="SP.POP.TOTL",
            pages=1,
            total=0,
            lastupdated=date(2026, 11, 11),
        )
    )
    run.commit(
        committed_at=COMMITTED,
        pipeline_version="0.1.0",
        git_sha="abc123",
        config={"scope": {"countries": ["BRA"]}},
        warnings=["w2", "w1", "w1"],
    )
    return run
