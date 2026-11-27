-- The warehouse's raw layer, created by `worldbank load` in every new warehouse file (ADR-0022).
-- One row per committed landing run, API request and response page; never deduplicated.
-- Timestamps are UTC. dbt declares these tables as sources in
-- pipelines/worldbank/dbt/models/staging/_worldbank__sources.yml: keep the two in step.

create schema raw;

create table raw.landing_runs (
    run_id varchar primary key,
    started_at timestamp not null,
    committed_at timestamp not null,
    pipeline_version varchar not null,
    git_sha varchar,
    config_hash varchar not null,
    config json not null,
    warnings json not null
);

create table raw.api_requests (
    run_id varchar not null,
    endpoint varchar not null,
    key varchar,
    pages integer not null,
    total integer not null,
    lastupdated date
);

create table raw.api_responses (
    response_id varchar primary key,
    run_id varchar not null,
    endpoint varchar not null,
    key varchar,
    page integer not null,
    url varchar not null,
    fetched_at timestamp not null,
    sha256 varchar not null,
    payload json not null
);
