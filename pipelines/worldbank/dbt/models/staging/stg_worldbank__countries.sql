-- One row per run x country, as returned by the country endpoint. Names are trimmed: the API
-- returns some region names with trailing spaces (source-system §2).
with

responses as (
    select * from {{ source('worldbank', 'api_responses') }}
    where endpoint = 'countries'
),

flattened as (
    select
        responses.response_id,
        responses.run_id,
        responses.url,
        responses.fetched_at,
        unnest(responses.payload -> '$[1][*]') as row
    from responses
),

final as (
    select
        response_id,
        run_id,
        row ->> 'id' as country_iso3,
        row ->> 'iso2Code' as country_iso2,
        trim(row ->> 'name') as country_name,
        row -> 'region' ->> 'id' as region_id,
        trim(row -> 'region' ->> 'value') as region_name,
        row -> 'incomeLevel' ->> 'id' as income_level_id,
        trim(row -> 'incomeLevel' ->> 'value') as income_level_name,
        url as source_url,
        fetched_at
    from flattened
)

select * from final
