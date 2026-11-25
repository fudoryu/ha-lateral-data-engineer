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
| n/a | `uv run worldbank extract` | fetch the configured scope and commit a landing run (calls the live API) |
| `just test` | `uv run pytest` | tests (offline) |
| `just record-fixtures` | `uv run python pipelines/worldbank/tests/record_fixtures.py` | re-record live API responses as test fixtures (commit separately) |
| `just check` | see the `justfile` | lint + format check + type check + tests: **the definition of done** (ADR-0013) |

One-time setup of git hooks: `uv run pre-commit install`. CLI: each pipeline has its own command, for example `uv run worldbank --help` (ADR-0014).

## Rules

**Data** (from the requirements)
- Missing is never zero (NFR-3).
- Every output value is traceable to the API response it came from (NFR-1).
- Scope changes (countries, indicators, years) go in configuration, never in code (NFR-4).
- Only `extract` calls the API; every other step reads from the landing zone `data/raw/<source>/` (ADR-0003, ADR-0014).
- The landing zone is the system of record; the warehouse is a rebuildable cache (ADR-0003).
- API responses are validated before a run commits; validation never alters the landed bytes (ADR-0005).

**Stack** (ADR-0001)
- Python 3.14 managed by uv; run everything through `uv run`.
- Dialect-specific SQL only in the staging layer and the raw loader; everything above staging stays portable.

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
