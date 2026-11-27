-- The latest run's indicators with the World Bank release their current values come from:
-- `lastupdated` on the latest run's observation pages (all pages of a request share it, ADR-0005).
WITH

indicators AS (
    SELECT * FROM {{ ref('int_indicators_filtered_to_latest_run') }}
),

releases AS (
    SELECT
        request_key AS indicator_id,
        max(source_lastupdated) AS source_lastupdated
    FROM {{ ref('int_responses_joined_to_runs') }}
    WHERE is_latest_run AND endpoint = 'observations'
    GROUP BY request_key
),

final AS (
    SELECT
        indicators.indicator_id,
        indicators.indicator_name,
        indicators.definition,
        indicators.source_organization,
        releases.source_lastupdated,
        indicators.run_id,
        indicators.source_response_id
    FROM indicators
    LEFT JOIN releases ON indicators.indicator_id = releases.indicator_id
)

SELECT * FROM final
