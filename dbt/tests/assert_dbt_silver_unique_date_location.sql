-- Singular test: passes when this returns zero rows. Mirrors the
-- (date, location) uniqueness check Great Expectations runs on the
-- PySpark Silver output (src/lakehouse/quality/expectations.py).
select date, location, count(*) as row_count
from {{ ref('dbt_silver_weather_daily') }}
group by date, location
having count(*) > 1
