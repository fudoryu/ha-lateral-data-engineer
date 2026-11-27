-- One row per run x country, as returned by the country endpoint. Text is normalized
-- (normalize_text): the API returns some region names with trailing spaces (source-system §2).
WITH

responses AS (
    SELECT * FROM {{ source('worldbank', 'api_responses') }}
    WHERE endpoint = 'countries'
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
        item ->> 'id' AS country_id,
        item ->> 'iso2Code' AS country_iso2,
        {{ normalize_text("item ->> 'name'") }} AS country_name,
        item -> 'region' ->> 'id' AS region_id,
        {{ normalize_text("item -> 'region' ->> 'value'") }} AS region_name,
        item -> 'incomeLevel' ->> 'id' AS income_group_id,
        {{ normalize_text("item -> 'incomeLevel' ->> 'value'") }} AS income_group_name,
        response_id AS source_response_id,
        url AS source_url,
        fetched_at
    FROM flattened
)

SELECT * FROM final
