-- One row per run x country, as returned by the country endpoint. Names are trimmed: the API
-- returns some region names with trailing spaces (source-system §2).
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
        item ->> 'id' AS country_iso3,
        item ->> 'iso2Code' AS country_iso2,
        trim(item ->> 'name') AS country_name,
        item -> 'region' ->> 'id' AS region_id,
        trim(item -> 'region' ->> 'value') AS region_name,
        item -> 'incomeLevel' ->> 'id' AS income_level_id,
        trim(item -> 'incomeLevel' ->> 'value') AS income_level_name,
        response_id AS source_response_id,
        url AS source_url,
        fetched_at
    FROM flattened
)

SELECT * FROM final
