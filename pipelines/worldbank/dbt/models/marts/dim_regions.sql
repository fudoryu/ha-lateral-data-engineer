-- One row per region of the latest run's countries, keyed by the World Bank's region code
-- (ADR-0039).
WITH

regions AS (
    SELECT * FROM {{ ref('int_regions_derived_from_countries') }}
),

final AS (
    SELECT
        region_id,
        region_name
    FROM regions
)

SELECT * FROM final
