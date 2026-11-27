"""The manifest: the on-disk record that commits a run (ADR-0004).

It lists every request and every landed file with its sha256, plus the configuration and code
version the run was made with. Its schema is source-agnostic: endpoints, keys and pages are
plain strings here.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LandedFile(_Model):
    response_id: str  # path relative to the landing root
    endpoint: str
    key: str | None
    page: int
    url: str
    fetched_at: datetime
    sha256: str
    bytes: int


class RequestRecord(_Model):
    endpoint: str
    key: str | None
    pages: int
    total: int
    lastupdated: date | None


class Manifest(_Model):
    run_id: str
    started_at: datetime
    committed_at: datetime
    pipeline_version: str
    git_sha: str | None
    config: dict[str, Any]
    config_hash: str
    requests: list[RequestRecord]
    files: list[LandedFile]
    warnings: list[str]
