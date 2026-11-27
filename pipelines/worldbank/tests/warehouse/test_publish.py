from pathlib import Path

import pytest
from typer.testing import CliRunner

from worldbank.cli import app
from worldbank.warehouse.publish import NothingToPublish, UnsafeToPublish, publish


def warehouse_dir(tmp_path: Path, *, live: bytes | None, build: bytes | None) -> Path:
    directory = tmp_path / "warehouse"
    directory.mkdir()
    if live is not None:
        (directory / "worldbank.duckdb").write_bytes(live)
    if build is not None:
        (directory / "worldbank.next.duckdb").write_bytes(build)
    return directory


def test_publish_replaces_the_live_file_with_the_build(tmp_path: Path) -> None:
    directory = warehouse_dir(tmp_path, live=b"old", build=b"new")

    live = publish(directory / "worldbank.duckdb")

    assert live.read_bytes() == b"new"
    assert not (directory / "worldbank.next.duckdb").exists()


def test_the_first_publish_creates_the_live_file(tmp_path: Path) -> None:
    directory = warehouse_dir(tmp_path, live=None, build=b"new")

    assert publish(directory / "worldbank.duckdb").read_bytes() == b"new"


def test_nothing_to_publish_without_a_build(tmp_path: Path) -> None:
    directory = warehouse_dir(tmp_path, live=b"old", build=None)

    with pytest.raises(NothingToPublish):
        publish(directory / "worldbank.duckdb")
    assert (directory / "worldbank.duckdb").read_bytes() == b"old"


@pytest.mark.parametrize("wal", ["worldbank.next.duckdb.wal", "worldbank.duckdb.wal"])
def test_a_write_ahead_log_blocks_publishing(tmp_path: Path, wal: str) -> None:
    directory = warehouse_dir(tmp_path, live=b"old", build=b"new")
    (directory / wal).write_bytes(b"")

    with pytest.raises(UnsafeToPublish, match=wal):
        publish(directory / "worldbank.duckdb")
    assert (directory / "worldbank.duckdb").read_bytes() == b"old"


def test_cli_publish_reports_the_live_file(tmp_path: Path) -> None:
    warehouse_dir(tmp_path, live=b"old", build=b"new")

    result = CliRunner().invoke(app, ["publish", "--data-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "published" in result.stdout
    assert (tmp_path / "warehouse" / "worldbank.duckdb").read_bytes() == b"new"


def test_cli_publish_fails_with_exit_code_1_and_keeps_the_live_file(tmp_path: Path) -> None:
    warehouse_dir(tmp_path, live=b"old", build=None)

    result = CliRunner().invoke(app, ["publish", "--data-dir", str(tmp_path)])

    assert result.exit_code == 1
    assert "publish failed, live warehouse unchanged" in result.stderr
    assert (tmp_path / "warehouse" / "worldbank.duckdb").read_bytes() == b"old"
