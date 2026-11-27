-- The latest run's countries: current country metadata, including each country's current income
-- group (ADR-0006, ADR-0011).
WITH

countries AS (
    SELECT * FROM {{ ref('stg_worldbank__countries') }}
),

latest_run AS (
    SELECT run_id FROM {{ ref('int_runs_ranked') }}
    WHERE is_latest
),

final AS (
    SELECT
        countries.country_iso3,
        countries.country_iso2,
        countries.country_name,
        countries.region_id,
        countries.region_name,
        countries.income_level_id,
        countries.income_level_name,
        countries.run_id,
        countries.source_response_id
    FROM countries
    INNER JOIN latest_run ON countries.run_id = latest_run.run_id
)

SELECT * FROM final
