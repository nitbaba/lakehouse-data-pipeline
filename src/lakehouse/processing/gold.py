from lakehouse.processing.silver import SILVER_TABLE
from lakehouse.processing.spark_session import CATALOG, build_spark_session

GOLD_TABLE = f"{CATALOG}.gold.monthly_location_climate_summary"

# Full recompute (CREATE OR REPLACE) rather than incremental — the aggregate
# is small enough over all of Silver's history that incremental buys nothing
# and would still need to detect/re-derive any month a corrected Silver row
# lands in anyway.
CREATE_GOLD_TABLE_SQL = f"""
CREATE OR REPLACE TABLE {GOLD_TABLE}
USING iceberg AS
SELECT
    date_format(date, 'yyyy-MM') AS year_month,
    location,
    ROUND(AVG(temperature_2m_max), 2) AS avg_temp_max_c,
    ROUND(AVG(temperature_2m_min), 2) AS avg_temp_min_c,
    ROUND(MAX(temperature_2m_max), 2) AS max_temp_max_c,
    ROUND(MIN(temperature_2m_min), 2) AS min_temp_min_c,
    ROUND(SUM(precipitation_sum), 2) AS total_precipitation_mm,
    ROUND(AVG(precipitation_sum), 2) AS avg_precipitation_mm,
    SUM(CASE WHEN precipitation_sum > 0 THEN 1 ELSE 0 END) AS days_with_precipitation,
    COUNT(*) AS days_observed
FROM {SILVER_TABLE}
GROUP BY date_format(date, 'yyyy-MM'), location
"""


def run() -> None:
    spark = build_spark_session("gold_weather")
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {CATALOG}.gold")
    spark.sql(CREATE_GOLD_TABLE_SQL)

    count = spark.table(GOLD_TABLE).count()
    print(f"Gold: wrote {count} rows to {GOLD_TABLE}")


if __name__ == "__main__":
    run()
