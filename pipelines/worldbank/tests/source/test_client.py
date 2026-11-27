import json
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from typing import Any

import pytest
import requests
import responses
from responses import matchers

from worldbank.source.client import (
    Client,
    InconsistentPages,
    NetworkError,
    PermanentHTTPError,
    TransientHTTPError,
)
from worldbank.source.contracts import ApiErrorResponse, Observation
from worldbank.source.errors import ExtractError
from worldbank.source.settings import Api

BASE = "https://api.worldbank.org/v2"
PATH = "country/BRA;IND/indicator/SP.POP.TOTL"
URL = f"{BASE}/{PATH}"


def api(**overrides: Any) -> Api:
    raw: dict[str, Any] = {
        "base_url": BASE,
        "source": 2,
        "per_page": 2,
        "timeout": {"connect_seconds": 10, "read_seconds": 30},
        "retry": {"attempts": 3, "initial_backoff_seconds": 1, "max_backoff_seconds": 4},
    }
    raw.update(overrides)
    return Api.model_validate(raw)


def row(country: str, year: int) -> dict[str, Any]:
    return {
        "indicator": {"id": "SP.POP.TOTL", "value": "Population, total"},
        "country": {"id": country[:2], "value": country},
        "countryiso3code": country,
        "date": str(year),
        "value": 1000 + year,
        "unit": "",
        "obs_status": "",
        "decimal": 0,
    }


def page_body(
    page: int, pages: int, total: int, rows: list[dict[str, Any]], lastupdated: str = "2026-11-11"
) -> str:
    meta = {
        "page": page,
        "pages": pages,
        "per_page": 2,
        "total": total,
        "sourceid": "2",
        "lastupdated": lastupdated,
    }
    return json.dumps([meta, rows])


def add_page(page: int, body: str, status: int = 200) -> None:
    responses.add(
        responses.GET,
        URL,
        body=body,
        status=status,
        match=[
            matchers.query_param_matcher(
                {"format": "json", "per_page": "2", "page": str(page), "source": "2"}
            )
        ],
    )


class Sleeps:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def client(sleeps: Sleeps | None = None, **api_overrides: Any) -> Client:
    return Client(api(**api_overrides), sleep=sleeps or Sleeps())


@responses.activate
def test_follows_every_page_and_keeps_exact_bytes() -> None:
    bodies = [
        page_body(1, 3, 5, [row("BRA", 2023), row("BRA", 2024)]),
        page_body(2, 3, 5, [row("IND", 2023), row("IND", 2024)]),
        page_body(3, 3, 5, [row("BRA", 2022)]),
    ]
    for number, body in enumerate(bodies, start=1):
        add_page(number, body)

    result = client().fetch(PATH, Observation, {"source": 2})

    assert [p.page_number for p in result.pages] == [1, 2, 3]
    assert [p.body.decode() for p in result.pages] == bodies
    assert len(result.items) == 5
    assert "page=2" in result.pages[1].url
    assert responses.calls[0].request.headers["User-Agent"].startswith("worldbank-pipeline/")


@responses.activate
def test_retries_transient_errors_then_succeeds() -> None:
    add_page(1, "busy", status=503)
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))
    sleeps = Sleeps()

    result = client(sleeps).fetch(PATH, Observation, {"source": 2})

    assert len(result.items) == 1
    assert len(responses.calls) == 2
    assert len(sleeps.calls) == 1


@responses.activate
def test_retries_connection_errors() -> None:
    responses.add(responses.GET, URL, body=requests.ConnectionError("reset"))
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))

    assert len(client().fetch(PATH, Observation, {"source": 2}).items) == 1


@responses.activate
def test_a_network_failure_that_outlasts_the_retries_is_an_extract_error() -> None:
    for _ in range(3):
        responses.add(responses.GET, URL, body=requests.ConnectionError("reset"))

    with pytest.raises(NetworkError, match="reset") as caught:
        client().fetch(PATH, Observation, {"source": 2})
    assert isinstance(caught.value, ExtractError)


@responses.activate
def test_gives_up_after_configured_attempts() -> None:
    for _ in range(3):
        add_page(1, "rate limited", status=429)
    sleeps = Sleeps()

    with pytest.raises(TransientHTTPError, match="429"):
        client(sleeps).fetch(PATH, Observation, {"source": 2})
    assert len(responses.calls) == 3
    assert len(sleeps.calls) == 2


@responses.activate
def test_backoff_never_exceeds_the_configured_maximum() -> None:
    for _ in range(3):
        add_page(1, "busy", status=500)
    sleeps = Sleeps()

    with pytest.raises(TransientHTTPError):
        client(sleeps).fetch(PATH, Observation, {"source": 2})
    assert all(0 <= s <= 4 for s in sleeps.calls)


@responses.activate
def test_client_errors_are_not_retried() -> None:
    add_page(1, "not found", status=404)

    with pytest.raises(PermanentHTTPError, match="404"):
        client().fetch(PATH, Observation, {"source": 2})
    assert len(responses.calls) == 1


@responses.activate
def test_error_bodies_are_not_retried() -> None:
    add_page(1, json.dumps([{"message": [{"id": "120", "key": "Invalid value", "value": "bad"}]}]))

    with pytest.raises(ApiErrorResponse):
        client().fetch(PATH, Observation, {"source": 2})
    assert len(responses.calls) == 1


@responses.activate
def test_refetches_once_when_pages_disagree() -> None:
    add_page(1, page_body(1, 2, 3, [row("BRA", 2023), row("BRA", 2024)], lastupdated="2026-11-11"))
    add_page(2, page_body(2, 2, 3, [row("IND", 2024)], lastupdated="2026-12-01"))
    add_page(1, page_body(1, 2, 3, [row("BRA", 2023), row("BRA", 2024)], lastupdated="2026-12-01"))
    add_page(2, page_body(2, 2, 3, [row("IND", 2024)], lastupdated="2026-12-01"))

    result = client().fetch(PATH, Observation, {"source": 2})

    assert len(responses.calls) == 4
    assert {
        p.parsed.meta.lastupdated.isoformat() for p in result.pages if p.parsed.meta.lastupdated
    } == {"2026-12-01"}


@responses.activate
def test_fails_when_pages_still_disagree() -> None:
    for _ in range(2):
        add_page(
            1, page_body(1, 2, 3, [row("BRA", 2023), row("BRA", 2024)], lastupdated="2026-11-11")
        )
        add_page(2, page_body(2, 2, 3, [row("IND", 2024)], lastupdated="2026-12-01"))

    with pytest.raises(InconsistentPages, match="disagree"):
        client().fetch(PATH, Observation, {"source": 2})


@responses.activate
def test_fails_when_rows_do_not_add_up_to_total() -> None:
    add_page(1, page_body(1, 1, 3, [row("BRA", 2024)]))

    with pytest.raises(InconsistentPages, match="received 1 rows, API reported 3"):
        client().fetch(PATH, Observation, {"source": 2})


@responses.activate
def test_empty_result_is_one_page_with_no_items() -> None:
    meta = {
        "page": 1,
        "pages": 1,
        "per_page": 2,
        "total": 0,
        "sourceid": "2",
        "lastupdated": "2026-11-11",
    }
    add_page(1, json.dumps([meta, None]))

    assert client().fetch(PATH, Observation, {"source": 2}).items == []


class RecordingSession(requests.Session):
    def __init__(self) -> None:
        super().__init__()
        self.kwargs: list[dict[str, Any]] = []

    def get(self, url: str | bytes, **kwargs: Any) -> requests.Response:
        self.kwargs.append(kwargs)
        return super().get(url, **kwargs)


@responses.activate
def test_configured_timeouts_are_sent_on_every_request() -> None:
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))
    session = RecordingSession()

    Client(api(), session=session, sleep=Sleeps()).fetch(PATH, Observation, {"source": 2})

    assert session.kwargs[0]["timeout"] == (10, 30)


@responses.activate
def test_read_timeouts_are_retried() -> None:
    responses.add(responses.GET, URL, body=requests.Timeout("read timed out"))
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))

    assert len(client().fetch(PATH, Observation, {"source": 2}).items) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 410])
@responses.activate
def test_no_client_error_is_retried(status: int) -> None:
    add_page(1, "nope", status=status)

    with pytest.raises(PermanentHTTPError, match=str(status)):
        client().fetch(PATH, Observation, {"source": 2})
    assert len(responses.calls) == 1


@pytest.mark.parametrize("status", [500, 502, 503, 504])
@responses.activate
def test_every_server_error_is_retried(status: int) -> None:
    add_page(1, "busy", status=status)
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))

    assert len(client().fetch(PATH, Observation, {"source": 2}).items) == 1


@responses.activate
def test_callers_cannot_override_paging_parameters() -> None:
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))

    client().fetch(PATH, Observation, {"source": 2, "format": "xml", "page": 9, "per_page": 1})

    query = str(responses.calls[0].request.url)
    assert "format=json" in query and "page=1" in query and "per_page=2" in query


@responses.activate
def test_base_url_trailing_slash_and_leading_path_slash_are_tolerated() -> None:
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))

    result = Client(api(base_url=BASE + "/"), sleep=Sleeps()).fetch(
        "/" + PATH, Observation, {"source": 2}
    )

    assert len(result.items) == 1


@responses.activate
def test_each_page_records_its_final_url_and_utc_fetch_time() -> None:
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))

    [page] = client().fetch(PATH, Observation, {"source": 2}).pages

    assert page.url.startswith(URL + "?") and "source=2" in page.url
    assert page.fetched_at.utcoffset() == timedelta(0)


@responses.activate
def test_warnings_are_collected_across_pages_without_duplicates() -> None:
    extra = {**row("BRA", 2024), "footnote": "x"}
    add_page(1, page_body(1, 2, 2, [extra]))
    add_page(2, page_body(2, 2, 2, [{**row("IND", 2024), "footnote": "y"}]))

    result = client().fetch(PATH, Observation, {"source": 2})

    assert result.warnings == ["unknown field in response: Observation.footnote"]


def add_rate_limit(retry_after: str) -> None:
    responses.add(
        responses.GET, URL, body="slow down", status=429, headers={"Retry-After": retry_after}
    )


@pytest.mark.parametrize(
    ("retry_after", "expected"),
    [("3", 3.0), ("60", 4.0)],  # honoured, but never beyond max_backoff_seconds (4)
)
@responses.activate
def test_retry_after_seconds_are_honoured_up_to_the_maximum(
    retry_after: str, expected: float
) -> None:
    add_rate_limit(retry_after)
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))
    sleeps = Sleeps()

    client(sleeps).fetch(PATH, Observation, {"source": 2})

    assert sleeps.calls == [expected]


@responses.activate
def test_retry_after_as_an_http_date_is_honoured() -> None:
    in_three_seconds = datetime.now(UTC) + timedelta(seconds=3)
    add_rate_limit(format_datetime(in_three_seconds, usegmt=True))
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))
    sleeps = Sleeps()

    client(sleeps).fetch(PATH, Observation, {"source": 2})

    [slept] = sleeps.calls
    assert 2.0 <= slept <= 3.0


@responses.activate
def test_an_unreadable_retry_after_falls_back_to_the_backoff() -> None:
    add_rate_limit("soon")
    add_page(1, page_body(1, 1, 1, [row("BRA", 2024)]))
    sleeps = Sleeps()

    client(sleeps).fetch(PATH, Observation, {"source": 2})

    [slept] = sleeps.calls
    assert 1.0 <= slept <= 2.0  # first exponential step with jitter
