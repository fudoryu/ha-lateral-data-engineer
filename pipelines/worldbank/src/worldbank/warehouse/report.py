"""Report: render the reporting tables of the published warehouse as an HTML dashboard.

Reads only the published warehouse's `reporting` schema, so the page shows audited answers
(ADR-0036). It's one self-contained, deterministic file: inline CSS and SVG, no external files,
no timestamp. The filters are native radio buttons and checkboxes, and CSS (`:has()`) shows the
selected indicator and countries, so filtering works without scripts; one small static script only
adds "all" and "none" buttons (ADR-0045). Every value from the warehouse is HTML-escaped, and none
reaches the script.
"""

import html
import logging
import math
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

import duckdb

from worldbank.warehouse.errors import WarehouseError

log = logging.getLogger(__name__)

Row = dict[str, Any]

REASONS = {
    "prior_out_of_scope": "first year",
    "current_missing": "no value",
    "prior_missing": "no prior value",
    "prior_zero": "prior was 0",
}
# Income groups from low to high income, for display only; any other group follows (ADR-0040).
INCOME_GROUP_ORDER = ("LIC", "LMC", "UMC", "HIC")
STATUS_TEXT = {
    "present": "present",
    "null_value": "returned as null",
    "missing_row": "not returned",
}


class NothingToReport(WarehouseError):
    """There's no published warehouse, or it lacks the reporting tables or their rows."""


def render_report(warehouse: Path, output: Path) -> Path:
    """Write the HTML dashboard of `warehouse`'s reporting tables to `output`; return its path."""
    if not warehouse.is_file():
        raise NothingToReport(f"{warehouse} doesn't exist; publish a build first")
    with duckdb.connect(str(warehouse), read_only=True) as con:
        try:
            tables = {name: _rows(con, name) for name in _TABLES}
        except duckdb.CatalogException as exc:
            raise NothingToReport(f"{warehouse} lacks a reporting table: {exc}") from exc
    if not tables["rpt_completeness"]:
        raise NothingToReport(f"{warehouse} has no expected values to report")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.name}.tmp")
    temporary.write_text(_page(_data(tables)), encoding="utf-8")
    temporary.replace(output)
    log.info("report rendered", extra={"path": str(output)})
    return output


_TABLES = {
    "rpt_completeness": "indicator_id, country_id, observation_year",
    "rpt_year_over_year": "indicator_id, country_id, observation_year",
    "rpt_latest_year": "indicator_id, country_id",
    "rpt_income_group_by_year": "indicator_id, income_group_id, observation_year",
}


def _rows(con: duckdb.DuckDBPyConnection, table: str) -> list[Row]:
    result = con.execute(f"SELECT * FROM reporting.{table} ORDER BY {_TABLES[table]}")
    columns = [description[0] for description in result.description]
    return [dict(zip(columns, values, strict=True)) for values in result.fetchall()]


# --- data ----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Data:
    """The reporting tables, indexed; the expected cells define the indicators, countries, years."""

    indicators: list[tuple[str, str]]  # (indicator_id, name), by name
    countries: list[tuple[str, str]]  # (country_id, name), by code
    years: list[int]
    cells: dict[tuple[str, str, int], Row]  # (indicator_id, country_id, year)
    changes: dict[tuple[str, str, int], Row]
    latest: dict[tuple[str, str], Row]  # (indicator_id, country_id)
    series: dict[tuple[str, str], Row]  # the series' status and its cells counted by status
    groups: dict[str, list[Row]]  # indicator_id -> income group rows

    def cell(self, indicator: str, country: str, year: int) -> Row:
        return self.cells.get((indicator, country, year)) or {}

    def index(self, country: str) -> int:
        return [code for code, _ in self.countries].index(country)


def _by_year(rows: list[Row]) -> dict[tuple[str, str, int], Row]:
    return {(r["indicator_id"], r["country_id"], r["observation_year"]): r for r in rows}


def _by_series(rows: list[Row]) -> dict[tuple[str, str], Row]:
    return {(r["indicator_id"], r["country_id"]): r for r in rows}


def _series(cells: list[Row]) -> dict[tuple[str, str], Row]:
    series: dict[tuple[str, str], Row] = {}
    for cell in cells:
        counts = series.setdefault(
            (cell["indicator_id"], cell["country_id"]),
            {"series_status": cell["series_status"], "n_expected": 0}
            | {f"n_{status}": 0 for status in STATUS_TEXT},
        )
        counts["n_expected"] += 1
        counts[f"n_{cell['value_status']}"] += 1
    return series


def _group_order(row: Row) -> tuple[int, str]:
    code = row["income_group_id"]
    known = code in INCOME_GROUP_ORDER
    return (INCOME_GROUP_ORDER.index(code) if known else len(INCOME_GROUP_ORDER), code)


def _data(tables: dict[str, list[Row]]) -> _Data:
    cells = tables["rpt_completeness"]
    groups: dict[str, list[Row]] = defaultdict(list)
    for row in tables["rpt_income_group_by_year"]:
        groups[row["indicator_id"]].append(row)
    return _Data(
        indicators=sorted(
            {(r["indicator_id"], r["indicator_name"]) for r in cells}, key=lambda i: (i[1], i[0])
        ),
        countries=sorted({(r["country_id"], r["country_name"]) for r in cells}),
        years=sorted({r["observation_year"] for r in cells}),
        cells=_by_year(cells),
        changes=_by_year(tables["rpt_year_over_year"]),
        latest=_by_series(tables["rpt_latest_year"]),
        series=_series(cells),
        groups=dict(groups),
    )


def _short_names(indicators: list[tuple[str, str]]) -> dict[str, str]:
    """Indicator names without unit or qualifier, for the filter; full names if that's ambiguous."""
    short = {code: re.split(r" \(|, ", name, maxsplit=1)[0] for code, name in indicators}
    if len(set(short.values())) < len(short):
        return dict(indicators)
    return short


# --- formatting ----------------------------------------------------------------------------------


def _e(value: object) -> str:
    return html.escape(str(value))


def _number(value: float | None) -> str:
    if value is None:
        return "—"
    for suffix, scale in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if abs(value) >= scale:
            return f"{value / scale:,.1f} {suffix}"
    return f"{value:,.1f}"


def _sign(value: float) -> str:
    return "+" if value > 0 else "&minus;" if value < 0 else ""


def _signed_number(value: float | None) -> str:
    return "—" if value is None else f"{_sign(value)}{_number(abs(value))}"


def _signed_percent(value: float) -> str:
    rounded = round(value, 1)
    return f"{_sign(rounded)}{abs(rounded):,.1f}%"


def _tick_label(value: float) -> str:
    return re.sub(r"\.0(?= |$)", "", _number(value))


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _countries(count: int) -> str:
    return f"{count} {'country' if count == 1 else 'countries'}"


def _coverage_text(cells: list[Row]) -> str:
    counts = Counter(c["value_status"] for c in cells)
    if counts["present"] == len(cells):
        return f"All {len(cells)} expected values are present"
    return (
        f"{counts['present']} of {len(cells)} expected values present: "
        f"{counts['null_value']} returned as null, {counts['missing_row']} not returned"
    )


def _change_text(change: Row, year: int) -> str:
    percent = change.get("percent_change")
    if percent is not None:
        return f"{_signed_percent(percent)} on {year - 1}"
    reason = change.get("null_change_reason")
    return _e(REASONS.get(reason or "", reason or "no change"))


def _runs(values: list[float | None]) -> list[list[tuple[int, float]]]:
    """Split a series at its gaps: each run is consecutive (index, value) pairs with a value."""
    runs: list[list[tuple[int, float]]] = [[]]
    for i, value in enumerate(values):
        if value is None:
            runs.append([])
        else:
            runs[-1].append((i, value))
    return [run for run in runs if run]


def _lines(
    values: list[float | None], x: Callable[[int], float], y: Callable[[float], float]
) -> str:
    """A polyline per run, so a gap breaks the line, and a dot on every value."""
    lines = "".join(
        '<polyline class="line" points="'
        + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in run)
        + '"/>'
        for run in _runs(values)
    )
    dots = "".join(
        f'<circle class="dot" cx="{x(i):.1f}" cy="{y(v):.1f}" r="3"/>'
        for run in _runs(values)
        for i, v in run
    )
    return lines + dots


def _ticks(low: float, high: float) -> list[float]:
    """Round axis ticks (steps of 1, 2, 2.5 or 5 times a power of ten) covering low to high."""
    span = high - low or abs(high) or 1.0
    raw = span / 4
    step = 10 ** math.floor(math.log10(raw))
    step *= next(m for m in (1, 2, 2.5, 5, 10) if step * m >= raw)
    first = math.floor(low / step) * step
    count = max(math.ceil((high - first) / step), 1)
    return [first + k * step for k in range(count + 1)]


# --- the status squares: present, returned as null, not returned ---------------------------------


_SQUARES = {
    "present": '<rect class="sq-present" x="{x:.1f}" y="{y}" width="{s}" height="{s}" rx="2"/>',
    "null_value": (
        '<rect class="sq-null" x="{x:.1f}" y="{y}" width="{s}" height="{s}" rx="2"/>'
        '<path class="sq-slash" d="M{x0:.1f} {y1} L{x1:.1f} {y0}"/>'
    ),
    "missing_row": (
        '<rect class="sq-missing" x="{xi:.1f}" y="{yi}" width="{si}" height="{si}" rx="2"/>'
    ),
}


def _square(x: float, y: float, size: float, status: str | None) -> str:
    return _SQUARES.get(status or "", "").format(
        x=x, y=y, s=size, x0=x + 2, x1=x + size - 2, y0=y + 2, y1=y + size - 2,
        xi=x + 0.75, yi=y + 0.75, si=size - 1.5,
    )  # fmt: skip


def _strip(statuses: list[str | None]) -> str:
    width = 12 * len(statuses) - 2
    squares = "".join(_square(12 * i, 0, 10, status) for i, status in enumerate(statuses))
    return (
        f'<svg class="strip" width="{width}" height="10" viewBox="0 0 {width} 10" '
        f'aria-hidden="true">{squares}</svg>'
    )


def _square_key() -> str:
    items = "".join(
        f'<span><svg class="key" viewBox="0 0 12 12" aria-hidden="true">{_square(1, 1, 10, status)}'
        f"</svg>{label}</span>"
        for status, label in STATUS_TEXT.items()
    )
    return f'<p class="key-row">{items}</p>'


# --- one indicator -------------------------------------------------------------------------------


def _board(d: _Data, k: int, indicator: str, name: str, short: str) -> str:
    cells = [c for (code, _, _), c in d.cells.items() if code == indicator]
    aggregation = next((g["aggregation"] for g in d.groups.get(indicator, [])), None)
    combined = (
        f"Income-group value: {_e(aggregation)}." if aggregation else "No income-group value."
    )
    tiles = "".join(_tile(d, indicator, short, code, country) for code, country in d.countries)
    return f"""
<section class="board" data-ind="{k}" aria-labelledby="board-{k}">
<header class="board-head"><h2 id="board-{k}">{_e(name)}</h2>
<p class="meta">{_coverage_text(cells)}. {combined}</p></header>
<p class="no-countries">Select at least one country to see the country views.</p>
<div class="row">{_ranking(d, indicator)}{_income_groups(d, indicator)}</div>
<div class="panel"><h3>Each country, {d.years[0]} to {d.years[-1]}</h3>
<p class="sub">Each chart has its own scale, so it shows the shape of the change; the ranking
compares levels. Point at a year to read it.</p>
{_square_key()}<div class="tiles">{tiles}</div>{_values_table(d, indicator)}</div>
{_changes(d, indicator)}
</section>"""


def _ranking(d: _Data, indicator: str) -> str:
    rows = sorted(
        ((code, country, d.latest.get((indicator, code)) or {}) for code, country in d.countries),
        key=lambda r: (r[2].get("latest_rank") is None, r[2].get("latest_rank") or 0),
    )
    top = max((abs(r.get("latest_value") or 0) for _, _, r in rows), default=0) or 1
    items = ""
    for code, country, row in rows:
        value = row.get("latest_value")
        if value is None:
            rank, track, year = "—", '<span class="val muted">no value</span>', ""
        else:
            tone = " neg" if value < 0 else ""
            rank, year = row["latest_rank"], row["latest_year"]
            track = (
                f'<span class="bar{tone}" style="--w:{abs(value) / top:.4f}"></span>'
                f'<span class="val">{_number(value)}</span>'
            )
        items += (
            f'<li data-cty="{d.index(code)}"><span class="pos">{rank}</span>'
            f'<span class="who"><b class="code">{_e(code)}</b>{_e(country)}</span>'
            f'<span class="track">{track}</span><span class="yr">{year}</span></li>'
        )
    return f"""<div class="panel"><h3>Ranked at each country's latest year</h3>
<p class="sub">Each country at its most recent year with a value; 1 is the highest, among all
countries, whichever are selected.</p>
<ol class="rank">{items}</ol>{_common_year(d, rows)}</div>"""


def _common_year(d: _Data, rows: list[tuple[str, str, Row]]) -> str:
    year = next((r["common_year"] for _, _, r in rows if r.get("common_year") is not None), None)
    if year is None:
        return (
            '<p class="note">No year has a value for every country, so there\'s no like-for-like '
            "comparison.</p>"
        )
    if all(r.get("latest_year") == year for _, _, r in rows):
        return (
            f'<p class="note">Every country\'s latest year is {year}, so the ranking compares like '
            "with like.</p>"
        )
    items = "".join(
        f'<li data-cty="{d.index(code)}"><span class="pos">{r.get("common_rank")}</span>'
        f'<span class="who"><b class="code">{_e(code)}</b>{_e(country)}</span>'
        f'<span class="val">{_number(r.get("common_value"))}</span></li>'
        for code, country, r in sorted(rows, key=lambda r: r[2].get("common_rank") or 0)
    )
    return f"""<p class="note">Latest years differ by country.</p>
<details><summary>Compare every country in {year}, the latest year they all have</summary>
<ol class="rank compact">{items}</ol></details>"""


_W, _H, _L, _R, _T, _B = 600, 250, 60, 150, 12, 26  # income chart: size and margins


def _income_groups(d: _Data, indicator: str) -> str:
    head = """<div class="panel ig hoverable"><h3>By income group</h3>
<p class="sub">Each group combines all of its countries in the warehouse, whichever countries are
selected above. Point at a year to read it.</p>"""
    rows = d.groups.get(indicator, [])
    values = [r["group_value"] for r in rows if r["group_value"] is not None]
    if not values:
        return head + '<p class="empty">No income group has a value for this indicator.</p></div>'
    years = sorted({r["observation_year"] for r in rows})
    groups: dict[tuple[int, str, str], dict[int, Row]] = defaultdict(dict)
    for row in rows:
        key = (*_group_order(row), row["income_group_name"])
        groups[key][row["observation_year"]] = row
    ticks = _ticks(min(values), max(values))
    low, high = ticks[0], ticks[-1]

    def x(i: int) -> float:
        return _L + i * (_W - _L - _R) / max(len(years) - 1, 1)

    def y(value: float) -> float:
        return _T + (high - value) / (high - low) * (_H - _T - _B)

    default = max(
        i
        for i, year in enumerate(years)
        if any(g.get(year, {}).get("group_value") is not None for g in groups.values())
    )
    series, legend, ends = "", "", []
    for (order, _, name), by_year in sorted(groups.items()):
        tone = f"c{min(order + 1, 4)}"
        points = [by_year.get(year, {}).get("group_value") for year in years]
        series += f'<g class="series {tone}">{_lines(points, x, y)}</g>'
        last = max((i for i, v in enumerate(points) if v is not None), default=None)
        if last is not None:
            ends.append((y(points[last] or 0), x(last), name))
        readouts = "".join(
            _readout(i, default, _group_value(by_year.get(year, {})))
            for i, year in enumerate(years)
        )
        legend += (
            f'<li><svg class="keyline" viewBox="0 0 18 10" aria-hidden="true"><line class="{tone}" '
            f'x1="1" x2="17" y1="5" y2="5"/></svg><span>{_e(name)}</span>'
            f'<span class="vals">{readouts}</span></li>'
        )
    tops = sorted(e[0] for e in ends)
    collide = any(b - a < 14 for a, b in pairwise(tops))
    labels = "".join(
        f'<text class="end-label" x="{ex + 10:.1f}" y="{ey + 4:.1f}">{_e(name)}</text>'
        for ey, ex, name in ends
        if not collide
    )
    grid = "".join(
        f'<line class="gridline" x1="{_L}" x2="{_W - _R + 6}" y1="{y(t):.1f}" y2="{y(t):.1f}"/>'
        f'<text x="{_L - 8}" y="{y(t) + 4:.1f}" text-anchor="end">{_e(_tick_label(t))}</text>'
        for t in ticks
    )
    axis = "".join(
        f'<text x="{x(i):.1f}" y="{_H - 6}" text-anchor="middle">{year}</text>'
        for i, year in enumerate(years)
    )
    step = (_W - _L - _R) / max(len(years) - 1, 1)
    hover = "".join(
        f'<g class="cross" data-y="{i}"><line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{_T}" '
        f'y2="{_H - _B}"/></g><rect class="band" data-y="{i}" x="{x(i) - step / 2:.1f}" y="0" '
        f'width="{step:.1f}" height="{_H}"/>'
        for i in range(len(years))
    )
    heading = "".join(_readout(i, default, f"In {year}") for i, year in enumerate(years))
    return f"""{head}<p class="ro-head">{heading}</p><ul class="ig-legend">{legend}</ul>
<div class="chart"><svg viewBox="0 0 {_W} {_H}" role="img" aria-label="Income groups by year">
<g class="axis">{grid}{axis}</g>{series}{labels}{hover}</svg></div>
{_groups_table(groups, years)}</div>"""


def _readout(i: int, default: int, content: str) -> str:
    tone = " ro-default" if i == default else ""
    return f'<span class="ro{tone}" data-y="{i}">{content}</span>'


def _group_value(row: Row) -> str:
    return (
        f"<b>{_number(row.get('group_value'))}</b><small>{row.get('n_countries_with_data', 0)} of "
        f"{_countries(row.get('n_countries', 0))}</small>"
    )


def _groups_table(groups: dict[tuple[int, str, str], dict[int, Row]], years: list[int]) -> str:
    head = "".join(f'<th scope="col">{year}</th>' for year in years)
    body = "".join(
        f'<tr><th scope="row">{_e(name)}</th>'
        + "".join(
            f"<td>{_number(by_year.get(year, {}).get('group_value'))}"
            f"<small>{by_year.get(year, {}).get('n_countries_with_data', 0)}/"
            f"{by_year.get(year, {}).get('n_countries', 0)}</small></td>"
            for year in years
        )
        + "</tr>"
        for (_, _, name), by_year in sorted(groups.items())
    )
    return (
        "<details><summary>Show as a table, with countries with data out of countries in the "
        f'group</summary><div class="scroll"><table class="plain"><thead><tr><th scope="col">'
        f"Group</th>{head}</tr></thead><tbody>{body}</tbody></table></div></details>"
    )


_TW = 240  # tile chart width; the plot spans y 6..54, the squares sit at y 64


def _tile(d: _Data, indicator: str, short: str, code: str, country: str) -> str:
    years = d.years
    cells = [d.cell(indicator, code, year) for year in years]
    values = [c.get("indicator_value") for c in cells]
    present = [v for v in values if v is not None]
    low, high = (min(present), max(present)) if present else (0.0, 1.0)
    pad = (high - low) * 0.1 or abs(high) * 0.05 or 1.0
    low, high = low - pad, high + pad
    step = (_TW - 20) / max(len(years) - 1, 1)

    def x(i: int) -> float:
        return 10 + i * step

    def y(value: float) -> float:
        return 6 + (high - value) / (high - low) * 48

    default = max((i for i, v in enumerate(values) if v is not None), default=len(years) - 1)
    readouts = "".join(
        _readout(
            i, default, _tile_readout(cell, d.changes.get((indicator, code, year)) or {}, year)
        )
        for i, (year, cell) in enumerate(zip(years, cells, strict=True))
    )
    hover = "".join(
        f'<g class="cross" data-y="{i}"><line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="2" y2="58"/>'
        + (f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="4"/>' if v is not None else "")
        + "</g>"
        for i, v in enumerate(values)
    )
    squares = "".join(_square(x(i) - 5, 64, 10, c.get("value_status")) for i, c in enumerate(cells))
    bands = "".join(
        f'<rect class="band" data-y="{i}" x="{x(i) - step / 2:.1f}" y="0" width="{step:.1f}" '
        'height="80"/>'
        for i in range(len(years))
    )
    return f"""<article class="tile hoverable" data-cty="{d.index(code)}">
<header class="tile-head"><p class="who-block"><b>{_e(code)}</b>
<span title="{_e(country)}">{_e(country)}</span></p>
<p class="readouts">{readouts}</p></header>
<svg class="spark" viewBox="0 0 {_TW} 80" role="img"
 aria-label="{_e(country)}, {_e(short)}, {years[0]} to {years[-1]}">
{_lines(values, x, y)}{hover}{squares}{bands}</svg>
<p class="tile-axis"><span>{years[0]}</span><span>{years[-1]}</span></p></article>"""


def _tile_readout(cell: Row, change: Row, year: int) -> str:
    value = cell.get("indicator_value")
    if value is None:
        status = STATUS_TEXT.get(cell.get("value_status") or "", "not expected")
        return f'<b class="fig">—</b><small>{year}, {status}</small>'
    return f'<b class="fig">{_number(value)}</b><small>{year}, {_change_text(change, year)}</small>'


def _values_table(d: _Data, indicator: str) -> str:
    head = "".join(f'<th scope="col">{year}</th>' for year in d.years)
    body = "".join(
        f'<tr data-cty="{j}"><th scope="row">{_e(country)}</th>'
        + "".join(
            f"<td>{_number(d.cell(indicator, code, year).get('indicator_value'))}</td>"
            for year in d.years
        )
        + "</tr>"
        for j, (code, country) in enumerate(d.countries)
    )
    return (
        '<details><summary>Show the values as a table</summary><div class="scroll">'
        f'<table class="plain"><thead><tr><th scope="col">Country</th>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div></details>"
    )


def _changes(d: _Data, indicator: str) -> str:
    percents = [
        c["percent_change"]
        for (code, _, _), c in d.changes.items()
        if code == indicator and c["percent_change"] is not None
    ]
    domain = max((abs(p) for p in percents), default=0.0) or 1.0
    head = "".join(f'<th scope="col">{year}</th>' for year in d.years)
    body = "".join(
        f'<tr data-cty="{j}"><th scope="row"><b class="code">{_e(code)}</b>{_e(country)}</th>'
        + "".join(
            _change_cell(d.changes.get((indicator, code, year)) or {}, year, domain)
            for year in d.years
        )
        + "</tr>"
        for j, (code, country) in enumerate(d.countries)
    )
    scale = "".join(f'<i class="{tone}"></i>' for tone in ("d4", "d3", "d2", "d1", "z"))
    scale += "".join(f'<i class="{tone}"></i>' for tone in ("u1", "u2", "u3", "u4"))
    return f"""<div class="panel"><h3>Change from the year before</h3>
<p class="sub">Percent change on the previous year. Shading is relative to this indicator's largest
change; a change that can't be computed says why, and is never shown as 0.</p>
<div class="scroll"><table class="heat"><thead><tr><th scope="col">Country</th>{head}</tr></thead>
<tbody>{body}</tbody></table></div>
<p class="scale" aria-hidden="true"><span>{_signed_percent(-domain)}</span>{scale}
<span>{_signed_percent(domain)}</span></p></div>"""


def _change_cell(change: Row, year: int, domain: float) -> str:
    percent = change.get("percent_change")
    if percent is None:
        return f'<td class="na">{_change_text(change, year)}</td>'
    ratio = abs(percent) / domain
    level = 0 if ratio < 0.1 else min(4, math.ceil(ratio * 4))
    tone = "z" if level == 0 else f"{'u' if percent > 0 else 'd'}{level}"
    title = (
        f"{year}: {_number(change.get('indicator_value'))}, from "
        f"{_number(change.get('prior_indicator_value'))} "
        f"({_signed_number(change.get('absolute_change'))})"
    )
    return f'<td class="{tone}" title="{title}">{_signed_percent(percent)}</td>'


# --- the page ------------------------------------------------------------------------------------


def _masthead(d: _Data) -> str:
    cells = list(d.cells.values())
    complete = all(c["value_status"] == "present" for c in cells)
    tone, icon = ("ok", "&#x2713;") if complete else ("warn", "!")
    return f"""<header class="masthead"><div>
<h1>World Bank country indicators</h1>
<p class="lede">{_countries(len(d.countries))} and
{_plural(len(d.indicators), "indicator")}, {d.years[0]} to {d.years[-1]}. Every number comes
from the published warehouse, which is only published after every data test has passed.</p></div>
<p class="status {tone}"><span class="icon" aria-hidden="true">{icon}</span>
{_coverage_text(cells)}</p>
</header>"""


def _filters(d: _Data, short: dict[str, str]) -> str:
    tabs = "".join(
        f'<label><input class="vh" type="radio" name="indicator" id="ind-{k}"'
        f"{' checked' if k == 0 else ''}><span>{_e(short[code])}</span></label>"
        for k, (code, _) in enumerate(d.indicators)
    )
    chips = "".join(
        f'<label><input class="vh" type="checkbox" id="cty-{j}" checked>'
        f"<span><b>{_e(code)}</b>{_e(country)}</span></label>"
        for j, (code, country) in enumerate(d.countries)
    )
    return f"""<form class="filters" aria-label="Filters">
<fieldset><legend>Indicator</legend><div class="tabs">{tabs}</div></fieldset>
<fieldset id="countries"><legend>Countries</legend><div class="chips">{chips}</div>
<div class="bulk" hidden><button type="button" data-bulk="all">All</button>
<button type="button" data-bulk="none">None</button></div></fieldset>
<p class="fallback">This browser can't apply the filters, so every indicator and country is
shown.</p></form>"""


def _completeness(d: _Data, short: dict[str, str]) -> str:
    head = "".join(
        f'<th scope="col" data-col="{k}">{_e(short[code])}</th>'
        for k, (code, _) in enumerate(d.indicators)
    )
    body, gaps = "", ""
    for j, (country_code, country) in enumerate(d.countries):
        tds = ""
        for k, (code, name) in enumerate(d.indicators):
            series = d.series.get((code, country_code)) or {}
            statuses = [d.cell(code, country_code, year).get("value_status") for year in d.years]
            missing = series.get("n_null_value", 0), series.get("n_missing_row", 0)
            detail = (
                f"<small>{missing[0]} null, {missing[1]} not returned</small>"
                if any(missing)
                else ""
            )
            tds += (
                f'<td data-col="{k}">{_strip(statuses)}<span class="count">'
                f"{series.get('n_present', 0)} of {series.get('n_expected', 0)}</span>{detail}</td>"
            )
            if series.get("series_status", "complete") != "complete":
                gaps += (
                    f'<li data-cty="{j}">{_e(country)}, {_e(name)}: {_e(series["series_status"])}, '
                    f"{series['n_present']} of {series['n_expected']} years ({missing[0]} returned "
                    f"as null, {missing[1]} not returned)</li>"
                )
        body += (
            f'<tr data-cty="{j}"><th scope="row"><b class="code">{_e(country_code)}</b>'
            f"{_e(country)}</th>{tds}</tr>"
        )
    summary = (
        f'<ul class="gaps">{gaps}</ul>'
        if gaps
        else '<p class="note">Nothing is missing: every series has a value for every year.</p>'
    )
    return f"""<section class="sheet" aria-labelledby="completeness">
<h2 id="completeness">Missing and incomplete values</h2>
<p class="meta">Every expected value, by country and indicator, one square per year. A value can
be missing in two ways: the API returned it as null, or didn't return it at all.</p>
{_square_key()}<div class="scroll"><table class="cover"><thead><tr>
<th scope="col">Country</th>{head}</tr></thead><tbody>{body}</tbody></table></div>
{summary}</section>"""


def _filter_css(d: _Data) -> str:
    """The rules that apply the filters and the year readouts, for browsers with `:has()`."""
    rules = [".board { display: none; }"]
    for k in range(len(d.indicators)):
        rules.append(f'body:has(#ind-{k}:checked) .board[data-ind="{k}"] {{ display: block; }}')
        rules.append(f'body:has(#ind-{k}:checked) [data-col="{k}"] {{ background: var(--col); }}')
    rules += [
        f'body:has(#cty-{j}:not(:checked)) [data-cty="{j}"] {{ display: none; }}'
        for j in range(len(d.countries))
    ]
    rules.append("body:not(:has(#countries input:checked)) .no-countries { display: block; }")
    rules.append(".hoverable:has(.band:hover) .ro-default { display: none; }")
    for i in range(len(d.years)):
        rules.append(
            f'.hoverable:has(.band[data-y="{i}"]:hover) .ro[data-y="{i}"] {{ display: block; }}'
        )
        rules.append(
            f'.hoverable:has(.band[data-y="{i}"]:hover) .cross[data-y="{i}"] {{ opacity: 1; }}'
        )
    return "@supports selector(:has(*)) {\n" + "\n".join(rules) + "\n}"


def _page(d: _Data) -> str:
    short = _short_names(d.indicators)
    boards = "".join(
        _board(d, k, code, name, short[code]) for k, (code, name) in enumerate(d.indicators)
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>World Bank country indicators</title>
<style>{_CSS}{_filter_css(d)}</style></head>
<body><div class="page">
{_masthead(d)}
{_filters(d, short)}
{boards}
{_completeness(d, short)}
<footer class="foot">Source: World Bank API, World Development Indicators. Built from the reporting
tables of the published warehouse; the same tables are exported as CSV to
<code>data/outputs/</code>. Missing values are never shown as 0.</footer>
</div>
<script>{_SCRIPT}</script>
</body></html>
"""


# Static: no warehouse value ever reaches the script.
_SCRIPT = """
document.querySelectorAll("[data-bulk]").forEach(function (button) {
  button.addEventListener("click", function () {
    document.querySelectorAll("#countries input").forEach(function (box) {
      box.checked = button.dataset.bulk === "all";
    });
  });
});
document.querySelector(".bulk").hidden = false;
"""

_CSS = """
:root {
  color-scheme: light;
  --plane: #f1f3ef; --surface: #ffffff; --ink: #15202b; --ink-2: #5b6670; --rule: #dde2dc;
  --grid: #e8ebe6; --axis: #c2c8c2; --data: #257de0; --select: #15202b; --on-select: #ffffff;
  --present: #c5d2de; --warning: #fbb315; --critical: #dc3c3d; --good: #0aac23; --col: #eaf2fc;
  --z: #eef0ee; --u1: #dceafb; --u2: #b6d5f8; --u3: #84b9f3; --u4: #5aa1ee;
  --d1: #fbe3e1; --d2: #f6c2bd; --d3: #ef9790; --d4: #e8716a;
  --ig1: #84b9f3; --ig2: #338ced; --ig3: #1b64be; --ig4: #0e3d7e;
  --condensed: "DIN Alternate", Bahnschrift, "Nimbus Sans Narrow", "Roboto Condensed",
    "Arial Narrow", sans-serif;
  --text: system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
    --plane: #121518; --surface: #1a1e22; --ink: #e9ecef; --ink-2: #9aa3ab; --rule: #2c3238;
    --grid: #262b30; --axis: #48505a; --data: #338ced; --select: #e9ecef; --on-select: #121518;
    --present: #3b4b5c; --col: #1d2a38;
    --z: #2a2f34; --u1: #1c3048; --u2: #1d4373; --u3: #1e58a0; --u4: #2268c4;
    --d1: #3d2426; --d2: #5c2b2c; --d3: #843234; --d4: #a8393a;
    --ig1: #1b64be; --ig2: #338ced; --ig3: #84b9f3; --ig4: #cce3fd;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--plane); color: var(--ink); font: 14px/1.5 var(--text); }
.page { max-width: 1240px; margin: 0 auto; padding: 32px 24px 64px; }
h1, h2, .code, .who-block b, .fig, .tabs span, .chips b { font-family: var(--condensed); }
h1 { font-size: 36px; line-height: 1.1; font-weight: 700; margin: 0 0 8px;
  letter-spacing: -0.01em; }
h2 { font-size: 26px; line-height: 1.15; font-weight: 700; margin: 0 0 6px; }
h3 { font-size: 15px; line-height: 1.3; font-weight: 600; margin: 0 0 4px; }
.lede, .meta { margin: 0; color: var(--ink-2); max-width: 70ch; }
.sub { margin: 0 0 14px; color: var(--ink-2); font-size: 13px; max-width: 70ch; }
.note, .empty { margin: 12px 0 0; color: var(--ink-2); font-size: 13px; }
.muted { color: var(--ink-2); }

.masthead { display: flex; flex-wrap: wrap; gap: 16px 40px; align-items: flex-end;
  justify-content: space-between; margin-bottom: 20px; }
.status { display: flex; align-items: center; gap: 8px; margin: 0; font-weight: 600; }
.status .icon { flex: none; width: 22px; height: 22px; border-radius: 50%; display: grid;
  place-items: center; font-size: 13px; color: #ffffff; background: var(--good); }
.status.warn .icon { background: var(--warning); color: #0b0b0b; }

.filters { display: grid; gap: 10px; padding: 12px 0 14px; background: var(--plane);
  border-bottom: 1px solid var(--rule); }
@media (min-width: 960px) { .filters { position: sticky; top: 0; z-index: 5; } }
fieldset { border: 0; margin: 0; padding: 0; min-width: 0; display: flex; flex-wrap: wrap;
  align-items: center; gap: 8px 12px; }
legend { float: left; width: 6rem; padding: 0; font-size: 12px; color: var(--ink-2); }
.vh { position: absolute; width: 1px; height: 1px; opacity: 0; overflow: hidden; }
.tabs { display: flex; flex-wrap: wrap; gap: 3px; padding: 3px; background: var(--surface);
  border: 1px solid var(--rule); border-radius: 8px; }
.tabs span { display: block; padding: 5px 14px; border-radius: 5px; font-size: 15px;
  font-weight: 700; color: var(--ink-2); cursor: pointer; }
.tabs input:checked + span { background: var(--select); color: var(--on-select); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chips span { display: flex; align-items: center; gap: 6px; padding: 4px 10px 4px 8px;
  border: 1px solid var(--rule); border-radius: 4px; background: var(--surface);
  color: var(--ink-2); font-size: 13px; cursor: pointer; }
.chips span::before { content: ""; width: 10px; height: 10px; border-radius: 2px;
  border: 1.5px solid var(--axis); }
.chips b { font-size: 14px; letter-spacing: 0.02em; }
.chips input:checked + span { color: var(--ink); }
.chips input:checked + span::before { background: var(--data); border-color: var(--data); }
.tabs input:focus-visible + span, .chips input:focus-visible + span, .bulk button:focus-visible,
summary:focus-visible { outline: 2px solid var(--data); outline-offset: 2px; }
.bulk { display: flex; gap: 2px; }
.bulk[hidden] { display: none; }
.bulk button { font: inherit; font-size: 13px; padding: 4px 6px; border: 0; background: none;
  color: var(--ink-2); text-decoration: underline; cursor: pointer; }
.fallback { display: none; margin: 0; font-size: 12px; color: var(--ink-2); }
@supports not selector(:has(*)) { .fallback { display: block; } }

.board, .sheet { margin-top: 20px; padding: 24px; background: var(--surface);
  border: 1px solid var(--rule); border-radius: 10px; }
.board-head { margin-bottom: 24px; }
.no-countries { display: none; margin: 0 0 20px; padding: 10px 12px;
  border-left: 3px solid var(--warning); background: var(--plane); }
.row { display: grid; gap: 40px; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
.panel { min-width: 0; margin-top: 40px; }
.row .panel { margin-top: 0; }

.code { font-weight: 700; letter-spacing: 0.02em; margin-right: 6px; }
.rank { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.rank li { display: grid; grid-template-columns: 2ch 9.5rem minmax(0, 1fr) 3.5ch; gap: 10px;
  align-items: center; min-height: 28px; }
.rank.compact li { grid-template-columns: 2ch minmax(0, 1fr) auto; min-height: 24px; }
.pos, .yr { font-size: 12px; color: var(--ink-2); font-variant-numeric: tabular-nums; }
.pos { text-align: right; }
.who { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.track { display: flex; align-items: center; gap: 6px; min-width: 0; }
.bar { flex: none; height: 14px; min-width: 2px; width: calc((100% - 7.5ch) * var(--w));
  background: var(--data); border-radius: 0 4px 4px 0; }
.bar.neg { background: var(--d4); }
.val { font-size: 13px; white-space: nowrap; font-variant-numeric: tabular-nums; }

.ro { display: none; }
.ro-default { display: block; }
.ro-head { margin: 0 0 6px; font-size: 12px; color: var(--ink-2); }
.ig-legend { list-style: none; margin: 0 0 6px; padding: 0; display: grid; gap: 2px; }
.ig-legend li { display: grid; grid-template-columns: 18px minmax(0, 1fr) auto; gap: 8px;
  align-items: center; }
.ig-legend b { font-variant-numeric: tabular-nums; }
.ig-legend small { margin-left: 8px; font-size: 12px; color: var(--ink-2); }
.keyline { width: 18px; height: 10px; }
.keyline line { stroke: var(--c); stroke-width: 3; stroke-linecap: round; }
.chart { overflow-x: auto; }
.chart svg { display: block; width: 100%; min-width: 460px; height: auto; }
.axis text { font-size: 11px; fill: var(--ink-2); font-variant-numeric: tabular-nums; }
.gridline { stroke: var(--grid); stroke-width: 1; }
.c1 { --c: var(--ig1); } .c2 { --c: var(--ig2); } .c3 { --c: var(--ig3); } .c4 { --c: var(--ig4); }
.series .line { stroke: var(--c); }
.series .dot { fill: var(--c); }
.end-label { font-size: 12px; fill: var(--ink); }
.line { fill: none; stroke: var(--data); stroke-width: 2; stroke-linejoin: round;
  stroke-linecap: round; vector-effect: non-scaling-stroke; }
.dot { fill: var(--data); stroke: var(--surface); stroke-width: 2; }
.cross { opacity: 0; }
.cross line { stroke: var(--ink-2); stroke-width: 1; vector-effect: non-scaling-stroke; }
.cross circle { fill: var(--surface); stroke: var(--ink); stroke-width: 2; }
.band { fill: transparent; }

.key-row { display: flex; flex-wrap: wrap; gap: 4px 16px; margin: 0 0 14px; font-size: 12px;
  color: var(--ink-2); }
.key-row span { display: inline-flex; align-items: center; gap: 6px; }
.key { width: 12px; height: 12px; }
.sq-present { fill: var(--present); }
.sq-null { fill: var(--warning); }
.sq-slash { stroke: #15202b; stroke-width: 1.5; }
.sq-missing { fill: none; stroke: var(--critical); stroke-width: 1.5; }

.tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; }
.tile { padding: 12px 14px 10px; background: var(--surface); border: 1px solid var(--rule);
  border-radius: 8px; }
.tile-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.who-block { margin: 0; display: grid; min-width: 0; }
.who-block b { font-size: 22px; line-height: 1; letter-spacing: 0.02em; }
.who-block span { margin-top: 3px; font-size: 12px; color: var(--ink-2); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.readouts { flex: none; margin: 0; text-align: right; }
.fig { display: block; font-size: 20px; line-height: 1.1; font-weight: 700; }
.readouts small { display: block; font-size: 12px; color: var(--ink-2); white-space: nowrap; }
.spark { display: block; width: 100%; height: auto; margin-top: 8px; overflow: visible; }
.tile-axis { display: flex; justify-content: space-between; margin: 2px 0 0; font-size: 11px;
  color: var(--ink-2); font-variant-numeric: tabular-nums; }

.scroll { overflow-x: auto; }
table { font-size: 13px; }
.heat { width: 100%; border-collapse: separate; border-spacing: 2px; }
.heat th, .heat td { padding: 6px 8px; text-align: right; white-space: nowrap;
  font-variant-numeric: tabular-nums; }
.heat thead th { font-size: 12px; font-weight: 500; color: var(--ink-2); }
.heat tbody th { text-align: left; font-weight: 400; }
.heat td { border-radius: 3px; }
.heat td.na { font-size: 12px; color: var(--ink-2); }
.z { background: var(--z); } .u1 { background: var(--u1); } .u2 { background: var(--u2); }
.u3 { background: var(--u3); } .u4 { background: var(--u4); } .d1 { background: var(--d1); }
.d2 { background: var(--d2); } .d3 { background: var(--d3); } .d4 { background: var(--d4); }
.scale { display: flex; align-items: center; gap: 2px; margin: 10px 0 0; font-size: 12px;
  color: var(--ink-2); font-variant-numeric: tabular-nums; }
.scale i { width: 22px; height: 10px; border-radius: 2px; }
.scale span:first-child { margin-right: 6px; }
.scale span:last-child { margin-left: 6px; }

.cover { width: 100%; border-collapse: collapse; }
.cover th, .cover td { padding: 8px 10px; text-align: left; white-space: nowrap;
  border-bottom: 1px solid var(--rule); }
.cover thead th { font-size: 12px; font-weight: 500; color: var(--ink-2); }
.cover tbody th { font-weight: 400; }
.strip { vertical-align: -1px; margin-right: 8px; }
.count { font-variant-numeric: tabular-nums; }
.cover small { margin-left: 8px; font-size: 12px; color: var(--ink-2); }
.gaps { margin: 14px 0 0; padding-left: 18px; }

details { margin-top: 12px; font-size: 13px; }
summary { cursor: pointer; color: var(--ink-2); }
.plain { margin-top: 8px; border-collapse: collapse; }
.plain th, .plain td { padding: 4px 14px 4px 0; text-align: right; white-space: nowrap;
  font-variant-numeric: tabular-nums; border-bottom: 1px solid var(--rule); }
.plain th:first-child { text-align: left; font-weight: 400; }
.plain thead th { font-weight: 500; color: var(--ink-2); }
.plain small { margin-left: 4px; color: var(--ink-2); }
.foot { margin-top: 32px; max-width: 80ch; font-size: 12px; color: var(--ink-2); }

@media (max-width: 960px) { .row { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 640px) {
  .page { padding: 20px 16px 48px; }
  .board, .sheet { padding: 16px; }
  h1 { font-size: 30px; }
  legend { float: none; width: auto; }
  .rank li { grid-template-columns: 2ch 6.5rem minmax(0, 1fr) 3.5ch; }
}
@media print {
  .filters { display: none; }
  .board { display: block !important; }
}
"""
