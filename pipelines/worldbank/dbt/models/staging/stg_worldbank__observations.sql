-- One row per observation the API returned: run x country x indicator x year.
-- Values are never coerced: a JSON null stays null (NFR-3).
with

responses as (
    select * from {{ source('worldbank', 'api_responses') }}
    where endpoint = 'observations'
),

flattened as (
    select
        responses.response_id,
        responses.run_id,
        responses.url,
        responses.fetched_at,
        responses.payload -> '$[0]' ->> 'lastupdated' as lastupdated,
        unnest(responses.payload -> '$[1][*]') as row
    from responses
),

final as (
    select
        run_id,
        row ->> 'countryiso3code' as country_iso3,
        row -> 'indicator' ->> 'id' as indicator_id,
        (row ->> 'date')::integer as observation_year,
        (row ->> 'value')::double as indicator_value,
        nullif(row ->> 'unit', '') as unit,
        nullif(row ->> 'obs_status', '') as obs_status,
        (row ->> 'decimal')::integer as decimals,
        row -> 'country' ->> 'id' as country_iso2,
        response_id as source_response_id,
        url as source_url,
        fetched_at,
        lastupdated::date as source_lastupdated
    from flattened
)

select * from final
