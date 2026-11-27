-- A fact row's run is the run of the page its value came from (ADR-0017): the two lineage keys
-- never disagree.
SELECT
    facts.country_iso3,
    facts.indicator_id,
    facts.observation_year,
    facts.run_id,
    responses.run_id AS response_run_id
FROM {{ ref('fct_indicator_value') }} AS facts
INNER JOIN {{ ref('dim_source_response') }} AS responses
    ON facts.source_response_id = responses.source_response_id
WHERE facts.run_id <> responses.run_id
