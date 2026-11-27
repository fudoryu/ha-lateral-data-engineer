-- FR-ANA-3, like-for-like view: per indicator, every country at the latest year all countries
-- have a value for, so they're compared on the same year (ADR-0009). An indicator with no such
-- year keeps its rows, with a null year and values.
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

year_coverage AS (
    SELECT
        indicator_id,
        observation_year,
        count(*) AS n_countries,
        sum(CASE WHEN value_status = 'present' THEN 1 ELSE 0 END) AS n_present
    FROM facts
    GROUP BY indicator_id, observation_year
),

common_years AS (
    SELECT
        indicator_id,
        max(observation_year) AS common_year
    FROM year_coverage
    WHERE n_present = n_countries
    GROUP BY indicator_id
),

series AS (
    SELECT DISTINCT
        country_id,
        indicator_id
    FROM facts
),

common_values AS (
    SELECT
        series.country_id,
        series.indicator_id,
        common_years.common_year,
        facts.indicator_value
    FROM series
    LEFT JOIN common_years ON series.indicator_id = common_years.indicator_id
    LEFT JOIN facts
        ON
            series.country_id = facts.country_id
            AND series.indicator_id = facts.indicator_id
            AND common_years.common_year = facts.observation_year
),

final AS (
    SELECT
        common_values.country_id,
        countries.country_name,
        common_values.indicator_id,
        indicators.indicator_name,
        common_values.common_year,
        common_values.indicator_value,
        CASE
            WHEN common_values.indicator_value IS NOT NULL
                THEN rank() OVER (
                    PARTITION BY common_values.indicator_id, common_values.indicator_value IS NULL
                    ORDER BY common_values.indicator_value DESC
                )
        END AS rank_in_indicator
    FROM common_values
    INNER JOIN countries ON common_values.country_id = countries.country_id
    INNER JOIN indicators ON common_values.indicator_id = indicators.indicator_id
)

SELECT * FROM final
