-- FR-ANA-4: each indicator per income group and year, aggregated the way the indicator requires
-- (dim_indicators.aggregation_method, ADR-0009): sum; ratio of the sums of two other indicators
-- (GDP per capita = sum of GDP / sum of population, never an average of ratios); or mean
-- weighted by another indicator (life expectancy by population). Only countries with everything
-- their method needs contribute, and the coverage counts say how many did. Groups use the
-- current classification for every year (ADR-0011, ADR-0030; see the README's assumptions).
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

income_groups AS (
    SELECT DISTINCT
        income_group_id,
        income_group_name,
        income_group_sort_order
    FROM countries
),

cells AS (
    SELECT
        countries.income_group_id,
        facts.indicator_id,
        facts.observation_year,
        indicators.aggregation_method,
        facts.indicator_value,
        numerators.indicator_value AS numerator_value,
        denominators.indicator_value AS denominator_value,
        weights.indicator_value AS weight_value,
        CASE indicators.aggregation_method
            WHEN 'sum' THEN facts.value_status = 'present'
            WHEN 'ratio'
                THEN numerators.value_status = 'present' AND denominators.value_status = 'present'
            WHEN 'weighted_mean'
                THEN facts.value_status = 'present' AND weights.value_status = 'present'
        END AS has_data
    FROM facts
    INNER JOIN countries ON facts.country_id = countries.country_id
    INNER JOIN indicators ON facts.indicator_id = indicators.indicator_id
    LEFT JOIN facts AS numerators
        ON
            facts.country_id = numerators.country_id
            AND facts.observation_year = numerators.observation_year
            AND indicators.numerator_indicator_id = numerators.indicator_id
    LEFT JOIN facts AS denominators
        ON
            facts.country_id = denominators.country_id
            AND facts.observation_year = denominators.observation_year
            AND indicators.denominator_indicator_id = denominators.indicator_id
    LEFT JOIN facts AS weights
        ON
            facts.country_id = weights.country_id
            AND facts.observation_year = weights.observation_year
            AND indicators.weight_indicator_id = weights.indicator_id
),

groups AS (
    SELECT
        income_group_id,
        indicator_id,
        observation_year,
        aggregation_method,
        count(*) AS n_countries,
        sum(CASE WHEN has_data THEN 1 ELSE 0 END) AS n_countries_with_data,
        sum(CASE WHEN has_data THEN indicator_value END) AS value_sum,
        sum(CASE WHEN has_data THEN numerator_value END) AS numerator_sum,
        sum(CASE WHEN has_data THEN denominator_value END) AS denominator_sum,
        sum(CASE WHEN has_data THEN indicator_value * weight_value END) AS weighted_value_sum,
        sum(CASE WHEN has_data THEN weight_value END) AS weight_sum
    FROM cells
    GROUP BY income_group_id, indicator_id, observation_year, aggregation_method
),

final AS (
    SELECT
        groups.income_group_id,
        income_groups.income_group_name,
        income_groups.income_group_sort_order,
        groups.indicator_id,
        indicators.indicator_name,
        groups.observation_year,
        groups.aggregation_method,
        CASE groups.aggregation_method
            WHEN 'sum' THEN groups.value_sum
            WHEN 'ratio' THEN groups.numerator_sum / nullif(groups.denominator_sum, 0)
            WHEN 'weighted_mean' THEN groups.weighted_value_sum / nullif(groups.weight_sum, 0)
        END AS group_value,
        groups.n_countries,
        groups.n_countries_with_data
    FROM groups
    INNER JOIN income_groups ON groups.income_group_id = income_groups.income_group_id
    INNER JOIN indicators ON groups.indicator_id = indicators.indicator_id
)

SELECT * FROM final
