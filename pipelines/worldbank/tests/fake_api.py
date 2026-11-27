"""A fake World Bank API that answers any scope, for configuration-driven tests (NFR-4).

The recorded responses (ADR-0012) only match the recorded scope's exact URLs. This fake answers
any countries, indicators and years with deterministic values that are consistent with each
other: GDP per capita is exactly GDP / population, so the consistency check (ADR-0010) holds.
"""

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import parse_qs, urlsplit

import requests
import responses

POP, GDP, GDP_PER_CAPITA, LIFE_EXPECTANCY = (
    "SP.POP.TOTL",
    "NY.GDP.MKTP.CD",
    "NY.GDP.PCAP.CD",
    "SP.DYN.LE00.IN",
)
INCOME_GROUPS = [("LMC", "Lower middle income"), ("UMC", "Upper middle income")]


def _seed(code: str) -> int:
    return sum(ord(character) for character in code)


def value(indicator: str, country: str, year: int) -> float:
    population = _seed(country) * 100_000 + year
    if indicator == POP:
        return float(population)
    if indicator == GDP:
        return float(population * _seed(country))
    if indicator == GDP_PER_CAPITA:
        return float(_seed(country))  # = GDP / population, exactly
    if indicator == LIFE_EXPECTANCY:
        return 60 + _seed(country) % 20 + (year - 2000) / 10
    return float(_seed(indicator) * year)


def _page(rows: list[dict[str, Any]]) -> tuple[int, dict[str, str], str]:
    meta = {
        "page": 1,
        "pages": 1,
        "per_page": 1000,
        "total": len(rows),
        "lastupdated": "2026-11-11",
    }
    return 200, {}, json.dumps([meta, rows])


def _countries(codes: list[str]) -> tuple[int, dict[str, str], str]:
    def row(code: str) -> dict[str, Any]:
        group_id, group_name = INCOME_GROUPS[_seed(code) % len(INCOME_GROUPS)]
        return {
            "id": code,
            "iso2Code": code[:2],
            "name": f"Country {code}",
            "region": {"id": "WLD", "iso2code": "1W", "value": "World"},
            "incomeLevel": {"id": group_id, "iso2code": "XX", "value": group_name},
        }

    return _page([row(code) for code in codes])


def _indicator(code: str) -> tuple[int, dict[str, str], str]:
    source = {"id": "2", "value": "World Development Indicators"}
    return _page([{"id": code, "name": f"Indicator {code}", "unit": "", "source": source}])


def _observations(
    codes: list[str], indicator: str, years: range
) -> tuple[int, dict[str, str], str]:
    rows = [
        {
            "indicator": {"id": indicator, "value": f"Indicator {indicator}"},
            "country": {"id": code[:2], "value": f"Country {code}"},
            "countryiso3code": code,
            "date": str(year),
            "value": value(indicator, code, year),
            "decimal": 0,
        }
        for code in codes
        for year in years
    ]
    return _page(rows)


def _answer(request: requests.PreparedRequest) -> tuple[int, dict[str, str], str]:
    parts = urlsplit(str(request.url))
    path = parts.path.split("/v2/", 1)[1]
    observations = re.fullmatch(r"country/([^/]+)/indicator/([^/]+)", path)
    if observations:
        start, end = parse_qs(parts.query)["date"][0].split(":")
        codes, indicator = observations.group(1).split(";"), observations.group(2)
        return _observations(codes, indicator, range(int(start), int(end) + 1))
    if path.startswith("country/"):
        return _countries(path.removeprefix("country/").split(";"))
    return _indicator(path.removeprefix("indicator/"))


@contextmanager
def fake_world_bank(base_url: str) -> Iterator[None]:
    """Serve every request under `base_url` from the fake, for the duration of the block."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        mock.add_callback(responses.GET, re.compile(re.escape(base_url) + r"/.*"), _answer)
        yield
