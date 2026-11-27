-- The latest run's indicators: current indicator metadata (ADR-0006).
WITH

indicators AS (
    SELECT * FROM {{ ref('stg_worldbank__indicators') }}
),

latest_run AS (
    SELECT run_id FROM {{ ref('int_runs_ranked') }}
    WHERE is_latest
),

final AS (
    SELECT
        indicators.indicator_id,
        indicators.indicator_name,
        indicators.definition,
        indicators.source_organization,
        indicators.run_id,
        indicators.source_response_id
    FROM indicators
    INNER JOIN latest_run ON indicators.run_id = latest_run.run_id
)

SELECT * FROM final
