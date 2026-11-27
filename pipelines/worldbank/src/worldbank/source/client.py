"""HTTP client for the World Bank API: timeouts, retries, and paging (ADR-0002, ADR-0005, ADR-0007).

Only transient failures are retried (timeouts, connection errors, HTTP 429 and 5xx), with
exponential backoff and jitter; when the server sends `Retry-After`, the client waits at least
that long, capped by the configured maximum backoff so a run stays bounded. Error bodies,
other HTTP errors, and contract violations fail immediately. Every request is followed through all
of its pages; if pages disagree on `lastupdated` or `total` (the source changed mid-request), the
whole request is fetched again once and fails if it still disagrees.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Self

import requests
from pydantic import BaseModel
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from worldbank import __version__
from worldbank.source.contracts import Page, parse_page
from worldbank.source.errors import ExtractError
from worldbank.source.settings import Api

USER_AGENT = f"worldbank-pipeline/{__version__}"

log = logging.getLogger(__name__)


class NetworkError(ExtractError):
    """A connection failure or timeout that outlasted every retry."""


class TransientHTTPError(ExtractError):
    """A failure worth retrying: HTTP 429 or 5xx, with the server's `Retry-After` if it sent one."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class PermanentHTTPError(ExtractError):
    """An HTTP error that retrying won't fix (4xx other than 429)."""


class InconsistentPages(ExtractError):
    """Pages of one request disagree, or don't add up to the reported total."""


@dataclass(frozen=True)
class FetchedPage[T: BaseModel]:
    """One response page: the exact bytes (for landing) and its parsed form."""

    url: str
    page_number: int
    body: bytes
    fetched_at: datetime
    parsed: Page[T]


@dataclass(frozen=True)
class FetchResult[T: BaseModel]:
    """All pages of one request."""

    pages: list[FetchedPage[T]]

    @property
    def items(self) -> list[T]:
        return [item for page in self.pages for item in page.parsed.items]

    @property
    def warnings(self) -> list[str]:
        return sorted({w for page in self.pages for w in page.parsed.warnings})


class Client:
    """Fetches World Bank requests page by page. Use it as a context manager, or call `close`.

    `sleep` and `clock` are injectable so tests can skip waits and fix fetch times.
    """

    def __init__(
        self,
        api: Api,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._api = api
        self._owns_session = session is None
        self._session = session or requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT
        self._sleep = sleep
        self._clock = clock

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP session, unless the caller passed one in and still owns it."""
        if self._owns_session:
            self._session.close()

    def fetch[T: BaseModel](
        self, path: str, item_model: type[T], params: dict[str, Any] | None = None
    ) -> FetchResult[T]:
        """Fetch every page of `path`, retrying transient failures and checking consistency."""
        started = time.monotonic()
        result = self._fetch_all_pages(path, item_model, params or {})
        if not _consistent(result):
            log.warning("pages disagree, refetching the request", extra={"path": path})
            result = self._fetch_all_pages(path, item_model, params or {})
            if not _consistent(result):
                raise InconsistentPages(f"pages of {path} disagree on lastupdated or total")

        expected = result.pages[0].parsed.meta.total
        received = len(result.items)
        if received != expected:
            raise InconsistentPages(f"{path}: received {received} rows, API reported {expected}")
        log.info(
            "request fetched",
            extra={
                "path": path,
                "pages": len(result.pages),
                "rows": received,
                "lastupdated": result.pages[0].parsed.meta.lastupdated,
                "duration_ms": _elapsed_ms(started),
            },
        )
        return result

    def _fetch_all_pages[T: BaseModel](
        self, path: str, item_model: type[T], params: dict[str, Any]
    ) -> FetchResult[T]:
        first = self._fetch_page(path, item_model, params, page_number=1)
        pages = [first]
        for number in range(2, first.parsed.meta.pages + 1):
            pages.append(self._fetch_page(path, item_model, params, page_number=number))
        return FetchResult(pages)

    def _fetch_page[T: BaseModel](
        self, path: str, item_model: type[T], params: dict[str, Any], page_number: int
    ) -> FetchedPage[T]:
        query = {**params, "format": "json", "per_page": self._api.per_page, "page": page_number}
        url = f"{str(self._api.base_url).rstrip('/')}/{path.lstrip('/')}"
        started = time.monotonic()
        response = self._get_with_retries(url, query)
        log.debug(
            "page fetched",
            extra={
                "url": response.url,
                "page": page_number,
                "status": response.status_code,
                "bytes": len(response.content),
                "duration_ms": _elapsed_ms(started),
            },
        )
        return FetchedPage(
            url=response.url,
            page_number=page_number,
            body=response.content,
            fetched_at=self._clock(),
            parsed=parse_page(response.content, item_model),  # error bodies raise, never retried
        )

    def _get_with_retries(self, url: str, params: dict[str, Any]) -> requests.Response:
        retry = self._api.retry
        retrying = Retrying(
            stop=stop_after_attempt(retry.attempts),
            wait=_wait_honouring_retry_after(
                wait_exponential_jitter(
                    multiplier=retry.initial_backoff_seconds, max=retry.max_backoff_seconds
                ),
                retry.max_backoff_seconds,
            ),
            retry=retry_if_exception_type(
                (TransientHTTPError, requests.ConnectionError, requests.Timeout)
            ),
            sleep=self._sleep,
            before_sleep=_log_retry,
            reraise=True,
        )
        try:
            return retrying(self._get, url, params)
        except requests.RequestException as exc:
            raise NetworkError(f"{url}: {exc}") from exc

    def _get(self, url: str, params: dict[str, Any]) -> requests.Response:
        timeout = (self._api.timeout.connect_seconds, self._api.timeout.read_seconds)
        response = self._session.get(url, params=params, timeout=timeout)
        if response.status_code == 429 or response.status_code >= 500:
            raise TransientHTTPError(
                f"HTTP {response.status_code} from {response.url}",
                retry_after=_retry_after_seconds(response.headers.get("Retry-After")),
            )
        if response.status_code >= 400:
            raise PermanentHTTPError(f"HTTP {response.status_code} from {response.url}")
        return response


def _consistent(result: FetchResult[Any]) -> bool:
    metas = [page.parsed.meta for page in result.pages]
    return len({(m.lastupdated, m.total) for m in metas}) == 1


def _log_retry(state: RetryCallState) -> None:
    failure = state.outcome.exception() if state.outcome else None
    log.warning(
        "retrying request",
        extra={
            "url": state.args[0],
            "attempt": state.attempt_number,
            "wait_seconds": round(state.next_action.sleep, 2) if state.next_action else None,
            "reason": str(failure),
        },
    )


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


def _wait_honouring_retry_after(
    backoff: Callable[[RetryCallState], float], maximum: float
) -> Callable[[RetryCallState], float]:
    """Wait the backoff, or longer if the server asked to with `Retry-After`, up to `maximum`."""

    def wait(state: RetryCallState) -> float:
        failure = state.outcome.exception() if state.outcome else None
        asked = failure.retry_after if isinstance(failure, TransientHTTPError) else None
        return min(max(backoff(state), asked or 0.0), maximum)

    return wait


def _retry_after_seconds(header: str | None) -> float | None:
    """`Retry-After` as seconds: either a number of seconds or an HTTP date (RFC 9110)."""
    if header is None:
        return None
    if header.strip().isdigit():
        return float(header)
    try:
        moment = parsedate_to_datetime(header)
    except TypeError, ValueError:
        return None  # unparseable: fall back to the backoff
    return max((moment - datetime.now(UTC)).total_seconds(), 0.0)
