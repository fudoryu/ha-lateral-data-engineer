-- Every committed run, ranked from the most recent commit: the latest run is current state
-- (ADR-0006). The only place that decides which run is the latest.
WITH

runs AS (
    SELECT * FROM {{ ref('stg_worldbank__runs') }}
),

ranked AS (
    SELECT
        runs.*,
        row_number() OVER (ORDER BY runs.committed_at DESC, runs.run_id DESC) AS recency_rank
    FROM runs
),

final AS (
    SELECT
        run_id,
        started_at,
        committed_at,
        pipeline_version,
        git_sha,
        config_hash,
        recency_rank,
        recency_rank = 1 AS is_latest
    FROM ranked
)

SELECT * FROM final
