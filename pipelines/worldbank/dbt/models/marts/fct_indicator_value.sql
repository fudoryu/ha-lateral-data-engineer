-- Current state: one row per expected country x indicator x year of the latest run, with its
-- value and status (ADR-0008, ADR-0028). `indicator_value` is null unless the status is present;
-- missing is never zero (NFR-3). `source_response_id` is technical lineage (NFR-1).
WITH

cells AS (
    SELECT * FROM {{ ref('int_indicator_values_filtered_to_latest_run') }}
),

final AS (
    SELECT
        country_iso3,
        indicator_id,
        observation_year,
        indicator_value,
        value_status,
        unit,
        obs_status,
        decimals,
        source_response_id
    FROM cells
)

SELECT * FROM final
