-- The latest run's indicators with how each is aggregated across an income group (ADR-0009):
-- the method and the indicators it combines, from the indicator_aggregations seed.
WITH

indicators AS (
    SELECT * FROM {{ ref('int_indicators_joined_to_latest_observations') }}
),

aggregations AS (
    SELECT * FROM {{ ref('indicator_aggregations') }}
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
        indicators.source_lastupdated,
        indicators.display_decimals,
        aggregations.aggregation_method,
        aggregations.numerator_indicator_id,
        aggregations.denominator_indicator_id,
        aggregations.weight_indicator_id,
        indicators.run_id,
        indicators.source_response_id
    FROM indicators
    LEFT JOIN aggregations ON indicators.indicator_id = aggregations.indicator_id
)

SELECT * FROM final
