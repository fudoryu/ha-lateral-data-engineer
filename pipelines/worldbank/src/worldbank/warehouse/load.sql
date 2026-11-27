-- Load committed landing runs into the raw layer, set-based (ADR-0020, ADR-0022): the local
-- equivalent of COPY INTO from a stage with an explicit file list. Runs after schema.sql, on two
-- temporary tables load.py fills from the files it has verified:
--   landed_manifest (manifest json)                one row per run's manifest.json
--   landed_page     (response_id varchar, content) one row per landed page, by response ID
-- Nothing is reshaped: payloads are copied as received. The session time zone is UTC, so
-- timestamps with any offset are stored as UTC.

INSERT INTO raw.landing_runs BY NAME
SELECT
    manifest ->> 'run_id' AS run_id,
    (manifest ->> 'started_at')::TIMESTAMPTZ::TIMESTAMP AS started_at,
    (manifest ->> 'committed_at')::TIMESTAMPTZ::TIMESTAMP AS committed_at,
    manifest ->> 'pipeline_version' AS pipeline_version,
    manifest ->> 'git_sha' AS git_sha,
    manifest ->> 'config_hash' AS config_hash,
    manifest -> 'config' AS config,
    manifest -> 'warnings' AS warnings
FROM landed_manifest;

INSERT INTO raw.api_requests BY NAME
SELECT
    manifest ->> 'run_id' AS run_id,
    request ->> 'endpoint' AS endpoint,
    request ->> 'key' AS request_key,
    (request ->> 'pages')::INTEGER AS pages,
    (request ->> 'total')::INTEGER AS total,
    (request ->> 'lastupdated')::DATE AS lastupdated
FROM landed_manifest, unnest(manifest -> '$.requests[*]') AS requests (request);

INSERT INTO raw.api_responses BY NAME
SELECT
    files.listed_file ->> 'response_id' AS response_id,
    landed_manifest.manifest ->> 'run_id' AS run_id,
    files.listed_file ->> 'endpoint' AS endpoint,
    files.listed_file ->> 'key' AS request_key,
    (files.listed_file ->> 'page')::INTEGER AS page,
    files.listed_file ->> 'url' AS url,
    (files.listed_file ->> 'fetched_at')::TIMESTAMPTZ::TIMESTAMP AS fetched_at,
    files.listed_file ->> 'sha256' AS sha256,
    landed_page.content AS payload
FROM landed_manifest, unnest(landed_manifest.manifest -> '$.files[*]') AS files (listed_file)
INNER JOIN landed_page ON landed_page.response_id = files.listed_file ->> 'response_id';
