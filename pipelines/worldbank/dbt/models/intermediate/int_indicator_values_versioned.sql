-- One row per version of each cell's value across runs (ADR-0006, ADR-0017). Runs are taken in
-- commit order; a new version starts at a cell's first run and whenever its value or status
-- differs from the previous run's, compared null-safely. A version is valid from its first run
-- until the first run with a different value (exclusive). The current version is the one the
-- latest run holds; a cell later removed from the scope keeps its history but has none.
WITH

cells AS (
    SELECT * FROM {{ ref('int_indicator_values_joined_to_expected') }}
),

runs AS (
    SELECT * FROM {{ ref('int_runs_ranked') }}
),

in_run_order AS (
    SELECT
        cells.country_iso3,
        cells.indicator_id,
        cells.observation_year,
        cells.run_id,
        cells.indicator_value,
        cells.value_status,
        cells.source_response_id,
        runs.committed_at,
        lag(cells.indicator_value) OVER (
            PARTITION BY cells.country_iso3, cells.indicator_id, cells.observation_year
            ORDER BY runs.committed_at, cells.run_id
        ) AS previous_value,
        lag(cells.value_status) OVER (
            PARTITION BY cells.country_iso3, cells.indicator_id, cells.observation_year
            ORDER BY runs.committed_at, cells.run_id
        ) AS previous_status,
        max(CASE WHEN runs.is_latest THEN 1 ELSE 0 END) OVER (
            PARTITION BY cells.country_iso3, cells.indicator_id, cells.observation_year
        ) = 1 AS is_in_latest_run
    FROM cells
    INNER JOIN runs ON cells.run_id = runs.run_id
),

version_starts AS (
    SELECT *
    FROM in_run_order
    WHERE
        previous_status IS NULL
        OR indicator_value IS DISTINCT FROM previous_value
        OR value_status IS DISTINCT FROM previous_status
),

versions AS (
    SELECT
        country_iso3,
        indicator_id,
        observation_year,
        run_id AS valid_from_run_id,
        indicator_value,
        value_status,
        lead(run_id) OVER (
            PARTITION BY country_iso3, indicator_id, observation_year
            ORDER BY committed_at, run_id
        ) AS valid_to_run_id,
        is_in_latest_run,
        source_response_id
    FROM version_starts
),

final AS (
    SELECT
        country_iso3,
        indicator_id,
        observation_year,
        valid_from_run_id,
        indicator_value,
        value_status,
        valid_to_run_id,
        valid_to_run_id IS NULL AND is_in_latest_run AS is_current,
        source_response_id
    FROM versions
)

SELECT * FROM final
