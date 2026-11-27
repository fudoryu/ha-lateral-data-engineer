-- Every landed page with a flag for the latest run, so lineage can be narrowed to the pages
-- behind current state.
WITH

responses AS (
    SELECT * FROM {{ ref('stg_worldbank__responses') }}
),

runs AS (
    SELECT * FROM {{ ref('int_runs_ranked') }}
),

final AS (
    SELECT
        responses.source_response_id,
        responses.run_id,
        responses.endpoint,
        responses.request_key,
        responses.page,
        responses.source_url,
        responses.fetched_at,
        responses.sha256,
        responses.source_lastupdated,
        runs.is_latest AS is_latest_run
    FROM responses
    INNER JOIN runs ON responses.run_id = runs.run_id
)

SELECT * FROM final
