# Decision Log

Architecture decision records (ADRs): one entry per significant decision or assumption. Each entry states the context, the decision, the alternatives considered, the consequences, and the requirements it serves ([`requirements.md`](requirements.md)). Evidence about the source lives in [`source-system.md`](source-system.md).

Entries are append-only. To change a decision, add a new entry that supersedes the old one, and mark the old one `Superseded by ADR-NNNN`.

| ID | Title | Kind | Status |
|---|---|---|---|
| [ADR-0001](#adr-0001-technology-stack) | Technology stack | Decision | Accepted |
| [ADR-0002](#adr-0002-one-request-per-indicator-covering-all-countries) | One request per indicator, covering all countries | Decision | Accepted |
| [ADR-0003](#adr-0003-separate-ingestion-from-transformation-replay-from-landed-files) | Separate ingestion from transformation; replay from landed files | Decision | Accepted |
| [ADR-0004](#adr-0004-a-landing-run-is-committed-by-writing-its-manifest-last) | A landing run is committed by writing its manifest last | Decision | Accepted |
| [ADR-0005](#adr-0005-validate-configuration-and-api-responses-before-committing-a-run) | Validate configuration and API responses before committing a run | Decision | Accepted |
| [ADR-0006](#adr-0006-fetch-the-full-scope-every-run-keep-every-run-latest-run-wins) | Fetch the full scope every run, keep every run, latest run wins | Decision | Accepted |
| [ADR-0007](#adr-0007-all-or-nothing-runs-and-write-audit-publish) | All-or-nothing runs and write-audit-publish | Decision | Accepted |
| [ADR-0008](#adr-0008-definitions-of-missing-and-incomplete-data) | Definitions of missing and incomplete data | Decision | Accepted |

---

## ADR-0001: Technology stack

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
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

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
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

- **Date:** 2026-11-24 · **Kind:** Decision · **Status:** Accepted
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
