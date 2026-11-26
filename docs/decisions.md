# Decision Log

Architecture decision records (ADRs): one entry per significant decision or assumption. Each entry states the context, the decision, the alternatives considered, the consequences, and the requirements it serves ([`requirements.md`](requirements.md)). Evidence about the source lives in [`source-system.md`](source-system.md).

Entries are append-only. To change a decision, add a new entry that supersedes the old one, and mark the old one `Superseded by ADR-NNNN`.

| ID | Title | Kind | Status |
|---|---|---|---|
| [ADR-0001](#adr-0001-technology-stack) | Technology stack | Decision | Accepted (configuration library amended by ADR-0015) |
| [ADR-0002](#adr-0002-one-request-per-indicator-covering-all-countries) | One request per indicator, covering all countries | Decision | Accepted |
| [ADR-0003](#adr-0003-separate-ingestion-from-transformation-replay-from-landed-files) | Separate ingestion from transformation; replay from landed files | Decision | Accepted (command name amended by ADR-0018) |
| [ADR-0004](#adr-0004-a-landing-run-is-committed-by-writing-its-manifest-last) | A landing run is committed by writing its manifest last | Decision | Accepted (path amended by ADR-0014) |
| [ADR-0005](#adr-0005-validate-configuration-and-api-responses-before-committing-a-run) | Validate configuration and API responses before committing a run | Decision | Accepted |
| [ADR-0006](#adr-0006-fetch-the-full-scope-every-run-keep-every-run-latest-run-wins) | Fetch the full scope every run, keep every run, latest run wins | Decision | Accepted |
| [ADR-0007](#adr-0007-all-or-nothing-runs-and-write-audit-publish) | All-or-nothing runs and write-audit-publish | Decision | Accepted |
| [ADR-0008](#adr-0008-definitions-of-missing-and-incomplete-data) | Definitions of missing and incomplete data | Decision | Accepted |
| [ADR-0009](#adr-0009-analytics-interpretations-latest-year-income-group-aggregation-year-over-year) | Analytics interpretations: latest year, income-group aggregation, year-over-year | Decision | Accepted |
| [ADR-0010](#adr-0010-gdp-consistency-check-with-a-01-tolerance) | GDP consistency check with a 0.1% tolerance | Decision | Accepted |
| [ADR-0011](#adr-0011-current-income-classification-applies-to-every-year) | Current income classification applies to every year | **Assumption** | Accepted |
| [ADR-0012](#adr-0012-test-fixtures-recorded-responses-plus-crafted-scenarios) | Test fixtures: recorded responses plus crafted scenarios | Decision | Accepted |
| [ADR-0013](#adr-0013-developer-tooling-and-documentation-layout) | Developer tooling and documentation layout | Decision | Accepted (recipe names amended by ADR-0018) |
| [ADR-0014](#adr-0014-one-project-per-pipeline-in-a-uv-workspace) | One project per pipeline in a uv workspace | Decision | Accepted |
| [ADR-0015](#adr-0015-configuration-is-loaded-with-plain-pydantic-and-pyyaml) | Configuration is loaded with plain Pydantic and PyYAML | Decision | Accepted |
| [ADR-0016](#adr-0016-dbt-project-layout-layers-and-naming) | dbt project layout, layers and naming | Decision | Accepted |
| [ADR-0017](#adr-0017-marts-data-model-grain-keys-relationships-and-lineage) | Marts data model: grain, keys, relationships and lineage | Decision | Accepted |
| [ADR-0018](#adr-0018-pipeline-commands-extract-build-run) | Pipeline commands: extract, build, run | Decision | Accepted |
| [ADR-0019](#adr-0019-hand-written-extraction-instead-of-an-el-framework) | Hand-written extraction instead of an EL framework | Decision | Accepted |

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

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
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

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
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

- **Date:** 2026-11-24 · **Kind:** Assumption · **Status:** Accepted
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

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
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

- **Date:** 2026-11-26 · **Kind:** Decision · **Status:** Accepted
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
