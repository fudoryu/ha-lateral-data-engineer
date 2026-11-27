-- Value history: one row per version of each cell across runs, so the source's silent revisions
-- stay visible (ADR-0006, ADR-0017). `is_current` marks the version in fct_indicator_value.
WITH

versions AS (
    SELECT * FROM {{ ref('int_indicator_values_versioned') }}
),

final AS (
    SELECT
        country_iso3,
        indicator_id,
        observation_year,
        valid_from_run_id,
        indicator_value,
        value_status,
        valid_to_run_id,
        is_current,
        source_response_id
    FROM versions
)

SELECT * FROM final
