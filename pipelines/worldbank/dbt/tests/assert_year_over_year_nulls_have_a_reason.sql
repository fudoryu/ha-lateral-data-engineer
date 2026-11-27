-- No unexplained gap (FR-ANA-2, ADR-0009): a percentage change is null exactly when there's a
-- reason, and the absolute change is null exactly when the reason isn't prior_zero.
SELECT
    country_id,
    indicator_id,
    observation_year,
    absolute_change,
    percent_change,
    null_change_reason
FROM {{ ref('rpt_year_over_year') }}
WHERE
    (percent_change IS NULL) <> (null_change_reason IS NOT NULL)
    OR (absolute_change IS NULL)
    <> (null_change_reason IS NOT NULL AND null_change_reason <> 'prior_zero')
