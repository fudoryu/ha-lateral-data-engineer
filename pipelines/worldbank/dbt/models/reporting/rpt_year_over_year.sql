-- FR-ANA-2: each country x indicator x year's change from the year before, absolute and in
-- percent (ADR-0009). A change that can't be computed is null with a reason, never 0, checked in
-- this order: current_missing (no value this year), prior_out_of_scope (the year before isn't in
-- the reporting range, always the case for the first year), prior_missing (no value the year
-- before), prior_zero (the absolute change is computed; the percentage can't be).
WITH

facts AS (
    SELECT * FROM {{ ref('fct_country_indicator_values') }}
),

countries AS (
    SELECT * FROM {{ ref('dim_countries') }}
),

indicators AS (
    SELECT * FROM {{ ref('dim_indicators') }}
),

changes AS (
    SELECT
        this_year.country_id,
        this_year.indicator_id,
        this_year.observation_year,
        this_year.indicator_value,
        prior_year.indicator_value AS prior_indicator_value,
        CASE
            WHEN this_year.value_status = 'present' AND prior_year.value_status = 'present'
                THEN this_year.indicator_value - prior_year.indicator_value
        END AS absolute_change,
        CASE
            WHEN
                this_year.value_status = 'present'
                AND prior_year.value_status = 'present'
                AND prior_year.indicator_value <> 0
                THEN
                    (this_year.indicator_value - prior_year.indicator_value)
                    / prior_year.indicator_value * 100
        END AS percent_change,
        CASE
            WHEN this_year.value_status <> 'present' THEN 'current_missing'
            WHEN prior_year.country_id IS NULL THEN 'prior_out_of_scope'
            WHEN prior_year.value_status <> 'present' THEN 'prior_missing'
            WHEN prior_year.indicator_value = 0 THEN 'prior_zero'
        END AS null_change_reason
    FROM facts AS this_year
    LEFT JOIN facts AS prior_year
        ON
            this_year.country_id = prior_year.country_id
            AND this_year.indicator_id = prior_year.indicator_id
            AND this_year.observation_year - 1 = prior_year.observation_year
),

final AS (
    SELECT
        changes.country_id,
        countries.country_name,
        changes.indicator_id,
        indicators.indicator_name,
        changes.observation_year,
        changes.indicator_value,
        changes.prior_indicator_value,
        changes.absolute_change,
        changes.percent_change,
        changes.null_change_reason
    FROM changes
    INNER JOIN countries ON changes.country_id = countries.country_id
    INNER JOIN indicators ON changes.indicator_id = indicators.indicator_id
)

SELECT * FROM final
