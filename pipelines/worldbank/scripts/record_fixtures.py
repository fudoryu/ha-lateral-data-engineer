"""Record live World Bank API responses as test fixtures (ADR-0012).

Usage (from the repo root): `uv run python pipelines/worldbank/scripts/record_fixtures.py`

Runs a real extract with a small page size, so observations span several pages, and copies the
exact response bytes into tests/fixtures/recorded/ with an index. Recordings are immutable:
re-record deliberately, in a commit of its own.
"""

import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from worldbank.api.client import Client
from worldbank.config import load_config
from worldbank.steps.extract import extract

HERE = Path(__file__).parent
CONFIG = HERE.parent / "config.yml"
TARGET = HERE.parent / "tests" / "fixtures" / "recorded"
RECORDING_PAGE_SIZE = 25  # 63 rows per indicator -> 3 pages


def main() -> None:
    config = load_config(CONFIG)
    config = config.model_copy(
        update={"api": config.api.model_copy(update={"per_page": RECORDING_PAGE_SIZE})}
    )
    with tempfile.TemporaryDirectory() as tmp:
        manifest = extract(config, Client(config.api), Path(tmp))
        run_dir = Path(tmp) / f"run_id={manifest.run_id}"
        if TARGET.exists():
            shutil.rmtree(TARGET)
        TARGET.mkdir(parents=True)
        index = []
        for landed in manifest.files:
            relative = Path(landed.response_id).relative_to(run_dir.name)
            destination = TARGET / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(run_dir / relative, destination)
            index.append({"file": relative.as_posix(), "url": landed.url, "sha256": landed.sha256})
    recorded_at = datetime.now(UTC).isoformat(timespec="seconds")
    (TARGET / "index.json").write_text(
        json.dumps(
            {"recorded_at": recorded_at, "config": config.model_dump(mode="json"), "files": index},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"recorded {len(index)} responses into {TARGET}")


if __name__ == "__main__":
    main()
