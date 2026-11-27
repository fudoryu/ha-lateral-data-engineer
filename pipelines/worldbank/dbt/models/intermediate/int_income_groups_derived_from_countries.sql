-- The income groups of the latest run's countries, one row each (ADR-0040). The API describes an
-- income group only on its countries, so this collects the distinct ones; a group id with two
-- names fails the uniqueness test instead of splitting the group.
WITH

countries AS (
    SELECT * FROM {{ ref('int_countries_filtered_to_latest_run') }}
),

final AS (
    SELECT DISTINCT
        income_group_id,
        income_group_name
    FROM countries
)

SELECT * FROM final
