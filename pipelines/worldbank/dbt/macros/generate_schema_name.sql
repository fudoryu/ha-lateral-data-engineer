{#- Use each layer's schema name as is (staging, marts, ...) instead of dbt's default
    "<target schema>_<custom schema>" prefixing (ADR-0016). -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name | trim if custom_schema_name else target.schema }}
{%- endmacro %}
