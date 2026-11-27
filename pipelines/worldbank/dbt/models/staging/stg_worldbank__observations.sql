-- One row per observation the API returned: run x country x indicator x year.
-- Values are never coerced: a JSON null stays null (NFR-3).
WITH

responses AS (
    SELECT * FROM {{ source('worldbank', 'api_responses') }}
    WHERE endpoint = 'observations'
),

flattened AS (
    SELECT
        responses.response_id,
        responses.run_id,
        responses.url,
        responses.fetched_at,
        responses.payload -> '$[0]' ->> 'lastupdated' AS lastupdated,
        unnest(responses.payload -> '$[1][*]') AS item
    FROM responses
),

final AS (
    SELECT
        run_id,
        item ->> 'countryiso3code' AS country_iso3,
        item -> 'indicator' ->> 'id' AS indicator_id,
        (item ->> 'date')::INTEGER AS observation_year,
        (item ->> 'value')::DOUBLE AS indicator_value,
        nullif(item ->> 'unit', '') AS unit,
        nullif(item ->> 'obs_status', '') AS obs_status,
        (item ->> 'decimal')::INTEGER AS decimals,
        item -> 'country' ->> 'id' AS country_iso2,
        response_id AS source_response_id,
        url AS source_url,
        fetched_at,
        lastupdated::DATE AS source_lastupdated
    FROM flattened
)

SELECT * FROM final
