{#
  dbt's default behavior prefixes a model's custom schema with the profile's
  target schema (e.g. "dbt_staging_dbt_silver"). Models here set their real
  target schema explicitly via +schema in dbt_project.yml, so use it as-is.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
