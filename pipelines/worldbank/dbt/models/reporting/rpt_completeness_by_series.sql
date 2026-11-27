-- FR-ANA-1, series level: each country x indicator across the reporting years is complete (every
-- year present), incomplete (some) or missing (none), with its counts (ADR-0008).
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
        sum(CASE WHEN value_status = 'present' THEN 1 ELSE 0 END) AS n_present,
        sum(CASE WHEN value_status = 'null_value' THEN 1 ELSE 0 END) AS n_null_value,
        sum(CASE WHEN value_status = 'missing_row' THEN 1 ELSE 0 END) AS n_missing_row
    FROM facts
    GROUP BY country_id, indicator_id
),

final AS (
    SELECT
        series.country_id,
        countries.country_name,
        series.indicator_id,
        indicators.indicator_name,
        CASE
            WHEN series.n_present = series.n_expected THEN 'complete'
            WHEN series.n_present = 0 THEN 'missing'
            ELSE 'incomplete'
        END AS series_status,
        series.n_present,
        series.n_expected,
        series.n_null_value,
        series.n_missing_row
    FROM series
    INNER JOIN countries ON series.country_id = countries.country_id
    INNER JOIN indicators ON series.indicator_id = indicators.indicator_id
)

SELECT * FROM final
