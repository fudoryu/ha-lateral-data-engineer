"""Shared test fixtures: serve recorded API responses offline (ADR-0012)."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest
import responses
from responses import matchers

from worldbank.config import Config

RECORDED_DIR = Path(__file__).parent / "fixtures" / "recorded"


@pytest.fixture(scope="session")
def recorded_dir() -> Path:
    return RECORDED_DIR


@pytest.fixture(scope="session")
def recorded_index() -> dict[str, Any]:
    index: dict[str, Any] = json.loads((RECORDED_DIR / "index.json").read_text(encoding="utf-8"))
    return index


@pytest.fixture(scope="session")
def recorded_config(recorded_index: dict[str, Any]) -> Config:
    """The exact configuration the fixtures were recorded with (including the small page size)."""
    return Config.model_validate(recorded_index["config"])


@pytest.fixture
def recorded_api(recorded_index: dict[str, Any]) -> Iterator[responses.RequestsMock]:
    """Serve every recorded response, matched on path and exact query parameters."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        for entry in recorded_index["files"]:
            parts = urlsplit(entry["url"])
            mock.add(
                responses.GET,
                f"{parts.scheme}://{parts.netloc}{parts.path}",
                body=(RECORDED_DIR / entry["file"]).read_bytes(),
                match=[matchers.query_param_matcher(dict(parse_qsl(parts.query)))],
            )
        yield mock
