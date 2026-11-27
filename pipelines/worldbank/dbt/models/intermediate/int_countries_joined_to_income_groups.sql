-- The latest run's countries with their income group's place from low to high income (seed
-- income_groups), so reports list groups in their natural order (ADR-0030).
WITH

countries AS (
    SELECT * FROM {{ ref('int_countries_filtered_to_latest_run') }}
),

income_groups AS (
    SELECT * FROM {{ ref('income_groups') }}
),

final AS (
    SELECT
        countries.country_id,
        countries.country_iso2,
        countries.country_name,
        countries.region_id,
        countries.region_name,
        countries.income_group_id,
        countries.income_group_name,
        income_groups.sort_order AS income_group_sort_order,
        countries.run_id,
        countries.source_response_id
    FROM countries
    LEFT JOIN income_groups
        ON countries.income_group_id = income_groups.income_group_id
)

SELECT * FROM final
