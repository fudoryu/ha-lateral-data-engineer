-- Each country's income group for every reporting year of the latest run (ADR-0011). The API
-- gives only the current classification, so it's applied to every year and labelled as such;
-- the grain is country x year so a historical source could replace it without changing reports.
WITH

countries AS (
    SELECT * FROM {{ ref('int_countries_filtered_to_latest_run') }}
),

years AS (
    SELECT DISTINCT observation_year FROM {{ ref('int_indicator_values_filtered_to_latest_run') }}
),

latest_run AS (
    SELECT committed_at FROM {{ ref('int_runs_ranked') }}
    WHERE is_latest
),

final AS (
    SELECT
        countries.country_id,
        years.observation_year,
        countries.income_group_id,
        countries.income_group_name,
        'current_applied_to_all_years' AS classification_basis,
        cast(latest_run.committed_at AS DATE) AS classified_as_of,
        countries.run_id,
        countries.source_response_id
    FROM countries
    CROSS JOIN years
    CROSS JOIN latest_run
)

SELECT * FROM final
