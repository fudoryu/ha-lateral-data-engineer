-- Load committed landing runs into the raw layer, set-based (ADR-0020, ADR-0022): the local
-- equivalent of COPY INTO from a stage with an explicit file list. Runs after schema.sql, on two
-- temporary tables load.py fills from the files it has verified:
--   landed_manifest (manifest json)                one row per run's manifest.json
--   landed_page     (response_id varchar, content) one row per landed page, by response ID
-- Nothing is reshaped: payloads are copied as received. The session time zone is UTC, so
-- timestamps with any offset are stored as UTC.

insert into raw.landing_runs by name
select
    manifest ->> 'run_id' as run_id,
    (manifest ->> 'started_at')::timestamptz::timestamp as started_at,
    (manifest ->> 'committed_at')::timestamptz::timestamp as committed_at,
    manifest ->> 'pipeline_version' as pipeline_version,
    manifest ->> 'git_sha' as git_sha,
    manifest ->> 'config_hash' as config_hash,
    manifest -> 'config' as config,
    manifest -> 'warnings' as warnings
from landed_manifest;

insert into raw.api_requests by name
select
    manifest ->> 'run_id' as run_id,
    request ->> 'endpoint' as endpoint,
    request ->> 'key' as key,
    (request ->> 'pages')::integer as pages,
    (request ->> 'total')::integer as total,
    (request ->> 'lastupdated')::date as lastupdated
from landed_manifest, unnest(manifest -> '$.requests[*]') as requests (request);

insert into raw.api_responses by name
select
    file ->> 'response_id' as response_id,
    manifest ->> 'run_id' as run_id,
    file ->> 'endpoint' as endpoint,
    file ->> 'key' as key,
    (file ->> 'page')::integer as page,
    file ->> 'url' as url,
    (file ->> 'fetched_at')::timestamptz::timestamp as fetched_at,
    file ->> 'sha256' as sha256,
    landed_page.content as payload
from landed_manifest, unnest(manifest -> '$.files[*]') as files (file)
inner join landed_page on landed_page.response_id = file ->> 'response_id';
