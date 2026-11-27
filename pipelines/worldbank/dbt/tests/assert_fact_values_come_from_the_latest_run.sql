-- Every current value comes from a page of the latest run (ADR-0006, ADR-0028): the lineage
-- column never points at an older run.
SELECT
    facts.country_id,
    facts.indicator_id,
    facts.observation_year,
    facts.source_response_id
FROM {{ ref('fct_country_indicator_values') }} AS facts
INNER JOIN {{ ref('int_responses_joined_to_runs') }} AS responses
    ON facts.source_response_id = responses.source_response_id
WHERE NOT responses.is_latest_run
