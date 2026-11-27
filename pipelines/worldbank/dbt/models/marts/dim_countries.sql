-- One row per configured country, from the latest run, with its region (→ dim_regions) and its
-- income group (→ dim_income_groups) (ADR-0039, ADR-0040).
WITH

countries AS (
    SELECT * FROM {{ ref('int_countries_filtered_to_latest_run') }}
),

final AS (
    SELECT
        country_id,
        country_name,
        region_id,
        income_group_id,
        source_response_id
    FROM countries
)

SELECT * FROM final
