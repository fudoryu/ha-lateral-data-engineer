-- One row per configured indicator, from the latest run: its metadata, the World Bank release its
-- current values come from, and how it aggregates across an income group (ADR-0009).
WITH

indicators AS (
    SELECT * FROM {{ ref('int_indicators_joined_to_aggregations') }}
),

final AS (
    SELECT
        indicator_id,
        indicator_name,
        unit,
        source_id,
        source_name,
        definition,
        source_organization,
        source_lastupdated,
        aggregation_method,
        numerator_indicator_id,
        denominator_indicator_id,
        weight_indicator_id,
        source_response_id
    FROM indicators
)

SELECT * FROM final
