-- One row per configured country, from the latest run. `income_level_id` is the current
-- classification; the yearly view is dim_country_income_group_by_year (ADR-0011).
WITH

countries AS (
    SELECT * FROM {{ ref('int_countries_filtered_to_latest_run') }}
),

final AS (
    SELECT
        country_iso3,
        country_iso2,
        country_name,
        region_id,
        region_name,
        income_level_id,
        income_level_name,
        source_response_id
    FROM countries
)

SELECT * FROM final
