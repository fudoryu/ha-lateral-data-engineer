-- One row per run x indicator, as returned by the indicator endpoint.
WITH

responses AS (
    SELECT * FROM {{ source('worldbank', 'api_responses') }}
    WHERE endpoint = 'indicators'
),

flattened AS (
    SELECT
        responses.response_id,
        responses.run_id,
        responses.url,
        responses.fetched_at,
        unnest(responses.payload -> '$[1][*]') AS item
    FROM responses
),

final AS (
    SELECT
        run_id,
        item ->> 'id' AS indicator_id,
        trim(item ->> 'name') AS indicator_name,
        nullif(item ->> 'unit', '') AS unit,
        item -> 'source' ->> 'id' AS source_id,
        trim(item -> 'source' ->> 'value') AS source_name,
        nullif(trim(item ->> 'sourceNote'), '') AS definition,
        nullif(trim(item ->> 'sourceOrganization'), '') AS source_organization,
        response_id AS source_response_id,
        url AS source_url,
        fetched_at
    FROM flattened
)

SELECT * FROM final
