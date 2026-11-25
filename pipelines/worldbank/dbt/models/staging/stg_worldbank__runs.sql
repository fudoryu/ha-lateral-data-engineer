-- One row per committed landing run.
with

landing_runs as (
    select * from {{ source('worldbank', 'landing_runs') }}
),

final as (
    select
        run_id,
        pipeline_version,
        git_sha,
        config_hash,
        started_at,
        committed_at
    from landing_runs
)

select * from final
