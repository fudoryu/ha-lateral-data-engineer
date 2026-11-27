-- Current state has exactly one row per cell the latest run was configured to fetch (ADR-0008,
-- ADR-0028): no cell is lost, none is invented. Fails with both counts when they differ.
WITH

latest_expected AS (
    SELECT count(*) AS cells
    FROM {{ ref('stg_worldbank__expected_cells') }} AS expected
    INNER JOIN {{ ref('int_runs_ranked') }} AS runs ON expected.run_id = runs.run_id
    WHERE runs.is_latest
),

facts AS (
    SELECT count(*) AS cells FROM {{ ref('fct_country_indicator_value') }}
)

SELECT
    latest_expected.cells AS expected_cells,
    facts.cells AS fact_rows
FROM latest_expected
CROSS JOIN facts
WHERE latest_expected.cells <> facts.cells
