-- One row per income group used by the latest run's countries, with its low-to-high sort order
-- and how today's classification was made (ADR-0011, ADR-0029).
WITH

countries AS (
    SELECT * FROM {{ ref('int_countries_filtered_to_latest_run') }}
),

income_group_order AS (
    SELECT * FROM {{ ref('income_group_order') }}
),

latest_run AS (
    SELECT committed_at FROM {{ ref('int_runs_ranked') }}
    WHERE is_latest
),

income_groups AS (
    SELECT DISTINCT
        income_group_id,
        income_group_name
    FROM countries
),

final AS (
    SELECT
        income_groups.income_group_id,
        income_groups.income_group_name,
        income_group_order.sort_order,
        'current_applied_to_all_years' AS classification_basis,
        cast(latest_run.committed_at AS DATE) AS classified_as_of
    FROM income_groups
    LEFT JOIN income_group_order
        ON income_groups.income_group_id = income_group_order.income_group_id
    CROSS JOIN latest_run
)

SELECT * FROM final
