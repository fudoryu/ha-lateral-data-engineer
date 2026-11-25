# List available recipes.
default:
    @just --list

# Run the test suite (offline).
test:
    uv run pytest

# Lint, format check, type check, and tests: the definition of done (ADR-0013).
check:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy
    uv run pytest
