-- FR-ANA-4: each indicator per income group and year, as the average of the group's countries that
-- have a value (ADR-0038). One rule for every indicator, so a new indicator needs no setup; it
-- describes the typical country in the group, not the group's total. `avg` and `count` skip the
-- nulls, which are exactly the values that aren't present, so a group without data has a null
-- average, never 0, and the counts show how many countries contributed. Groups are the current
-- classification, applied to every year (ADR-0011, ADR-0030; see the README's assumptions).
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
        countries.income_group_id,
        countries.income_group_name,
        countries.income_group_sort_order,
        facts.indicator_id,
        indicators.indicator_name,
        facts.observation_year,
        avg(facts.indicator_value) AS average_value,
        count(*) AS n_countries,
        count(facts.indicator_value) AS n_countries_with_data
    FROM facts
    INNER JOIN countries ON facts.country_id = countries.country_id
    INNER JOIN indicators ON facts.indicator_id = indicators.indicator_id
    GROUP BY
        countries.income_group_id,
        countries.income_group_name,
        countries.income_group_sort_order,
        facts.indicator_id,
        indicators.indicator_name,
        facts.observation_year
)

SELECT * FROM final
