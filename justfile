# List available recipes.
default:
    @just --list

# Write every report table of the published warehouse to data/outputs/ as CSV (ADR-0034).
export:
    uv run worldbank export

# Fetch from the API, then rebuild and publish the warehouse (calls the live API).
run:
    uv run worldbank extract
    just build

# Rebuild the warehouse from landed runs (offline); publish only if every dbt test passes (ADR-0022).
build:
    uv run worldbank load
    uv run dbt build --project-dir pipelines/worldbank/dbt --profiles-dir pipelines/worldbank/dbt
    uv run worldbank publish

# Run the test suite (offline).
test:
    uv run pytest

# Python and SQL lint, format check, type check, and tests with coverage: the definition of done
# (ADR-0013, ADR-0025). The tests include one end-to-end run of the chain, dbt build included.
check:
    uv run ruff check .
    uv run ruff format --check .
    uv run sqlfluff lint pipelines
    uv run mypy
    uv run pytest --cov --cov-report=term

# Re-record live API responses as test fixtures (calls the live API; commit separately).
record-fixtures:
    uv run python pipelines/worldbank/scripts/record_fixtures.py
