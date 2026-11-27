"""Extract: fetch the configured scope from the API and land it as one committed run.

Order (ADR-0002, ADR-0005):
1. Country metadata for all configured countries; every configured code must come back
   (an invalid code would otherwise look like missing data).
2. Indicator metadata, one request per configured indicator.
3. Observations, one request per indicator covering all configured countries and years,
   checked against the request: indicator, countries, years, no duplicate (country, year).

What each request looks like and how its response is checked lives in `endpoints.py`; this
module is only the plan and the landing. Every page is landed as it arrives. The manifest is
written only if everything succeeds, so a failed extract never produces a committed run
(ADR-0007).
"""

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from worldbank import __version__
from worldbank.source import endpoints
from worldbank.source.client import Client, FetchResult
from worldbank.source.errors import ExtractError
from worldbank.source.settings import Config
from worldbank.storage.manifest import Manifest, RequestRecord
from worldbank.storage.write import RunWriter

log = logging.getLogger(__name__)


class RunAlreadyExists(ExtractError):
    """Another run started in the same second already uses this run's folder."""


def extract(
    config: Config,
    client: Client,
    landing_root: Path,
    *,
    git_sha: str | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Manifest:
    scope = config.scope
    try:
        run = RunWriter.start(landing_root, now())
    except FileExistsError as exc:
        raise RunAlreadyExists(f"a run with this timestamp already exists: {exc.filename}") from exc
    started = time.monotonic()
    log.info(
        "extract started",
        extra={
            "run_id": run.run_id,
            "countries": len(scope.countries),
            "indicators": len(scope.indicators),
            "years": f"{scope.years.start}-{scope.years.end}",
        },
    )
    warnings: list[str] = []

    fetched_countries = _fetch_and_land(client, run, endpoints.countries(scope), warnings)
    endpoints.check_countries(fetched_countries.items, scope)

    for code in scope.indicators:
        fetched_indicator = _fetch_and_land(client, run, endpoints.indicator(code), warnings)
        endpoints.check_indicator(fetched_indicator.items, code)

    for code in scope.indicators:
        request = endpoints.observations(code, scope, config.api.source)
        fetched = _fetch_and_land(client, run, request, warnings)
        endpoints.check_observations(fetched.items, code, scope)

    manifest = run.commit(
        committed_at=now(),
        pipeline_version=__version__,
        git_sha=git_sha,
        config=config.model_dump(mode="json"),
        warnings=warnings,
    )
    for warning in manifest.warnings:
        log.warning(warning, extra={"run_id": manifest.run_id})
    log.info(
        "run committed",
        extra={
            "run_id": manifest.run_id,
            "requests": len(manifest.requests),
            "files": len(manifest.files),
            "warnings": len(manifest.warnings),
            "duration_ms": round((time.monotonic() - started) * 1000),
        },
    )
    return manifest


def _fetch_and_land[T: BaseModel](
    client: Client, run: RunWriter, request: endpoints.Request[T], warnings: list[str]
) -> FetchResult[T]:
    """Fetch every page of `request` and land it, byte for byte, before anything checks it."""
    result = client.fetch(request.path, request.contract, request.params)
    for page in result.pages:
        run.write_page(
            endpoint=request.endpoint,
            key=request.key,
            page=page.page_number,
            body=page.body,
            url=page.url,
            fetched_at=page.fetched_at,
        )
    meta = result.pages[0].parsed.meta
    run.record_request(
        RequestRecord(
            endpoint=request.endpoint,
            key=request.key,
            pages=len(result.pages),
            total=meta.total,
            lastupdated=meta.lastupdated,
        )
    )
    warnings.extend(result.warnings)
    return result
