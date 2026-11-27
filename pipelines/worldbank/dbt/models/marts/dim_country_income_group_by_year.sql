-- One row per country and reporting year with the income group that applies (ADR-0011): today
-- the current classification for every year, labelled by `classification_basis`.
WITH

income_groups AS (
    SELECT * FROM {{ ref('int_income_groups_spread_over_years') }}
),

final AS (
    SELECT
        country_iso3,
        observation_year,
        income_level_id,
        income_level_name,
        classification_basis,
        classified_as_of,
        source_response_id
    FROM income_groups
)

SELECT * FROM final
