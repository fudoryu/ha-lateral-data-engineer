# World Bank Country Indicators Pipeline

This repository is my submission for the data engineering take-home assessment. It's a local, configuration-driven pipeline that fetches country indicators from the World Bank API, keeps every API response exactly as received, and builds a tested warehouse that answers the four analytics questions in the brief. The scope is 9 countries × 4 indicators × 2018–2024, and all of it lives in configuration.

Below I explain how to run it, what it produces, how I designed it and why, and how I would operate it in production.

**Where to look first:**

- [`reports/report.html`](reports/report.html): the four answers on one page, with charts (open it in a browser).
- [`data/outputs/`](data/outputs/): the same answers as CSV, one file per reporting table.
- [Data model](#data-model) and [Key decisions](#key-decisions), below.
- [`docs/decisions.md`](docs/decisions.md): every design decision as an ADR (ADR-0001 to ADR-0036), with the alternatives I considered. [`docs/requirements.md`](docs/requirements.md) restates the brief as numbered requirements with a traceability matrix, and [`docs/source-system.md`](docs/source-system.md) documents how the API actually behaves, as I measured it.

## Running it

The only prerequisite is [uv](https://docs.astral.sh/uv/). It installs Python 3.14 and every dependency, and no account or credential is needed anywhere.

```sh
git clone <this repository> && cd ha-lateral-data-engineer
uvx --from rust-just just run
```

`just run` executes the whole pipeline: it fetches the configured scope from the API, rebuilds and tests the warehouse, publishes it only if every test passed, exports the reporting tables to `data/outputs/` and renders `reports/report.html`. `uvx` ships with uv and runs `just` without installing it; it's short for `uv tool run --from rust-just just run`, which works with the `uv` command alone. With `just` installed (`uv tool install rust-just`), `just run` is enough.

I verified this on a fresh clone with empty uv caches: uv downloads Python and every dependency, the run completes, and the regenerated outputs are byte-identical to the committed ones.

| Command | Without `just` | What it does |
|---|---|---|
| `just run` | the commands below, in order | the whole pipeline (calls the live API) |
| `just extract` | `uv run worldbank extract` | fetches from the API and commits a landing run |
| `just build` | `uv run worldbank load`, `uv run dbt build --project-dir pipelines/worldbank/dbt --profiles-dir pipelines/worldbank/dbt`, `uv run worldbank publish` | rebuilds the warehouse from landed runs, offline; publishes only if every dbt test passes |
| `just export` | `uv run worldbank export` | writes every reporting table to `data/outputs/*.csv` |
| `just report` | `uv run worldbank report` | renders the four answers as one HTML page, `reports/report.html` |
| `just check` | see the `justfile` | Python and SQL lint, types and every test, offline: my definition of done |

The warehouse is `data/warehouse/worldbank.duckdb` and opens in any DuckDB client. `uv run worldbank --help` lists every command and option, including `--log-format json`, `load --as-of <run_id>` to rebuild the warehouse as of an earlier run, and scope overrides for a single run, for example `just run --countries BRA,IND --indicators SP.POP.TOTL --years 2020:2024` (ADR-0035).

## What it produces

[`reports/report.html`](reports/report.html) presents all four answers on one page. Behind it are six reporting tables, each exported to `data/outputs/`:

| Question in the brief | Table | Grain |
|---|---|---|
| Which country-indicator-year combinations are missing or incomplete? | `rpt_completeness_by_cell`: every expected cell with its status (`present`, `null_value`, `missing_row`) | country × indicator × year |
| | `rpt_completeness_by_series`: `complete`, `incomplete` or `missing` across the years, with counts | country × indicator |
| What is the year-over-year change, handling missing or zero prior values? | `rpt_year_over_year`: absolute and percent change, or null with a `null_change_reason` | country × indicator × year |
| How do the countries compare for the latest available year? | `rpt_latest_year_by_country`: each country at its own latest year, shown and ranked | country × indicator |
| | `rpt_latest_common_year`: every country at the latest year they all share | country × indicator |
| How do the indicators compare across income groups, by year? | `rpt_income_group_by_year`: the average of each group's countries, with coverage counts | income group × indicator × year |

With today's data every series in scope is complete, so `null_value`, `missing_row` and most null-change reasons appear only in the tests that prove them. To see how the pipeline behaves with real gaps, I also ran it on a wider, random scope (see [Beyond the brief](#beyond-the-brief)).

## How I built it

```
World Bank API ─extract─▶ landing zone ─load─▶ raw ─dbt─▶ staging ─▶ intermediate ─▶ marts ─▶ reporting ─▶ CSV + HTML
                          data/raw/worldbank/        └──────────── worldbank.next.duckdb ───────────┘
                          (exact responses,               audited by dbt tests, then published
                           one folder per run)            as worldbank.duckdb by an atomic rename
```

| Step | Done by | What I made sure of |
|---|---|---|
| Extract | Python (`source/`) | It's the only step that calls the API. It follows every page, retries transient failures (honouring `Retry-After`), validates every response against explicit contracts, and checks that each response answers its request. A run counts only once its manifest is written last, so a failed run leaves nothing behind (ADR-0003 to ADR-0005, ADR-0007). |
| Land | Python (`storage/`) | Every response is kept byte for byte, with its sha256. Committed runs are immutable and never deleted (ADR-0004, ADR-0006). |
| Load | Python (`warehouse/`) | It verifies every file's size and sha256, then copies all committed runs into `raw` set-based, the local equivalent of `COPY INTO` from a stage (ADR-0020). |
| Transform and test | dbt | Staging, intermediate, marts and reporting, with unit tests, data tests and a cross-indicator consistency check (ADR-0016, ADR-0026). |
| Publish | Python (`warehouse/`) | The live warehouse is replaced atomically, and only after a successful `dbt build`: write-audit-publish (ADR-0007, ADR-0023). |
| Export and report | Python (`warehouse/`) | The published reporting tables become CSV files and one HTML page (ADR-0034, ADR-0036). |

Each dbt layer reads only the layer directly below it, and only intermediate models may read their own layer; a test enforces this (ADR-0026, ADR-0027). For readers who think in medallion terms (ADR-0033):

| Layer | Holds | Medallion |
|---|---|---|
| landing zone and `raw` | API responses exactly as received, every run | bronze |
| `staging` | per source entity: flattened, renamed, typed and cleaned | silver |
| `intermediate` | the logic: latest run, cell status, value history | silver |
| `marts` | the star schema analysts query | gold |
| `reporting` | the answers | gold |

## Data model

The marts are a current-state dimensional model: one fact and four dimensions at natural keys, holding the latest run only; a country reaches its region and income group through `dim_countries` (ADR-0017, ADR-0028 to ADR-0032, ADR-0039, ADR-0040).

```
  dim_regions             dim_countries           fct_country_indicator_values    dim_indicators
    region_id (PK)          country_id (PK)         country_id (FK)                 indicator_id (PK)
    region_name             country_iso2            indicator_id (FK)               indicator_name
                            country_name            observation_year                definition
  dim_income_groups         region_id (FK)          indicator_value                 source_organization
    income_group_id (PK)    income_group_id (FK)    value_status                    source_lastupdated
    income_group_name                               source_response_id

  fct → dim_countries → dim_regions, dim_income_groups;  fct → dim_indicators
```

| Table | Grain | Key | Relationships |
|---|---|---|---|
| `fct_country_indicator_values` | one expected country × indicator × year | (`country_id`, `indicator_id`, `observation_year`) | → `dim_countries`, `dim_indicators` |
| `dim_countries` | one configured country | `country_id` (ISO 3166-1 alpha-3) | → `dim_regions`, `dim_income_groups` |
| `dim_regions` | one region of the configured countries | `region_id` (World Bank region code) | n/a |
| `dim_income_groups` | one income group of the configured countries | `income_group_id` (World Bank income group code) | n/a |
| `dim_indicators` | one configured indicator | `indicator_id` | n/a |

- **Every expected cell is a row,** including those the API didn't return. `value_status` records `present`, `null_value` or `missing_row`, and `indicator_value` is null unless the value is present. Missing is never zero (NFR-3, ADR-0008).
- **I chose one long fact table,** so a new indicator adds rows, not columns, and every report works on any indicator without per-indicator setup.
- **Lineage is a platform concern, not an analyst one.** Only the fact carries a technical column, `source_response_id`, which names the landed page the value came from and is also its file path. Dimensions hold business attributes only. Runs, pages, the history of revised values and the dimensions' lineage stay in intermediate for engineers (ADR-0042), and [`trace_value.sql`](pipelines/worldbank/dbt/analyses/trace_value.sql) traces any value back to its source (NFR-1).
- Every model's grain, key and relationships are also documented in its dbt YAML and enforced by tests.

## Data quality and testing

- **At extract:** response contracts (a value is a number or null, never coerced), row totals across pages, page consistency (a request is refetched once if the source changed mid-request), and scope checks (only the requested countries, years and indicator, with no duplicates). Unknown API fields are recorded as warnings in the manifest.
- **On every build, before publish:** keys and relationships; agreement between status, value and lineage; the fact covering exactly the expected set; current values coming from the latest run; and **GDP per capita within 0.1% of GDP ÷ population** (FR-DQ-2, ADR-0010).
- **dbt unit tests** for every model with logic, including the cases live data doesn't show: null values, missing rows, revisions, every year-over-year reason and income groups with partial or no data.
- **`just check`** runs ruff, SQLFluff, mypy and pytest with a 95% line-and-branch coverage gate, all offline. The tests replay recorded API responses and crafted scenarios (errors returned with HTTP 200, torn pages, retries, revisions), and end-to-end tests run the whole chain, `dbt build` included, to prove idempotency and configuration-only scope changes.
- **CI** (GitHub Actions) runs every pre-commit hook on every file, including a secret scan, checks each pushed commit's message against Conventional Commits, and runs `just check`.

## Assumptions

The brief leaves several questions open. I resolved them as follows ([requirements §9](docs/requirements.md#9-open-questions-ambiguities-in-the-source)):

- **Missing and incomplete** (Q1, ADR-0008): I measure against the configured scope. A cell is `null_value` (a row with a null) or `missing_row` (no row); a series is `incomplete` when some years are present and `missing` when none are.
- **Latest available year** (Q2, ADR-0009): each country at its own latest year with a value, with the year shown, plus a separate like-for-like table at the latest year all countries share.
- **Income groups are the World Bank's current classification, applied to every year** (Q3, ADR-0011, ADR-0030). The API publishes only today's classification, and the brief allows no other source. If a country changed group during 2018–2024, its earlier years are grouped with hindsight; whether any of the nine did can't be verified through the API. Note that the lower-middle-income group contains India alone.
- **Income-group aggregation** (Q4, ADR-0038): each group's value is the average of its countries that have a value, the same rule for every indicator. It describes the typical country in the group, not the group's total, so it's an average population rather than a total, and an average of GDP per capita rather than Σ GDP ÷ Σ population. The coverage counts say how many countries contributed.
- **The 2018 year-over-year change** (Q5, ADR-0009) is null with the reason `prior_out_of_scope`, because 2017 isn't fetched.
- **Consistency tolerance** (Q6, ADR-0010): 0.1%. The largest difference I measured on live data was below 0.000001%.
- **Revised values** (Q7, ADR-0006): the World Bank revises past values silently, so every run fetches the full scope and the latest committed run wins. Earlier values remain in the landing zone and the value history.

## Key decisions

The decisions I consider most important, each recorded with its alternatives:

1. **Land first, replay everything else** (ADR-0003, ADR-0006). Only extract calls the API, and it keeps every response exactly as received. The warehouse is a rebuildable cache, so models can change freely and tests never need the network.
2. **All or nothing, twice** (ADR-0004, ADR-0007). A run counts only when its manifest is written last, and a warehouse goes live only after every dbt test has passed. Analysts never see a partial run or an untested build.
3. **Contracts at the boundary, integrity on load** (ADR-0005, ADR-0020). I validate responses before a run commits; afterwards, a matching sha256 proves the bytes are the ones that were validated.
4. **Each tool does one job** (ADR-0022, ADR-0034). Python extracts, loads, publishes and exports; dbt transforms and tests; `just` orders the steps, as an orchestrator's DAG would.
5. **Hand-written extraction rather than dlt** (ADR-0019). My lineage rests on exact response pages and their metadata, which a framework that yields records doesn't preserve.
6. **Logic in intermediate, a small star schema for analysts** (ADR-0026 to ADR-0032). Every rule lives in one place and is unit-tested; analysts work with one fact and four dimensions.
7. **Missing is a status, not a gap** (ADR-0008). The fact table is built on the expected set, so every question about gaps becomes a filter.

## Trade-offs

- **A full fetch on every run** rather than incremental loading. It's simple and catches silent revisions, but it grows with history (ADR-0006). In production I would compact old runs and trigger refreshes from the source's release date.
- **DuckDB as a stand-in for Snowflake.** I confined dialect-specific SQL to staging and the loader, so most models port by switching the dbt adapter, but some differences can't be caught locally (ADR-0001).
- **The current income classification for every year.** It's the only option the brief allows, so I state it as an assumption rather than model around it (ADR-0030).
- **Publishing trusts the task order.** `publish` doesn't re-check the audit; `just build`, or an orchestrator, guarantees dbt ran first. Recording the dbt run inside the build would close the gap of a manual publish (ADR-0023).
- **No orchestrator and no container.** `just` orders the steps locally, and scheduling belongs to production (ADR-0001).

## Adding a country or indicator

This takes configuration only (NFR-4):

1. Add the code to `scope.countries` or `scope.indicators` in [`pipelines/worldbank/config.yml`](pipelines/worldbank/config.yml). Codes are validated against the API before anything is fetched.
2. Run `just run`. The expected set, every model and every report extend on their own, and an end-to-end test proves it.

To try a different scope once without editing the file, pass it on the command line: `just run --countries BRA,IND,ZAF --years 2020:2024`.

## Production design note

How I would operate this in production, following the five points in the brief. The local design already has the production shape (immutable landing, write-audit-publish, structured logs); each piece maps to a managed service.

### Scheduling and incremental refreshes
- An orchestrator (Airflow, for example MWAA on AWS, or Azure Data Factory) runs the same tasks as `just run`: extract, then load, then `dbt build`, then the swap, with retries per task. A daily schedule is more than enough: the World Bank publishes a few releases a year.
- **Incremental where it's safe:** the raw load is incremental, one new committed run at a time, and the orchestrator can skip the extract when no indicator's `lastupdated` has changed. The extract itself still fetches the whole window, because the World Bank revises past values silently (ADR-0006); at this volume that's a few requests a day. Old landing runs are compacted or moved to cold storage, keeping their manifests for audit.
- In CI, `dbt build` runs against a Snowflake CI schema, with slim CI for changed models and the same unit and data tests.

### Handling late, corrected, or changed source data
- **Late data** (a 2024 value published months later) and **corrections** need no special path: every run is a complete snapshot and the latest wins, so the next run picks them up, and `int_indicator_values_versioned` keeps every revision with the run that introduced it.
- **Changed structure** is caught at the boundary: a contract violation (a type change, a missing field, an error returned with HTTP 200, a response that doesn't match its request) stops the extract before anything is committed, so analysts keep the last good state. New, unknown fields are recorded as warnings in the manifest rather than failing the run.
- **Changed meaning** (a unit or definition change) is caught by the data tests, notably the cross-indicator check that GDP per capita stays within 0.1% of GDP ÷ population (ADR-0010).

### Monitoring, alerting, and data-quality failures
- **Logs:** every step emits structured events (ADR-0024); `--log-format json` gives one object per line for CloudWatch, Azure Monitor or Datadog, and `run_id` reconstructs a run end to end.
- **Metrics:** requests, retries and latency per run; rows per indicator; extract and build duration; and **freshness**: the time since the last committed run, and each indicator's `source_lastupdated`.
- **Data-quality failures block, they don't leak:** dbt tests gate every publish, so a failed test leaves the last good warehouse live, and the failed build is kept for inspection. `run_results.json` is stored per build to track failures over time, and coverage (`missing_row`, `null_value`) and revision rates are compared with the previous run.
- **Alerting:**

  | Severity | When |
  |---|---|
  | Page | the extract failed after its retries; a dbt test failed, so publishing was refused; no run was committed within the freshness SLA (for example 26 hours on a daily schedule) |
  | Warn | retries above a threshold; new API fields; a spike in revisions; a drop in coverage |

### Backfills and replay-ability
- **Replay:** the landing zone is the system of record, so any warehouse state, current or past, is a replay of committed runs (`worldbank load --as-of <run_id>`, then `dbt build`), with no API call. Changing a model and rebuilding history is the same operation.
- **Backfill:** extending the scope, whether an earlier year or a new country, is a configuration change and one run. Each run's expected set comes from the configuration recorded in its manifest, so older runs keep their own scope (ADR-0016).
- **Tracing:** `analyses/trace_value.sql` follows any published value to its landed page, its run and its revision history.

### Mapping to Snowflake plus AWS Glue or EMR, or Azure

| Local | Snowflake + AWS | Azure |
|---|---|---|
| landing zone on disk | S3, same layout; uploading the manifest last is the atomic commit | ADLS Gen2, same layout and commit rule |
| `worldbank extract` | a Python job: AWS Glue Python shell, Lambda or a container task | Azure Functions or a Container Apps job |
| `worldbank load` | `COPY INTO` or Snowpipe from an S3 external stage, with an explicit file list; or Glue/EMR (Spark) writing Iceberg tables that Snowflake reads | `COPY INTO` or Snowpipe from an ADLS stage (Snowflake on Azure); or Databricks or Fabric Spark writing Delta/Iceberg tables |
| dbt on DuckDB | dbt on Snowflake (dbt-snowflake), databases per layer and grants per layer, so analysts read only marts and reporting | the same on Snowflake on Azure; or dbt on Databricks, Fabric or Synapse |
| the `.next` file and the atomic rename | build in a cloned schema, test, then `ALTER SCHEMA … SWAP WITH` | the same on Snowflake; on Delta, publish by swapping views or tables after tests pass |
| `just` | Airflow (MWAA) or Step Functions | Azure Data Factory or Airflow |
| structured logs on stderr | CloudWatch | Azure Monitor (Log Analytics) |

## Beyond the brief

To see how the pipeline handles real gaps, I ran it on a random scope of 50 economies × 50 indicators, in a separate folder (findings in [source-system §6 and §9](docs/source-system.md#6-missing-values)). The API returned every row, but 45% of the values were null, a third of the series were entirely empty, and recent years lagged. All of it reached the reports as defined, never as 0. The exploration also surfaced two issues I fixed: indicator codes with underscores or lower case were rejected by my configuration rule, and some responses took longer than the read timeout.

## Unfinished work and next steps

The wider run also showed where my design is strict at scale:

- **A latest common year is rare across many countries** (3 of 50 indicators had one). A rule such as "the latest year with at least 90% coverage" would serve wide scopes better.
- **All-or-nothing extraction is costly at scale.** Stopping an all-indicator run discarded 712 fetched indicators, and a single stale code fails a run. In production I would checkpoint per indicator or resume interrupted runs, keeping the manifest as the commit.
- **An interactive dashboard** would be the next step beyond the HTML report (the brief's optional extra).

## How I used AI

I built this project with Claude Code (Anthropic) as a pair programmer. I set the direction and made the decisions: the requirements, the architecture and every entry in the ADR log, several of which I reversed after weighing the trade-offs (the log keeps them). The assistant drafted most of the code, tests, SQL and documentation, ran the checks, and laid out options with their trade-offs for me to choose from. [`AGENTS.md`](AGENTS.md) is the guide I wrote for it, and it applies equally to human contributors. I didn't take anything on trust: everything is verified by `just check`, in CI, and by real runs against the recorded and live API.
