import json
from typing import Any

import pytest

from worldbank.api.contracts import (
    ApiErrorResponse,
    Country,
    Indicator,
    Observation,
    UnexpectedResponse,
    parse_page,
)

META = {
    "page": 1,
    "pages": 1,
    "per_page": 1000,
    "total": 1,
    "sourceid": "2",
    "lastupdated": "2026-11-11",
}


def observation(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "indicator": {"id": "SP.POP.TOTL", "value": "Population, total"},
        "country": {"id": "BR", "value": "Brazil"},
        "countryiso3code": "BRA",
        "date": "2024",
        "value": 211998573,
        "unit": "",
        "obs_status": "",
        "decimal": 0,
    }
    row.update(overrides)
    return row


def body(payload: Any) -> bytes:
    return json.dumps(payload).encode()


def test_parses_an_observation_page() -> None:
    page = parse_page(body([META, [observation()]]), Observation)

    assert page.meta.total == 1
    assert page.meta.lastupdated is not None and page.meta.lastupdated.isoformat() == "2026-11-11"
    assert page.items[0].countryiso3code == "BRA"
    assert page.items[0].value == 211998573
    assert page.warnings == []


def test_meta_accepts_numeric_strings() -> None:
    """The country and indicator endpoints return per_page as a string (source-system §2)."""
    page = parse_page(body([{**META, "per_page": "50"}, []]), Observation)

    assert page.meta.per_page == 50


def test_null_value_stays_null() -> None:
    page = parse_page(body([META, [observation(value=None)]]), Observation)

    assert page.items[0].value is None


def test_null_data_array_is_an_empty_page() -> None:
    page = parse_page(body([{**META, "total": 0}, None]), Observation)

    assert page.items == []


@pytest.mark.parametrize("bad_value", ["", "N/A", "123", True])
def test_value_is_never_coerced(bad_value: object) -> None:
    with pytest.raises(UnexpectedResponse, match="Observation contract"):
        parse_page(body([META, [observation(value=bad_value)]]), Observation)


@pytest.mark.parametrize(
    ("field", "bad"),
    [("date", "2020Q1"), ("date", "20"), ("countryiso3code", "BR"), ("countryiso3code", "")],
)
def test_field_contracts_are_enforced(field: str, bad: str) -> None:
    with pytest.raises(UnexpectedResponse):
        parse_page(body([META, [observation(**{field: bad})]]), Observation)


def test_missing_required_field_fails() -> None:
    row = observation()
    del row["countryiso3code"]

    with pytest.raises(UnexpectedResponse):
        parse_page(body([META, [row]]), Observation)


def test_error_body_raises_api_error() -> None:
    """Invalid codes return HTTP 200 with an error body (source-system §3)."""
    error = [
        {
            "message": [
                {
                    "id": "120",
                    "key": "Invalid value",
                    "value": "The provided parameter value is not valid",
                }
            ]
        }
    ]

    with pytest.raises(ApiErrorResponse, match="120 Invalid value") as exc:
        parse_page(body(error), Observation)
    assert exc.value.messages[0]["id"] == "120"


@pytest.mark.parametrize(
    "raw",
    [
        b"<html>oops</html>",
        body({"page": 1}),
        body([META]),
        body([META, [], []]),
        body([META, {"x": 1}]),
    ],
)
def test_unexpected_shapes_fail(raw: bytes) -> None:
    with pytest.raises(UnexpectedResponse):
        parse_page(raw, Observation)


def test_unknown_fields_become_warnings() -> None:
    page = parse_page(body([{**META, "extra_meta": 1}, [observation(new_field="x")]]), Observation)

    assert page.items[0].countryiso3code == "BRA"
    assert page.warnings == [
        "unknown field in response: Meta.extra_meta",
        "unknown field in response: Observation.new_field",
    ]


def test_parses_country_metadata() -> None:
    country = {
        "id": "BRA",
        "iso2Code": "BR",
        "name": "Brazil",
        "region": {"id": "LCN", "iso2code": "ZJ", "value": "Latin America & Caribbean "},
        "adminregion": {
            "id": "LAC",
            "iso2code": "XJ",
            "value": "Latin America & Caribbean (excluding high income)",
        },
        "incomeLevel": {"id": "UMC", "iso2code": "XT", "value": "Upper middle income"},
        "lendingType": {"id": "IBD", "iso2code": "XF", "value": "IBRD"},
        "capitalCity": "Brasilia",
        "longitude": "-47.9292",
        "latitude": "-15.7801",
    }

    page = parse_page(body([{**META, "per_page": "50"}, [country]]), Country)

    assert page.items[0].incomeLevel.id == "UMC"
    assert page.warnings == []  # every field the live API sends is known
    assert (
        page.items[0].region.value == "Latin America & Caribbean "
    )  # kept raw; trimmed in staging


def test_parses_indicator_metadata() -> None:
    indicator = {
        "id": "SP.POP.TOTL",
        "name": "Population, total",
        "unit": "",
        "source": {"id": "2", "value": "World Development Indicators"},
        "sourceNote": "Total population is based on the de facto definition of population.",
        "sourceOrganization": "World Population Prospects, United Nations (UN).",
        "topics": [{"id": "8", "value": "Health "}],
    }

    page = parse_page(body([{**META, "per_page": "50"}, [indicator]]), Indicator)

    assert page.items[0].source.id == "2"
    assert page.warnings == []


def test_unknown_fields_in_nested_objects_become_warnings() -> None:
    row = observation(indicator={"id": "SP.POP.TOTL", "value": "Population, total", "brand_new": 1})

    page = parse_page(body([META, [row]]), Observation)

    assert page.warnings == ["unknown field in response: Observation.indicator.brand_new"]


@pytest.mark.parametrize("value", [0, -12.5, 1.5e13, 70.746, 211998573])
def test_numeric_values_are_kept_as_is(value: float) -> None:
    page = parse_page(body([META, [observation(value=value)]]), Observation)

    assert page.items[0].value == value


def test_invalid_lastupdated_fails() -> None:
    with pytest.raises(UnexpectedResponse):
        parse_page(body([{**META, "lastupdated": "yesterday"}, []]), Observation)


def test_every_error_message_is_reported() -> None:
    error = [
        {
            "message": [
                {
                    "id": "120",
                    "key": "Invalid value",
                    "value": "The provided parameter value is not valid",
                },
                {"id": "175", "key": "Invalid format", "value": "The indicator was not found"},
            ]
        }
    ]

    with pytest.raises(ApiErrorResponse, match=r"120 Invalid value.*175 Invalid format"):
        parse_page(body(error), Observation)


def test_lowercase_iso3_is_rejected() -> None:
    with pytest.raises(UnexpectedResponse):
        parse_page(body([META, [observation(countryiso3code="bra")]]), Observation)


def test_unicode_is_preserved() -> None:
    row = observation(country={"id": "CI", "value": "Côte d'Ivoire"})

    page = parse_page(json.dumps([META, [row]], ensure_ascii=False).encode(), Observation)

    assert page.items[0].country.value == "Côte d'Ivoire"
