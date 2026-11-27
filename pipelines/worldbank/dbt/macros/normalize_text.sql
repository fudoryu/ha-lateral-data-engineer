{#- Clean text from the source, in staging only (ADR-0033): trim it, collapse every run of
    whitespace (spaces, tabs, newlines) into one space, and turn an empty result into null.
    Uses a regular expression, so it's dialect-specific, which staging allows (ADR-0001). -#}
{% macro normalize_text(expression) -%}
    nullif(trim(regexp_replace({{ expression }}, '\s+', ' ', 'g')), '')
{%- endmacro %}
