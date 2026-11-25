# Decision Log

Architecture decision records (ADRs): one entry per significant decision or assumption. Each entry states the context, the decision, the alternatives considered, the consequences, and the requirements it serves ([`requirements.md`](requirements.md)). Evidence about the source lives in [`source-system.md`](source-system.md).

Entries are append-only. To change a decision, add a new entry that supersedes the old one, and mark the old one `Superseded by ADR-NNNN`.

| ID | Title | Kind | Status |
|---|---|---|---|
| [ADR-0001](#adr-0001-technology-stack) | Technology stack | Decision | Accepted |
| [ADR-0002](#adr-0002-one-request-per-indicator-covering-all-countries) | One request per indicator, covering all countries | Decision | Accepted |
| [ADR-0003](#adr-0003-separate-ingestion-from-transformation-replay-from-landed-files) | Separate ingestion from transformation; replay from landed files | Decision | Accepted |
| [ADR-0004](#adr-0004-a-landing-run-is-committed-by-writing-its-manifest-last) | A landing run is committed by writing its manifest last | Decision | Accepted |

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
