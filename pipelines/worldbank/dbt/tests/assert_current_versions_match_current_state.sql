-- The value history agrees with current state (ADR-0017): every cell of the latest run has
-- exactly one current version, with the same value and status, and no other cell has one.
WITH

current_versions AS (
    SELECT * FROM {{ ref('int_indicator_values_versioned') }}
    WHERE is_current
),

current_cells AS (
    SELECT * FROM {{ ref('int_indicator_values_filtered_to_latest_run') }}
)

SELECT
    coalesce(current_cells.country_id, current_versions.country_id) AS country_id,
    coalesce(current_cells.indicator_id, current_versions.indicator_id) AS indicator_id,
    coalesce(current_cells.observation_year, current_versions.observation_year)
        AS observation_year
FROM current_cells
FULL OUTER JOIN current_versions
    ON
        current_cells.country_id = current_versions.country_id
        AND current_cells.indicator_id = current_versions.indicator_id
        AND current_cells.observation_year = current_versions.observation_year
WHERE
    current_cells.country_id IS NULL
    OR current_versions.country_id IS NULL
    OR current_cells.indicator_value IS DISTINCT FROM current_versions.indicator_value
    OR current_cells.value_status IS DISTINCT FROM current_versions.value_status
