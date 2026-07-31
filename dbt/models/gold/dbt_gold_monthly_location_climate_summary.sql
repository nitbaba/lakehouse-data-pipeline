-- SQL translation of compute_monthly_summary() in
-- src/lakehouse/processing/gold.py -- same aggregates, same rounding,
-- different engine. Full recompute each run, same as the PySpark job.
select
    date_format(date, '%Y-%m') as year_month,
    location,
    round(avg(temperature_2m_max), 2) as avg_temp_max_c,
    round(avg(temperature_2m_min), 2) as avg_temp_min_c,
    round(max(temperature_2m_max), 2) as max_temp_max_c,
    round(min(temperature_2m_min), 2) as min_temp_min_c,
    round(sum(precipitation_sum), 2) as total_precipitation_mm,
    round(avg(precipitation_sum), 2) as avg_precipitation_mm,
    sum(case when precipitation_sum > 0 then 1 else 0 end) as days_with_precipitation,
    count(*) as days_observed
from {{ ref('dbt_silver_weather_daily') }}
group by date_format(date, '%Y-%m'), location
