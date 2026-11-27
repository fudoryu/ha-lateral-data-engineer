# List available recipes.
default:
    @just --list

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

# Lint, format check, type check, and tests with coverage: the definition of done (ADR-0013).
check:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy
    uv run pytest --cov --cov-report=term

# Re-record live API responses as test fixtures (calls the live API; commit separately).
record-fixtures:
    uv run python pipelines/worldbank/scripts/record_fixtures.py
