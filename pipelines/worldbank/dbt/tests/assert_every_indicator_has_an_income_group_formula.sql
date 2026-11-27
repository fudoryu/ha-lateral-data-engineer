-- FR-ANA-4, NFR-4 (ADR-0046): every indicator in scope is compared across income groups. The
-- report writes out one formula per indicator (ADR-0043), so an indicator added to configuration
-- without its formula would otherwise be left out of that report silently. A failure blocks
-- publishing (ADR-0007) and names each indicator whose formula is missing.
WITH

indicators AS (
    SELECT * FROM {{ ref('dim_indicators') }}
),

aggregated AS (
    SELECT DISTINCT indicator_id FROM {{ ref('rpt_income_group_by_year') }}
)

SELECT
    indicators.indicator_id,
    indicators.indicator_name
FROM indicators
LEFT JOIN aggregated ON indicators.indicator_id = aggregated.indicator_id
WHERE aggregated.indicator_id IS NULL
