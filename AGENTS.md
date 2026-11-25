# AGENTS.md

The single guide for AI agents and humans in this repo. Tool-specific files (`CLAUDE.md`) only import this file.

## Project

A local, configuration-driven pipeline: World Bank API → traceable yearly indicator dataset (9 countries × 4 indicators × 2018–2024) → four analytics outputs. It's a take-home assessment with a 4–6h time box.

**Read in this order:**
1. [`docs/requirements.md`](docs/requirements.md): what and why, IDs (FR-*, NFR-*, Q*), deliverables (§11)
2. [`docs/source-system.md`](docs/source-system.md): verified World Bank API behavior (errors, quirks, silent revisions)
3. [`docs/references/home-assessment.md`](docs/references/home-assessment.md): the original brief, immutable

## Rules

**Data** (from the requirements)
- Missing is never zero (NFR-3).
- Every output value is traceable to the API response it came from (NFR-1).
- Scope changes (countries, indicators, years) go in configuration, never in code (NFR-4).

**Commits** (Conventional Commits; the hook enforces the format)
- Scopes: `ingestion`, `storage`, `transformation`, `serving`, `config`, `docs`, `repo`.
- Reference requirement IDs in the body, for example `Implements FR-ING-3.`
- Commit small, in the brief's priority order (requirements §8). Never squash: the history is a deliverable.

## Guardrails

- **Never call the live API in tests** (FR-DQ-3).
- **Never hand-edit recorded API responses.**
- **Never edit `docs/references/`.**
- **No cloud resources, accounts, or credentials** (NFR-5).
- Plan non-trivial changes against the requirements first. Update the traceability matrix (requirements §10) when you implement or test a requirement.
