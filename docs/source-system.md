# Source System: World Bank API v2

How the source behaves, verified against the live API on **2026-11-24**. Each finding includes a request that reproduces it. This document records facts about the source; it doesn't prescribe a design.

- **Base URL:** `https://api.worldbank.org/v2`
- **Docs:** [API basic call structures](https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures)
- **Access:** public; no account or key.
- **Dataset:** World Development Indicators (WDI) is `source=2`.

## 1. Endpoints relevant to the requirements

| Purpose | Request | Pipeline name |
|---|---|---|
| Country metadata (FR-ING-1) | `/country/BRA;CAN;DEU;GBR;IND;JPN;MEX;USA;ZAF?format=json&per_page=50` | `countries` |
| Indicator metadata | `/indicator/SP.POP.TOTL?format=json` | `indicators` |
| Indicator values by country (FR-ING-2) | `/country/BRA;CAN;…/indicator/SP.POP.TOTL?format=json&date=2018:2024&per_page=1000&source=2` | `observations` |
| Historical releases ("vintages") | `/sources/57/country/{iso3}/series/{code}/time/YR{year}/version/{yyyymm}?format=json` | not used by the pipeline |

**Why the pipeline names differ from the API paths.** The API doesn't name its endpoints, only URL paths, and its documentation groups both indicator calls under "indicator queries". The values call isn't a separate resource: it's `indicator` nested under `country`. Naming landing folders after the path would give two calls named `indicator`, one returning a definition and one returning values. The pipeline therefore names each call by what it returns: `countries` (country metadata), `indicators` (indicator metadata), and `observations` (one value per country, indicator and year). These names appear in landing paths (`endpoint=<name>/`), manifests, and raw tables.

Several countries can be requested in one call, separated by `;`. Several indicators can be too, when `source` is given: `/country/BRA;IND/indicator/SP.POP.TOTL;NY.GDP.MKTP.CD?format=json&source=2` returns both indicators, but `meta.sourceid` comes back as `null` in that case.

## 2. Response shape

Successful responses are a two-element array, `[meta, data]`:

```json
[
  {"page": 1, "pages": 1, "per_page": 1000, "total": 72, "sourceid": "2", "lastupdated": "2026-11-11"},
  [
    {"indicator": {"id": "SP.POP.TOTL", "value": "Population, total"},
     "country": {"id": "BR", "value": "Brazil"},
     "countryiso3code": "BRA", "date": "2024", "value": 211998573,
     "unit": "", "obs_status": "", "decimal": 0}
  ]
]
```

- **Paging:** read `meta.pages` and request `&page=N`. For example, 72 rows with `per_page=5` gives 15 pages.
- **Inconsistent types:** `per_page` is a number on the observations endpoint (`1000`) but a string on the country and indicator endpoints (`"50"`).
- **`date` is a string** (`"2024"`).
- **Country codes:**
  - The country endpoint's `id` is ISO3 (`"BRA"`).
  - In observations, `country.id` is **ISO2** (`"BR"`) and `countryiso3code` is ISO3 (`"BRA"`).
- **Untrimmed strings:** some region names have trailing spaces (`"Latin America & Caribbean "`, `"Sub-Saharan Africa "`).
- `unit` and `obs_status` are usually empty strings.

## 3. Errors are returned with HTTP 200

An invalid country or indicator code doesn't produce a 4xx status. It returns **HTTP 200** with an error body:

```json
[{"message": [{"id": "120", "key": "Invalid value", "value": "The provided parameter value is not valid"}]}]
```

Reproduce with `/country/BRZ/indicator/SP.POP.TOTL?format=json` or `/country/BRA/indicator/XX.FAKE.CODE?format=json&source=2`. The status code alone can't tell success from failure.

## 4. An unsatisfiable `date` filter is silently ignored

A date range with no data doesn't return an empty result. The API **drops the filter and returns every available year**.

Reproduce with `/country/BRA/indicator/SP.POP.TOTL?format=json&date=1900:1901&source=2`: it returns 66 rows covering 1960–2025.

The response can therefore contain years outside the requested range.

## 5. Data beyond the requested scope exists

Values for **2025** are already published (see §4), so the source has years beyond the brief's 2018–2024 range.

## 6. Missing values

A missing observation can appear in two ways:
- a row with `"value": null`
- no row at all for that country and year

For the brief's scope (9 countries × 4 indicators × 2018–2024), **all values were present** as of `lastupdated` 2026-11-11. Missing-data behavior can't currently be observed in live data for this scope.

## 7. Past values are revised silently

The World Bank publishes WDI as periodic releases, and each release can **change values for past years**. The regular API (`source=2`) returns only the current value. There's no per-value revision flag or changelog, only one `lastupdated` date for the whole source. Re-fetching the same country, indicator and year at a later date can return a different number.

**Evidence** from the WDI Database Archives (`source=57`), which keeps past releases:

| Indicator | Country, year | Release | Value |
|---|---|---|---|
| GDP, current US$ (`NY.GDP.MKTP.CD`) | Brazil 2018 | 2020-07 | 1,885,482,534,238.33 |
| | | 2021-07 | 1,916,947,014,067.55 (**+1.7%**) |
| | | 2022-07 | 1,916,933,708,381.89 |
| | | 2024-07 | 1,916,933,898,038.36 |
| | | 2025-07 → current | 1,916,933,898,010.99 |
| Population (`SP.POP.TOTL`) | India 2019 | 2021-07 | 1,366,417,756 |
| | | 2023-07 | 1,383,112,050 |
| | | 2025-07 → current | 1,389,030,312 (**+22.6 M vs 2021, +1.7%**) |
| Life expectancy (`SP.DYN.LE00.IN`) | India 2019 | 2021-07 | 69.656 |
| | | 2023-07 | 70.910 |
| | | 2025-07 → current | 70.746 (revised **down**) |

Reproduce with, for example, `/sources/57/country/IND/series/SP.POP.TOTL/time/YR2019/version/202107?format=json`. The available releases are listed at `/sources/57/version?format=json`.

**Why it happens:**
- GDP is revised as countries revise and rebase their national accounts.
- Population and life expectancy come largely from the UN World Population Prospects, which re-estimates entire historical series in each edition. The indicator metadata describes population values as "midyear estimates".

**Consequences for any consumer of this API:**
- A value fetched today may differ from the same value fetched later. "Unchanged source data" can't be assumed between runs.
- Fetching only new years misses revisions to past years.
- The only change signal the API offers is the source-level `meta.lastupdated` date.

## 8. Income classification is current only

The country endpoint returns `incomeLevel` (for example `{"id": "UMC", "value": "Upper middle income"}`). This is the **current** classification. The World Bank reclassifies countries every July 1, but the endpoint has no history by year. As of 2026-11-24:

| Income level | Countries |
|---|---|
| High income (HIC) | CAN, DEU, GBR, JPN, USA |
| Upper middle income (UMC) | BRA, MEX, ZAF |
| Lower middle income (LMC) | IND |
