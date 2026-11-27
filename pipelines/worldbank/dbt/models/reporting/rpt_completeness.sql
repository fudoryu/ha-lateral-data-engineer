-- FR-ANA-1: every expected country x indicator x year with its status, and its series' status
-- across the reporting years (ADR-0008, ADR-0044). A cell is present, null_value (the API returned
-- the row with a null) or missing_row (no row at all); a series is complete (every year present),
-- incomplete (some) or missing (none). Filter `value_status` for the missing combinations and
-- `series_status` for the incomplete series.
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

series AS (
    SELECT
        country_id,
        indicator_id,
        count(*) AS n_expected,
        sum(CASE WHEN value_status = 'present' THEN 1 ELSE 0 END) AS n_present
    FROM facts
    GROUP BY country_id, indicator_id
),

final AS (
    SELECT
        facts.country_id,
        countries.country_name,
        facts.indicator_id,
        indicators.indicator_name,
        facts.observation_year,
        facts.value_status,
        facts.indicator_value,
        CASE
            WHEN series.n_present = series.n_expected THEN 'complete'
            WHEN series.n_present = 0 THEN 'missing'
            ELSE 'incomplete'
        END AS series_status
    FROM facts
    INNER JOIN series
        ON
            facts.country_id = series.country_id
            AND facts.indicator_id = series.indicator_id
    INNER JOIN countries ON facts.country_id = countries.country_id
    INNER JOIN indicators ON facts.indicator_id = indicators.indicator_id
)

SELECT * FROM final
