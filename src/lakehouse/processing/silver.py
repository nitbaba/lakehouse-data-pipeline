from lakehouse.processing.bronze import BRONZE_TABLE
from lakehouse.processing.spark_session import CATALOG, build_spark_session

SILVER_TABLE = f"{CATALOG}.silver.weather_daily"

CREATE_SILVER_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {SILVER_TABLE} (
    date DATE,
    location STRING,
    temperature_2m_max DOUBLE,
    temperature_2m_min DOUBLE,
    precipitation_sum DOUBLE,
    ingestion_load_id STRING,
    updated_at TIMESTAMP
)
USING iceberg
PARTITIONED BY (location)
"""

# Structural cleaning only (null keys). Value/range validation belongs to
# Phase 4 (Great Expectations), not here. Dedup keyed on (date, location),
# keeping the latest dlt load per key in case of any duplicate landing.
MERGE_SILVER_SQL = f"""
MERGE INTO {SILVER_TABLE} AS target
USING (
    SELECT date, location, temperature_2m_max, temperature_2m_min,
           precipitation_sum, ingestion_load_id, current_timestamp() AS updated_at
    FROM (
        SELECT CAST(date AS DATE) AS date, location, temperature_2m_max,
               temperature_2m_min, precipitation_sum,
               _dlt_load_id AS ingestion_load_id,
               ROW_NUMBER() OVER (
                   PARTITION BY date, location ORDER BY _dlt_load_id DESC
               ) AS rn
        FROM {BRONZE_TABLE}
        WHERE date IS NOT NULL AND location IS NOT NULL
    )
    WHERE rn = 1
) AS source
ON target.date = source.date AND target.location = source.location
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
"""


def run() -> None:
    spark = build_spark_session("silver_weather")
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {CATALOG}.silver")
    spark.sql(CREATE_SILVER_TABLE_SQL)
    spark.sql(MERGE_SILVER_SQL)

    count = spark.table(SILVER_TABLE).count()
    print(f"Silver: {SILVER_TABLE} now has {count} rows")


if __name__ == "__main__":
    run()
