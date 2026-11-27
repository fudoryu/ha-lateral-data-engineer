-- FR-DQ-2 (ADR-0010): related indicators agree. Every indicator defined as a ratio of two others
-- (dim_indicators: GDP per capita = GDP / population) must match that ratio within the
-- `ratio_consistency_tolerance` (0.1%), for each country and year where all three are present.
-- A failure blocks publishing (ADR-0007). Fails with each disagreeing value and its difference.
WITH

facts AS (
    SELECT * FROM {{ ref('fct_country_indicator_values') }}
    WHERE value_status = 'present'
),

ratios AS (
    SELECT * FROM {{ ref('dim_indicators') }}
    WHERE aggregation_method = 'ratio'
),

comparisons AS (
    SELECT
        published.country_id,
        published.indicator_id,
        published.observation_year,
        published.indicator_value AS published_value,
        numerators.indicator_value / nullif(denominators.indicator_value, 0) AS derived_value
    FROM facts AS published
    INNER JOIN ratios ON published.indicator_id = ratios.indicator_id
    INNER JOIN facts AS numerators
        ON
            published.country_id = numerators.country_id
            AND published.observation_year = numerators.observation_year
            AND ratios.numerator_indicator_id = numerators.indicator_id
    INNER JOIN facts AS denominators
        ON
            published.country_id = denominators.country_id
            AND published.observation_year = denominators.observation_year
            AND ratios.denominator_indicator_id = denominators.indicator_id
)

SELECT
    country_id,
    indicator_id,
    observation_year,
    published_value,
    derived_value,
    abs(derived_value - published_value) / abs(published_value) AS relative_difference
FROM comparisons
WHERE
    derived_value IS NULL
    OR abs(derived_value - published_value) / abs(published_value)
    > {{ var('ratio_consistency_tolerance') }}
