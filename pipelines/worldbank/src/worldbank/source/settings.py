"""World Bank settings: how to talk to the API and which scope to fetch (ADR-0002, NFR-4)."""

from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    model_validator,
)

CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
IndicatorCode = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]+(\.[A-Z0-9]+)+$")]


def _unique[T](values: list[T]) -> list[T]:
    duplicates = sorted({str(v) for v in values if values.count(v) > 1})
    if duplicates:
        raise ValueError(f"duplicate entries: {', '.join(duplicates)}")
    return values


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Timeout(_Model):
    connect_seconds: float = Field(gt=0)
    read_seconds: float = Field(gt=0)


class Retry(_Model):
    attempts: int = Field(ge=1)
    initial_backoff_seconds: float = Field(ge=0)
    max_backoff_seconds: float = Field(ge=0)

    @model_validator(mode="after")
    def _backoff_bounds(self) -> Self:
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError("max_backoff_seconds must be >= initial_backoff_seconds")
        return self


class Api(_Model):
    base_url: HttpUrl
    source: int = Field(ge=1)
    per_page: int = Field(ge=1, le=32_500)
    timeout: Timeout
    retry: Retry


class Years(_Model):
    start: int = Field(ge=1960)
    end: int = Field(le=2100)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start > self.end:
            raise ValueError("years.start must be <= years.end")
        return self

    def as_range(self) -> range:
        return range(self.start, self.end + 1)


class Scope(_Model):
    countries: Annotated[list[CountryCode], Field(min_length=1), AfterValidator(_unique)]
    indicators: Annotated[list[IndicatorCode], Field(min_length=1), AfterValidator(_unique)]
    years: Years


class Config(_Model):
    """The pipeline's whole configuration (`config.yml`): how to call the API and what to fetch."""

    api: Api
    scope: Scope
