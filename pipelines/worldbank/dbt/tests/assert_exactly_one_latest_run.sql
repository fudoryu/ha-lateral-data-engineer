-- Current state comes from exactly one run (ADR-0006): when any run exists, exactly one is the
-- latest. Fails with the number of latest runs found.
SELECT count(*) AS latest_runs
FROM {{ ref('int_runs_ranked') }}
WHERE is_latest
HAVING count(*) <> 1 AND (SELECT count(*) FROM {{ ref('int_runs_ranked') }}) > 0
