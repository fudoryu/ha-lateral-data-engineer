-- The warehouse's raw layer, created by `worldbank load` in every new warehouse file (ADR-0022).
-- One row per committed landing run, API request and response page; never deduplicated.
-- Timestamps are UTC. dbt declares these tables as sources in
-- pipelines/worldbank/dbt/models/staging/_worldbank__sources.yml: keep the two in step.

CREATE SCHEMA raw;

CREATE TABLE raw.landing_runs (
    run_id VARCHAR PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    committed_at TIMESTAMP NOT NULL,
    pipeline_version VARCHAR NOT NULL,
    git_sha VARCHAR,
    config_hash VARCHAR NOT NULL,
    config JSON NOT NULL,
    warnings JSON NOT NULL
);

CREATE TABLE raw.api_requests (
    run_id VARCHAR NOT NULL,
    endpoint VARCHAR NOT NULL,
    request_key VARCHAR,  -- the request's key, e.g. the indicator code; null for countries
    pages INTEGER NOT NULL,
    total INTEGER NOT NULL,
    lastupdated DATE
);

CREATE TABLE raw.api_responses (
    response_id VARCHAR PRIMARY KEY,
    run_id VARCHAR NOT NULL,
    endpoint VARCHAR NOT NULL,
    request_key VARCHAR,  -- the request's key, e.g. the indicator code; null for countries
    page INTEGER NOT NULL,
    url VARCHAR NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    sha256 VARCHAR NOT NULL,
    payload JSON NOT NULL
);
