{{
  config(
    materialized='incremental',
    unique_key=['date', 'location'],
    incremental_strategy='merge'
  )
}}

-- SQL translation of dedupe_bronze() in src/lakehouse/processing/silver.py:
-- keep the latest dlt load per (date, location). Bronze is fully recreated
-- (not append-only) on every run, so this always processes the whole
-- staging view -- the incremental+merge materialization only makes the
-- upsert into this table efficient, matching what MERGE_SILVER_SQL already
-- does on the PySpark side.
with ranked as (
    select
        date,
        location,
        temperature_2m_max,
        temperature_2m_min,
        precipitation_sum,
        _dlt_load_id,
        row_number() over (
            partition by date, location
            order by _dlt_load_id desc
        ) as rn
    from {{ ref('stg_weather_bronze') }}
)

select
    date,
    location,
    temperature_2m_max,
    temperature_2m_min,
    precipitation_sum,
    _dlt_load_id as ingestion_load_id,
    current_timestamp as updated_at
from ranked
where rn = 1
