-- The latest run's countries with their income group's place from low to high income (seed
-- income_group_order), so reports list groups in their natural order (ADR-0030).
WITH

countries AS (
    SELECT * FROM {{ ref('int_countries_filtered_to_latest_run') }}
),

income_group_order AS (
    SELECT * FROM {{ ref('income_group_order') }}
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
        income_group_order.sort_order AS income_group_sort_order,
        countries.run_id,
        countries.source_response_id
    FROM countries
    LEFT JOIN income_group_order
        ON countries.income_group_id = income_group_order.income_group_id
)

SELECT * FROM final
