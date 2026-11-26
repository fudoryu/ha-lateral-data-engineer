-- One row per run x indicator, as returned by the indicator endpoint.
with

responses as (
    select * from {{ source('worldbank', 'api_responses') }}
    where endpoint = 'indicators'
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
        run_id,
        row ->> 'id' as indicator_id,
        trim(row ->> 'name') as indicator_name,
        nullif(row ->> 'unit', '') as unit,
        row -> 'source' ->> 'id' as source_id,
        trim(row -> 'source' ->> 'value') as source_name,
        nullif(trim(row ->> 'sourceNote'), '') as definition,
        nullif(trim(row ->> 'sourceOrganization'), '') as source_organization,
        response_id as source_response_id,
        url as source_url,
        fetched_at
    from flattened
)

select * from final
