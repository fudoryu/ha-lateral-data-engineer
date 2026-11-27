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
        {{ normalize_text("item ->> 'name'") }} AS indicator_name,
        {{ normalize_text("item ->> 'unit'") }} AS unit,
        item -> 'source' ->> 'id' AS source_id,
        {{ normalize_text("item -> 'source' ->> 'value'") }} AS source_name,
        {{ normalize_text("item ->> 'sourceNote'") }} AS definition,
        {{ normalize_text("item ->> 'sourceOrganization'") }} AS source_organization,
        response_id AS source_response_id,
        url AS source_url,
        fetched_at
    FROM flattened
)

SELECT * FROM final
