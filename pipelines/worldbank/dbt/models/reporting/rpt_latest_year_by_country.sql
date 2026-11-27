-- FR-ANA-3, main view: each country at its own latest year with a value, per indicator, with the
-- year shown, since it can differ by country (ADR-0009). Countries are ranked within each
-- indicator by that value; a country with no value at all keeps its row, with nulls.
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
    SELECT DISTINCT
        country_id,
        indicator_id
    FROM facts
),

latest_years AS (
    SELECT
        country_id,
        indicator_id,
        max(observation_year) AS latest_year
    FROM facts
    WHERE value_status = 'present'
    GROUP BY country_id, indicator_id
),

latest_values AS (
    SELECT
        series.country_id,
        series.indicator_id,
        latest_years.latest_year,
        facts.indicator_value
    FROM series
    LEFT JOIN latest_years
        ON
            series.country_id = latest_years.country_id
            AND series.indicator_id = latest_years.indicator_id
    LEFT JOIN facts
        ON
            latest_years.country_id = facts.country_id
            AND latest_years.indicator_id = facts.indicator_id
            AND latest_years.latest_year = facts.observation_year
),

final AS (
    SELECT
        latest_values.country_id,
        countries.country_name,
        latest_values.indicator_id,
        indicators.indicator_name,
        latest_values.latest_year,
        latest_values.indicator_value,
        CASE
            WHEN latest_values.indicator_value IS NOT NULL
                THEN rank() OVER (
                    PARTITION BY latest_values.indicator_id, latest_values.indicator_value IS NULL
                    ORDER BY latest_values.indicator_value DESC
                )
        END AS rank_in_indicator
    FROM latest_values
    INNER JOIN countries ON latest_values.country_id = countries.country_id
    INNER JOIN indicators ON latest_values.indicator_id = indicators.indicator_id
)

SELECT * FROM final
