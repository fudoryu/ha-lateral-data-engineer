{#- Fails for every row where `expression` isn't true: a row-level rule a built-in test can't
    express (ADR-0016: no dbt packages). Keep expressions portable SQL. -#}
{% test expression_is_true(model, expression) %}

SELECT *
FROM {{ model }}
WHERE NOT ({{ expression }})

{% endtest %}
