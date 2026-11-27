import hashlib
import json
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from worldbank.storage.manifest import RequestRecord
from worldbank.storage.runs import (
    AlreadyCommitted,
    IntegrityError,
    RunWriter,
    committed_runs,
    config_hash,
    new_run_id,
)

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


def test_run_id_is_a_utc_timestamp() -> None:
    assert new_run_id(STARTED) == "2026-11-24T18-30-00Z"


def test_pages_are_written_byte_for_byte(tmp_path: Path) -> None:
    run = write_and_commit(tmp_path)

    page = run.path / "endpoint=observations" / "SP.POP.TOTL" / "page=1.json"
    assert page.read_bytes() == BODY


def test_manifest_records_files_requests_and_config(tmp_path: Path) -> None:
    run = write_and_commit(tmp_path)

    manifest = json.loads((run.path / "manifest.json").read_text())
    [landed] = manifest["files"]
    assert (
        landed["response_id"]
        == "run_id=2026-11-24T18-30-00Z/endpoint=observations/SP.POP.TOTL/page=1.json"
    )
    assert landed["sha256"] == hashlib.sha256(BODY).hexdigest()
    assert landed["bytes"] == len(BODY)
    assert manifest["requests"][0]["lastupdated"] == "2026-11-11"
    assert manifest["config_hash"] == config_hash({"scope": {"countries": ["BRA"]}})
    assert manifest["git_sha"] == "abc123"
    assert manifest["warnings"] == ["w1", "w2"]
    assert not (run.path / "manifest.json.tmp").exists()


def test_metadata_pages_without_a_key(tmp_path: Path) -> None:
    run = RunWriter.start(tmp_path, STARTED)
    landed = run.write_page(
        endpoint="countries", key=None, page=1, body=BODY, url="u", fetched_at=STARTED
    )

    assert landed.response_id == "run_id=2026-11-24T18-30-00Z/endpoint=countries/page=1.json"


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


def test_a_run_folder_is_never_reused(tmp_path: Path) -> None:
    RunWriter.start(tmp_path, STARTED)

    with pytest.raises(FileExistsError):
        RunWriter.start(tmp_path, STARTED)


def test_config_hash_ignores_key_order() -> None:
    assert config_hash({"a": 1, "b": [1, 2]}) == config_hash({"b": [1, 2], "a": 1})
    assert config_hash({"a": 1}) != config_hash({"a": 2})


def test_a_committed_run_is_immutable(tmp_path: Path) -> None:
    run = write_and_commit(tmp_path)
    manifest_before = (run.path / "manifest.json").read_bytes()

    with pytest.raises(AlreadyCommitted):
        run.write_page(
            endpoint="countries", key=None, page=1, body=b"x", url="u", fetched_at=STARTED
        )
    with pytest.raises(AlreadyCommitted):
        run.commit(
            committed_at=COMMITTED, pipeline_version="0.1.0", git_sha=None, config={}, warnings=[]
        )
    assert (run.path / "manifest.json").read_bytes() == manifest_before


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


def test_run_ids_are_utc_even_for_local_times() -> None:
    sao_paulo = timezone(timedelta(hours=-3))

    assert new_run_id(datetime(2026, 11, 24, 15, 30, tzinfo=sao_paulo)) == "2026-11-24T18-30-00Z"


def test_non_ascii_bytes_are_kept_exactly(tmp_path: Path) -> None:
    body = '[{"page":1},[{"name":"Côte d\'Ivoire"}]]'.encode()
    run = RunWriter.start(tmp_path, STARTED)

    landed = run.write_page(
        endpoint="countries", key=None, page=1, body=body, url="u", fetched_at=STARTED
    )

    assert (tmp_path / landed.response_id).read_bytes() == body
    assert landed.bytes == len(body)


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
