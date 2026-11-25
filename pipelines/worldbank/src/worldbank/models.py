"""World Bank API response models and envelope parsing (ADR-0005).

Responses are a two-element array `[meta, data]`, or an error body returned with HTTP 200
(docs/source-system.md §2-§3). Models are tolerant readers: strict on the fields the pipeline
relies on, lax where the API is inconsistent, and they allow unknown fields, which are reported
as warnings rather than errors.
"""

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictFloat,
    StrictInt,
    StringConstraints,
    ValidationError,
)

Iso3 = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
Year = Annotated[str, StringConstraints(pattern=r"^\d{4}$")]


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class Meta(_Model):
    page: int  # lax on purpose: per_page is "50" on some endpoints, 50 on others
    pages: int
    per_page: int
    total: int
    sourceid: str | None = None
    lastupdated: date | None = None


class Ref(_Model):
    id: str
    value: str


class CodedRef(Ref):
    iso2code: str


class Observation(_Model):
    indicator: Ref
    country: Ref  # country.id is ISO2; the ISO3 business key is countryiso3code
    countryiso3code: Iso3
    date: Year
    value: StrictInt | StrictFloat | None  # never coerced: "" or "N/A" must not become 0 (NFR-3)
    unit: str | None = None
    obs_status: str | None = None
    decimal: int | None = None


class Country(_Model):
    id: Iso3
    iso2Code: str
    name: str
    region: CodedRef
    incomeLevel: CodedRef


class Indicator(_Model):
    id: str
    name: str
    unit: str | None = None
    source: Ref
    sourceNote: str | None = None
    sourceOrganization: str | None = None


class ApiErrorResponse(Exception):
    """The API returned an error body (often with HTTP 200). Not retryable."""

    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = messages
        details = "; ".join(f"{m.get('id')} {m.get('key')}: {m.get('value')}" for m in messages)
        super().__init__(f"World Bank API error: {details}")


class UnexpectedResponse(Exception):
    """The response is neither a page nor a recognizable error body. Not retryable."""


@dataclass(frozen=True)
class Page[T: BaseModel]:
    meta: Meta
    items: list[T]
    warnings: list[str] = field(default_factory=list)


def parse_page[T: BaseModel](body: bytes, item_model: type[T]) -> Page[T]:
    """Classify a response body and validate it against `item_model`.

    Raises ApiErrorResponse for error bodies and UnexpectedResponse for anything else that is
    not a well-formed page, including field-contract violations.
    """
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise UnexpectedResponse(f"response is not valid JSON: {exc}") from exc

    if (
        isinstance(payload, list)
        and len(payload) == 1
        and isinstance(payload[0], dict)
        and "message" in payload[0]
    ):
        raise ApiErrorResponse(list(payload[0]["message"]))

    if not (
        isinstance(payload, list)
        and len(payload) == 2
        and isinstance(payload[0], dict)
        and (payload[1] is None or isinstance(payload[1], list))
    ):
        raise UnexpectedResponse("expected a [meta, data] array")

    try:
        meta = Meta.model_validate(payload[0])
        items = [item_model.model_validate(item) for item in payload[1] or []]
    except ValidationError as exc:
        raise UnexpectedResponse(
            f"response violates the {item_model.__name__} contract: {exc}"
        ) from exc

    return Page(meta=meta, items=items, warnings=_unknown_fields(meta, items))


def _unknown_fields(meta: Meta, items: list[Any]) -> list[str]:
    found: set[str] = set()
    for model in [meta, *items]:
        found.update(f"{type(model).__name__}.{key}" for key in (model.model_extra or {}))
    return [f"unknown field in response: {name}" for name in sorted(found)]
