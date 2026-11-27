-- Every expected cell of every run (ADR-0008) with what the API returned for it: a value, a null
-- value, or no row at all. The only place that decides a cell's status; missing is never zero
-- (NFR-3), and a cell the API didn't return keeps its run but has no source response.
WITH

expected AS (
    SELECT * FROM {{ ref('stg_worldbank__expected_cells') }}
),

observations AS (
    SELECT * FROM {{ ref('stg_worldbank__observations') }}
),

final AS (
    SELECT
        expected.run_id,
        expected.country_id,
        expected.indicator_id,
        expected.observation_year,
        observations.indicator_value,
        CASE
            WHEN observations.run_id IS NULL THEN 'missing_row'
            WHEN observations.indicator_value IS NULL THEN 'null_value'
            ELSE 'present'
        END AS value_status,
        observations.obs_status,
        observations.source_response_id,
        observations.source_lastupdated
    FROM expected
    LEFT JOIN observations
        ON
            expected.run_id = observations.run_id
            AND expected.country_id = observations.country_id
            AND expected.indicator_id = observations.indicator_id
            AND expected.observation_year = observations.observation_year
)

SELECT * FROM final
