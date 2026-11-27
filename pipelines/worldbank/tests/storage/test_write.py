import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from landed import BODY, COMMITTED, STARTED, write_and_commit

from worldbank.storage.write import AlreadyCommitted, RunWriter, config_hash, new_run_id


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
