-- Current state: one row per expected country x indicator x year of the latest run, with its
-- value and status (ADR-0008, ADR-0028). `indicator_value` is null unless the status is present;
-- missing is never zero (NFR-3). `income_group_id` is the group that applied that year
-- (ADR-0029); `source_response_id` is technical lineage (NFR-1).
WITH

cells AS (
    SELECT * FROM {{ ref('int_indicator_values_joined_to_income_groups') }}
),

final AS (
    SELECT
        country_id,
        indicator_id,
        observation_year,
        income_group_id,
        indicator_value,
        value_status,
        unit,
        obs_status,
        decimals,
        source_response_id
    FROM cells
)

SELECT * FROM final
