import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from landed import BODY, STARTED, write_and_commit

from worldbank.storage.read import IntegrityError, committed_runs
from worldbank.storage.write import RunWriter


def test_only_committed_runs_are_listed_oldest_first(tmp_path: Path) -> None:
    write_and_commit(tmp_path, datetime(2026, 11, 25, tzinfo=UTC))
    write_and_commit(tmp_path, datetime(2026, 11, 24, tzinfo=UTC))
    incomplete = RunWriter.start(tmp_path, datetime(2026, 11, 26, tzinfo=UTC))
    incomplete.write_page(
        endpoint="countries", key=None, page=1, body=BODY, url="u", fetched_at=STARTED
    )

    runs = committed_runs(tmp_path)

    assert [r.manifest.run_id for r in runs] == ["2026-11-24T00-00-00Z", "2026-11-25T00-00-00Z"]


def test_no_landing_root_means_no_runs(tmp_path: Path) -> None:
    assert committed_runs(tmp_path / "missing") == []


def test_committed_runs_round_trip_the_manifest(tmp_path: Path) -> None:
    run = write_and_commit(tmp_path)

    [loaded] = committed_runs(tmp_path)

    assert loaded.path == run.path
    assert loaded.manifest.files[0].sha256 == hashlib.sha256(BODY).hexdigest()
    assert loaded.manifest.started_at == STARTED


def test_a_corrupt_manifest_fails_loudly(tmp_path: Path) -> None:
    """A committed run that can't be read is an integrity problem, not an incomplete run."""
    run = write_and_commit(tmp_path)
    (run.path / "manifest.json").write_text("{ not json")

    with pytest.raises(ValueError):
        committed_runs(tmp_path)


def test_unrelated_entries_in_the_landing_root_are_ignored(tmp_path: Path) -> None:
    write_and_commit(tmp_path)
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "scratch").mkdir()

    assert len(committed_runs(tmp_path)) == 1


def test_reading_a_committed_run_returns_its_listed_files(tmp_path: Path) -> None:
    write_and_commit(tmp_path)
    (run,) = committed_runs(tmp_path)

    assert list(run.read_files().values()) == [BODY]


def test_a_tampered_file_fails_the_read(tmp_path: Path) -> None:
    run_writer = write_and_commit(tmp_path)
    next(run_writer.path.glob("endpoint=*/**/page=1.json")).write_bytes(BODY + b" ")
    (run,) = committed_runs(tmp_path)

    with pytest.raises(IntegrityError, match="sha256"):
        run.read_files()


def test_a_missing_file_fails_the_read(tmp_path: Path) -> None:
    run_writer = write_and_commit(tmp_path)
    next(run_writer.path.glob("endpoint=*/**/page=1.json")).unlink()
    (run,) = committed_runs(tmp_path)

    with pytest.raises(IntegrityError, match="missing"):
        run.read_files()
