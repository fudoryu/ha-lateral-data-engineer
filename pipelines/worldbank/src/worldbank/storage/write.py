"""Write a run into the landing zone, committed by a manifest written last (ADR-0004).

Every page is written byte for byte as it arrives. Nothing in the run counts until `commit`
writes the manifest, atomically; after that the run is immutable. A response's ID is its path
relative to the landing root, so it survives warehouse rebuilds (ADR-0006).
"""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from worldbank.storage.manifest import (
    MANIFEST,
    RUN_PREFIX,
    LandedFile,
    Manifest,
    RequestRecord,
)


class AlreadyCommitted(Exception):
    """A committed run is immutable: it can't be written to or committed again."""


def new_run_id(now: datetime) -> str:
    return now.astimezone(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


def config_hash(config: dict[str, Any]) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


class RunWriter:
    """A run being written. Nothing in it counts until `commit` writes the manifest."""

    def __init__(self, landing_root: Path, run_id: str, started_at: datetime) -> None:
        self.landing_root = landing_root
        self.run_id = run_id
        self.started_at = started_at
        self.path = landing_root / f"{RUN_PREFIX}{run_id}"
        self._files: list[LandedFile] = []
        self._requests: list[RequestRecord] = []

    @classmethod
    def start(cls, landing_root: Path, now: datetime) -> RunWriter:
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
        self._ensure_open()
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
        self._ensure_open()
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

    def _ensure_open(self) -> None:
        if (self.path / MANIFEST).exists():
            raise AlreadyCommitted(f"{self.path.name} is committed and immutable")
