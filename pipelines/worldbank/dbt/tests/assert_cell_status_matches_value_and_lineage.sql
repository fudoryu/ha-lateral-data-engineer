-- A cell's status, value and lineage agree (ADR-0008, ADR-0017): only present cells have a
-- value, and only missing rows lack a source response.
SELECT
    run_id,
    country_id,
    indicator_id,
    observation_year,
    value_status,
    indicator_value,
    source_response_id
FROM {{ ref('int_indicator_values_joined_to_expected') }}
WHERE
    (value_status = 'present') <> (indicator_value IS NOT NULL)
    OR (value_status = 'missing_row') <> (source_response_id IS NULL)
