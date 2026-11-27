-- One row per committed landing run.
WITH

landing_runs AS (
    SELECT * FROM {{ source('worldbank', 'landing_runs') }}
),

final AS (
    SELECT
        run_id,
        pipeline_version,
        git_sha,
        config_hash,
        started_at,
        committed_at
    FROM landing_runs
)

SELECT * FROM final
