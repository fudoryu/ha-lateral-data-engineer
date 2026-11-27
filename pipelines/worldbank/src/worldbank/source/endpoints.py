"""The World Bank endpoints this pipeline uses: each one's request, contract and scope check.

Everything the pipeline knows about an endpoint lives here (ADR-0002, ADR-0005): how to ask for
it, which contract its rows must meet, and how to prove a response answers its request. An
endpoint's name is also its landing folder (`endpoint=<name>`) and what dbt staging selects on,
so renaming one breaks both.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from worldbank.source.config import Scope
from worldbank.source.contracts import Country, Indicator, Observation
from worldbank.source.errors import ExtractError


class ScopeViolation(ExtractError):
    """The API response doesn't match what was requested."""


@dataclass(frozen=True)
class Request[T: BaseModel]:
    """One API request: where its pages land, what to fetch, and the contract its rows meet."""

    endpoint: str
    key: str | None
    path: str
    contract: type[T]
    params: dict[str, Any] = field(default_factory=dict)


# --- countries: metadata for every configured country, in one request --------------------------


def countries(scope: Scope) -> Request[Country]:
    return Request("countries", None, f"country/{';'.join(scope.countries)}", Country)


def check_countries(rows: list[Country], scope: Scope) -> None:
    """Every configured code must come back, or an invalid one would look like missing data."""
    returned = {country.id for country in rows}
    missing = sorted(set(scope.countries) - returned)
    if missing:
        raise ScopeViolation(f"unknown country codes in config: {', '.join(missing)}")
    unrequested = sorted(returned - set(scope.countries))
    if unrequested:
        raise ScopeViolation(f"country metadata outside the request: {', '.join(unrequested)}")


# --- indicators: metadata for one configured indicator -----------------------------------------


def indicator(code: str) -> Request[Indicator]:
    return Request("indicators", code, f"indicator/{code}", Indicator)


def check_indicator(rows: list[Indicator], code: str) -> None:
    if [row.id for row in rows] != [code]:
        raise ScopeViolation(f"unknown indicator code in config: {code}")


# --- observations: one indicator for every configured country and year (ADR-0002) -------------


def observations(code: str, scope: Scope, source: int) -> Request[Observation]:
    return Request(
        "observations",
        code,
        f"country/{';'.join(scope.countries)}/indicator/{code}",
        Observation,
        {"date": f"{scope.years.start}:{scope.years.end}", "source": source},
    )


def check_observations(rows: list[Observation], code: str, scope: Scope) -> None:
    """The response holds only the requested indicator, countries and years, each pair once."""
    wrong_indicator = sorted({row.indicator.id for row in rows} - {code})
    if wrong_indicator:
        raise ScopeViolation(f"{code}: response contains other indicators: {wrong_indicator}")

    extra_countries = sorted({row.countryiso3code for row in rows} - set(scope.countries))
    if extra_countries:
        raise ScopeViolation(f"{code}: countries outside the request: {extra_countries}")

    extra_years = sorted({int(row.date) for row in rows} - set(scope.years.as_range()))
    if extra_years:  # the API ignores date filters it can't satisfy (source-system §4)
        raise ScopeViolation(f"{code}: years outside the request: {extra_years}")

    pairs = Counter((row.countryiso3code, row.date) for row in rows)
    duplicates = sorted(pair for pair, count in pairs.items() if count > 1)
    if duplicates:
        raise ScopeViolation(f"{code}: duplicate country-years: {duplicates}")
