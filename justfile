# List available recipes.
default:
    @just --list

# Write every report table of the published warehouse to data/outputs/ as CSV (ADR-0034).
export:
    uv run worldbank export

# The whole pipeline (fetch, build, publish, export); args override the scope: --years 2020:2024.
run *args:
    uv run worldbank extract {{args}}
    just build
    just export

# Fetch from the API and commit a landing run; arguments override the scope, as for `run`.
extract *args:
    uv run worldbank extract {{args}}

# Rebuild the warehouse from landed runs (offline); publish only if every dbt test passes (ADR-0022).
build:
    uv run worldbank load
    uv run dbt build --project-dir pipelines/worldbank/dbt --profiles-dir pipelines/worldbank/dbt
    uv run worldbank publish

# Run the test suite (offline).
test:
    uv run pytest

# Definition of done (ADR-0013, ADR-0025): Python and SQL lint, types, tests incl. dbt end to end.
check:
    uv run ruff check .
    uv run ruff format --check .
    uv run sqlfluff lint pipelines
    uv run mypy
    uv run pytest --cov --cov-report=term

# Re-record live API responses as test fixtures (calls the live API; commit separately).
record-fixtures:
    uv run python pipelines/worldbank/scripts/record_fixtures.py
