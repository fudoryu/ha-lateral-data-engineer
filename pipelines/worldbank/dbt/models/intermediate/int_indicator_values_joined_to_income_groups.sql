-- The latest run's cells with the income group that applied to each country in each year
-- (ADR-0011, ADR-0029), so the fact carries it and reports join on it directly.
WITH

cells AS (
    SELECT * FROM {{ ref('int_indicator_values_filtered_to_latest_run') }}
),

income_groups AS (
    SELECT * FROM {{ ref('int_income_groups_spread_over_years') }}
),

final AS (
    SELECT
        cells.country_id,
        cells.indicator_id,
        cells.observation_year,
        income_groups.income_group_id,
        cells.indicator_value,
        cells.value_status,
        cells.unit,
        cells.obs_status,
        cells.decimals,
        cells.source_response_id
    FROM cells
    LEFT JOIN income_groups
        ON
            cells.country_id = income_groups.country_id
            AND cells.observation_year = income_groups.observation_year
)

SELECT * FROM final
