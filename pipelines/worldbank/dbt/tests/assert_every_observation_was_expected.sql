-- Every observation belongs to its run's expected set, so the left join from expected cells
-- drops nothing. Extract already refuses out-of-scope rows (ADR-0005); this guards the join.
SELECT
    observations.run_id,
    observations.country_id,
    observations.indicator_id,
    observations.observation_year
FROM {{ ref('stg_worldbank__observations') }} AS observations
LEFT JOIN {{ ref('stg_worldbank__expected_cells') }} AS expected
    ON
        observations.run_id = expected.run_id
        AND observations.country_id = expected.country_id
        AND observations.indicator_id = expected.indicator_id
        AND observations.observation_year = expected.observation_year
WHERE expected.run_id IS NULL
