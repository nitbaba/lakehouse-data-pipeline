-- Structural cleanup only, mirroring dedupe_bronze()'s pre-dedup step in
-- src/lakehouse/processing/silver.py: cast the raw date string to a real
-- DATE and drop rows missing either key column. Dedup itself happens in
-- the Silver model, not here.
select
    cast(date as date) as date,
    location,
    temperature_2m_max,
    temperature_2m_min,
    precipitation_sum,
    _dlt_load_id
from {{ source('iceberg_bronze', 'weather_daily_raw') }}
where date is not null
  and location is not null
