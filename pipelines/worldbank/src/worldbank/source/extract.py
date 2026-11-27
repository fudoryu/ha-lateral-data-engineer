"""Extract: fetch the configured scope from the API and land it as one committed run.

Order (ADR-0002, ADR-0005):
1. Country metadata for all configured countries; every configured code must come back
   (an invalid code would otherwise look like missing data).
2. Indicator metadata, one request per configured indicator.
3. Observations, one request per indicator covering all configured countries and years,
   checked against the request: indicator, countries, years, no duplicate (country, year).

Every page is landed as it arrives. The manifest is written only if everything succeeds, so a
failed extract never produces a committed run (ADR-0007).
"""

from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from worldbank import __version__
from worldbank.config import Config
from worldbank.source.client import Client, FetchResult
from worldbank.source.contracts import Country, Indicator, Observation
from worldbank.source.errors import ExtractError
from worldbank.storage.manifest import Manifest, RequestRecord
from worldbank.storage.write import RunWriter


class ScopeViolation(ExtractError):
    """The API response doesn't match what was requested."""


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
    warnings: list[str] = []
    countries = ";".join(scope.countries)

    fetched_countries = client.fetch(f"country/{countries}", Country)
    _land(run, "countries", None, fetched_countries, warnings)
    returned = {c.id for c in fetched_countries.items}
    missing = sorted(set(scope.countries) - returned)
    if missing:
        raise ScopeViolation(f"unknown country codes in config: {', '.join(missing)}")
    unrequested = sorted(returned - set(scope.countries))
    if unrequested:
        raise ScopeViolation(f"country metadata outside the request: {', '.join(unrequested)}")

    for code in scope.indicators:
        fetched_indicator = client.fetch(f"indicator/{code}", Indicator)
        _land(run, "indicators", code, fetched_indicator, warnings)
        if [i.id for i in fetched_indicator.items] != [code]:
            raise ScopeViolation(f"unknown indicator code in config: {code}")

    years = scope.years
    for code in scope.indicators:
        fetched = client.fetch(
            f"country/{countries}/indicator/{code}",
            Observation,
            {"date": f"{years.start}:{years.end}", "source": config.api.source},
        )
        _land(run, "observations", code, fetched, warnings)
        _check_observations(code, fetched.items, set(scope.countries), set(years.as_range()))

    return run.commit(
        committed_at=now(),
        pipeline_version=__version__,
        git_sha=git_sha,
        config=config.model_dump(mode="json"),
        warnings=warnings,
    )


def _land[T: BaseModel](
    run: RunWriter, endpoint: str, key: str | None, result: FetchResult[T], warnings: list[str]
) -> None:
    for page in result.pages:
        run.write_page(
            endpoint=endpoint,
            key=key,
            page=page.page_number,
            body=page.body,
            url=page.url,
            fetched_at=page.fetched_at,
        )
    meta = result.pages[0].parsed.meta
    run.record_request(
        RequestRecord(
            endpoint=endpoint,
            key=key,
            pages=len(result.pages),
            total=meta.total,
            lastupdated=meta.lastupdated,
        )
    )
    warnings.extend(result.warnings)


def _check_observations(
    code: str, rows: list[Observation], countries: set[str], years: set[int]
) -> None:
    wrong_indicator = sorted({r.indicator.id for r in rows} - {code})
    if wrong_indicator:
        raise ScopeViolation(f"{code}: response contains other indicators: {wrong_indicator}")

    extra_countries = sorted({r.countryiso3code for r in rows} - countries)
    if extra_countries:
        raise ScopeViolation(f"{code}: countries outside the request: {extra_countries}")

    extra_years = sorted({int(r.date) for r in rows} - years)
    if extra_years:  # the API ignores date filters it can't satisfy (source-system §4)
        raise ScopeViolation(f"{code}: years outside the request: {extra_years}")

    duplicates = [k for k, n in Counter((r.countryiso3code, r.date) for r in rows).items() if n > 1]
    if duplicates:
        raise ScopeViolation(f"{code}: duplicate country-years: {sorted(duplicates)}")
