# World Bank country indicators pipeline

A local, configuration-driven pipeline that fetches country indicators from the World Bank API, keeps every API response exactly as received, and builds a tested warehouse that answers four analytics questions. It covers 9 countries × 4 indicators × 2018–2024, all set in configuration.

- **Answers:** [`data/outputs/`](data/outputs/), one CSV per question (see [What you get](#what-you-get)).
- **Requirements, decisions, source behavior:** [`docs/requirements.md`](docs/requirements.md), [`docs/decisions.md`](docs/decisions.md) (ADR-0001 to ADR-0034), [`docs/source-system.md`](docs/source-system.md).

## Quick start

Prerequisite: [uv](https://docs.astral.sh/uv/). It installs Python 3.14 and every dependency; nothing else is needed, and no account or credential is used.

```sh
git clone <this repository> && cd ha-lateral-data-engineer
uvx --from rust-just just run
```

`just run` is the whole pipeline: it fetches the configured scope from the API, rebuilds and tests the warehouse, publishes it only if every test passed, and exports the reports to `data/outputs/`. `uvx` runs `just` without installing it; with `just` installed (`uv tool install rust-just`), `just run` is enough.

| Command | Without `just` | Does |
|---|---|---|
| `just run` | the four commands below, in order | the whole pipeline (calls the live API) |
| n/a | `uv run worldbank extract` | fetch from the API and commit a landing run |
| `just build` | `uv run worldbank load`, `uv run dbt build --project-dir pipelines/worldbank/dbt --profiles-dir pipelines/worldbank/dbt`, `uv run worldbank publish` | rebuild the warehouse from landed runs, offline; publish only if every dbt test passes |
| `just export` | `uv run worldbank export` | write every report table to `data/outputs/*.csv` |
| `just check` | see the `justfile` | lint (Python and SQL), types, and all tests, offline: the definition of done |

The warehouse is `data/warehouse/worldbank.duckdb`; open it with any DuckDB client. `uv run worldbank --help` lists every command and option, including `--log-format json` and `load --as-of <run_id>` (rebuild as of an earlier run).

## What you get

| Question (brief §3) | Table, and CSV in `data/outputs/` | Grain |
|---|---|---|
| Which country-indicator-year combinations are missing or incomplete? | `rpt_completeness_by_cell`: every expected cell's status (`present`, `null_value`, `missing_row`) | country × indicator × year |
| | `rpt_completeness_by_series`: `complete`, `incomplete` or `missing` over the years, with counts | country × indicator |
| What is the year-over-year change, handling missing or zero prior values? | `rpt_year_over_year`: absolute and percent change, or null with `null_change_reason` | country × indicator × year |
| How do countries compare for the latest available year? | `rpt_latest_year_by_country`: each country at its own latest year, shown, and ranked | country × indicator |
| | `rpt_latest_common_year`: everyone at the latest year all countries have | country × indicator |
| How do indicators compare across income groups, by year? | `rpt_income_group_by_year`: aggregated by each indicator's method, with coverage counts | income group × indicator × year |

With today's data every series is complete, so `null_value`, `missing_row` and most null-change reasons appear only in the tests that prove them (dbt unit tests and crafted API scenarios).

## How it works

```
World Bank API ─extract─▶ landing zone ─load─▶ raw ─dbt─▶ staging ─▶ intermediate ─▶ marts ─▶ reporting ─export─▶ CSV
                          data/raw/worldbank/        └──────────── worldbank.next.duckdb ───────────┘
                          (exact responses,               audited by dbt tests, then published
                           one folder per run)            as worldbank.duckdb by an atomic rename
```

| Step | Done by | Rule |
|---|---|---|
| Extract | Python (`source/`) | the only step that calls the API; pages, retries (honouring `Retry-After`), response contracts, scope checks; a run counts only when its manifest is written last, so a failed run leaves nothing (ADR-0003 to ADR-0005, ADR-0007) |
| Land | Python (`storage/`) | every response kept byte for byte with its sha256; runs are immutable and never deleted (ADR-0004, ADR-0006) |
| Load | Python (`warehouse/`) | verifies every file's size and sha256, then copies all committed runs into `raw` set-based, like `COPY INTO` from a stage (ADR-0020) |
| Transform and test | dbt | staging, intermediate, marts, reporting; unit tests, data tests and the consistency check (ADR-0016, ADR-0026) |
| Publish | Python (`warehouse/`) | replaces the live warehouse atomically, only after a successful `dbt build`: write-audit-publish (ADR-0007, ADR-0023) |
| Export | Python (`warehouse/`) | every report table of the published warehouse to CSV (ADR-0034) |

**Layers,** and their medallion equivalents (ADR-0033): each reads only the layer below it, and only intermediate models read their own layer (ADR-0026, ADR-0027; enforced by a test).

| Layer | Holds | Medallion |
|---|---|---|
| landing zone and `raw` | API responses exactly as received, every run | bronze |
| `staging` | per source entity: flattened, renamed, typed, cleaned | silver |
| `intermediate` | the logic: latest run, cell status, value history, aggregation methods | silver |
| `marts` | the star schema analysts query | gold |
| `reporting` | the answers | gold |

## Data model

The marts are a current-state star schema (ADR-0017, ADR-0028 to ADR-0032): one fact and two dimensions, at natural keys, latest run only.

```
dim_countries ──────────── fct_country_indicator_values ──────────── dim_indicators
  country_id (PK)            country_id (FK)                          indicator_id (PK)
  country_iso2, name         indicator_id (FK)                        name, unit, source, definition
  region_id, region_name     observation_year                         source_lastupdated ("data as of")
  income_group_id, _name     indicator_value                          display_decimals
  income_group_sort_order    value_status                             aggregation_method and its
                             obs_status                               numerator, denominator and
                             source_response_id (lineage)             weight indicators (FK → itself)
```

| Table | Grain | Key | Relationships |
|---|---|---|---|
| `fct_country_indicator_values` | one expected country × indicator × year | (`country_id`, `indicator_id`, `observation_year`) | → `dim_countries`, `dim_indicators` |
| `dim_countries` | one configured country | `country_id` (ISO 3166-1 alpha-3) | n/a |
| `dim_indicators` | one configured indicator | `indicator_id` | aggregation inputs → `dim_indicators` |

- **Every expected cell is a row,** including the ones the API didn't return: `value_status` says `present`, `null_value` or `missing_row`, and `indicator_value` is null unless present. Missing is never zero (NFR-3, ADR-0008).
- **One long fact:** a new indicator is new rows, not a new column. The value is additive for population and GDP but not for GDP per capita or life expectancy; `dim_indicators.aggregation_method` says how to combine each.
- **Lineage:** each row carries one technical column, `source_response_id`, the landed page it came from, which is also its file path. Runs, pages and the history of revised values stay in intermediate, for engineers; [`trace_value.sql`](pipelines/worldbank/dbt/analyses/trace_value.sql) traces any value (NFR-1).
- Every model's grain, key and relationships are also stated in its dbt YAML and enforced by tests.

## Data quality and tests

- **At extract:** response contracts (a value is a number or null, never coerced), row totals across pages, consistent pages (refetched once if the source changed mid-request), and scope checks (only the requested countries, years and indicator, no duplicates). Unknown API fields are warnings, recorded in the manifest.
- **On every build (dbt, before publish):** keys and relationships; status, value and lineage agree; the fact covers exactly the expected set; current values come from the latest run; **GDP per capita within 0.1% of GDP ÷ population** (FR-DQ-2, ADR-0010, for every ratio indicator); every indicator has an aggregation method.
- **dbt unit tests** for every model with logic, including the cases live data doesn't show: null values, missing rows, revisions, every year-over-year reason, all aggregation methods.
- **`just check`:** ruff, SQLFluff, mypy and pytest with a 95% line-and-branch coverage gate, all offline. The tests replay recorded API responses and crafted scenarios (errors returned with HTTP 200, torn pages, retries, revisions), and one test runs the whole chain, `dbt build` included.

## Assumptions

How the brief's open questions are resolved ([requirements §9](docs/requirements.md#9-open-questions-ambiguities-in-the-source)):

- **Missing and incomplete** (Q1, ADR-0008): measured against the configured scope. A cell is `null_value` (row with a null) or `missing_row` (no row); a series is `incomplete` with some years present, `missing` with none.
- **Latest available year** (Q2, ADR-0009): each country's own latest year with a value, shown, plus a separate like-for-like table at the latest year all countries share.
- **Income groups are the World Bank's current classification, applied to every year** (Q3, ADR-0011, ADR-0030). The API publishes only today's classification and the brief allows no other source. If a country changed group during 2018–2024, its earlier years are grouped with hindsight; whether any of the nine did can't be verified through the API. The lower-middle-income group is India alone.
- **Income-group aggregation** (Q4, ADR-0009): population and GDP are summed; GDP per capita is Σ GDP ÷ Σ population (not an average of ratios); life expectancy is weighted by population. Only countries with the data their method needs contribute, and the coverage counts say how many.
- **2018's year-over-year change** (Q5, ADR-0009) is null with `prior_out_of_scope`: 2017 isn't fetched.
- **Consistency tolerance** (Q6, ADR-0010): 0.1%; the largest difference measured on live data was below 0.000001%.
- **Revised values** (Q7, ADR-0006): the World Bank revises past values silently, so every run fetches the full scope and the latest committed run wins; older values stay in the landing zone and the value history.

## Key decisions

The decisions that shape the project, with their records:

1. **Land first, replay everything else** (ADR-0003, ADR-0006). Only extract calls the API; it keeps every response exactly as received. The warehouse is a rebuildable cache, so models can change freely and tests never need the network.
2. **All or nothing, twice** (ADR-0004, ADR-0007). A run counts only when its manifest is written last; a warehouse goes live only after every dbt test passed. Analysts never see a partial run or an untested build.
3. **Contracts at the boundary, integrity on load** (ADR-0005, ADR-0020). Responses are validated before a run commits; afterwards, a matching sha256 proves the bytes are the validated ones.
4. **Each tool does one job** (ADR-0022, ADR-0034). Python extracts, loads, publishes and exports; dbt transforms and tests; `just` orders them, as an orchestrator's DAG would.
5. **Hand-written extraction instead of dlt** (ADR-0019). Lineage rests on exact response pages and the page metadata, which a framework that yields records doesn't keep.
6. **Logic in intermediate, a small star schema for analysts** (ADR-0026 to ADR-0032). Every rule lives once, unit-tested; analysts see one fact and two dimensions.
7. **Missing is a status, not a gap** (ADR-0008). The fact is built on the expected set, so every question about gaps is a filter.

## Trade-offs

- **Full fetch every run** instead of incremental loading: simple and catches silent revisions, but grows with history (ADR-0006); production would compact old runs and refresh when the source's release date changes.
- **DuckDB stands in for Snowflake:** dialect-specific SQL is confined to staging and the loader, so most models port by switching the dbt adapter, but differences can't all be caught locally (ADR-0001).
- **Current income classification for every year:** the only option the brief allows, stated instead of modelled (ADR-0030).
- **Publish trusts the task order:** `publish` doesn't re-check the audit; `just build` (or an orchestrator) guarantees dbt ran first. A record of the dbt run inside the build would close the manual-publish gap (ADR-0023).
- **No orchestrator, no container:** `just` orders the steps locally; scheduling belongs to production (ADR-0001).

## Adding a country or indicator

Configuration only (NFR-4):

1. Add the code to `scope.countries` or `scope.indicators` in [`pipelines/worldbank/config.yml`](pipelines/worldbank/config.yml). Codes are validated against the API before anything is fetched.
2. **Indicators only:** add a row to [`seeds/indicator_aggregations.csv`](pipelines/worldbank/dbt/seeds/indicator_aggregations.csv) saying how it aggregates by income group (`sum`, `ratio` with its numerator and denominator, or `weighted_mean` with its weight). The build fails if it's missing, and a `ratio` indicator is automatically checked against its parts.
3. Run `just run`. The expected set, every model and every report extend on their own.

## Production design note

### Scheduling and incremental refreshes
- An orchestrator (Airflow or Dagster) runs the same four tasks as `just run`: extract → load (`COPY INTO` or Snowpipe from S3) → `dbt build` → swap, with per-task retries. A daily schedule is plenty: the World Bank releases a few times a year.
- Refreshes are triggered by the source's `lastupdated` changing, but still re-fetch the whole window, since revisions are silent (ADR-0006). Raw loads become incremental (one new run at a time); old landing runs are compacted or tiered to cold storage, keeping their manifests for audit.
- In CI, `dbt build` runs against a Snowflake CI schema (slim CI on changed models), with the same unit and data tests.

### Late, corrected or changed source data
- Every run is a complete snapshot and the latest wins, so corrections land automatically; the value history (`int_indicator_values_versioned`) records each revision.
- A spike in revisions, new API fields (recorded as warnings) or a coverage drop raises a warning alert; a contract violation stops the extract before anything is committed.

### Monitoring, alerting and data-quality failures
- **Logs:** every step logs structured events (ADR-0024); `--log-format json` sends one object per line to CloudWatch or Datadog, and `run_id` reconstructs a run end to end.
- **Metrics:** requests, retries and latency per run; rows per indicator; extract and build duration; **freshness** (time since the last committed run, and each indicator's `source_lastupdated`).
- **Data quality:** dbt tests gate every publish; `run_results.json` is stored per build to trend failures; coverage (`missing_row`, `null_value`) and revision rates are compared with the previous run.
- **Alerting:**

  | Severity | When |
  |---|---|
  | Page | extract failed after its retries; a dbt test failed, so publish was refused; no committed run within the freshness SLA (for example 26 hours for a daily schedule) |
  | Warn | retries above a threshold; new API fields; a spike in revisions; a drop in coverage |

- **Investigating:** nothing is lost on failure: landed runs are immutable and the failed build is kept. `worldbank load --as-of <run_id>` plus `dbt build` rebuilds any past state, and `trace_value.sql` traces a value to its page, run and history.

### Backfills and replay
- The landing zone is the system of record: any warehouse state is a replay of committed runs (`load --as-of`), with no API call.
- Extending the scope (an earlier year, a new country) is a configuration change and one run; the expected set of each run comes from the configuration recorded with it, so older runs keep their own scope (ADR-0016).

### Mapping to Snowflake and AWS
| Local | Production |
|---|---|
| landing zone on disk | S3 bucket, same layout; the manifest upload is the atomic commit |
| `worldbank extract` | a Python task (AWS Glue Python shell, Lambda or a container); with many sources, an EL framework such as dlt, keeping the landing conventions (ADR-0019) |
| `worldbank load` | `COPY INTO` or Snowpipe from an S3 stage with an explicit file list; or AWS Glue/EMR (Spark) writing Iceberg tables Snowflake reads |
| DuckDB layers as schemas | Snowflake databases per layer and schemas per domain (`MARTS.<DOMAIN>.…`), with grants per layer: analysts read marts and reporting only |
| `.next` file, atomic rename | build in a cloned schema, test, then `ALTER SCHEMA … SWAP WITH` (or Iceberg branches) |
| `just` | the orchestrator's DAG |

## Unfinished work and next steps

- **NFR-2 end to end:** reruns are proven idempotent at landing and load (identical bytes, fresh rebuilds); a test that two builds from the same runs give identical reports would prove it at the output.
- **NFR-4 demo:** a test that adds a country and an indicator through configuration only and checks every report extends.
- **Crafted scenarios through dbt:** the end-to-end test uses recorded data, where everything is present; running the null, missing and revision scenarios through dbt would complement the dbt unit tests.
- **Optional extras** (brief, FR-ANA-5): a dashboard or extra view.

## AI usage

Built with Claude Code (Anthropic) as a pair programmer. The engineer set the direction and made the calls: the requirements, every decision in the ADR log (several reversed after discussion, which the log records), and the review of every commit. The assistant drafted code, tests, SQL and documentation, ran the checks, and proposed options with trade-offs. [`AGENTS.md`](AGENTS.md) is the guide any agent or person follows in this repository. Everything was verified the same way: `just check` and real runs against the recorded and live API.
