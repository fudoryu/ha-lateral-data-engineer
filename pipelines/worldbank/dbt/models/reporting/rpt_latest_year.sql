-- FR-ANA-3: each country per indicator at its own latest year with a value, next to the latest
-- year every country has a value for, so both views sit side by side (ADR-0009, ADR-0044). The
-- latest year can differ by country, so it's shown; the common year compares like with like and
-- is null when no year has a value for every country. Ranks are within the indicator, 1 being the
-- highest; a country without a value keeps its row, unranked.
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

country_values AS (
    SELECT
        series.country_id,
        series.indicator_id,
        latest_years.latest_year,
        latest.indicator_value AS latest_value,
        common_years.common_year,
        common.indicator_value AS common_value
    FROM series
    LEFT JOIN latest_years
        ON
            series.country_id = latest_years.country_id
            AND series.indicator_id = latest_years.indicator_id
    LEFT JOIN facts AS latest
        ON
            latest_years.country_id = latest.country_id
            AND latest_years.indicator_id = latest.indicator_id
            AND latest_years.latest_year = latest.observation_year
    LEFT JOIN common_years ON series.indicator_id = common_years.indicator_id
    LEFT JOIN facts AS common
        ON
            series.country_id = common.country_id
            AND series.indicator_id = common.indicator_id
            AND common_years.common_year = common.observation_year
),

final AS (
    SELECT
        country_values.country_id,
        countries.country_name,
        country_values.indicator_id,
        indicators.indicator_name,
        country_values.latest_year,
        country_values.latest_value,
        CASE
            WHEN country_values.latest_value IS NOT NULL
                THEN rank() OVER (
                    PARTITION BY country_values.indicator_id, country_values.latest_value IS NULL
                    ORDER BY country_values.latest_value DESC
                )
        END AS latest_rank,
        country_values.common_year,
        country_values.common_value,
        CASE
            WHEN country_values.common_value IS NOT NULL
                THEN rank() OVER (
                    PARTITION BY country_values.indicator_id, country_values.common_value IS NULL
                    ORDER BY country_values.common_value DESC
                )
        END AS common_rank
    FROM country_values
    INNER JOIN countries ON country_values.country_id = countries.country_id
    INNER JOIN indicators ON country_values.indicator_id = indicators.indicator_id
)

SELECT * FROM final
