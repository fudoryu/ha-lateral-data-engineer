-- The latest run's indicators with what their current observations say about them: the World
-- Bank release they come from (`lastupdated` on the observation pages; all pages of a request
-- share it, ADR-0005) and how many decimals to display them with (the source's `decimal`, the
-- same for every value of an indicator).
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

precisions AS (
    SELECT
        indicator_id,
        max(decimals) AS display_decimals
    FROM {{ ref('int_indicator_values_filtered_to_latest_run') }}
    GROUP BY indicator_id
),

final AS (
    SELECT
        indicators.indicator_id,
        indicators.indicator_name,
        indicators.unit,
        indicators.source_id,
        indicators.source_name,
        indicators.definition,
        indicators.source_organization,
        releases.source_lastupdated,
        precisions.display_decimals,
        indicators.run_id,
        indicators.source_response_id
    FROM indicators
    LEFT JOIN releases ON indicators.indicator_id = releases.indicator_id
    LEFT JOIN precisions ON indicators.indicator_id = precisions.indicator_id
)

SELECT * FROM final
