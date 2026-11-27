-- One row per configured country, from the latest run, with its income group: the current
-- classification, which the analysis applies to every year (ADR-0011, ADR-0030).
WITH

countries AS (
    SELECT * FROM {{ ref('int_countries_joined_to_income_group_order') }}
),

final AS (
    SELECT
        country_id,
        country_iso2,
        country_name,
        region_id,
        region_name,
        income_group_id,
        income_group_name,
        income_group_sort_order,
        source_response_id
    FROM countries
)

SELECT * FROM final
