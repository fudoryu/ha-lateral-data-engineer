-- One row per income group of the latest run's countries, keyed by the World Bank's income group
-- code: the current classification, which the analysis applies to every year (ADR-0011,
-- ADR-0040).
WITH

income_groups AS (
    SELECT * FROM {{ ref('int_income_groups_derived_from_countries') }}
),

final AS (
    SELECT
        income_group_id,
        income_group_name
    FROM income_groups
)

SELECT * FROM final
