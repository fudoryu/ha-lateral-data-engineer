-- One row per configured indicator, from the latest run: its metadata and the World Bank release
-- its current values come from.
WITH

indicators AS (
    SELECT * FROM {{ ref('int_indicators_joined_to_latest_observations') }}
),

final AS (
    SELECT
        indicator_id,
        indicator_name,
        definition,
        source_organization,
        source_lastupdated,
        source_response_id
    FROM indicators
)

SELECT * FROM final
