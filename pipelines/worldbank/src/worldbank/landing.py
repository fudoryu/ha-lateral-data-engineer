"""Landing zone: immutable run folders committed by a manifest written last (ADR-0004, ADR-0014).

Layout under the source's landing root (for example `data/raw/worldbank/`):

    run_id=2026-11-24T18-30-00Z/
        endpoint=countries/page=1.json
        endpoint=indicators/SP.POP.TOTL/page=1.json
        endpoint=observations/SP.POP.TOTL/page=1.json
        manifest.json          <- written last; its existence is the commit

A response's ID is its path relative to the landing root, so it survives warehouse rebuilds
(ADR-0006). Runs without a valid manifest are incomplete and are never read.
"""

import hashlib
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

MANIFEST = "manifest.json"
RUN_PREFIX = "run_id="


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


class CommittedRun(_Model):
    path: Path
    manifest: Manifest


def new_run_id(now: datetime) -> str:
    return now.astimezone(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


def config_hash(config: dict[str, Any]) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


class LandingRun:
    """A run being written. Nothing in it counts until `commit` writes the manifest."""

    def __init__(self, landing_root: Path, run_id: str, started_at: datetime) -> None:
        self.landing_root = landing_root
        self.run_id = run_id
        self.started_at = started_at
        self.path = landing_root / f"{RUN_PREFIX}{run_id}"
        self._files: list[LandedFile] = []
        self._requests: list[RequestRecord] = []

    @classmethod
    def start(cls, landing_root: Path, now: datetime) -> LandingRun:
        run = cls(landing_root, new_run_id(now), now)
        run.path.mkdir(parents=True, exist_ok=False)  # never reuse or overwrite a run
        return run

    def write_page(
        self,
        *,
        endpoint: str,
        key: str | None,
        page: int,
        body: bytes,
        url: str,
        fetched_at: datetime,
    ) -> LandedFile:
        """Write one response page, byte for byte."""
        relative = Path(f"endpoint={endpoint}")
        if key is not None:
            relative /= key
        relative /= f"page={page}.json"
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        landed = LandedFile(
            response_id=(Path(self.path.name) / relative).as_posix(),
            endpoint=endpoint,
            key=key,
            page=page,
            url=url,
            fetched_at=fetched_at,
            sha256=hashlib.sha256(body).hexdigest(),
            bytes=len(body),
        )
        self._files.append(landed)
        return landed

    def record_request(self, record: RequestRecord) -> None:
        self._requests.append(record)

    def commit(
        self,
        *,
        committed_at: datetime,
        pipeline_version: str,
        git_sha: str | None,
        config: dict[str, Any],
        warnings: list[str],
    ) -> Manifest:
        """Write the manifest last, atomically: this is what makes the run count."""
        manifest = Manifest(
            run_id=self.run_id,
            started_at=self.started_at,
            committed_at=committed_at,
            pipeline_version=pipeline_version,
            git_sha=git_sha,
            config=config,
            config_hash=config_hash(config),
            requests=self._requests,
            files=self._files,
            warnings=sorted(set(warnings)),
        )
        temporary = self.path / f"{MANIFEST}.tmp"
        temporary.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.path / MANIFEST)
        return manifest


def committed_runs(landing_root: Path) -> list[CommittedRun]:
    """Committed runs under `landing_root`, oldest first. Incomplete runs are skipped."""
    if not landing_root.exists():
        return []
    runs = []
    for path in sorted(landing_root.glob(f"{RUN_PREFIX}*")):
        manifest_path = path / MANIFEST
        if path.is_dir() and manifest_path.is_file():
            manifest = Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
            runs.append(CommittedRun(path=path, manifest=manifest))
    return runs
