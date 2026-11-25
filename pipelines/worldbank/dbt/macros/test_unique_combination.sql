{#- Fails for every combination of `columns` that occurs more than once: the grain test for
    models whose key spans several columns (ADR-0016: no dbt packages). -#}
{% test unique_combination(model, columns) %}

select
    {{ columns | join(', ') }},
    count(*) as n_rows
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1

{% endtest %}
