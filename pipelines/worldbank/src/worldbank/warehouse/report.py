"""Report: render the reporting tables of the published warehouse as one HTML page (ADR-0036).

Reads only the published warehouse's `reporting` schema, so the page shows audited answers. The
page is self-contained (inline CSS and SVG, no scripts or external files), so it opens anywhere,
and every value from the warehouse is HTML-escaped. One section per question of the brief.
"""

import html
import logging
from collections import defaultdict
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
STATUS_COLORS = {"complete": "#d8efe0", "incomplete": "#fbe7c6", "missing": "#f6d0cc"}
LINE_COLORS = ("#c2410c", "#0f766e", "#1d4ed8", "#7e22ce")

# Income groups from low to high income, for display only (ADR-0040); any other group follows.
INCOME_GROUP_ORDER = ("LIC", "LMC", "UMC", "HIC")


def _group_order(row: Row) -> tuple[int, str]:
    code = row["income_group_id"]
    known = code in INCOME_GROUP_ORDER
    return (INCOME_GROUP_ORDER.index(code) if known else len(INCOME_GROUP_ORDER), code)


class NothingToReport(WarehouseError):
    """There's no published warehouse, or it lacks the reporting tables."""


def render_report(warehouse: Path, output: Path) -> Path:
    """Write the HTML report of `warehouse`'s reporting tables to `output`; return its path."""
    if not warehouse.is_file():
        raise NothingToReport(f"{warehouse} doesn't exist; publish a build first")
    with duckdb.connect(str(warehouse), read_only=True) as con:
        try:
            tables = {name: _rows(con, name) for name in _TABLES}
        except duckdb.CatalogException as exc:
            raise NothingToReport(f"{warehouse} lacks a reporting table: {exc}") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.name}.tmp")
    temporary.write_text(_page(tables), encoding="utf-8")
    temporary.replace(output)
    log.info("report rendered", extra={"path": str(output)})
    return output


_TABLES = {
    "rpt_completeness_by_cell": "country_id, indicator_id, observation_year",
    "rpt_completeness_by_series": "country_name, indicator_name",
    "rpt_year_over_year": "indicator_name, country_name, observation_year",
    "rpt_latest_year_by_country": "indicator_name, rank_in_indicator NULLS LAST, country_name",
    "rpt_latest_common_year": "indicator_name, rank_in_indicator NULLS LAST, country_name",
    "rpt_income_group_by_year": "indicator_name, income_group_id, observation_year",
}


def _rows(con: duckdb.DuckDBPyConnection, table: str) -> list[Row]:
    result = con.execute(f"SELECT * FROM reporting.{table} ORDER BY {_TABLES[table]}")
    columns = [description[0] for description in result.description]
    return [dict(zip(columns, values, strict=True)) for values in result.fetchall()]


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


def _percent(value: float | None, reason: str | None) -> str:
    if value is not None:
        tone = "up" if value > 0 else "down" if value < 0 else ""
        return f'<td class="num {tone}">{value:+.1f}%</td>'
    return f'<td class="num muted">{_e(REASONS.get(reason or "", reason or "—"))}</td>'


def _grouped(rows: list[Row], key: str) -> dict[str, list[Row]]:
    groups: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    return groups


# --- sections ------------------------------------------------------------------------------------


def _completeness(cells: list[Row], series: list[Row]) -> str:
    counts = {
        status: sum(1 for c in cells if c["value_status"] == status)
        for status in ("present", "null_value", "missing_row")
    }
    countries = sorted({s["country_name"] for s in series})
    indicators = sorted({s["indicator_name"] for s in series})
    by_pair = {(s["country_name"], s["indicator_name"]): s for s in series}
    header = "".join(f"<th>{_e(name)}</th>" for name in indicators)
    body = ""
    for country in countries:
        cells_html = ""
        for indicator in indicators:
            s = by_pair[(country, indicator)]
            color = STATUS_COLORS[s["series_status"]]
            cells_html += (
                f'<td style="background:{color}" title="{_e(s["series_status"])}">'
                f"{s['n_present']}/{s['n_expected']}</td>"
            )
        body += f"<tr><th>{_e(country)}</th>{cells_html}</tr>"
    gaps = [s for s in series if s["series_status"] != "complete"]
    gap_note = (
        f"<p>All {len(series)} series are complete: every expected value is present.</p>"
        if not gaps
        else "<p>Series with gaps:</p><ul>"
        + "".join(
            f"<li>{_e(s['country_name'])}, {_e(s['indicator_name'])}: "
            f"{_e(s['series_status'])} ({s['n_present']} of {s['n_expected']} years; "
            f"{s['n_null_value']} null, {s['n_missing_row']} missing)</li>"
            for s in gaps
        )
        + "</ul>"
    )
    return f"""
<section id="completeness"><h2>1. Missing and incomplete data</h2>
<p class="lead">Every expected country &times; indicator &times; year:
<b>{counts["present"]}</b> present, <b>{counts["null_value"]}</b> returned as null,
<b>{counts["missing_row"]}</b> not returned.
Cells show years present of years expected.</p>
<div class="scroll"><table class="grid"><tr><th></th>{header}</tr>{body}</table></div>
{gap_note}</section>"""


def _year_over_year(changes: list[Row]) -> str:
    out = ""
    for indicator, rows in _grouped(changes, "indicator_name").items():
        years = sorted({r["observation_year"] for r in rows})
        head = "".join(f"<th>{year}</th>" for year in years)
        body = ""
        for country, by_country in _grouped(rows, "country_name").items():
            by_year = {r["observation_year"]: r for r in by_country}
            body += (
                f"<tr><th>{_e(country)}</th>"
                + "".join(
                    _percent(by_year[y]["percent_change"], by_year[y]["null_change_reason"])
                    for y in years
                )
                + "</tr>"
            )
        out += (
            f'<h3>{_e(indicator)}</h3><div class="scroll">'
            f"<table><tr><th></th>{head}</tr>{body}</table></div>"
        )
    return f"""
<section id="year-over-year"><h2>2. Year-over-year change</h2>
<p class="lead">Percent change from the previous year. A change that can't be computed says why;
it's never shown as 0. The first year has no prior year in scope.</p>{out}</section>"""


def _latest(latest: list[Row], common: list[Row]) -> str:
    out = ""
    common_by = {(r["indicator_name"], r["country_name"]): r for r in common}
    for indicator, rows in _grouped(latest, "indicator_name").items():
        common_year = next(
            (
                c["common_year"]
                for c in common
                if c["indicator_name"] == indicator and c["common_year"] is not None
            ),
            None,
        )
        common_values = {
            country: row["indicator_value"]
            for (name, country), row in common_by.items()
            if name == indicator
        }
        body = "".join(
            f'<tr><td class="num">{r["rank_in_indicator"] or "—"}</td>'
            f"<th>{_e(r['country_name'])}</th>"
            f'<td class="num">{_number(r["indicator_value"])}</td>'
            f'<td class="num">{r["latest_year"] or "—"}</td>'
            f'<td class="num">{_number(common_values[r["country_name"]])}</td></tr>'
            for r in rows
        )
        common_label = f"value in {common_year}" if common_year else "no year common to all"
        out += (
            f'<h3>{_e(indicator)}</h3><div class="scroll"><table>'
            "<tr><th>Rank</th><th>Country</th><th>Latest value</th><th>Year</th>"
            f"<th>{_e(common_label)}</th></tr>{body}</table></div>"
        )
    return f"""
<section id="latest"><h2>3. Countries at their latest available year</h2>
<p class="lead">Each country at its own latest year with a value, ranked; the last column compares
everyone at the latest year all countries share.</p>{out}</section>"""


def _chart(rows: list[Row]) -> str:
    points = [r for r in rows if r["group_value"] is not None]
    if not points:
        return '<p class="muted">No group has data for this indicator.</p>'
    years = sorted({r["observation_year"] for r in rows})
    low, high = min(p["group_value"] for p in points), max(p["group_value"] for p in points)
    span = (high - low) or abs(high) or 1
    low, high = low - span * 0.08, high + span * 0.08
    width, height, left, bottom = 640, 220, 70, 30

    def x(year: int) -> float:
        return float(left + (year - years[0]) / max(len(years) - 1, 1) * (width - left - 20))

    def y(value: float) -> float:
        return float(10 + (high - value) / (high - low) * (height - bottom - 10))

    lines, legend = "", ""
    groups = _grouped(sorted(rows, key=_group_order), "income_group_name")
    for index, (group, by_group) in enumerate(groups.items()):
        color = LINE_COLORS[index % len(LINE_COLORS)]
        coords = " ".join(
            f"{x(r['observation_year']):.1f},{y(r['group_value']):.1f}"
            for r in by_group
            if r["group_value"] is not None
        )
        lines += f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{coords}"/>'
        legend += f'<span><i style="background:{color}"></i>{_e(group)}</span>'
    axis = "".join(
        f'<text x="{x(year):.1f}" y="{height - 8}" text-anchor="middle">{year}</text>'
        for year in years
    )
    ticks = "".join(
        f'<text x="{left - 8}" y="{y(v) + 4:.1f}" text-anchor="end">{_e(_number(v))}</text>'
        f'<line x1="{left}" x2="{width - 20}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="gridline"/>'
        for v in (low + (high - low) * f for f in (0.1, 0.5, 0.9))
    )
    return (
        f'<div class="legend">{legend}</div><svg viewBox="0 0 {width} {height}" role="img">'
        f"{ticks}{axis}{lines}</svg>"
    )


def _income_groups(groups: list[Row]) -> str:
    out = ""
    for indicator, rows in _grouped(groups, "indicator_name").items():
        years = sorted({r["observation_year"] for r in rows})
        body = ""
        ordered = _grouped(sorted(rows, key=_group_order), "income_group_name")
        for group, by_group in ordered.items():
            by_year = {r["observation_year"]: r for r in by_group}
            body += (
                f"<tr><th>{_e(group)}</th>"
                + "".join(
                    f'<td class="num">{_number(by_year[yr]["group_value"])}'
                    f"<small>{by_year[yr]['n_countries_with_data']}/{by_year[yr]['n_countries']}</small></td>"
                    for yr in years
                )
                + "</tr>"
            )
        head = "".join(f"<th>{year}</th>" for year in years)
        out += (
            f'<h3>{_e(indicator)} <span class="muted">({_e(rows[0]["aggregation"])})</span></h3>'
            f"{_chart(rows)}"
            f'<div class="scroll"><table><tr><th></th>{head}</tr>{body}</table></div>'
        )
    return f"""
<section id="income-groups"><h2>4. Indicators across income groups, by year</h2>
<p class="lead">Each indicator combined the way it requires: totals for population and GDP,
total GDP over total population for GDP per capita, a population-weighted mean for life
expectancy. Small numbers show countries with data out of countries in the group. Income groups
are the World Bank's current classification, applied to every year.</p>{out}</section>"""


def _page(tables: dict[str, list[Row]]) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>World Bank country indicators</title>
<style>
:root {{ --ink:#1c1917; --muted:#78716c; --rule:#e7e5e4; --bg:#fafaf9; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:24px 16px 64px; }}
h1 {{ font-size:32px; margin:0 0 4px; letter-spacing:-.02em; }}
h2 {{ font-size:22px; margin:40px 0 4px; border-top:2px solid var(--ink); padding-top:12px; }}
h3 {{ font-size:16px; margin:24px 0 8px; }}
nav a {{ margin-right:16px; color:var(--ink); }}
.lead, .muted {{ color:var(--muted); }}
.scroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; font-size:13px; background:#fff; }}
th, td {{ padding:5px 9px; border-bottom:1px solid var(--rule); text-align:left;
  white-space:nowrap; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.up {{ color:#15803d; }} .down {{ color:#b91c1c; }}
.grid td {{ text-align:center; }}
small {{ display:block; color:var(--muted); font-size:11px; }}
svg {{ width:100%; max-width:640px; font-size:11px; fill:var(--muted); }}
.gridline {{ stroke:var(--rule); }}
.legend span {{ margin-right:14px; font-size:13px; }}
.legend i {{ display:inline-block; width:12px; height:3px; margin-right:6px;
  vertical-align:middle; }}
footer {{ margin-top:48px; color:var(--muted); font-size:13px; }}
</style></head>
<body><main>
<h1>World Bank country indicators</h1>
<p class="muted">The answers to the brief's four questions, from the published warehouse's
reporting tables.</p>
<nav><a href="#completeness">Completeness</a><a href="#year-over-year">Year over year</a>
<a href="#latest">Latest year</a><a href="#income-groups">Income groups</a></nav>
{_completeness(tables["rpt_completeness_by_cell"], tables["rpt_completeness_by_series"])}
{_year_over_year(tables["rpt_year_over_year"])}
{_latest(tables["rpt_latest_year_by_country"], tables["rpt_latest_common_year"])}
{_income_groups(tables["rpt_income_group_by_year"])}
<footer>Source: World Bank API, World Development Indicators. Missing values are never shown as
0. The same tables are exported as CSV to <code>data/outputs/</code>.</footer>
</main></body></html>
"""
