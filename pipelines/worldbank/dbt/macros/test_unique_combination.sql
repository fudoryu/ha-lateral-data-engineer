{#- Fails for every combination of `columns` that occurs more than once: the grain test for
    models whose key spans several columns (ADR-0016: no dbt packages). -#}
{% test unique_combination(model, columns) %}

SELECT
    {{ columns | join(', ') }},
    count(*) AS n_rows
FROM {{ model }}
GROUP BY {{ columns | join(', ') }}
HAVING count(*) > 1

{% endtest %}
