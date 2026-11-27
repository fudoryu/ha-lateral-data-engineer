-- FR-ANA-4: the brief's four indicators per income group and year, each aggregated the way its
-- nature requires (ADR-0043): population and GDP summed; GDP per capita as total GDP over total
-- population, never an average of the countries' ratios; life expectancy weighted by population.
-- Only countries with everything a formula needs contribute, and the coverage counts say how many
-- did; a group without data has a null value, never 0. An indicator outside the four gets no row
-- (README). Groups are the current classification, applied to every year (ADR-0011, ADR-0040).
WITH

facts AS (
    SELECT * FROM {{ ref('fct_country_indicator_values') }}
),

countries AS (
    SELECT * FROM {{ ref('dim_countries') }}
),

income_groups AS (
    SELECT * FROM {{ ref('dim_income_groups') }}
),

indicators AS (
    SELECT * FROM {{ ref('dim_indicators') }}
),

-- One row per country and year with the inputs side by side; a value is null unless present.
country_years AS (
    SELECT
        countries.income_group_id,
        facts.country_id,
        facts.observation_year,
        max(CASE WHEN facts.indicator_id = 'SP.POP.TOTL' THEN facts.indicator_value END)
            AS population,
        max(CASE WHEN facts.indicator_id = 'NY.GDP.MKTP.CD' THEN facts.indicator_value END)
            AS gdp,
        max(CASE WHEN facts.indicator_id = 'SP.DYN.LE00.IN' THEN facts.indicator_value END)
            AS life_expectancy
    FROM facts
    INNER JOIN countries ON facts.country_id = countries.country_id
    GROUP BY countries.income_group_id, facts.country_id, facts.observation_year
),

-- Each formula sums only the countries that have all of its inputs. Sums are DECIMAL, so they're
-- exact and the same on every run: a parallel sum of doubles depends on the order of its terms.
groups AS (
    SELECT
        income_group_id,
        observation_year,
        count(*) AS n_countries,
        sum(cast(population AS DECIMAL(38, 4))) AS population_total,
        count(population) AS n_with_population,
        sum(cast(gdp AS DECIMAL(38, 4))) AS gdp_total,
        count(gdp) AS n_with_gdp,
        sum(CASE WHEN population IS NOT NULL THEN cast(gdp AS DECIMAL(38, 4)) END)
            AS gdp_of_countries_with_both,
        sum(CASE WHEN gdp IS NOT NULL THEN cast(population AS DECIMAL(38, 4)) END)
            AS population_of_countries_with_both,
        count(CASE WHEN gdp IS NOT NULL AND population IS NOT NULL THEN 1 END)
            AS n_with_gdp_and_population,
        sum(cast(life_expectancy * population AS DECIMAL(38, 4))) AS life_expectancy_person_years,
        sum(CASE WHEN life_expectancy IS NOT NULL THEN cast(population AS DECIMAL(38, 4)) END)
            AS population_with_life_expectancy,
        count(CASE WHEN life_expectancy IS NOT NULL AND population IS NOT NULL THEN 1 END)
            AS n_with_life_expectancy_and_population
    FROM country_years
    GROUP BY income_group_id, observation_year
),

aggregates AS (
    SELECT
        income_group_id,
        observation_year,
        'SP.POP.TOTL' AS indicator_id,
        'sum' AS aggregation,
        population_total AS group_value,
        n_with_population AS n_countries_with_data,
        n_countries
    FROM groups
    UNION ALL
    SELECT
        income_group_id,
        observation_year,
        'NY.GDP.MKTP.CD' AS indicator_id,
        'sum' AS aggregation,
        gdp_total AS group_value,
        n_with_gdp AS n_countries_with_data,
        n_countries
    FROM groups
    UNION ALL
    SELECT
        income_group_id,
        observation_year,
        'NY.GDP.PCAP.CD' AS indicator_id,
        'total GDP / total population' AS aggregation,
        gdp_of_countries_with_both / nullif(population_of_countries_with_both, 0) AS group_value,
        n_with_gdp_and_population AS n_countries_with_data,
        n_countries
    FROM groups
    UNION ALL
    SELECT
        income_group_id,
        observation_year,
        'SP.DYN.LE00.IN' AS indicator_id,
        'population-weighted mean' AS aggregation,
        life_expectancy_person_years / nullif(population_with_life_expectancy, 0) AS group_value,
        n_with_life_expectancy_and_population AS n_countries_with_data,
        n_countries
    FROM groups
),

final AS (
    SELECT
        aggregates.income_group_id,
        income_groups.income_group_name,
        aggregates.indicator_id,
        indicators.indicator_name,
        aggregates.observation_year,
        aggregates.aggregation,
        cast(aggregates.group_value AS DOUBLE) AS group_value,
        aggregates.n_countries,
        aggregates.n_countries_with_data
    FROM aggregates
    INNER JOIN income_groups ON aggregates.income_group_id = income_groups.income_group_id
    INNER JOIN indicators ON aggregates.indicator_id = indicators.indicator_id
)

SELECT * FROM final
