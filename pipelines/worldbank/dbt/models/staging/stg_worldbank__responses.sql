-- One row per landed response page, for lineage (NFR-1): where each page came from, without its
-- payload. The source's lastupdated comes from the page's own metadata; the country and
-- indicator endpoints don't send one, so it's null for their pages.
WITH

responses AS (
    SELECT * FROM {{ source('worldbank', 'api_responses') }}
),

final AS (
    SELECT
        response_id AS source_response_id,
        run_id,
        endpoint,
        request_key,
        page,
        url AS source_url,
        fetched_at,
        sha256,
        (payload -> '$[0]' ->> 'lastupdated')::DATE AS source_lastupdated
    FROM responses
)

SELECT * FROM final
