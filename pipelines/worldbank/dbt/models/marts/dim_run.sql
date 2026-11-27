-- One row per committed extract run; `is_latest` marks the run behind current state (ADR-0006).
WITH

runs AS (
    SELECT * FROM {{ ref('int_runs_ranked') }}
),

final AS (
    SELECT
        run_id,
        started_at,
        committed_at,
        pipeline_version,
        git_sha,
        config_hash,
        is_latest
    FROM runs
)

SELECT * FROM final
