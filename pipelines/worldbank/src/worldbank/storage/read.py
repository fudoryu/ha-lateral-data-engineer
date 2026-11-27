"""Read committed runs from the landing zone, verified (ADR-0004, ADR-0006, ADR-0020).

Only runs with a valid manifest are committed; incomplete runs are skipped, never read. A
manifest must describe its own folder: its run ID matches the folder name and every file it lists
lies inside it. A run's files are reached only through `CommittedRun.verified_files`, which
returns exactly the files the manifest lists after checking each one's size and sha256, so an
edited, missing, moved or corrupted file stops every reader.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from worldbank.storage.manifest import MANIFEST, RUN_PREFIX, Manifest


class IntegrityError(Exception):
    """A landed file is missing or doesn't match the sha256 recorded in its manifest."""


@dataclass(frozen=True)
class CommittedRun:
    path: Path
    manifest: Manifest

    @property
    def manifest_path(self) -> Path:
        return self.path / MANIFEST

    def verified_files(self) -> list[Path]:
        """Every file the manifest lists, each checked against its size and sha256 first."""
        files = []
        for landed in self.manifest.files:
            if not landed.response_id.startswith(f"{self.path.name}/"):
                raise IntegrityError(
                    f"{landed.response_id}: listed outside its run {self.path.name}"
                )
            path = self.path.parent / landed.response_id
            if not path.is_file():
                raise IntegrityError(f"{landed.response_id}: listed in the manifest but missing")
            if path.stat().st_size != landed.bytes:
                raise IntegrityError(f"{landed.response_id}: size doesn't match the manifest")
            if _sha256(path) != landed.sha256:
                raise IntegrityError(f"{landed.response_id}: sha256 doesn't match the manifest")
            files.append(path)
        return files


def committed_runs(landing_root: Path) -> list[CommittedRun]:
    """Committed runs under `landing_root`, oldest first. Incomplete runs are skipped."""
    if not landing_root.exists():
        return []
    runs = []
    for path in sorted(landing_root.glob(f"{RUN_PREFIX}*")):
        manifest_file = path / MANIFEST
        if path.is_dir() and manifest_file.is_file():
            manifest = Manifest.model_validate_json(manifest_file.read_text(encoding="utf-8"))
            if f"{RUN_PREFIX}{manifest.run_id}" != path.name:
                raise IntegrityError(f"{path.name}: its manifest is for run {manifest.run_id}")
            runs.append(CommittedRun(path=path, manifest=manifest))
    return runs


def _sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()  # streamed, not read whole
