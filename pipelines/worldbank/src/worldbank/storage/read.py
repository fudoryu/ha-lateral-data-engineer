"""Read committed runs from the landing zone, verified (ADR-0004, ADR-0006, ADR-0020).

Only runs with a valid manifest are committed; incomplete runs are skipped, never read. A run's
files are read only through `CommittedRun.read_files`, which returns exactly the files the
manifest lists and checks each one against its sha256, so an edited, missing or corrupted file
stops every reader.
"""

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from worldbank.storage.manifest import MANIFEST, RUN_PREFIX, Manifest


class IntegrityError(Exception):
    """A landed file is missing or doesn't match the sha256 recorded in its manifest."""


class CommittedRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    manifest: Manifest

    def read_files(self) -> dict[str, bytes]:
        """The bytes of every file the manifest lists, by response ID, each checked by sha256."""
        files = {}
        for landed in self.manifest.files:
            path = self.path / Path(landed.response_id).relative_to(self.path.name)
            if not path.is_file():
                raise IntegrityError(f"{landed.response_id}: listed in the manifest but missing")
            body = path.read_bytes()
            if hashlib.sha256(body).hexdigest() != landed.sha256:
                raise IntegrityError(f"{landed.response_id}: sha256 doesn't match the manifest")
            files[landed.response_id] = body
        return files


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
