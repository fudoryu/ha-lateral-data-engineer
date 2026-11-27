-- Trace one cell to everything behind it (ADR-0028, NFR-1): each version of its value across
-- runs, the landed page it came from (URL, fetch time, sha256, the source's release date) and
-- the run that fetched it (commit time, code version). The current version is the value
-- analysts see in fct_indicator_value; the page is also its file in the landing zone.
--
-- From the repo root, against the live warehouse:
--   WORLDBANK_WAREHOUSE=data/warehouse/worldbank.duckdb uv run dbt show \
--     --project-dir pipelines/worldbank/dbt --profiles-dir pipelines/worldbank/dbt \
--     --select trace_value --vars '{country: BRA, indicator: NY.GDP.MKTP.CD, year: 2023}'
-- Add `--output json` to see every column instead of those that fit the terminal.
WITH

history AS (
    SELECT * FROM {{ ref('int_indicator_values_versioned') }}
    WHERE
        country_id = '{{ var("country", "BRA") }}'
        AND indicator_id = '{{ var("indicator", "NY.GDP.MKTP.CD") }}'
        AND observation_year = {{ var("year", 2023) }}
),

pages AS (
    SELECT * FROM {{ ref('int_responses_joined_to_runs') }}
),

runs AS (
    SELECT * FROM {{ ref('int_runs_ranked') }}
)

SELECT
    history.country_id,
    history.indicator_id,
    history.observation_year,
    history.is_current,
    history.indicator_value,
    history.value_status,
    history.valid_from_run_id,
    history.valid_to_run_id,
    pages.source_response_id,
    pages.source_url,
    pages.fetched_at,
    pages.source_lastupdated,
    pages.sha256,
    runs.committed_at AS run_committed_at,
    runs.git_sha AS run_git_sha,
    runs.pipeline_version AS run_pipeline_version
FROM history
LEFT JOIN pages ON history.source_response_id = pages.source_response_id
LEFT JOIN runs ON history.valid_from_run_id = runs.run_id
ORDER BY runs.committed_at
