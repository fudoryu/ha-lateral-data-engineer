-- The expected set of each run: its configured countries x indicators x years (ADR-0008),
-- taken from the configuration recorded with the run (ADR-0016).
with

landing_runs as (
    select * from {{ source('worldbank', 'landing_runs') }}
),

countries as (
    select
        run_id,
        unnest(from_json(config -> '$.scope.countries', '["varchar"]')) as country_iso3
    from landing_runs
),

indicators as (
    select
        run_id,
        unnest(from_json(config -> '$.scope.indicators', '["varchar"]')) as indicator_id
    from landing_runs
),

years as (
    select
        run_id,
        unnest(
            generate_series(
                (config -> '$.scope.years' ->> 'start')::integer,
                (config -> '$.scope.years' ->> 'end')::integer
            )
        )::integer as observation_year
    from landing_runs
),

final as (
    select
        countries.run_id,
        countries.country_iso3,
        indicators.indicator_id,
        years.observation_year
    from countries
    inner join indicators on countries.run_id = indicators.run_id
    inner join years on countries.run_id = years.run_id
)

select * from final
