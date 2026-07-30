from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from lakehouse.processing.bronze import BRONZE_TABLE
from lakehouse.processing.spark_session import CATALOG, build_spark_session
from lakehouse.quality.expectations import validate_silver

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

MERGE_SILVER_SQL = f"""
MERGE INTO {SILVER_TABLE} AS target
USING silver_source AS source
ON target.date = source.date AND target.location = source.location
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
"""


def dedupe_bronze(bronze_df: DataFrame) -> DataFrame:
    # Structural cleaning + dedup only, keeping the latest dlt load per key.
    # Value/range validation is validate_silver()'s job, not this function's.
    window = Window.partitionBy("date", "location").orderBy(F.col("_dlt_load_id").desc())
    return (
        bronze_df.filter(F.col("date").isNotNull() & F.col("location").isNotNull())
        .withColumn("date", F.col("date").cast("date"))
        .withColumn("rn", F.row_number().over(window))
        .filter(F.col("rn") == 1)
        .select(
            "date",
            "location",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            F.col("_dlt_load_id").alias("ingestion_load_id"),
            F.current_timestamp().alias("updated_at"),
        )
    )


def run() -> None:
    spark = build_spark_session("silver_weather")
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {CATALOG}.silver")
    spark.sql(CREATE_SILVER_TABLE_SQL)

    deduped = dedupe_bronze(spark.table(BRONZE_TABLE))
    validate_silver(deduped)
    deduped.createOrReplaceTempView("silver_source")
    spark.sql(MERGE_SILVER_SQL)

    count = spark.table(SILVER_TABLE).count()
    print(f"Silver: {SILVER_TABLE} now has {count} rows")


if __name__ == "__main__":
    run()
