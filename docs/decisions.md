# Decision Log

Architecture decision records (ADRs): one entry per significant decision or assumption. Each entry states the context, the decision, the alternatives considered, the consequences, and the requirements it serves ([`requirements.md`](requirements.md)). Evidence about the source lives in [`source-system.md`](source-system.md).

Entries are append-only. To change a decision, add a new entry that supersedes the old one, and mark the old one `Superseded by ADR-NNNN`.

| ID | Title | Kind | Status |
|---|---|---|---|
| [ADR-0001](#adr-0001-technology-stack) | Technology stack | Decision | Accepted |

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
