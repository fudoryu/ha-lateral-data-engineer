"""Crafted scenarios built from the recorded API responses (ADR-0012).

`RecordedApi` starts from the exact recorded bodies and lets a test change one thing (a null value,
a missing row, a revised value, a failing page, a torn pagination) before serving them through a
`responses` mock. Every scenario therefore reads as "real data, except ...".
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import requests
import responses
from responses import matchers

Payload = list[Any]


class RecordedApi:
    def __init__(self, recorded_dir: Path, index: dict[str, Any]) -> None:
        self._urls: dict[str, str] = {e["file"]: e["url"] for e in index["files"]}
        self._bodies: dict[str, bytes] = {
            e["file"]: (recorded_dir / e["file"]).read_bytes() for e in index["files"]
        }
        self._failures: dict[str, list[int | Exception | bytes]] = {}

    # --- reading -------------------------------------------------------------------------------

    def files(self, prefix: str = "") -> list[str]:
        return sorted(f for f in self._bodies if f.startswith(prefix))

    def observation_pages(self, indicator: str) -> list[str]:
        return self.files(f"endpoint=observations/{indicator}/")

    def payload(self, file: str) -> Payload:
        loaded: Payload = json.loads(self._bodies[file])
        return loaded

    def body(self, file: str) -> bytes:
        return self._bodies[file]

    def rows(self, indicator: str) -> list[dict[str, Any]]:
        return [row for f in self.observation_pages(indicator) for row in self.payload(f)[1] or []]

    # --- changing ------------------------------------------------------------------------------

    def set_payload(self, file: str, payload: Payload) -> None:
        self._bodies[file] = json.dumps(payload).encode()

    def set_body(self, file: str, body: bytes) -> None:
        self._bodies[file] = body

    def edit_rows(self, indicator: str, iso3: str, year: int, change: Any) -> None:
        """Apply `change(row) -> row | None` to one observation; None removes the row."""
        for file in self.observation_pages(indicator):
            meta, rows = self.payload(file)
            new_rows = []
            for row in rows or []:
                if row["countryiso3code"] == iso3 and row["date"] == str(year):
                    row = change(deepcopy(row))
                if row is not None:
                    new_rows.append(row)
            if new_rows != rows:
                self.set_payload(file, [meta, new_rows])

    def with_value(self, indicator: str, iso3: str, year: int, value: Any) -> None:
        self.edit_rows(indicator, iso3, year, lambda row: {**row, "value": value})

    def without_row(
        self, indicator: str, iso3: str, year: int, *, adjust_total: bool = True
    ) -> None:
        self.edit_rows(indicator, iso3, year, lambda row: None)
        if adjust_total:
            self.update_meta(self.observation_pages(indicator), total=lambda t: t - 1)

    def with_extra_row(
        self, indicator: str, row: dict[str, Any], *, adjust_total: bool = True
    ) -> None:
        last = self.observation_pages(indicator)[-1]
        meta, rows = self.payload(last)
        self.set_payload(last, [meta, [*(rows or []), row]])
        if adjust_total:
            self.update_meta(self.observation_pages(indicator), total=lambda t: t + 1)

    def update_meta(self, files: list[str], **changes: Any) -> None:
        for file in files:
            meta, rows = self.payload(file)
            for key, change in changes.items():
                meta[key] = change(meta[key]) if callable(change) else change
            self.set_payload(file, [meta, rows])

    def fail(self, file: str, *outcomes: int | Exception | bytes) -> None:
        """Serve each outcome once, in order, before the real body.

        An int is an HTTP status, an exception is raised by the transport, and bytes are served
        as a 200 body (for example a torn page that is correct on the next fetch).
        """
        self._failures.setdefault(file, []).extend(outcomes)

    # --- serving -------------------------------------------------------------------------------

    @contextmanager
    def serve(self) -> Iterator[responses.RequestsMock]:
        with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
            for file, url in self._urls.items():
                parts = urlsplit(url)
                base = f"{parts.scheme}://{parts.netloc}{parts.path}"
                match = [matchers.query_param_matcher(dict(parse_qsl(parts.query)))]
                for outcome in self._failures.get(file, []):
                    if isinstance(outcome, (Exception, bytes)):
                        mock.add(responses.GET, base, body=outcome, match=match)
                    else:
                        mock.add(responses.GET, base, body="failure", status=outcome, match=match)
                mock.add(responses.GET, base, body=self._bodies[file], match=match)
            yield mock


def connection_error() -> requests.ConnectionError:
    return requests.ConnectionError("connection reset by peer")
