# Decision Log

Architecture decision records (ADRs): one entry per significant decision or assumption. Each entry states the context, the decision, the alternatives considered, the consequences, and the requirements it serves ([`requirements.md`](requirements.md)). Evidence about the source lives in [`source-system.md`](source-system.md).

Entries are append-only. To change a decision, add a new entry that supersedes the old one, and mark the old one `Superseded by ADR-NNNN`.

| ID | Title | Kind | Status |
|---|---|---|---|
| [ADR-0001](#adr-0001-technology-stack) | Technology stack | Decision | Accepted (configuration library amended by ADR-0015) |
| [ADR-0002](#adr-0002-one-request-per-indicator-covering-all-countries) | One request per indicator, covering all countries | Decision | Accepted |
| [ADR-0003](#adr-0003-separate-ingestion-from-transformation-replay-from-landed-files) | Separate ingestion from transformation; replay from landed files | Decision | Accepted (command name amended by ADR-0018) |
| [ADR-0004](#adr-0004-a-landing-run-is-committed-by-writing-its-manifest-last) | A landing run is committed by writing its manifest last | Decision | Accepted (path amended by ADR-0014) |
| [ADR-0005](#adr-0005-validate-configuration-and-api-responses-before-committing-a-run) | Validate configuration and API responses before committing a run | Decision | Accepted (load-time re-validation removed by ADR-0020) |
| [ADR-0006](#adr-0006-fetch-the-full-scope-every-run-keep-every-run-latest-run-wins) | Fetch the full scope every run, keep every run, latest run wins | Decision | Accepted (§7's audience amended by ADR-0028) |
| [ADR-0007](#adr-0007-all-or-nothing-runs-and-write-audit-publish) | All-or-nothing runs and write-audit-publish | Decision | Accepted |
| [ADR-0008](#adr-0008-definitions-of-missing-and-incomplete-data) | Definitions of missing and incomplete data | Decision | Accepted |
| [ADR-0009](#adr-0009-analytics-interpretations-latest-year-income-group-aggregation-year-over-year) | Analytics interpretations: latest year, income-group aggregation, year-over-year | Decision | Accepted (income-group aggregation superseded by ADR-0038) |
| [ADR-0010](#adr-0010-gdp-consistency-check-with-a-01-tolerance) | GDP consistency check with a 0.1% tolerance | Decision | Accepted |
| [ADR-0011](#adr-0011-current-income-classification-applies-to-every-year) | Current income classification applies to every year | **Assumption** | Accepted (modelling amended by ADR-0030) |
| [ADR-0012](#adr-0012-test-fixtures-recorded-responses-plus-crafted-scenarios) | Test fixtures: recorded responses plus crafted scenarios | Decision | Accepted |
| [ADR-0013](#adr-0013-developer-tooling-and-documentation-layout) | Developer tooling and documentation layout | Decision | Accepted (recipe names amended by ADR-0018) |
| [ADR-0014](#adr-0014-one-project-per-pipeline-in-a-uv-workspace) | One project per pipeline in a uv workspace | Decision | Accepted |
| [ADR-0015](#adr-0015-configuration-is-loaded-with-plain-pydantic-and-pyyaml) | Configuration is loaded with plain Pydantic and PyYAML | Decision | Accepted |
| [ADR-0016](#adr-0016-dbt-project-layout-layers-and-naming) | dbt project layout, layers and naming | Decision | Accepted (mart names pluralized by ADR-0032; staging's job clarified by ADR-0033) |
| [ADR-0017](#adr-0017-marts-data-model-grain-keys-relationships-and-lineage) | Marts data model: grain, keys, relationships and lineage | Decision | Accepted (table list and lineage keys amended by ADR-0028; indicator columns trimmed by ADR-0037; regions and country columns by ADR-0039) |
| [ADR-0018](#adr-0018-pipeline-commands-extract-build-run) | Pipeline commands: extract, build, run | Decision | Superseded by ADR-0022 |
| [ADR-0019](#adr-0019-hand-written-extraction-instead-of-an-el-framework) | Hand-written extraction instead of an EL framework | Decision | Accepted |
| [ADR-0020](#adr-0020-load-verifies-integrity-not-contracts) | Load verifies integrity, not contracts | Decision | Accepted |
| [ADR-0021](#adr-0021-code-layout-source-storage-and-warehouse) | Code layout: source, storage and warehouse | Decision | Accepted |
| [ADR-0022](#adr-0022-python-stops-at-load-the-task-runner-orchestrates) | Python stops at load; the task runner orchestrates | Decision | Accepted (amended by ADR-0023 and ADR-0034) |
| [ADR-0023](#adr-0023-publish-trusts-the-orchestrators-order) | Publish trusts the orchestrator's order | Decision | Accepted |
| [ADR-0024](#adr-0024-structured-logging-with-the-standard-library) | Structured logging with the standard library | Decision | Accepted |
| [ADR-0025](#adr-0025-sql-style-and-linting-with-sqlfluff) | SQL style and linting with SQLFluff | Decision | Accepted |
| [ADR-0026](#adr-0026-each-dbt-layer-reads-only-its-own-layer-and-the-one-below) | Each dbt layer reads only its own layer and the one below | Decision | Accepted (amended by ADR-0027) |
| [ADR-0027](#adr-0027-only-intermediate-models-read-their-own-layer) | Only intermediate models read their own layer | Decision | Accepted |
| [ADR-0028](#adr-0028-marts-are-a-current-state-star-schema-for-analysts) | Marts are a current-state star schema for analysts | Decision | Accepted (income-group tables amended by ADR-0029; dimension lineage moved to intermediate by ADR-0042) |
| [ADR-0029](#adr-0029-the-fact-carries-the-income-group-that-applied-each-year) | The fact carries the income group that applied each year | Decision | Superseded by ADR-0030 |
| [ADR-0030](#adr-0030-income-group-is-a-country-attribute) | Income group is a country attribute | Decision | Accepted (a dimension of its own and no sort order, ADR-0040) |
| [ADR-0031](#adr-0031-the-fact-is-named-fct_country_indicator_value) | The fact is named fct_country_indicator_value | Decision | Accepted (pluralized by ADR-0032) |
| [ADR-0032](#adr-0032-every-table-name-is-plural) | Every table name is plural | Decision | Accepted |
| [ADR-0033](#adr-0033-staging-cleans-values-intermediate-interprets-them) | Staging cleans values; intermediate interprets them | Decision | Accepted |
| [ADR-0034](#adr-0034-report-tables-are-exported-to-csv-by-worldbank-export) | Report tables are exported to CSV by `worldbank export` | Decision | Accepted |
| [ADR-0035](#adr-0035-the-scope-can-be-overridden-for-one-run-on-the-command-line) | The scope can be overridden for one run on the command line | Decision | Accepted |
| [ADR-0036](#adr-0036-an-html-report-rendered-from-the-reporting-tables) | An HTML report rendered from the reporting tables | Decision | Accepted |
| [ADR-0037](#adr-0037-dim_indicators-keeps-only-columns-with-meaning) | dim_indicators keeps only columns with meaning | Decision | Accepted |
| [ADR-0038](#adr-0038-income-groups-average-their-countries) | Income groups average their countries | Decision | Superseded by ADR-0043 (the aggregation; the removed metadata stays removed) |
| [ADR-0039](#adr-0039-regions-get-their-own-dimension) | Regions get their own dimension | Decision | Accepted (income groups get a dimension too, ADR-0040; `country_iso2` restored by ADR-0041) |
| [ADR-0040](#adr-0040-income-groups-get-their-own-dimension) | Income groups get their own dimension | Decision | Accepted |
| [ADR-0041](#adr-0041-dim_countries-keeps-the-iso-alpha-2-code) | dim_countries keeps the ISO alpha-2 code | Decision | Accepted |
| [ADR-0042](#adr-0042-lineage-only-on-the-fact) | Lineage only on the fact | Decision | Accepted |
| [ADR-0043](#adr-0043-income-group-aggregates-written-out-in-the-report) | Income-group aggregates written out in the report | Decision | Accepted |
| [ADR-0044](#adr-0044-one-reporting-table-per-question) | One reporting table per question | Decision | Accepted |

---

## ADR-0001: Technology stack

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted (configuration library amended by [ADR-0015](#adr-0015-configuration-is-loaded-with-plain-pydantic-and-pyyaml))
- **Serves:** NFR-5 (local only), NFR-6 (reproducible from a clean checkout), FR-MOD-1, FR-DQ-1

### Context
The brief allows any stack, requires a local run with no cloud resources or accounts, and asks how the design maps to Snowflake plus AWS Glue/EMR. The data is small: 9 countries × 4 indicators × 7 years.

### Decision
| Layer | Choice |
|---|---|
| Runtime | Python **3.14**, pinned `>=3.14,<3.15`, managed by **uv** (the only prerequisite; uv installs Python itself) |
| Packaging | Application-style `pyproject.toml`, `src/` layout, `pipeline` entry point, committed `uv.lock`, dev dependency group |
| HTTP and retries | **requests** + **tenacity** |
| Validation and config | **Pydantic v2** + **pydantic-settings** |
| CLI | **Typer** |
| Warehouse | **DuckDB** (embedded, single file) |
| Transformation | **dbt-core** + **dbt-duckdb** |
| Tests and quality | **pytest** + **responses** (HTTP mocking), **mypy**, **ruff**; standard-library `logging` |
| Orchestrator | None |
| Container | None by default |

**Portability rule:** dialect-specific SQL lives only in the staging layer (JSON flattening) and the raw loader. Everything above staging is portable SQL and uses dbt cross-database macros where needed.

### Alternatives considered
- **Python 3.15:** released October 2026, but dbt doesn't support it yet (checked on PyPI 2026-11-24: dbt-core 1.12.7 and dbt-duckdb 1.11.1 list up to 3.14).
- **httpx:** nicer built-in test mocking, but no release since December 2024. requests is maintained and familiar.
- **Polars instead of DuckDB:** a DataFrame library, not a queryable warehouse. No dbt adapter, transformations wouldn't port to Snowflake, and serving would need a SQL engine anyway.
- **Iceberg tables locally:** an open table format with snapshots and WAP branches, but it adds a catalog and weak local dbt support for about 300 rows. Iceberg stays the storage design for the **production note** (S3 + Glue / Snowflake Open Catalog, with Snowflake reading the Iceberg tables).
- **SQLMesh instead of dbt:** built-in dialect transpilation, but less familiar to reviewers and a smaller Snowflake ecosystem.
- **An orchestrator (Airflow, Dagster):** a single linear pipeline doesn't need one locally. Scheduling belongs in the production note.
- **Docker:** uv already pins Python and dependencies. A uv-based Dockerfile is a stretch goal.
- **`ty` type checker:** still beta (0.0.x).

### Consequences
- A clean checkout needs only uv: `uv run pipeline …` works without anything else installed.
- About 90% of the transformation code ports to dbt-snowflake by switching the adapter. The rest is confined to staging and the loader by the portability rule.
- DuckDB is a local stand-in for Snowflake, made necessary by the no-cloud constraint. The production note must say that real development would use Snowflake dev schemas, since dialect differences can't be fully caught locally.

---

## ADR-0002: One request per indicator, covering all countries

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ING-1, FR-ING-2, FR-ING-3, NFR-4

### Context
Observations can be requested per country × indicator (36 requests for the current scope) or per indicator with every country in one call, since the API accepts `;`-separated country codes ([source-system §1](source-system.md#1-endpoints-relevant-to-the-requirements)). The API also has more than one dataset; World Development Indicators is `source=2`.

### Decision
- **Observations:** one request per configured indicator, covering all configured countries and the configured years:
  `/v2/country/{iso3;iso3;…}/indicator/{code}?format=json&date={start}:{end}&per_page=1000&source=2`
- **Metadata:** one request for all configured countries (`/v2/country/{iso3;…}`) and one per configured indicator (`/v2/indicator/{code}`).
- **Paging:** always follow `meta.pages`, even though the current scope fits in one page.
- **Dataset pinned:** `source=2` is always passed explicitly.

### Alternatives considered
- **One request per country × indicator:** finer-grained retries, but 36 requests now, and the count grows with every added country.
- **One request for all indicators:** the API supports it (`;`-separated indicator codes with `source=2`; verified 2026-11-24) and it would need the fewest requests. Rejected because one failure or retry would cover every indicator, `meta.sourceid` comes back `null` for multi-indicator calls, and per-indicator checks such as row counts against `meta.total` become coarser.

### Consequences
- The request count grows with indicators, not countries: 4 observation requests today. Countries are the more likely dimension to grow (NFR-4).
- A failed request affects every country for that indicator; a retry repeats just that one request.
- Paging matters only above 1000 rows per indicator (roughly 140 countries over 7 years), so tests must force paging with a small `per_page`.
- Pinning `source=2` means a change in the API's default dataset can't silently change results.

---

## ADR-0003: Separate ingestion from transformation; replay from landed files

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted (command name amended by [ADR-0018](#adr-0018-pipeline-commands-extract-build-run))
- **Serves:** FR-MOD-1, FR-DQ-3, NFR-1, NFR-2

### Context
Transformations must be re-runnable, debuggable and testable without the live API (FR-DQ-3). The raw source representation must stay separate from cleaned and analytics-ready data (FR-MOD-1). Values must trace back to the API response they came from (NFR-1).

### Decision
- **`extract` is the only step that calls the API.** It writes each response body, byte for byte, to a local landing zone under `data/raw/`.
- **Everything after extract reads only from the landing zone:** loading into the warehouse, transforming, exporting.
- A **`replay`** command runs load → transform → export from landed files with no network access.
- The landing zone is the **system of record**. The warehouse is a **rebuildable cache** derived from it.

### Alternatives considered
- **Fetch and transform in one pass (in memory):** fewer moving parts, but every transformation change or debugging session hits the API again, tests need the network or heavy mocking, and there's no stored response to trace values back to.
- **Load the API response straight into warehouse tables, with no files:** traceable, but the warehouse becomes the source of truth and can't be rebuilt from scratch, and the local design no longer mirrors an object-storage landing zone (S3) in production.

### Consequences
- Transformations can be changed and replayed freely, and the warehouse file can be deleted and rebuilt at any time.
- Tests exercise load and transform from landed files without the API.
- Locally, the landing zone maps directly to an S3 landing bucket in production.
- Needs a rule for when a landing run counts as complete; see the next decision.

---

## ADR-0004: A landing run is committed by writing its manifest last

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted (landing path amended by [ADR-0014](#adr-0014-one-project-per-pipeline-in-a-uv-workspace))
- **Serves:** FR-ING-4, NFR-1, NFR-2

### Context
Under ADR-0003, extract writes files to the landing zone before anything reads them. If a run crashes or fails validation halfway, its folder holds a partial set of files. The loader needs an unambiguous rule for which runs are complete, and the rule should work the same on local disk and on S3 in production.

### Decision
- Each run writes into its own folder, `data/raw/run_id=<UTC timestamp>/`, one file per response page with the exact response bytes.
- When every request has succeeded and passed validation, the run writes **`manifest.json` last**. **The manifest's existence is the commit.** Locally it's written to a temporary name and renamed in the same folder, so the manifest itself is never half-written. On S3, a single object upload is already atomic.
- The manifest records: `run_id`, start and commit timestamps, the pipeline version (git SHA), the resolved configuration and its hash, every request (URL, page count, `meta.total`, `lastupdated`), every file (path, sha256, size), and any validation warnings.
- **The loader only reads runs that have a valid manifest, and only the files the manifest lists.** A run without a manifest is incomplete: it's ignored, and its files stay on disk for debugging.

### Alternatives considered
- **`_SUCCESS` marker file:** the Hadoop-era convention. It marks completion but carries no information: no file list, no hashes, no request details.
- **Write to a temporary folder, then rename it:** readers never see a partial folder, but renaming isn't atomic on S3 (copy + delete), so it doesn't carry over to production.
- **Iceberg or Delta table commits:** the modern standard for tables, but overkill for a folder of raw JSON pages.
- **Commit status in a warehouse table:** contradicts ADR-0003, since the warehouse is a rebuildable cache and the commit state must live with the files.

### Consequences
- One mechanism behaves identically locally and on S3.
- The manifest doubles as traceability evidence (NFR-1): a value traces to a file, and the file to its request URL, configuration and code version.
- Failed runs leave debris that is harmless (ignored) and can be cleaned up explicitly.
- The per-file hashes make integrity checks on load possible.

---

## ADR-0005: Validate configuration and API responses before committing a run

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted (load-time re-validation removed by [ADR-0020](#adr-0020-load-verifies-integrity-not-contracts))
- **Serves:** FR-ING-3, FR-ING-4, NFR-3, NFR-4, FR-DQ-1

### Context
The API reports errors with HTTP 200 ([source-system §3](source-system.md#3-errors-are-returned-with-http-200)), silently ignores an unsatisfiable `date` filter and returns every year ([§4](source-system.md#4-an-unsatisfiable-date-filter-is-silently-ignored)), and has inconsistent types such as `per_page` as a number or a string ([§2](source-system.md#2-response-shape)). An invalid configured code would therefore look like "all data missing", and out-of-scope years could leak in unnoticed.

### Decision
Validation happens during extract, **before the run's manifest is written** (ADR-0004), so a run that fails validation is never committed. It has four levels:

1. **Configuration (pre-flight):** configured country and indicator codes are checked against the metadata responses before any observations are requested. Unknown codes fail fast.
2. **Envelope:** each response is classified as an error body (`[{"message": [...]}]`), a page (`[meta, data]`), or an unexpected shape. Error bodies and unexpected shapes fail without retry.
3. **Field contracts (Pydantic v2):**
   - Strict where correctness depends on it: `value` must be a number or `null` and is never coerced, so `""` or `"N/A"` can't become 0 (NFR-3); `date` must be a four-digit year; ISO3 codes must be three uppercase letters.
   - Lax where it's harmless: paging integers in `meta` accept `"50"` or `50`.
   - Tolerant of extra fields: unknown fields are allowed, and logged and recorded in the manifest as warnings. A missing required field or a type change fails the run.
4. **Request-level checks:**
   - total rows across pages = `meta.total`
   - all pages of one request share `meta.lastupdated` and `meta.total`; otherwise the whole request is refetched once, and fails if it still disagrees
   - returned countries and years ⊆ the requested ones
   - the indicator ID matches the request
   - no duplicate (country, year) within a response

Validation never alters the response bytes. The landing zone always holds exactly what the API returned. The loader runs the same validation again on replay.

### Alternatives considered
- **Check HTTP status only:** misses error bodies returned with HTTP 200.
- **Strict schemas everywhere, failing on any extra field:** brittle against harmless API additions, while raw already keeps the full payload.
- **Validate only later in SQL (dbt tests):** too late. A bad run would already be committed, and a configuration typo would look like missing data.

### Consequences
- Configuration typos, error bodies, out-of-range years and type changes stop a run before it commits.
- Missing values stay `null` from the API through to the warehouse.
- New categorical values (for example a new income level) and semantic changes (a unit change) aren't schema problems. They're left to data-quality tests in the transformation layer.

---

## ADR-0006: Fetch the full scope every run, keep every run, latest run wins

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted (§7's audience amended by [ADR-0028](#adr-0028-marts-are-a-current-state-star-schema-for-analysts))
- **Serves:** NFR-1, NFR-2, FR-DQ-1 · **Resolves:** Q7

### Context
The World Bank revises past values silently between releases ([source-system §7](source-system.md#7-past-values-are-revised-silently)): India's 2019 population moved by 22.6 million between releases, and Brazil's 2018 GDP by 1.7%. The API gives no per-value change signal, only a source-level `lastupdated` date. So "unchanged source data" (NFR-2) can't be assumed between runs, and fetching only new years would miss revisions. The data is also small (about 250 values).

### Decision
1. **Full fetch:** every run requests the full configured scope. There's no incremental loading by year, and warehouse tables are fully rebuilt on every run.
2. **Keep every run:** committed landing runs (ADR-0004) are never overwritten or deleted by the pipeline. The raw warehouse tables are rebuilt from all committed runs, as a log of fetches.
3. **Latest run wins:** each committed run is a complete snapshot, so **current state = the rows of the latest committed run**, not the latest value per record. A value the source revises is changed data: the newer run wins, and the older value stays in raw. **This resolves Q7.**
4. **Idempotency lives in the analytical layer:** replaying with unchanged landing data produces identical analytical tables, and the business key is unique (NFR-2).
5. **Stable lineage:** each response's ID is its landing path (for example `run_id=…/endpoint=indicator/SP.POP.TOTL/page=1.json`), assigned at landing, so it survives warehouse rebuilds. Analytical rows carry the source response ID, request URL, fetch time and the source's `lastupdated` (NFR-1).
6. **Integrity enforced:** the loader recomputes each file's sha256 and compares it with the manifest. Any mismatch fails the run.
7. **Revision history:** a model keeps one version per (country, indicator, year), starting a new version whenever the value changes between consecutive runs. Revisions are visible to analysts.

### Alternatives considered
- **Incremental loading of new years only:** misses revisions to past years, which the evidence shows are common.
- **Keep only the latest snapshot:** less storage, but loses revision detection, replay as of earlier runs, and historical lineage. At about 60 KB per run, keeping everything costs essentially nothing.
- **Latest value per record (instead of latest run):** a value the source deletes would survive forever from an older run.
- **IDs generated at load time:** they'd change on every warehouse rebuild and break lineage.

### Consequences
- Re-runs never duplicate analytical records. Revisions update current values and remain traceable.
- Replay as of any earlier committed run gives point-in-time state.
- Tests must prove it: replaying twice gives identical tables, two identical runs give identical tables, a changed value updates current state and creates a new version, a removed row shows as missing, and a tampered landing file fails the run.
- Rebuilding from every run doesn't scale indefinitely. The production note covers refreshes triggered by the source's `lastupdated` (still re-pulling the full history window), plus retention and compaction of landing runs.

---

## ADR-0007: All-or-nothing runs and write-audit-publish

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ING-4, FR-DQ-1, NFR-2, NFR-3

### Context
Two failure modes would hurt analysts:
- **A partially successful extract.** If one indicator fails, a first run would show it as "missing", indistinguishable from data genuinely missing at the source (NFR-3). Later runs would mix snapshots, breaking ADR-0006's "latest run is a complete snapshot".
- **A data-quality failure mid-transformation.** dbt stops downstream models when a test fails, but models already rebuilt stay rebuilt, leaving analytical tables half-updated.

### Decision
**Extract is all-or-nothing:**
- Transient failures (timeouts, connection errors, HTTP 429 and 5xx) are retried with exponential backoff and jitter, up to a configured number of attempts.
- Error bodies and contract violations (ADR-0005) aren't retried.
- If any request ultimately fails, the run isn't committed (no manifest, per ADR-0004), nothing new is loaded, and the command exits with a non-zero code and a clear error.

**Transformation uses write-audit-publish:**
1. **Write:** load raw tables and run the dbt models into a new warehouse file, `warehouse.next.duckdb`.
2. **Audit:** run every data-quality test against it.
3. **Publish:** only if every test passes, atomically rename it to the live warehouse file, then export the reporting outputs.

On any failure, the previous warehouse and outputs stay untouched, and the failed `.next` file is kept for debugging.

### Alternatives considered
- **Partial success (commit the indicators that worked):** friendlier on paper, but it needs a separate "not ingested" status and per-indicator snapshot selection, and missing data at the source becomes ambiguous. With about 6 requests and a run measured in seconds, re-running is cheap.
- **Build in place, without write-audit-publish:** simpler, but a failed test leaves half-updated tables visible to analysts.

### Consequences
- Analysts only ever see data from a complete run that passed every check.
- Possible because the warehouse is a rebuildable cache (ADR-0003): building a fresh copy costs seconds.
- In production this maps to one orchestrator task per indicator, with per-task retries and freshness alerts, and to write-audit-publish in Snowflake via a cloned schema plus `ALTER SCHEMA … SWAP WITH`, or via Iceberg branches.

---

## ADR-0008: Definitions of missing and incomplete data

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ANA-1, NFR-3 · **Resolves:** Q1

### Context
FR-ANA-1 asks which country-indicator-year combinations are "missing or incomplete", but the brief doesn't define either term. The source signals missing data in two different ways: a row with `"value": null`, or no row at all ([source-system §6](source-system.md#6-missing-values)). Missing data must never be treated as zero (NFR-3).

### Decision
Completeness is measured against the **expected set**: every configured country × configured indicator × reporting year (2018–2024), regardless of what the API returned.

- **Cell level** (one country, indicator, year):

  | Status | Meaning |
  |---|---|
  | `present` | the API returned a numeric value |
  | `null_value` | the API returned the row with `"value": null` |
  | `missing_row` | the API returned no row for this combination |

- **Series level** (one country × indicator across the reporting years):

  | Status | Meaning |
  |---|---|
  | `complete` | every expected year is `present` |
  | `incomplete` | some, but not all, expected years are `present` |
  | `missing` | no expected year is `present` |

  Each series also reports `n_present` and `n_expected`.

**This resolves Q1:** "missing" refers to a cell (or a whole series) with no value; "incomplete" refers to a series with partial coverage.

### Alternatives considered
- **Cell level only:** answers "which combinations", but makes partial coverage across years hard to see at a glance.
- **Treat `null_value` and `missing_row` as one status:** simpler, but hides a real difference in how the source reports gaps, which can matter when investigating a source issue.

### Consequences
- The completeness report covers every expected combination, including ones the API never mentioned.
- Adding a country or indicator in configuration automatically extends the expected set (NFR-4).
- Today's live data is fully `present` ([source-system §6](source-system.md#6-missing-values)), so `null_value`, `missing_row` and `incomplete` must be proven with crafted test fixtures.

---

## ADR-0009: Analytics interpretations: latest year, income-group aggregation, year-over-year

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ANA-2, FR-ANA-3, FR-ANA-4 · **Resolves:** Q2, Q4, Q5

### Context
Three analytics questions in the brief leave room for interpretation: what "latest available year" means (Q2), how to compare income groups when indicators differ in nature (Q4), and what 2018's year-over-year change is when 2017 is outside the requested range (Q5).

### Decision
**Latest available year (Q2):**
- The main comparison shows **each country at its own latest year with a value** within 2018–2024. Each value is shown with the year it comes from.
- The **latest year common to all countries** (for a like-for-like comparison) is provided in a **separate derived table**, not mixed into the main comparison.

**Income-group aggregation by year (Q4):** each indicator is aggregated in the way that matches its nature:

| Indicator | Group value |
|---|---|
| Population | sum |
| GDP | sum |
| GDP per capita | recomputed as Σ GDP ÷ Σ population (not an average of ratios) |
| Life expectancy | population-weighted mean |

- Each group-year row reports `n_countries` and `n_countries_with_data`.
- Values are computed over the countries that have data; the coverage columns make any gap visible.

**Year-over-year change (Q5, and nulls in general):** every row reports the absolute and the percentage change. When either can't be computed, it's `null` with a reason:

| Reason | When |
|---|---|
| `prior_out_of_scope` | the prior year is outside the reporting range, which always applies to 2018 |
| `prior_missing` | the prior year has no value |
| `prior_zero` | the prior value is 0: the absolute change is computed, the percentage isn't |
| `current_missing` | the current year has no value |

### Alternatives considered
- **Only each country's own latest year, or only a common year:** the first hides when countries are compared across different years; the second throws away newer data. Keeping both, in separate tables, avoids either problem.
- **Unweighted averages for every indicator in a group:** an average of GDP per capita or life expectancy across countries of very different sizes misrepresents the group.
- **Fetching 2017 as a lookback year for 2018 year-over-year:** considered and dropped for now. It would extend the request range beyond the brief's 2018–2024, and can be revisited in a superseding record.

### Consequences
- Every reported value states its year (latest-year view) or its coverage (income-group view).
- No year-over-year value is ever silently 0 or misleading. A null always comes with a reason.
- The lower-middle income group currently contains only India, which the README must point out.

---

## ADR-0010: GDP consistency check with a 0.1% tolerance

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-DQ-2 · **Resolves:** Q6

### Context
FR-DQ-2 requires checking that related indicators are consistent with each other. Among the four indicators, one relationship is definitional: GDP ÷ population = GDP per capita. The brief doesn't say how close the values must be (Q6).

Measured on the live data for the full scope (9 countries × 8 years, 72 combinations, fetched 2026-11-24): the largest relative difference between GDP ÷ population and the published GDP per capita was **below 0.000001%**. The World Bank derives GDP per capita from the same release's GDP and population.

### Decision
- For every country-year where all three values are present, the relative difference `|GDP ÷ population − GDP per capita| ÷ GDP per capita` must be **at most 0.1%**.
- A violation is a data-quality test failure, which blocks publishing under write-audit-publish (ADR-0007).
- Country-years with any of the three values missing are skipped by this check. Their gaps are reported by the completeness definitions (ADR-0008).

### Alternatives considered
- **A loose tolerance such as 2%:** would hide real problems, such as values from different releases being mixed, given that the measured gap is effectively zero.
- **Exact equality:** fragile against floating-point rounding.

### Consequences
- The check catches mixed releases, a wrong unit, or a mismatched join, while ignoring rounding noise.
- If the World Bank ever changes how it derives GDP per capita, the check will fail loudly and the tolerance must be revisited in a superseding record.

---

## ADR-0011: Current income classification applies to every year

- **Date:** 2026-11-24 · **Kind:** Assumption · **Status:** Accepted (modelling amended by [ADR-0030](#adr-0030-income-group-is-a-country-attribute))
- **Serves:** FR-ANA-4 · **Resolves:** Q3

### Context
FR-ANA-4 compares indicators across income groups **by year**. The World Bank reclassifies countries every July 1, so ideally each year would use that year's classification. The API's country endpoint provides only the **current** classification, with no history ([source-system §8](source-system.md#8-income-classification-is-current-only)). The brief also requires the public API to be the only production data source.

### Decision
- **Assumption:** each country's **current** income classification (from the latest committed run) applies to **every reporting year**.
- **Modeled at the right grain anyway:** income group is stored per **country × year**, and the income-group comparison joins on (country, year), not on a country attribute. If a historical source is ever allowed, only that table's contents change; the reports don't.
- **Visible in the output:** the income-group results carry `classification_basis = 'current_applied_to_all_years'` and `classified_as_of` (the run date), so analysts can't miss the assumption.
- **History captured going forward:** every committed run keeps its country metadata (ADR-0006), so future reclassifications are preserved from now on.

### Alternatives considered
- **The World Bank's historical classification file:** a spreadsheet published outside the API. Rejected: it breaks the brief's API-only rule.
- **Recomputing groups from GNI per capita and yearly thresholds:** the thresholds aren't available through the API and would have to be maintained by hand. Rejected.
- **Tracking classification changes across our own runs (SCD type 2) as the yearly basis:** it records when *we* saw a change (system time), not what applied in the data year (business time). Our first run is today, so every 2018–2024 observation would still map to today's group. It's kept as audit history (above), not as the yearly basis.

### Consequences
- Income-group comparisons for past years carry hindsight bias whenever a country changed group during 2018–2024. Whether any of the nine countries did can't be verified through the API, so the README states this as a caveat, not as a claim.
- The bias grows as countries near the classification thresholds are added.

---

## ADR-0012: Test fixtures: recorded responses plus crafted scenarios

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-DQ-1, FR-DQ-3, FR-ING-3, FR-ING-4, NFR-2

### Context
Tests must run without the live API (FR-DQ-3), yet they need to exercise behavior live data doesn't show today: there are no missing values in the current scope ([source-system §6](source-system.md#6-missing-values)), and revisions, error bodies and torn pages can't be triggered on demand. Replay and idempotency tests (ADR-0006) need landing runs with valid manifests and hashes (ADR-0004) as input.

### Decision
- **Recorded fixtures:** the exact response bytes for the pipeline's real requests (ADR-0002), captured once from the live API by a dedicated recording command, using a small page size so the recordings genuinely span several pages. They're committed under `tests/fixtures/recorded/` with an index (request URL, recording date), treated as immutable, and re-recorded only deliberately, in their own commit.
- **Crafted scenarios:** built by small Python helpers that modify the recorded baseline, not hand-written JSON files. Scenarios cover: a null value, a missing row, a revised value between runs, a row removed between runs, an HTTP 200 error body, a 5xx followed by success, retries exhausted, years outside the requested range, an unknown extra field, a missing required field, `lastupdated` mismatched across pages, and a tampered landing file.
- **Two test levels:**
  - **Ingestion tests** mock HTTP with `responses`, serving recorded or crafted bodies.
  - **Replay and transformation tests** create their landing runs by running the real extract step against mocked HTTP into a temporary directory, then replay from it. Manifests and hashes are therefore always genuine; none are committed or edited by hand.

### Alternatives considered
- **Committing ready-made landing runs with manifests:** manifests and hashes would have to be maintained by hand and would drift from the real code path.
- **One JSON file per crafted scenario:** dozens of near-identical files that drift apart and hide what each scenario changes.
- **Reusing the ad-hoc samples from exploration:** they don't match the pipeline's exact requests. They stay local and uncommitted.

### Consequences
- Tests run offline and still use real response data, with all its quirks.
- Each crafted scenario reads as a short, explicit change to the baseline.
- Pre-commit hooks that rewrite files (such as end-of-file fixing) must exclude `tests/fixtures/recorded/`. That exclusion is added in the same commit that adds the recordings.

---

## ADR-0013: Developer tooling and documentation layout

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted (recipe names amended by [ADR-0018](#adr-0018-pipeline-commands-extract-build-run))
- **Serves:** NFR-6, FR-DQ-1, deliverables (requirements §11)

### Context
The time box is 4–6 hours and the brief prioritizes ingestion, the data model and tests over tooling. Reviewers must be able to run everything from a clean checkout (NFR-6), and both humans and AI agents work in the repository.

### Decision
- **Task runner: `just`**, with recipes `run` (extract → load → transform → export), `replay` (no API calls), `test` (offline), and `check` (lint, type checks, tests, and dbt build on fixtures, all offline). `just` is a convenience, installed with `uv tool install rust-just`. Every recipe has a documented fallback, `uv run pipeline <step>`, that needs nothing beyond uv.
- **Definition of done:** `just check` passes.
- **Continuous integration:** one workflow runs `just check` offline on every push.
- **Kept lean:** the agent guide (`AGENTS.md`, imported by `CLAUDE.md`), pre-commit hooks, and CI are in scope. Agent-specific extras (custom skills, hooks, permission settings) are out of scope unless time remains.
- **Documentation layout: flat `docs/`, one file per purpose:** `requirements.md` (what and why), `source-system.md` (evidence about the source), `decisions.md` (this log), and `references/` (the immutable brief). A new document is added only when existing ones can't hold the content well.

### Alternatives considered
- **Make:** universally available, but recipes are harder to read and parameterize.
- **Plain `uv run` only:** no extra tool, but longer commands. Kept as the fallback.
- **Nested docs structure (product / design / guides):** better for large projects; unnecessary overhead for a handful of documents.
- **Full agent tooling from the start:** costs time that the brief's priorities assign elsewhere.

### Consequences
- A reviewer needs only uv; `just` makes common commands shorter.
- One command is the gate for every commit and for CI.
- The recipes, CI workflow and agent-guide command table are introduced together with the code they run, not before.

---

## ADR-0014: One project per pipeline in a uv workspace

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
- **Serves:** NFR-4, NFR-6 · **Amends:** ADR-0004 (landing path)

### Context
The repository starts with one source, the World Bank API, but the same research team could add other sources later. Each source has its own client, validation, landing and transformation logic, and may need different dependencies.

### Decision
- **uv workspace.** The repository root is a virtual workspace project: shared tooling and configuration only (lint, type check, test configuration, pre-commit), with no code of its own. Each pipeline is a **separate project** under `pipelines/<source>/` with its own `pyproject.toml`, `src/` and `tests/`. The first is `pipelines/worldbank/` (project and package `worldbank`). One `uv.lock` covers the whole workspace.
- **One command per pipeline.** Each pipeline provides its own command, named after its source: `worldbank <command>`.
- **Landing path per source (amends ADR-0004):** landing runs live under `data/raw/<source>/run_id=<UTC timestamp>/`, for example `data/raw/worldbank/run_id=…/`. Everything else in ADR-0004 stands.

### Alternatives considered
- **Single package with a namespace per source (`src/pipelines/worldbank/`):** simpler, with one project and one dependency set, but sources can't have isolated dependencies, and the boundary between sources is a convention rather than a project boundary.
- **Flat single-source project:** the least structure, but adding a second source would mean restructuring.

### Consequences
- A new source is a new folder under `pipelines/` with its own command, without touching existing pipelines.
- Shared code is extracted into a common workspace package only once a second source actually needs it.
- More structure than a single source strictly needs: two `pyproject.toml` files.
- There is no umbrella command across sources; one could be added later as its own workspace project if needed.

---

## ADR-0015: Configuration is loaded with plain Pydantic and PyYAML

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
- **Serves:** NFR-4, NFR-6 · **Amends:** ADR-0001 (configuration library)

### Context
ADR-0001 listed pydantic-settings for configuration. When implementing it, the pipeline turned out to have a single configuration source: a committed YAML file (`pipelines/worldbank/config.yml`), with no secrets and no per-environment differences. pydantic-settings' value is merging several sources (environment variables, `.env` files, secrets directories) with the environment taking precedence.

### Decision
- Configuration is a set of frozen **Pydantic** models (unknown keys rejected), read from YAML with **PyYAML** by an explicit `load_config(path)`.
- The YAML file is the **only** configuration input: no environment-variable overrides.

### Alternatives considered
- **pydantic-settings (as in ADR-0001):** environment overrides would be unused locally, and they would let a stray environment variable silently change what gets fetched. A runtime-chosen file path also needs a custom source hook.

### Consequences
- A run is fully determined by the committed configuration file (plus the code version), which the manifest records.
- One fewer dependency.
- **Production upgrade path:** if deployments need per-environment overrides (for example base URL or retry counts in containers or Airflow), switch the top-level model to pydantic-settings' `BaseSettings`. The nested models stay unchanged.

---

## ADR-0016: dbt project layout, layers and naming

- **Date:** 2026-11-25 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-MOD-1, FR-MOD-2, FR-MOD-3, NFR-4, NFR-5

### Context
ADR-0001 chose dbt-core and dbt-duckdb for transformation. Before writing models, the project needs a structure: where it lives, how layers are separated in a single DuckDB file, how models and columns are named, and where transformation-only parameters (such as how each indicator is aggregated) are configured.

### Decision
- **Location:** one dbt project per pipeline, at `pipelines/worldbank/dbt/`, with an in-repo `profiles.yml` (no credentials; the warehouse path comes from the `WORLDBANK_WAREHOUSE` environment variable, defaulting to `data/warehouse/worldbank.duckdb`).
- **dbt Core 1.x**, pinned by `uv.lock`. dbt v2 is out, but ADR-0001 was checked against dbt-core and dbt-duckdb 1.x, which support Python 3.14.
- **Layers are schemas in one database file:** `raw` (written by the Python loader), `staging`, `intermediate`, `marts`, `reporting`. Schema names are used as is, without dbt's default target-schema prefix. One file keeps write-audit-publish (ADR-0007) a single atomic rename, and maps one-to-one to schemas in one Snowflake database.
- **Materializations:** staging and intermediate are views; marts and reporting are tables.
- **Model names keep a layer prefix** even though the schema already shows the layer: `ref()` resolves by model name only, so names must be unique across the project, and the prefix shows the layer wherever the schema isn't visible. One name per object everywhere (file, `ref()`, table, CSV, docs), with no aliases.
  - Staging: `stg_<source>__<entities>` (one model per source entity; renaming, casting and flattening only).
  - Intermediate: `int_<entities>_<verb>`.
  - Marts: Kimball-style `dim_<entity>` and `fct_<process>`, because the model is a star schema and the prefix states the grain at a glance.
  - Reporting: `rpt_<question>`, one model per analytics output.
- **Column names:** snake_case, no reserved words (the API's `date` and `value` become `observation_year` and `indicator_value`), `_id` for keys, `is_`/`has_` for booleans, `_at` for UTC timestamps; the same concept has the same name in every model.
- **The expected set comes from the run's own configuration**, recorded in its manifest and loaded into `raw.landing_runs` (ADR-0004), not from the current `config.yml`. Replaying an older run therefore uses the scope that run was asked for.
- **How each indicator is aggregated by income group** (ADR-0009) is a documented parameter: the seed `indicator_aggregations.csv` (`sum`, `weighted_mean` or `ratio`, with the related indicators). A test fails if a configured indicator has no aggregation method, so adding an indicator means one configuration entry plus one seed row (NFR-4).
- **No dbt packages:** the few generic tests needed beyond dbt's built-ins are small macros in the project, so `dbt deps` and network access are never needed.

### Alternatives considered
- **One database file per layer (`ATTACH`):** mirrors Snowflake databases, but write-audit-publish would need several renames and there's no benefit at this size.
- **Plain entity names in marts (dbt Labs' current guide):** fine for wide denormalized marts; `dim_`/`fct_` communicates our star schema better.
- **Aliases for clean table names:** two names per object to translate between while debugging.
- **The expected set from the current `config.yml`, passed as a dbt variable:** replaying an older run would be judged against a scope it was never asked for.
- **`dbt_utils`:** convenient, but a dependency and a network fetch for one or two tests.

### Consequences
- Analysts query `marts.*` and `reporting.*`; `staging` and `intermediate` are implementation details.
- DuckDB has no roles or grants, so layer boundaries are a convention locally; in Snowflake they become access controls (production note).
- Every model above staging uses portable SQL (ADR-0001 portability rule).

---

## ADR-0017: Marts data model: grain, keys, relationships and lineage

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted (table list and lineage keys amended by [ADR-0028](#adr-0028-marts-are-a-current-state-star-schema-for-analysts))
- **Serves:** FR-MOD-2, FR-MOD-3, NFR-1, NFR-2, NFR-3, FR-ANA-1, FR-ANA-4

### Context
FR-MOD-2 asks for the grain, business keys and relationships of the final tables. Staging (ADR-0016) holds one row per run per source entity. The marts have to show current state (latest run wins, ADR-0006), make every expected cell visible, including ones the API never returned (ADR-0008), carry the yearly income classification at its own grain (ADR-0011), keep each value traceable to the API response it came from (NFR-1), and keep revisions visible (ADR-0006 §7).

### Decision
**A star schema with one long fact.** Every final table is keyed by natural keys from the source or the landing zone. There are no surrogate keys.

| Table | Grain | Key | Main columns |
|---|---|---|---|
| `fct_indicator_value` | country × indicator × year, latest run | `country_iso3`, `indicator_id`, `observation_year` | `indicator_value`, `value_status`, `run_id`, `source_response_id` |
| `fct_indicator_value_versions` | one version of a cell's value across runs | `country_iso3`, `indicator_id`, `observation_year`, `valid_from_run_id` | `indicator_value`, `value_status`, `valid_to_run_id`, `is_current`, `source_response_id` |
| `dim_country` | country, latest run | `country_iso3` | ISO2 code, name, region, `income_level_id` (the **current** classification) |
| `dim_indicator` | indicator, latest run | `indicator_id` | name, unit, source, definition |
| `dim_country_income_group_by_year` | country × year | `country_iso3`, `observation_year` | `income_level_id`, `classification_basis`, `classified_as_of` (ADR-0011) |
| `dim_run` | committed landing run | `run_id` | started and committed times, pipeline version, git SHA, config hash, `is_latest` |
| `dim_source_response` | landed response page | `source_response_id` | `run_id`, endpoint, request key, page, request URL, `fetched_at`, the source's `lastupdated`, sha256 |

**The fact is built on the expected set.** `fct_indicator_value` has one row for every cell in the latest run's expected set (ADR-0008, ADR-0016), left-joined to that run's observations. `value_status` is `present`, `null_value` or `missing_row`, and `indicator_value` is null unless the status is `present`. Missing is never zero (NFR-3).

**Values are `double`.** The API sends JSON numbers, which are already double precision, so a decimal type would only add precision the source doesn't have.

**No year dimension.** `observation_year` is an integer. A year has no attributes to describe here.

**Lineage is normalized into typed keys.** Each fact row carries:
- `run_id`: the run whose snapshot the row belongs to. For `missing_row` cells, it's the run that expected the cell.
- `source_response_id`: the landing path of the page the value was parsed from (ADR-0006 §5). It's null exactly when the status is `missing_row`, because no response contained the cell.

`run_id` is also part of `source_response_id`. Keeping it as its own column is deliberate: `missing_row` cells have a run but no response, and "current state" becomes a filter on one column. Tests ensure the two never disagree.

**Relationships** (each enforced by a `relationships` test):
- `fct_indicator_value` and `fct_indicator_value_versions` → `dim_country`, `dim_indicator`, `dim_run`, `dim_source_response`
- `dim_source_response` → `dim_run`
- `dim_country_income_group_by_year` → `dim_country`
- Reports join facts to income groups on (`country_iso3`, `observation_year`), never on a country attribute (ADR-0011).

**Revision history.** `fct_indicator_value_versions` compares each cell across consecutive committed runs whose expected set contains it. A new version starts when the value or the status changes, compared null-safely. `valid_to_run_id` is the first run with a different value (exclusive), or null while the version is still open. `is_current` marks the version that belongs to the latest run. A cell later removed from the scope keeps its history but has no current version.

**Tests that hold the model together:**
- each table's key is unique and not null;
- `value_status` takes only the three accepted values;
- `source_response_id` is null if and only if `value_status = 'missing_row'`;
- `indicator_value` is null unless `value_status = 'present'`;
- a fact row's `run_id` equals its response's `run_id`;
- the fact's row count equals the latest run's expected set;
- exactly one version per cell is current, and it matches `fct_indicator_value`.

### Alternatives considered
- **A wide fact (one column per indicator):** easier to read for one report, but every new indicator changes the schema (NFR-4), and a per-cell status and lineage need one column set per indicator. Wide shapes belong in reporting, if anywhere.
- **Surrogate keys:** the natural keys are stable, short and meaningful, and the marts are rebuilt from the landing zone anyway (ADR-0003). Hashed keys would only add a translation step.
- **Lineage as one JSON column on the fact:** it would break the rule that SQL above staging stays portable, lose types and dbt tests, and repeat the same details on every row from a page.
- **Only `source_response_id` on the fact, deriving the run from it:** `missing_row` cells have no response, so they would lose their run.
- **A composite response key (`run_id` plus a path within the run):** removes the overlap between the two columns, but changes the response ID ADR-0006 defined, and makes every lineage join a two-column join.
- **Income group as a column of `dim_country` only:** couldn't hold a yearly classification if a historical source is ever allowed (ADR-0011).

### Consequences
- Analysts get one fact table for every question. Gaps show up as rows with a status, not as absent rows.
- Any value can be traced to its file with one join: `source_response_id` names the landed page, and `dim_source_response` gives its URL, fetch time and checksum.
- `dim_source_response` and `dim_run` grow with pages and runs, not with values. In production they're append-only and can load incrementally.
- Revisions the World Bank makes without notice show up as new versions instead of disappearing.

---

## ADR-0018: Pipeline commands: extract, build, run

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Superseded by [ADR-0022](#adr-0022-python-stops-at-load-the-task-runner-orchestrates)
- **Serves:** NFR-2, NFR-6, FR-DQ-1 · **Amends:** ADR-0003 (the `replay` command), ADR-0013 (the `run` and `replay` recipes)

### Context
ADR-0003 names a `replay` command for load → transform → export, and ADR-0013 names the matching `just` recipes. Before the command exists, its name and its neighbours should be ones data engineers recognise without reading the docs. Write-audit-publish (ADR-0007) also decides which steps may run on their own: loading `raw` into the live warehouse before the audit would show analysts unaudited data.

### Decision
Each pipeline's command (ADR-0014) has three subcommands, named after the tools data engineers already use:

| Command | Does | Network |
|---|---|---|
| `worldbank extract` | calls the API and commits a new landing run (ADR-0003, ADR-0004) | yes |
| `worldbank build` | rebuilds the warehouse from the landing zone with write-audit-publish (ADR-0007): load `raw` from every committed run, `dbt build`, publish only if every test passes, then export the reports | no |
| `worldbank run` | `extract`, then `build`: the scheduled job | yes |

- **`build` replaces `replay`.** It matches `dbt build` (models plus tests) and says what the command does: rebuild the warehouse. "Replay" stays the name of the concept (rebuilding from landed files) used in ADR-0006, ADR-0012 and ADR-0016.
- **Load and transform are stages, not commands.** `build` logs each stage by name (load, transform, publish, export), so the ELT shape stays visible. A standalone `load` would write to the live warehouse before the audit.
- **`build --as-of <run_id>`** rebuilds from the committed runs up to that run, so "latest run" means that run (ADR-0006: point-in-time replay). It writes to its own file and never publishes over the live warehouse.
- **`build --no-publish`** stops after the audit and keeps `warehouse.next.duckdb` for inspection.
- **`just` recipes** follow the commands: `run` and `build`, with `uv run worldbank <command>` as the fallback (ADR-0013).

### Alternatives considered
- **`replay` (ADR-0003):** accurate, but not a name data engineers expect for "rebuild the warehouse".
- **Separate `load` and `transform` commands (textbook ELT):** familiar, but under write-audit-publish they only make sense together. Run apart, they'd publish unaudited data or need a hidden hand-off file.
- **`extract` also loading the warehouse:** merges the one networked step with the offline ones, against ADR-0003, and hides the S3 → warehouse boundary that exists in production.

### Consequences
- The README and agent guide document three commands. Running dbt by hand against a scratch file stays available for model development.
- Point-in-time rebuilds are one flag, which makes the landing zone's role as system of record easy to demonstrate.
- Possible later additions, each in its own commit if time allows: `worldbank runs` (list landing runs and which one is live), `worldbank docs` (dbt docs and lineage), `extract --dry-run`.

---

## ADR-0019: Hand-written extraction instead of an EL framework

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** NFR-1, NFR-2, NFR-3, FR-ING-3, FR-ING-4, FR-DQ-3

### Context
Extract-and-load frameworks such as **dlt**, Meltano (Singer SDK) and Airbyte provide paging, retries, schema handling, load history and loading into DuckDB, mostly through configuration. A reviewer will reasonably ask why this pipeline writes its own client, landing zone and raw loader (`api/`, `storage/`) instead. dlt is the strongest candidate: it's a Python library rather than a platform, has a REST API source driven by configuration, and loads into DuckDB.

### Decision
Keep extraction hand-written (requests + tenacity + Pydantic, ADR-0001), for these reasons:

1. **Byte-exact landed responses.** Lineage rests on the exact HTTP response pages: a value's `source_response_id` is the landed page's path, the loader checks each page's sha256 against the manifest, and validation never alters the landed bytes (ADR-0005, ADR-0006, ADR-0017). dlt extracts *items* and writes its own normalized files, not the responses as received. Keeping the pages would mean capturing them in hooks and running our landing zone next to dlt anyway.
2. **The envelope carries facts we need.** Each page's metadata (`lastupdated`, `page`, `pages`, `total`) feeds request-level checks (rows across pages = `meta.total`; all pages share `lastupdated`) and the `source_lastupdated` lineage column. A framework that yields only the data rows drops it, or needs custom code to keep it.
3. **The World Bank's quirks are the hard part.** Errors come back with HTTP 200, an unsatisfiable `date` filter is silently ignored, and paging fields change type ([source-system §2–4](source-system.md#2-response-shape)). Every one of these needs explicit handling: in dlt, as response hooks and custom checks. That's the same logic, written as workarounds around the framework instead of as plain tested code.
4. **The commit rule and audit metadata are ours.** A run counts only once its manifest is written last, recording the resolved configuration, its hash, the git SHA, every request and every file (ADR-0004). The run's own configuration also defines the expected set (ADR-0016). dlt's load IDs and pipeline state are close, but don't carry this rule or this record.
5. **Names and shapes stay untouched until staging.** dlt normalizes identifiers and splits nested JSON into child tables during load. This pipeline keeps the raw payload as received and does every rename and flattening in one visible place: the dbt staging layer (ADR-0016).
6. **Write-audit-publish stays ours either way.** dlt loads data; it doesn't audit the dbt models and publish the warehouse atomically (ADR-0007). A framework would remove only part of the code, while adding a second state store to reason about.
7. **Small scope, high bar.** Four endpoints and about 250 values per run don't need a framework's breadth, and the brief values correctness and traceability over coverage. The mechanics (paging, retries, atomic commits, contracts) are about 600 lines, fully tested offline against recorded responses (ADR-0012), and readable in one sitting.

### Alternatives considered
- **dlt with its REST API source:** the least code for paging, retries and loading, plus schema contracts and load history. Rejected for reasons 1 to 6: we'd keep most of our own code around it and lose byte-exact pages as the unit of lineage.
- **Meltano / Singer SDK tap:** a well-known connector structure (client, streams, schemas), but emits records rather than responses (same gap as reason 1) and adds a separate target and the Singer message protocol for one source.
- **Airbyte:** a platform with its own deployment, which the local-only, no-accounts constraint (NFR-5) rules out.

### Consequences
- We own paging, retries and contract checks, and their tests. Coverage is enforced by `just check` (ADR-0013).
- The code structure mirrors a connector: `api/client.py` and `api/contracts.py` play the roles of a Singer tap's `client.py` and `streams.py`/`schemas/`, which keeps the code familiar to reviewers who know those tools.
- **Production note:** with many sources, extraction should move to a framework such as dlt, keeping the landing zone conventions (raw responses as received, manifest commit, run IDs) and write-audit-publish as the platform's own contract. The README says so.

---

## ADR-0020: Load verifies integrity, not contracts

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** NFR-1, NFR-2, FR-DQ-1 · **Amends:** ADR-0005 (its last line: "The loader runs the same validation again on replay")

### Context
ADR-0005 validates every response during extract, before a run can be committed, and also has the loader run the same validation again. The loader also checks every landed file against the sha256 recorded in its run's manifest (ADR-0006). A file whose hash matches holds exactly the bytes that passed validation at extract time, so validating it again can't find anything new. It does make the loader import the World Bank response contracts, which ties the otherwise source-agnostic load step to one source.

### Decision
- **Contracts are enforced once, at the boundary:** during extract, before the manifest is written (ADR-0004, ADR-0005). These are consumer-side contracts: our explicit expectations of the API, since the World Bank agrees to none.
- **Load verifies integrity only:** it reads committed runs only, reads only the files their manifests list, and fails if a listed file is missing or its sha256 doesn't match. Loading stays a plain copy into `raw`, with no transformation (ELT).
- **Everything after load is dbt's job:** staging flattens and types the payloads, tests check the modelled data, and write-audit-publish (ADR-0007) publishes only a warehouse where every test passed.

### Alternatives considered
- **Keep re-validating on load (ADR-0005 as written):** defense in depth on paper, but redundant once hashes match, and it couples the loader to the source's contracts.
- **Let dbt read the landing files directly (DuckDB `read_json` / `read_blob` as dbt sources), with integrity as dbt tests:** removes the Python loader and resembles Snowflake external tables, but moves the load step into dbt, puts DuckDB-specific file reading into source definitions, and replaces a finished, tested loader. Production loading belongs in the production note instead: Snowflake `COPY INTO` or Snowpipe from the S3 landing zone.

### Consequences
- The loader needs nothing from the source package, so it can stay source-agnostic (see the code layout decision that follows).
- A landing file edited together with its manifest hash is no longer caught at load. Committed runs are immutable by rule (AGENTS.md guardrails, ADR-0006), and staging tests still check the modelled values.
- A contract change in code doesn't re-check old runs on load. If that's ever needed, it's a deliberate backfill check, not part of every build.

---

## ADR-0021: Code layout: source, storage and warehouse

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** NFR-4, NFR-6 · **Builds on:** ADR-0003, ADR-0014, ADR-0020

### Context
The pipeline package grew as flat modules, then as folders mixing kinds of names (`api/` a system, `storage/` a category, `steps/` a list of actions). The real seams in the code are two: what knows the World Bank versus what would serve any source, and the three systems data passes through (the API, the landing zone, the warehouse). Since load no longer re-validates contracts (ADR-0020), these seams coincide: only the extract side needs World Bank knowledge.

### Decision
Only `cli.py` and `config.py` stay top-level. Everything else lives in three packages:

| Package | Holds | Knows the World Bank |
|---|---|---|
| `source/` | settings (`Api`, `Scope`), HTTP client with paging and retries, response contracts, the extract run plan and scope checks | **yes**: the only package that does |
| `storage/` | the landing zone, the system of record: manifest schema, writing and committing runs, listing committed runs, verified reads (listed files only, sha256) | no |
| `warehouse/` | the rebuildable cache: raw tables loaded from committed runs, and next, the build (dbt, write-audit-publish, export) | no |

- **Dependency rule:** `storage/` imports nothing from the project; `warehouse/` imports only `storage/`; `source/` may import `storage/` (extract writes runs); nothing imports `source/` except `cli.py`, `config.py` and tests. A test enforces the rule for `storage/` and `warehouse/`.
- **"Landing zone" stays the name of the data area** (`data/raw/<source>/`) in docs and ADRs; `storage` is the package that owns its rules.
- **Outside Python, World Bank knowledge lives in exactly two more places:** `config.yml` (values) and the dbt staging models (interpretation). Everything between `source/` and staging is source-agnostic: the landing zone format, the raw tables and the build.
- Tests mirror the packages; the fixture recorder lives in `scripts/` because it calls the live API.

### Alternatives considered
- **Flat modules per concept:** fewest files, but boundaries such as "only this code touches the network" stay a convention.
- **By ELT stage (`extract/`, `load/`, `transform/`):** familiar, but splits the landing zone's write and read rules across two packages, and the Python `transform/` would hold a single dbt call.
- **By system with commands inside (`api/`, `landing_zone/`, `warehouse/`):** close to this one, but doesn't make the source-specific boundary explicit.
- **A shared workspace package for `storage/` now:** it's generic in its protocol, but its schema still carries paged-API fields (`endpoint`, `key`, `page`, `total`, `lastupdated`). Extracting it from one example would freeze those as the platform standard. Deferred, per ADR-0014.
- **Hexagonal (domain, ports, adapters):** one implementation per interface, and more indirection than about 1,300 lines need.
- **A `core/` package for the generic side:** an umbrella name that says nothing about its contents; `storage/` and `warehouse/` say what they are.

### Consequences
- A second source writes its own `source/` package and dbt staging, and reuses `storage/` and `warehouse/`.
- **When a second source arrives,** `storage/` and `warehouse/` move into a shared workspace project, and the manifest splits into a generic part (run identity, versions, configuration, files with hashes, warnings) and typed source metadata (for the World Bank: endpoint, key, page, total, `lastupdated`). The raw tables follow the same split.

---

## ADR-0022: Python stops at load; the task runner orchestrates

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted (amended by [ADR-0023](#adr-0023-publish-trusts-the-orchestrators-order) and [ADR-0034](#adr-0034-report-tables-are-exported-to-csv-by-worldbank-export))
- **Serves:** NFR-2, NFR-6, FR-DQ-1 · **Supersedes:** ADR-0018 · **Builds on:** ADR-0003, ADR-0007, ADR-0020, ADR-0021

### Context
ADR-0018 gave the pipeline a `build` command that loads `raw`, calls dbt, and publishes, so the Python package would also orchestrate and depend on dbt's Python API. Write-audit-publish (ADR-0007) needs *something* to run load, then `dbt build`, then publish only if dbt passed, but that something doesn't have to be the pipeline package. ADR-0018 rejected a standalone `load` because it would write to the live warehouse before the audit; that objection disappears if load always writes a new file and only publish touches the live one.

### Decision
**Each tool does one ELT job:**

| Phase | Done by | Command |
|---|---|---|
| Extract | Python (`source/`, `storage/`) | `worldbank extract` |
| Load | Python (`warehouse/`): committed runs → `raw` tables in a **new** file, `data/warehouse/worldbank.next.duckdb` | `worldbank load` |
| Transform and audit | dbt, run directly, against the new file (`WORLDBANK_WAREHOUSE` points at it) | `dbt build` |
| Publish | Python (`warehouse/`): atomically rename the new file over the live one, `data/warehouse/worldbank.duckdb` | `worldbank publish` |

- **The task runner orchestrates locally:** `just build` runs load, `dbt build` and publish, chained with `&&`, so publish never runs unless every model and test passed (ADR-0007). `just run` runs `worldbank extract` and then `just build`. Without `just`, the README documents the same commands with `uv run` (ADR-0013).
- **The Python package never calls dbt.** It has no `build` or `run` command.
- **`load` never writes the live warehouse,** so running it alone is always safe. Running load and `dbt build` without publish is the audit-only path; the new file stays for inspection.
- **`publish` refuses to run** if there's no new file to publish.
- **Point-in-time rebuilds:** `worldbank load --as-of <run_id>` loads the committed runs up to that run, into a file of its own. The recipe for it never publishes.
- **Report exports are dbt's job,** written next to the new warehouse file and published together with it. The mechanism is decided with the reporting models.
- **Code:** `warehouse/load.py` (renamed from `raw.py`) and `warehouse/publish.py`. There's no `build.py`.
- **Production:** the same four phases become tasks in an orchestrator DAG (Airflow or Dagster): extract job → `COPY INTO` or Snowpipe → `dbt build` → schema swap.

### Alternatives considered
- **Python orchestrates (ADR-0018's `build`):** one command, and the sequence is tested Python, but the pipeline package becomes an orchestrator and depends on dbt, blurring E and L in Python versus T in dbt.
- **An orchestrator (Dagster, Airflow) locally:** the production shape, but heavy for one linear pipeline (ADR-0001).
- **Write-audit-publish inside dbt (build into side schemas, then swap):** keeps everything in dbt, but DuckDB has no atomic schema swap, and the published file would still need a step outside dbt.

### Consequences
- The local commands and the production DAG match one to one.
- The ordering lives in three lines of the `justfile`, not in tested Python. The steps themselves (`load`, `publish`) are tested Python, and `&&` carries the only rule that matters: no publish after a failure.
- `just` becomes the convenient way to run a full build; the `uv run` fallback is three commands.

---

## ADR-0023: Publish trusts the orchestrator's order

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-DQ-1, NFR-2 · **Amends:** ADR-0022 · **Builds on:** ADR-0007

### Context
Under ADR-0022, `just build` runs load, `dbt build` and publish, and stops at the first failure. `worldbank publish` is also a command of its own, so someone could run `worldbank load` and then `worldbank publish` by hand, skipping dbt, and publish a build nothing tested. Separately, a load that failed halfway left a partial file under the very name publish looks for.

### Decision
- **The orchestrator owns the order.** `publish` runs only after a successful full `dbt build` on the next file; `just build` guarantees it locally, and the DAG dependency does in production (an orchestrator runs the swap only if the dbt task succeeded). `publish` doesn't re-check the audit. Its help text and the README say it's meant to run inside the chain, not on its own.
- **Builds appear only when complete.** `load` first removes any previous next file, loads into `<file>.loading`, and renames it to the next file only after the load succeeded. A failed load leaves no build behind, so there's nothing a stray `publish` could ship; the `.loading` file stays for debugging.

### Alternatives considered
- **Publish re-checks the audit from evidence inside the file:** `schema.sql` creates an `audit.dbt_invocations` table, an `on-run-end` macro records each dbt invocation (command, full or selected, passed or failed), and `publish` refuses unless the latest is a successful full `dbt build`. It closes the manual-publish gap and keeps an audit trail inside every published warehouse, but adds a schema, a macro, a three-way contract and its tests for a risk that is low in a single-user local warehouse. Worth doing once several people or tools can publish.
- **Gate on dbt's `target/run_results.json`:** a standard dbt artifact, but it can't prove it describes the file being published.

### Consequences
- Running `worldbank publish` by hand after skipping dbt is possible and documented as unsupported; the residual risk is accepted.
- A half-built warehouse file can never be published, by the chain or by hand.

---

## ADR-0024: Structured logging with the standard library

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ING-4, FR-DQ-1, NFR-1 · **Builds on:** ADR-0001 (standard-library `logging`), ADR-0022

### Context
The pipeline retries requests, refetches torn pages, skips incomplete runs, warns about new API fields and refuses unsafe publishes, but none of it was visible while it ran: a run that needed four retries looked like a clean one. Errors were printed ad hoc by the CLI. Whoever operates the pipeline, locally or from an orchestrator, needs to see what happened and why, in a form both people and log tools can read.

### Decision
- **Standard library only:** `logging`, no logging dependency. Every module logs through `logging.getLogger(__name__)`, so logger names follow the package layout (`worldbank.source.client`, …).
- **Only the CLI configures logging.** Library code never adds handlers, sets levels or prints. The CLI attaches one handler to the `worldbank` logger, writing to **stderr**; **stdout** is reserved for each command's one-line result, so output can be piped.
- **Two formats:** `text` (default, for people) and `json` (one object per line, for orchestrators and log tools). Both carry a UTC ISO 8601 timestamp, the level, the logger name, the message and the event's fields.
- **Structured fields, not formatted strings:** context goes in `extra={...}` with stable snake_case names (`run_id`, `endpoint`, `key`, `page`, `status`, `duration_ms`, `attempt`, …), rendered as `key=value` in text and as keys in JSON. Messages are short, lowercase event descriptions.
- **Levels mean the same thing everywhere:**

  | Level | For |
  |---|---|
  | DEBUG | per-file and per-attempt detail: each page written or verified |
  | INFO | milestones and per-request results: run started and committed, request fetched, load and publish done |
  | WARNING | handled but notable: retries, refetched pages, unknown API fields, skipped incomplete runs |
  | ERROR | a command failed: logged once, at the command boundary, without a stack trace for expected errors |

- **Errors are logged once,** where they're handled (the CLI), not where they're raised. Unexpected exceptions keep their traceback.
- **Never logged:** response bodies or payloads (they're in the landing zone), and anything secret (there's nothing secret today; the rule stands).
- **Options:** `worldbank --log-level {DEBUG,INFO,WARNING,ERROR} --log-format {text,json}`, also settable as `WORLDBANK_LOG_LEVEL` and `WORLDBANK_LOG_FORMAT`; defaults are INFO and text.

### Alternatives considered
- **structlog or loguru:** nicer APIs and processors, but a dependency for what a 30-line formatter does; ADR-0001 already chose the standard library.
- **JSON only:** best for machines, harder to read in a terminal during development; both formats share the same fields.
- **Printing with `typer.echo`:** what the CLI did; no levels, no fields, no way for an orchestrator to filter or parse.

### Consequences
- A run's log tells its story: what was requested, how long each request took, what was retried and why, what was committed, loaded and published.
- In production the JSON format goes straight to a log platform (CloudWatch, Datadog) with fields ready to filter on; the README's production note says so.
- Tests assert on important log events (retries, skipped runs, failures), so they're part of the behavior, not decoration.

---

## ADR-0025: SQL style and linting with SQLFluff

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** NFR-6, FR-MOD-3 · **Amends:** ADR-0013 (the definition of done) · **Builds on:** ADR-0016

### Context
SQL is now half the code: dbt models, macros and tests, and the warehouse's `schema.sql` and `load.sql`. Python has ruff in the definition of done (ADR-0013); SQL had no linter, so style drifted (mixed conventions, keywords used as names) and nothing would catch it in review.

### Decision
- **SQLFluff lints every `.sql` file in the repository,** as part of `just check` and as a pre-commit hook. Configuration lives in the root `pyproject.toml`, next to ruff and mypy; `.sqlfluffignore` excludes dbt's generated folders.
- **Dialect `duckdb`; Jinja templater with dbt's built-ins mocked** (`ref`, `source`, `config`, …) and our macros loaded, so dbt models lint offline in milliseconds, without compiling against a database.
- **Style:** keywords, types and keyword literals (`NULL`, `TRUE`) in **upper case**; identifiers and function names in lower case; explicit `AS` for aliases; trailing commas; lines up to 100 characters; no keywords as names.
- **One rule is off:** ST06 (simple columns before computed ones), because models order columns as grain, then attributes, then lineage, on purpose.
- **SQL embedded in Python strings** follows the same style by hand; SQLFluff only sees `.sql` files, so SQL belongs in `.sql` files wherever it can.

### Alternatives considered
- **The dbt templater (`sqlfluff-templater-dbt`):** renders models exactly as dbt would, but compiles the project against a database on every lint, which is slower and needs a warehouse file.
- **sqlfmt:** an opinionated formatter with no configuration, but formats only (no lint rules), and its lower-case keywords conflict with the chosen style.
- **No SQL linting:** style by review only, which is what drifted.

### Consequences
- `just check` and the commit hook fail on SQL style violations, as they do for Python.
- `sqlfluff fix` applies most fixes automatically.
- Macro bodies render to nothing when linted, so their SQL is kept in style by hand.

---

## ADR-0026: Each dbt layer reads only its own layer and the one below

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted (same-layer reads narrowed by [ADR-0027](#adr-0027-only-intermediate-models-read-their-own-layer))
- **Serves:** FR-MOD-1, FR-MOD-3 · **Amends:** ADR-0016 (layer dependencies), ADR-0017 (where mart logic lives)

### Context
ADR-0016 defines the layers (`raw`, `staging`, `intermediate`, `marts`, `reporting`) and treats intermediate as optional, as dbt Labs' guide does: a mart may read staging directly when nothing sits in between. That leaves each mart free to depend on any layer below it, so the DAG's shape depends on each model's author, and logic such as "which run is the latest" would be repeated in every mart that needs it.

### Decision
- **A model reads only models in its own layer or the layer directly below:**

  | Layer | May read |
  |---|---|
  | staging | `source()` only: raw, written by the loader |
  | intermediate | staging and intermediate |
  | marts | intermediate and marts, plus seeds |
  | reporting | marts and reporting |

- **Logic lives in intermediate; marts present it.** Ranking runs, filtering to the latest run, joining the expected set, versioning and spreading income groups over years happen in intermediate models, written once and unit-tested there. Marts select, name and document columns.
- **No pure pass-through models.** Every intermediate model does one named thing, and its name says what (`int_<entities>_<verb>`, ADR-0016).
- **Enforced by a test** that reads each model's `ref()` and `source()` calls and fails on any read outside these rules.

### Alternatives considered
- **dbt Labs' default (skip intermediate when there's no logic):** fewer models, but any mart may depend on staging, the DAG's shape varies by author, and shared logic tends to be repeated across marts.
- **Strict adjacency without same-layer reads:** a purer DAG, but "which run is the latest" would be computed again in every intermediate model that needs it.

### Consequences
- The DAG is predictable: a model's layer says what it may depend on, and a change in staging is absorbed in intermediate before it reaches marts.
- In Snowflake, layers become schemas, so the rule maps directly to grants: each layer's role reads only its own schema and the one below.
- More models than the minimum, each small, single-purpose and unit-tested.

---

## ADR-0027: Only intermediate models read their own layer

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-MOD-1, FR-MOD-3 · **Amends:** ADR-0026

### Context
ADR-0026 let every layer read its own layer as well as the one below. Same-layer reads are what let shared logic, such as "which run is the latest", be written once; that need exists only in intermediate. In marts and reporting, same-layer reads only add hidden dependencies between tables that analysts treat as independent (a fact built from a dimension, a report built from another report).

### Decision
- **Only intermediate models may read their own layer.** Marts read intermediate only; reporting reads marts only:

  | Layer | May read |
  |---|---|
  | staging | `source()` only |
  | intermediate | staging, intermediate, seeds |
  | marts | intermediate |
  | reporting | marts |

- **Seeds are read by intermediate,** like staging data: configuration such as each indicator's aggregation method (ADR-0016) is joined in intermediate and reaches marts and reports as columns (for example `dim_indicator.aggregation_method`).
- ADR-0026's other rules stand: logic in intermediate, marts present it, no pure pass-through intermediate models, enforced by a test.

### Alternatives considered
- **Same-layer reads everywhere (ADR-0026 as written):** convenient for building a fact from its dimensions or a report from another report, but it makes marts and reports depend on each other in ways their consumers can't see.

### Consequences
- Every mart and every report can be rebuilt, understood and tested on its own, from the layer below.
- Each indicator's aggregation method is visible in `dim_indicator`, not only inside the income-group report.

---

## ADR-0028: Marts are a current-state star schema for analysts

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted (income-group tables amended by [ADR-0029](#adr-0029-the-fact-carries-the-income-group-that-applied-each-year))
- **Serves:** FR-MOD-2, FR-MOD-3, NFR-1 · **Amends:** ADR-0017 (table list, lineage keys), ADR-0006 §7 (who sees revisions)

### Context
ADR-0017 put run-level detail in the marts: `dim_run`, `dim_source_response` (every page of every run), `fct_indicator_value_versions` (history across runs) and a `run_id` on the current-state fact. Runs are a technical detail of how the pipeline fetches data: analysts need current values, and traceability (NFR-1) is a property of the platform, not something analysts consume. Every lineage detail already exists below the marts: `int_runs_ranked`, `int_responses_joined_to_runs` and `stg_worldbank__responses` in the warehouse, and the landed files with their manifests.

### Decision
- **The marts are the analysts' view: a current-state star schema, latest run only.**

  | Mart | Grain | Key |
  |---|---|---|
  | `fct_indicator_value` | country × indicator × year | (`country_iso3`, `indicator_id`, `observation_year`) |
  | `dim_country` | country | `country_iso3` |
  | `dim_indicator` | indicator | `indicator_id` |
  | `dim_country_income_group_by_year` | country × year | (`country_iso3`, `observation_year`) |

- **Lineage enters the marts as one technical column:** `fct_indicator_value.source_response_id`, the landed page's path. It's documented as lineage, not for analysis, and it's the entry point that makes NFR-1 checkable from any final value. `run_id` leaves the fact: in a current-state table it's the same on every row, and the response path already contains it.
- **Run-level detail stays below the marts,** for engineers: runs in `int_runs_ranked`, pages in `int_responses_joined_to_runs`, value history in `int_indicator_values_versioned` (revisions are recorded and visible to engineers; ADR-0006 §7's "visible to analysts" no longer holds). A dbt analysis, `analyses/trace_value.sql`, traces any cell from its final value to its page, run and history in one query.
- **Audiences map to schemas:** analysts read `marts` and `reporting`; engineers read every schema. In Snowflake those are the roles' grants.

### Alternatives considered
- **Keep lineage and history as marts (ADR-0017 as written):** everything in one place, but analysts see runs, pages and versions they don't need, and the star schema stops being about indicators.
- **A separate `audit` group of marts for run-level tables:** keeps them out of the analysts' star, but duplicates what intermediate already holds and tests, for an audience that can read intermediate anyway.
- **No lineage column on the fact:** the purest analyst view, but tracing a value would mean re-deriving its run and joining back through intermediate on keys; one column makes NFR-1 directly demonstrable.

### Consequences
- Analysts get four tables that answer every question; the reports build on them.
- Engineers trace through intermediate, staging, the landed files and the logs, documented in `analyses/trace_value.sql` and the production note.
- ADR-0017's invariant "a fact's run matches its response's run" becomes "every fact row's response belongs to the latest run".

---

## ADR-0029: The fact carries the income group that applied each year

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Superseded by [ADR-0030](#adr-0030-income-group-is-a-country-attribute)
- **Serves:** FR-ANA-4, FR-MOD-2 · **Amends:** ADR-0028 (income-group tables) · **Builds on:** ADR-0011

### Context
ADR-0028's marts held the income group in two places: `dim_country.income_group_id` (the current classification) and `dim_country_income_group_by_year` (the group per country and year). An analyst comparing groups by year (FR-ANA-4) could join the wrong one, the mistake ADR-0011 guards against, and a dimension keyed by country × year is awkward in a star schema.

### Decision
- **The fact carries `income_group_id`:** the group that applied to that country in that year, assigned in intermediate from `int_income_groups_spread_over_years` (today the current classification for every year, per ADR-0011). The fact's grain already includes the year, so the group is a property of each row.
- **`dim_income_group` replaces `dim_country_income_group_by_year`:** one row per income group, with its name, a `sort_order` from low to high income (from the `income_group_order` seed, so reports don't sort alphabetically), and how today's classification was made: `classification_basis` and `classified_as_of` (ADR-0011).
- **`dim_country` keeps the current group, named as such:** `current_income_group_id` and `current_income_group_name`, a different concept from the yearly group on the fact, so it gets a different name.
- The marts become: `fct_indicator_value` → `dim_country`, `dim_indicator`, `dim_income_group`.

### Alternatives considered
- **Keep the country-by-year dimension (ADR-0028):** correct, but two places for the group and a join on two columns that analysts can get wrong.
- **Only the current group, on `dim_country`:** simplest, but it hard-codes ADR-0011's assumption into the model; a historical classification couldn't be added without changing every report.

### Consequences
- FR-ANA-4 is a join on `income_group_id`; there's no way to pick the wrong group.
- A historical classification, if ever allowed, changes only `int_income_groups_spread_over_years`.
- Reports list income groups in their natural order.

---

## ADR-0030: Income group is a country attribute

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ANA-4, FR-MOD-2 · **Supersedes:** ADR-0029 · **Amends:** ADR-0011 (its modelling and labelling bullets)

### Context
ADR-0011 assumes the current income classification for every year, because the API has no history and the brief allows no other source. It also modelled the group at country × year grain "anyway", so a historical source could replace it later, and labelled every result with `classification_basis` and `classified_as_of`; ADR-0029 then put the yearly group on the fact. None of that changes a single number: every year gets the current group. It exists only for a historical source the brief rules out, and it costs two intermediate models, a country attribute on the fact, and a "current" versus "yearly" distinction analysts have to learn. The brief weighs a clear data model most.

### Decision
- **The income group is an ordinary attribute of `dim_country`:** `income_group_id`, `income_group_name` and `income_group_sort_order` (low to high income, from the `income_group_order` seed). There is no separate income-group dimension and no group on the fact.
- **The assumption is stated, not modelled:** the README's assumptions say income groups are the current classification applied to every year, with the hindsight bias that implies (ADR-0011's consequences stand). The income-group report repeats it in its description.
- The marts are `fct_indicator_value` → `dim_country`, `dim_indicator`.

### Alternatives considered
- **The yearly group on the fact (ADR-0029) or at country × year grain (ADR-0011):** future-proof for a historical source, but that source is out of scope and the outputs are identical.
- **A separate `dim_income_group` for the name and sort order:** a cleaner normal form, but one more join for four rows; a denormalized dimension is standard star-schema practice.

### Consequences
- The analyst model is three tables, and FR-ANA-4 groups the fact by `dim_country.income_group_*` and year.
- If a historical classification is ever allowed, the group moves to the fact at country × year, a change to the model and the income-group report.

---

## ADR-0031: The fact is named fct_country_indicator_value

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-MOD-2 · **Amends:** the fact's name in ADR-0017, ADR-0028 and ADR-0030

### Decision
The current-state fact `fct_indicator_value` is renamed **`fct_country_indicator_value`**. It still follows ADR-0016's `fct_<process>` pattern, naming the measurement (a value), and now also reads as most of its grain (country × indicator, per year). Earlier ADRs keep the old name as written; this entry is the mapping.

### Alternatives considered
- **`fct_indicator_value`:** shorter and conventional for indicator data, but leaves the country implicit.
- **`fct_country_indicator`:** names two dimensions and no measurement, which reads as a bridge or factless table.

---

## ADR-0032: Every table name is plural

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-MOD-2, FR-MOD-3 · **Amends:** ADR-0016 (mart naming), ADR-0031 (the fact's name)

### Context
ADR-0016 names staging and intermediate models after plural entities (`stg_worldbank__countries`, `int_runs_ranked`) but marts after singular ones (`dim_<entity>`), so the layers disagreed. dbt Labs' style guide pluralizes model names, keeping the plural with `dim_`/`fct_` prefixes (`dim_customers`, `fct_orders`); the Kimball tradition uses singular names. Both are accepted; mixing them isn't.

### Decision
- **Every table name is plural, in every layer:** `dim_countries`, `dim_indicators`, `fct_country_indicator_values`, and the seed `income_groups` (formerly `income_group_order`), with `int_countries_joined_to_income_groups` following it.
- ADR-0016's mart pattern becomes `dim_<entities>` and `fct_<process, plural>`; queries read naturally (`FROM dim_countries`).
- Earlier ADRs keep the names as written; this entry is the mapping.

### Alternatives considered
- **Singular marts, justified as Kimball style:** defensible, but the marts would differ from staging and intermediate for no reason a reader could see.

### Consequences
- One convention from staging to marts, matching the dbt guide reviewers are likely to know.

---

## ADR-0033: Staging cleans values; intermediate interprets them

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-MOD-3 · **Amends:** ADR-0016 (what staging does)

### Context
ADR-0016 says staging does "renaming, casting and flattening only", yet staging already trimmed names because the API sends some with trailing spaces (source-system §2). Text from the source can also carry repeated spaces, tabs or empty strings. In medallion terms, the landing zone and `raw` are bronze (exact source), and staging starts silver (cleaned, typed, standardized).

### Decision
- **Staging renames, casts, flattens and cleans values,** one source entity at a time, with no joins or business rules. Every text value from the source goes through `normalize_text`: trimmed, runs of whitespace (spaces, tabs, newlines) collapsed to one space, and empty results turned into null.
- **Labels stay readable:** names keep the World Bank's wording and case (`High income`, `United States`); codes (`HIC`, `USA`) are the standardized values for logic, and our own category values stay lowercase snake_case.
- **Intermediate interprets:** anything that's a business decision rather than cleaning (mapping a source's region to a company's own region, reconciling two sources' spellings) belongs in intermediate.

### Alternatives considered
- **Normalize in intermediate:** every model reading staging would repeat it, or a cleaning-only model per entity would be needed, which ADR-0026 forbids as a pass-through.
- **Upper-case, underscored labels (`HIGH_INCOME`):** standard for codes, but these are display labels; codes already exist next to them.

### Consequences
- Every layer above staging sees clean text; the raw layer keeps the exact bytes.
- The README maps the layers to the medallion vocabulary for readers who think in bronze, silver and gold.

---

## ADR-0034: Report tables are exported to CSV by `worldbank export`

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ANA-1 to FR-ANA-4, NFR-6 · **Amends:** ADR-0022 (who exports, and when)

### Context
The brief asks for sample output of the reporting queries, committed (for example CSV), so a reviewer can read the answers without running anything. ADR-0022 left exports to dbt, published together with the warehouse, mechanism to be decided. Exporting on every build would rewrite tracked files on each run.

### Decision
- **`worldbank export` (just `export`) writes every table of the published warehouse's `reporting` schema to its own CSV,** `data/outputs/<table>.csv`, with a header and rows sorted for reading (income groups low to high, then country, indicator and year). Tables are discovered from the schema, so a new report is exported without code changes. `--output` overrides the folder.
- **It reads only the published warehouse,** so it exports audited data only, and refuses if nothing is published. Each file is written to a temporary name and renamed; report CSVs no longer in the schema are removed from the folder, other files are left alone.
- **It isn't part of `just build`:** a normal build never touches tracked files. Exporting and committing the sample are deliberate steps.
- **`data/outputs/` is committed** through an explicit `.gitignore` exception, so the sample in the repository is exactly what the command writes. Python does extract, load, publish and export; dbt does transform and test.

### Alternatives considered
- **A dbt operation after publish (ADR-0022's intent):** keeps exports in dbt, but less direct to test and to run on its own than a command next to `publish`.
- **Export on every build:** outputs always match the last build, but every run changes tracked files.
- **`data/samples/outputs/`:** `data/samples/` holds hand-saved API responses from exploration, kept local (ADR-0012); generated deliverables don't belong with them.

### Consequences
- One command regenerates the committed sample from an audited build.
- The sample can be older than the code if it isn't re-exported; the README's setup says when to run it.

---

## ADR-0035: The scope can be overridden for one run on the command line

- **Date:** 2026-11-27 · **Kind:** Decision · **Status:** Accepted
- **Serves:** NFR-4 · **Builds on:** ADR-0015, ADR-0016

### Context
Exploring a different scope (all economies and indicators, a shorter year range) meant editing `config.yml` and remembering to revert it. NFR-4 asks that scope changes need no code; it doesn't ask that every run use the committed file.

### Decision
- `worldbank extract` (and `just extract`, `just run`) take `--countries`, `--indicators` (comma-separated codes) and `--years START:END`. Each replaces only that part of the configured scope, for that run.
- The effective configuration is validated exactly like the file (same rules, same error, exit code 2) before any request, and recorded in the run's manifest, so the run's expected set and every report follow what was actually fetched (ADR-0016).
- `config.yml` stays the committed scope; overrides leave no trace except in the runs they produced.

### Alternatives considered
- **Edit `config.yml` for each exploration:** works, but easy to commit by mistake, and the committed sample would then describe a scope nobody intended.
- **A second configuration file per scope:** fine for long-lived scopes (`--config` already allows it), heavy for a one-off question.

### Consequences
- A run's scope is always the one in its manifest, which may differ from `config.yml`; the latest run's scope drives current state.
- Exploratory runs belong in their own data folder (`--data-dir`), so they don't become the latest run of the main landing zone.

---

## ADR-0036: An HTML report rendered from the reporting tables

- **Date:** 2026-11-27 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ANA-5 (optional), FR-ANA-1 to FR-ANA-4 · **Builds on:** ADR-0034

### Context
The CSV exports answer the brief's questions but are tables to open one by one. The brief's optional extra asks for a view or dashboard; a reviewer benefits from one page that shows all four answers.

### Decision
- **`worldbank report` (just `report`) renders the published warehouse's six `rpt_*` tables as one self-contained HTML page,** `reports/report.html` at the repository root (`--output` overrides it). It's a serving step like `export`: it reads only the published warehouse and refuses if nothing is published.
- **Self-contained and safe:** inline CSS and SVG charts, no scripts, no external files, no new dependency; every value from the warehouse is HTML-escaped. The page is deterministic (no timestamp), so re-rendering the same warehouse gives the same bytes.
- **One section per question:** a completeness grid with any gaps listed; year-over-year changes, coloured, with the reason for each null; rankings at each country's latest year with the like-for-like column; income-group lines and coverage per indicator. `just run` ends with it, and the rendered page is committed.

### Alternatives considered
- **A BI tool or notebook:** richer interaction, but an account, a server or a dependency, against NFR-5's local, credential-free setup.
- **A Jinja template:** cleaner separation for a bigger page; for one page, the standard library keeps the dependency list unchanged.

### Consequences
- A reviewer opens one file in a browser and sees every answer.
- The page shows what the reporting tables hold; changing a report means changing its dbt model, then re-rendering.

---

## ADR-0037: dim_indicators keeps only columns with meaning

- **Date:** 2026-11-27 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-MOD-2, NFR-1 · **Amends:** ADR-0017

### Context
A review of the marts found four indicator columns that misled more than they informed. `unit` is empty for every configured indicator; the unit is part of the name, for example "GDP (current US$)". `display_decimals`, taken from the observations' `decimal` field, is 0 for GDP and life expectancy although their values have decimals, and nothing reads it. `source_id` and `source_name` are constant, because the pipeline pins source 2, World Development Indicators (ADR-0002). With them, "source" meant four different things in one table.

### Decision
- **Drop `unit`, `display_decimals`, `source_id` and `source_name` from intermediate upward,** along with the singular test that guarded `display_decimals`. Staging keeps them, since it mirrors the landed responses (ADR-0033), so each is one model change away if a use appears.
- **The remaining `source_*` columns all describe where the data comes from:** `source_organization` (the producers the World Bank cites), `source_lastupdated` (the World Bank release of the current values, from the observation pages) and `source_response_id` (the landed metadata page the row comes from; values trace through the fact's own `source_response_id`).

### Alternatives considered
- **Keep the columns and document them:** honest, but an empty, constant or wrong column costs every reader a question.
- **Rename `source_id` and `source_name` to `database_*`:** clearer, but still constant.

### Consequences
- `dim_indicators` holds an indicator's identity, description, release and aggregation method, and nothing else.
- The API's other indicator fields stay in staging and the landing zone (NFR-1).

---

## ADR-0038: Income groups average their countries

- **Date:** 2026-11-27 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ANA-4, NFR-4, FR-MOD-2 · **Supersedes:** ADR-0009's income-group aggregation (Q4) · **Amends:** ADR-0010, ADR-0037

### Context
ADR-0009 aggregated each indicator by its nature: population and GDP summed, GDP per capita as Σ GDP ÷ Σ population, life expectancy weighted by population. That needed an aggregation seed, an intermediate model, four columns in `dim_indicators` (`aggregation_method` and the numerator, denominator and weight indicators), three self-joins in the report, and a seed row for every new indicator, without which the build failed. The marts should be a minimal star schema whose every column is obviously correct.

### Decision
- **An income group's value is the average of its countries that have a value,** the same rule for every indicator: `avg(indicator_value)` per group, indicator and year, with `n_countries_with_data` of `n_countries`. A group without data has a null average, never 0.
- **The aggregation recipe is removed:** the `indicator_aggregations` seed, `int_indicators_joined_to_aggregations` and the four `dim_indicators` columns.
- **The GDP consistency check (FR-DQ-2) names its three indicators directly** instead of reading them from `dim_indicators`, and checks nothing when any of them is out of scope.

### Alternatives considered
- **Keep the per-indicator recipe (ADR-0009):** economically exact totals and an aggregate GDP per capita, at the cost of metadata in the marts and setup for every indicator.
- **Exact aggregates written out in the report's SQL:** simple to read, but adding an indicator would mean editing the report.

### Consequences
- The value describes the typical country in a group: an average population, not a total, and an average of GDP per capita, not the group's GDP per capita. The README states it as an assumption.
- Adding an indicator is configuration only, with no seed row.
- `dim_indicators` holds an indicator's identity, description and release, and nothing about aggregation.

---

## ADR-0039: Regions get their own dimension

- **Date:** 2026-11-27 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-MOD-2 · **Amends:** ADR-0017, ADR-0028

### Context
`dim_countries` carried a country's ISO 3166-1 alpha-2 code next to its alpha-3 `country_id`, and its region's name next to the region's id, repeated for every country in the region. The fact carried `obs_status`, which the API leaves empty for every value in scope.

### Decision
- **`dim_regions`, one row per region of the latest run's countries,** keyed by the World Bank's `region_id`, with `region_name`. The API describes a region only on its countries, so `int_regions_derived_from_countries` collects the distinct ones; a region id with two names fails its uniqueness test.
- **`dim_countries` keeps `region_id` as a foreign key** to `dim_regions` and drops `region_name` and `country_iso2`, an alternate identifier nothing uses.
- **The fact drops `obs_status`.**
- Staging and intermediate keep all three fields as the API sent them, so each is one model change away.

### Alternatives considered
- **Keep the region name in `dim_countries`:** one join fewer for analysts, at the cost of a repeated attribute.
- **Move income groups to their own dimension too:** consistent, but the income group carries the analysis's own sort order and is read by a report on every query; it stays a country attribute (ADR-0030).

### Consequences
- Countries reach their region through `region_id`, a dimension-to-dimension relationship: a small snowflake on one attribute.
- Every mart column now has a use or a documented meaning.

---

## ADR-0040: Income groups get their own dimension

- **Date:** 2026-11-27 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-MOD-2 · **Amends:** ADR-0039 · **Supersedes:** ADR-0030's sort order

### Context
ADR-0039 gave regions their own dimension but kept the income group's name and sort order on every country, so the two groupings of a country were modeled differently. The sort order came from a seed that existed only to list groups from low to high income in reports.

### Decision
- **`dim_income_groups`, one row per income group of the latest run's countries,** keyed by the World Bank's `income_group_id`, with `income_group_name`. `int_income_groups_derived_from_countries` collects the distinct ones; a group id with two names fails its uniqueness test.
- **`dim_countries` keeps only foreign keys for its groupings:** `region_id` and `income_group_id`.
- **No sort order in the model:** the `income_groups` seed, `int_countries_joined_to_income_groups` and `income_group_sort_order` are removed. Ordering groups from low to high income is presentation, so the HTML report orders them itself; the CSV export sorts by `income_group_id`.

### Alternatives considered
- **Keep the group on the country (ADR-0039):** one join fewer for the income-group report, but two groupings modeled two ways.
- **Keep the sort order in `dim_income_groups`:** reports sort without knowing the groups, at the cost of a seed and a column that only serve display.

### Consequences
- Regions and income groups are modeled the same way: a dimension each, with an id and a name, reached from `dim_countries`.
- The project has no seeds left.
- A new income group would appear in the HTML report after the known ones, until the report's display order lists it.

---

## ADR-0041: dim_countries keeps the ISO alpha-2 code

- **Date:** 2026-11-27 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-MOD-2 · **Amends:** ADR-0039

### Context
ADR-0039 dropped `country_iso2` from `dim_countries` as an alternate identifier nothing used. But it's an attribute of the country, not a duplicate of another column: other datasets analysts join to are often keyed by the alpha-2 code.

### Decision
- **`dim_countries` keeps `country_iso2`,** the ISO 3166-1 alpha-2 code, as an attribute. `country_id` (alpha-3) stays the key.
- It's tested as unique, not null and two upper-case letters.

### Consequences
- Analysts can join external data keyed by either ISO code without a mapping table.

---

## ADR-0042: Lineage only on the fact

- **Date:** 2026-11-27 · **Kind:** Decision · **Status:** Accepted
- **Serves:** NFR-1, FR-MOD-2 · **Amends:** ADR-0028

### Context
`dim_countries` and `dim_indicators` carried `source_response_id`, the landed metadata page each row came from, while `dim_regions` and `dim_income_groups` couldn't, being derived from several countries. NFR-1 asks that every output value be traceable, and the values are in the fact.

### Decision
- **Only the fact carries `source_response_id`.** The dimensions hold business attributes only.
- A dimension attribute (a country's name, an indicator's definition) is traced through `int_countries_filtered_to_latest_run` and `int_indicators_filtered_to_latest_run`, which keep `run_id` and `source_response_id`, like runs, pages and history (ADR-0028).

### Alternatives considered
- **Lineage on every dimension that can have it:** one column fewer to look up for an engineer, at the cost of a technical column in analyst tables and an inconsistency with the derived dimensions.

### Consequences
- Every mart column except the fact's `source_response_id` is a business attribute.
- `trace_value.sql` is unchanged: it starts from the fact's history and the landed pages.

---

## ADR-0043: Income-group aggregates written out in the report

- **Date:** 2026-11-27 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ANA-4 · **Supersedes:** ADR-0038's average · **Restores:** ADR-0009's aggregation (Q4)

### Context
ADR-0038 replaced per-indicator aggregation with the average of a group's countries, to remove the aggregation metadata from the marts. The live run showed the cost: an average population per country (lower middle income, India alone, at 1.45 B against 132 M for high income) answers no one's question; an average of countries' GDP per capita is the average-of-ratios error ADR-0009 avoided; an unweighted life expectancy counts Canada like the United States. The problem was never the aggregation rules but where they were stored.

### Decision
- **`rpt_income_group_by_year` writes the aggregate of each of the brief's four indicators out in SQL:** population and GDP summed; GDP per capita as Σ GDP ÷ Σ population; life expectancy weighted by population. Each row says how its value was computed (`aggregation`) and how many countries contributed (`n_countries_with_data` of `n_countries`): only countries with everything their formula needs. A group without data has a null value, never 0.
- **The marts stay as they are:** no aggregation metadata, no seed (ADR-0038's removals stand).
- An indicator outside the four, or one whose inputs are out of scope, gets no row or a null value with zero coverage.

### Alternatives considered
- **The average of countries (ADR-0038):** one rule for any indicator, but wrong or weak for all four of the brief's.
- **Per-indicator recipes in a seed (ADR-0009):** extends to new indicators, at the cost of metadata in the marts and a seed row per indicator.

### Consequences
- The income-group comparison is economically correct for the brief's indicators, and each formula can be read and checked at a glance.
- **NFR-4 exception:** a new indicator extends every other report through configuration alone, but appears in this one only once its aggregate is written into the report. The README states it.

---

## ADR-0044: One reporting table per question

- **Date:** 2026-11-27 · **Kind:** Decision · **Status:** Accepted
- **Serves:** FR-ANA-1 to FR-ANA-4 · **Amends:** ADR-0008, ADR-0009

### Context
The reporting layer had six tables for the brief's four questions, in two redundant pairs: cell-level and series-level completeness (the second a rollup of the first), and each country's own latest year next to the latest common year, at the same grain.

### Decision
**Four tables, one per question, each named for it:**
- `rpt_completeness` (country × indicator × year): `value_status` for each cell and `series_status` for its series, so one table answers both "which combinations are missing" and "which series are incomplete".
- `rpt_year_over_year`, unchanged.
- `rpt_latest_year` (country × indicator): each country's own latest year, value and rank, next to the latest common year, the value in it and the rank on it.
- `rpt_income_group_by_year`, unchanged.

### Alternatives considered
- **Keep separate tables per view:** each is simpler on its own, but analysts join two tables to see one answer, and the series counts duplicate the cells.

### Consequences
- Each question maps to one table and one CSV.
- Per-series counts are a `GROUP BY` on `rpt_completeness` rather than a table of their own.
