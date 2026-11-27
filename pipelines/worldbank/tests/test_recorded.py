"""Extract against real recorded API responses, offline."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import responses

from worldbank.config import Config
from worldbank.source.client import Client
from worldbank.source.extract import extract
from worldbank.storage.runs import committed_runs


def test_recordings_are_unmodified(recorded_dir: Path, recorded_index: dict[str, Any]) -> None:
    for entry in recorded_index["files"]:
        digest = hashlib.sha256((recorded_dir / entry["file"]).read_bytes()).hexdigest()
        assert digest == entry["sha256"], entry["file"]


def test_recordings_span_several_pages(recorded_index: dict[str, Any]) -> None:
    prefix = "endpoint=observations/SP.POP.TOTL/"
    assert len([e for e in recorded_index["files"] if e["file"].startswith(prefix)]) > 1


def test_recorded_country_metadata_covers_the_scope(
    recorded_dir: Path, recorded_config: Config
) -> None:
    [meta, countries] = json.loads(
        (recorded_dir / "endpoint=countries" / "page=1.json").read_bytes()
    )
    assert sorted(c["id"] for c in countries) == sorted(recorded_config.scope.countries)
    assert meta["total"] == len(countries)


def test_extract_from_recorded_responses(
    recorded_api: responses.RequestsMock,
    recorded_config: Config,
    recorded_index: dict[str, Any],
    tmp_path: Path,
) -> None:
    client = Client(recorded_config.api, sleep=lambda _: None)

    manifest = extract(recorded_config, client, tmp_path, now=lambda: datetime.now(UTC))

    assert len(committed_runs(tmp_path)) == 1
    assert manifest.warnings == []
    expected_rows = len(recorded_config.scope.countries) * len(
        recorded_config.scope.years.as_range()
    )
    assert [r.total for r in manifest.requests if r.endpoint == "observations"] == [
        expected_rows
    ] * 4
    landed = {f.response_id.split("/", 1)[1] for f in manifest.files}
    assert landed == {e["file"] for e in recorded_index["files"]}
