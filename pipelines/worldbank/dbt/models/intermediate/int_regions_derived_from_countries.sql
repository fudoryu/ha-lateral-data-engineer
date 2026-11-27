-- The regions of the latest run's countries, one row each (ADR-0039). The API describes a region
-- only on its countries, so this collects the distinct ones; a region id with two names fails the
-- uniqueness test instead of splitting the region.
WITH

countries AS (
    SELECT * FROM {{ ref('int_countries_filtered_to_latest_run') }}
),

final AS (
    SELECT DISTINCT
        region_id,
        region_name
    FROM countries
)

SELECT * FROM final
