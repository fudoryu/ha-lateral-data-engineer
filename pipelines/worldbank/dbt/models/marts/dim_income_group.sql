-- One row per income group, low to high income, with how today's classification was made: the
-- current classification applied to every year (ADR-0011, ADR-0029).
WITH

income_groups AS (
    SELECT * FROM {{ ref('int_income_groups_joined_to_order') }}
),

final AS (
    SELECT
        income_group_id,
        income_group_name,
        sort_order,
        classification_basis,
        classified_as_of
    FROM income_groups
)

SELECT * FROM final
