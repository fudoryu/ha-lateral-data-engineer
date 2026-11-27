-- The expected set of each run: its configured countries x indicators x years (ADR-0008),
-- taken from the configuration recorded with the run (ADR-0016).
WITH

landing_runs AS (
    SELECT * FROM {{ source('worldbank', 'landing_runs') }}
),

countries AS (
    SELECT
        run_id,
        unnest(from_json(config -> '$.scope.countries', '["varchar"]')) AS country_iso3
    FROM landing_runs
),

indicators AS (
    SELECT
        run_id,
        unnest(from_json(config -> '$.scope.indicators', '["varchar"]')) AS indicator_id
    FROM landing_runs
),

years AS (
    SELECT
        run_id,
        unnest(
            generate_series(
                (config -> '$.scope.years' ->> 'start')::INTEGER,
                (config -> '$.scope.years' ->> 'end')::INTEGER
            )
        )::INTEGER AS observation_year
    FROM landing_runs
),

final AS (
    SELECT
        countries.run_id,
        countries.country_iso3,
        indicators.indicator_id,
        years.observation_year
    FROM countries
    INNER JOIN indicators ON countries.run_id = indicators.run_id
    INNER JOIN years ON countries.run_id = years.run_id
)

SELECT * FROM final
