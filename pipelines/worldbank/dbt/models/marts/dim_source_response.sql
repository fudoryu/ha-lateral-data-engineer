-- One row per landed API response page: where each value came from (NFR-1, ADR-0017).
WITH

responses AS (
    SELECT * FROM {{ ref('int_responses_joined_to_runs') }}
),

final AS (
    SELECT
        source_response_id,
        run_id,
        endpoint,
        request_key,
        page,
        source_url,
        fetched_at,
        source_lastupdated,
        sha256,
        is_latest_run
    FROM responses
)

SELECT * FROM final
