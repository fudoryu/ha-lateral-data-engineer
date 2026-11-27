"""HTTP client for the World Bank API: timeouts, retries, and paging (ADR-0002, ADR-0005, ADR-0007).

Only transient failures are retried (timeouts, connection errors, HTTP 429 and 5xx). Error bodies,
other HTTP errors, and contract violations fail immediately. Every request is followed through all
of its pages; if pages disagree on `lastupdated` or `total` (the source changed mid-request), the
whole request is fetched again once and fails if it still disagrees.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

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
    """A failure worth retrying: HTTP 429 or 5xx."""


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
    def __init__(
        self,
        api: Api,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api = api
        self._session = session or requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT
        self._sleep = sleep

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
            fetched_at=datetime.now(UTC),
            parsed=parse_page(response.content, item_model),  # error bodies raise, never retried
        )

    def _get_with_retries(self, url: str, params: dict[str, Any]) -> requests.Response:
        retry = self._api.retry
        retrying = Retrying(
            stop=stop_after_attempt(retry.attempts),
            wait=wait_exponential_jitter(
                multiplier=retry.initial_backoff_seconds, max=retry.max_backoff_seconds
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
            raise TransientHTTPError(f"HTTP {response.status_code} from {response.url}")
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
