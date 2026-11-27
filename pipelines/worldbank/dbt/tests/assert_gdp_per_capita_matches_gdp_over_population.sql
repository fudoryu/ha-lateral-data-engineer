-- FR-DQ-2 (ADR-0010): related indicators agree. GDP per capita must match GDP / population within
-- `gdp_consistency_tolerance` (0.1%), for each country and year where all three are present; if
-- any of them is out of scope, there's nothing to compare. A failure blocks publishing
-- (ADR-0007). Fails with each disagreeing value and its difference.
WITH

facts AS (
    SELECT * FROM {{ ref('fct_country_indicator_values') }}
    WHERE value_status = 'present'
),

gdp_per_capita AS (
    SELECT * FROM facts
    WHERE indicator_id = 'NY.GDP.PCAP.CD'
),

gdp AS (
    SELECT * FROM facts
    WHERE indicator_id = 'NY.GDP.MKTP.CD'
),

population AS (
    SELECT * FROM facts
    WHERE indicator_id = 'SP.POP.TOTL'
),

comparisons AS (
    SELECT
        gdp_per_capita.country_id,
        gdp_per_capita.observation_year,
        gdp_per_capita.indicator_value AS published_value,
        gdp.indicator_value / nullif(population.indicator_value, 0) AS derived_value
    FROM gdp_per_capita
    INNER JOIN gdp
        ON
            gdp_per_capita.country_id = gdp.country_id
            AND gdp_per_capita.observation_year = gdp.observation_year
    INNER JOIN population
        ON
            gdp_per_capita.country_id = population.country_id
            AND gdp_per_capita.observation_year = population.observation_year
)

SELECT
    country_id,
    observation_year,
    published_value,
    derived_value,
    abs(derived_value - published_value) / abs(published_value) AS relative_difference
FROM comparisons
WHERE
    derived_value IS NULL
    OR abs(derived_value - published_value) / abs(published_value)
    > {{ var('gdp_consistency_tolerance') }}
