-- FR-ANA-1, cell level: every expected country x indicator x year with its status (ADR-0008):
-- present, null_value (the API returned the row with a null) or missing_row (no row at all).
WITH

facts AS (
    SELECT * FROM {{ ref('fct_country_indicator_values') }}
),

countries AS (
    SELECT * FROM {{ ref('dim_countries') }}
),

indicators AS (
    SELECT * FROM {{ ref('dim_indicators') }}
),

final AS (
    SELECT
        facts.country_id,
        countries.country_name,
        facts.indicator_id,
        indicators.indicator_name,
        facts.observation_year,
        facts.value_status,
        facts.value_status <> 'present' AS is_missing,
        facts.indicator_value
    FROM facts
    INNER JOIN countries ON facts.country_id = countries.country_id
    INNER JOIN indicators ON facts.indicator_id = indicators.indicator_id
)

SELECT * FROM final
