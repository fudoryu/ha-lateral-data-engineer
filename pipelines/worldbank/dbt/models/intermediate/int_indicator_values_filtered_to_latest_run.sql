-- The latest run's cells: current state, one row per expected country x indicator x year
-- (ADR-0006, ADR-0017).
WITH

cells AS (
    SELECT * FROM {{ ref('int_indicator_values_joined_to_expected') }}
),

latest_run AS (
    SELECT run_id FROM {{ ref('int_runs_ranked') }}
    WHERE is_latest
),

final AS (
    SELECT
        cells.country_id,
        cells.indicator_id,
        cells.observation_year,
        cells.indicator_value,
        cells.value_status,
        cells.unit,
        cells.obs_status,
        cells.decimals,
        cells.run_id,
        cells.source_response_id,
        cells.source_lastupdated
    FROM cells
    INNER JOIN latest_run ON cells.run_id = latest_run.run_id
)

SELECT * FROM final
