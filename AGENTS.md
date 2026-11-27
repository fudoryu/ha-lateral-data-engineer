# AGENTS.md

The single guide for AI agents and humans in this repo. Tool-specific files (`CLAUDE.md`) only import this file.

## Project

A local, configuration-driven pipeline: World Bank API → traceable yearly indicator dataset (9 countries × 4 indicators × 2018–2024) → four analytics outputs. It's a take-home assessment with a 4–6h time box.

**Read in this order:**
1. [`docs/requirements.md`](docs/requirements.md): what and why, IDs (FR-*, NFR-*, Q*), deliverables (§11)
2. [`docs/source-system.md`](docs/source-system.md): verified World Bank API behavior (errors, quirks, silent revisions)
3. [`docs/decisions.md`](docs/decisions.md): accepted decisions and assumptions (ADR-*). Don't contradict one silently; add a superseding entry.
4. [`docs/references/home-assessment.md`](docs/references/home-assessment.md): the original brief, immutable

## Commands

Prerequisite: [uv](https://docs.astral.sh/uv/) (it installs Python 3.14). Optional: `just` (`uv tool install rust-just`).

| Command | Fallback without `just` | Purpose |
|---|---|---|
| `just run` | `uv run worldbank extract`, then the `just build` steps | fetch the configured scope, commit a landing run (calls the live API), then build |
| `just build` | `uv run worldbank load`, `uv run dbt build --project-dir pipelines/worldbank/dbt --profiles-dir pipelines/worldbank/dbt`, `uv run worldbank publish` | rebuild the warehouse from landed runs (offline); publishes only if every dbt test passes (ADR-0022) |
| n/a | `uv run worldbank load --as-of <run_id>` | rebuild as of an earlier run, into a file of its own (never published) |
| `just test` | `uv run pytest` | tests (offline) |
| `just record-fixtures` | `uv run python pipelines/worldbank/scripts/record_fixtures.py` | re-record live API responses as test fixtures (commit separately) |
| `just check` | see the `justfile` | Python and SQL lint + format check + type check + tests with a 95% line-and-branch coverage gate: **the definition of done** (ADR-0013, ADR-0025) |

One-time setup of git hooks: `uv run pre-commit install`. CLI: each pipeline has its own command, for example `uv run worldbank --help` (ADR-0014).

## Rules

**Data** (from the requirements)
- Missing is never zero (NFR-3).
- Every output value is traceable to the API response it came from (NFR-1).
- Scope changes (countries, indicators, years) go in configuration, never in code (NFR-4).
- Only `extract` calls the API; every other step reads from the landing zone `data/raw/<source>/` (ADR-0003, ADR-0014).
- Only `publish` writes the live warehouse; `load` and dbt work on the next file (ADR-0007, ADR-0022).
- The landing zone is the system of record; the warehouse is a rebuildable cache (ADR-0003).
- API responses are validated before a run commits; validation never alters the landed bytes (ADR-0005).

**Stack** (ADR-0001)
- Python 3.14 managed by uv; run everything through `uv run`.
- Dialect-specific SQL only in the staging layer and the raw loader; everything above staging stays portable.
- SQL style (ADR-0025): keywords, types and `NULL`/`TRUE` in upper case, identifiers and functions in lower case, explicit `AS`, no keywords as names. SQLFluff enforces it on `.sql` files (`uv run sqlfluff fix <file>`); keep SQL in `.sql` files, and match the style by hand in the rare SQL string in Python.

**Logging** (ADR-0024)
- Log with the standard library: `log = logging.getLogger(__name__)` at the top of each module; no logging dependencies.
- Only `cli.py` configures logging (handler, level, format). Library code never adds handlers, sets levels, or calls `print`/`typer.echo` for diagnostics.
- Logs go to stderr; stdout is only each command's one-line result.
- Put context in structured fields, not in the message: `log.info("request fetched", extra={"path": ..., "rows": ..., "duration_ms": ...})`. Messages are short lowercase event descriptions; field names are stable snake_case and reuse existing ones (`run_id`, `endpoint`, `page`, `duration_ms`, ...).
- Levels: DEBUG per-file or per-attempt detail; INFO milestones and per-request results; WARNING handled-but-notable (retries, refetches, unknown API fields, skipped runs); ERROR a failed command.
- Log an error once, where it's handled (the CLI), not where it's raised; expected errors without a traceback, unexpected ones with it.
- Never log response bodies or payloads (they're in the landing zone) or anything secret.
- New behavior that an operator would need to see (a retry, a skip, a refusal) gets a log event and a test asserting it.

**Commits** (Conventional Commits; the hook enforces the format)
- Scopes: `ingestion`, `storage`, `transformation`, `serving`, `config`, `docs`, `repo`.
- Reference requirement and decision IDs in the body, for example `Implements FR-ING-3; see ADR-0001.`
- Commit small, in the brief's priority order (requirements §8). Never squash: the history is a deliverable.

## Guardrails

- **Never call the live API in tests** (FR-DQ-3).
- **Never hand-edit recorded API responses** (`tests/fixtures/recorded/`); re-record them deliberately instead (ADR-0012).
- **Never modify or delete committed landing runs**; current state comes from the latest committed run (ADR-0006).
- **Never edit `docs/references/`.**
- **No cloud resources, accounts, or credentials** (NFR-5).
- Plan non-trivial changes against the requirements first. Update the traceability matrix (requirements §10) when you implement or test a requirement.
