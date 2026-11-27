-- dim_indicator's display_decimals is one number per indicator, so every current value of an
-- indicator must report the same `decimal` precision. Fails with each indicator that doesn't.
SELECT
    indicator_id,
    count(DISTINCT decimals) AS precisions
FROM {{ ref('int_indicator_values_filtered_to_latest_run') }}
GROUP BY indicator_id
HAVING count(DISTINCT decimals) > 1
