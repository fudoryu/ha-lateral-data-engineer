# List available recipes.
default:
    @just --list

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
