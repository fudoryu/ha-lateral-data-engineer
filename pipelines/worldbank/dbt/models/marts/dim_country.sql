-- One row per configured country, from the latest run. Its current income group is named as such;
-- the group that applied in a given year is on fct_indicator_value (ADR-0011, ADR-0029).
WITH

countries AS (
    SELECT * FROM {{ ref('int_countries_filtered_to_latest_run') }}
),

final AS (
    SELECT
        country_id,
        country_iso2,
        country_name,
        region_id,
        region_name,
        income_group_id AS current_income_group_id,
        income_group_name AS current_income_group_name,
        source_response_id
    FROM countries
)

SELECT * FROM final
