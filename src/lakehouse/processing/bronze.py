from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, input_file_name
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

from lakehouse.common.config import Settings
from lakehouse.processing.spark_session import CATALOG, build_spark_session

# Matches the row shape dlt's open_meteo pipeline lands in S3 (see
# src/lakehouse/ingestion/open_meteo.py) — explicit schema, not inference,
# since it's a fixed, dlt-managed shape.
RAW_WEATHER_SCHEMA = StructType(
    [
        StructField("date", StringType()),
        StructField("location", StringType()),
        StructField("temperature_2m_max", DoubleType()),
        StructField("temperature_2m_min", DoubleType()),
        StructField("precipitation_sum", DoubleType()),
        StructField("_dlt_load_id", StringType()),
        StructField("_dlt_id", StringType()),
    ]
)

BRONZE_TABLE = f"{CATALOG}.bronze.weather_daily_raw"


def read_raw_weather(spark: SparkSession, landing_path_s3a: str) -> DataFrame:
    # dlt's bookkeeping dirs (_dlt_loads/, _dlt_pipeline_state/, etc.) are
    # siblings of the daily_weather_* dirs, not nested inside them, so this
    # glob naturally excludes them.
    glob = f"{landing_path_s3a}open_meteo/daily_weather_*/*.jsonl.gz"
    return (
        spark.read.schema(RAW_WEATHER_SCHEMA)
        .json(glob)
        .withColumn("_bronze_ingested_at", current_timestamp())
        .withColumn("_bronze_source_file", input_file_name())
    )


def run() -> None:
    settings = Settings.from_env()
    spark = build_spark_session("bronze_weather")
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {CATALOG}.bronze")

    df = read_raw_weather(spark, settings.landing_path_s3a)
    # Landing is append-only across dlt runs, so a naive append here would
    # duplicate history on every rerun. Data volume is tiny, so full
    # overwrite is the simplest correctly-idempotent approach — this does
    # create a new Iceberg snapshot each run, which is what makes the
    # maintenance job's snapshot expiration meaningful to demonstrate.
    df.writeTo(BRONZE_TABLE).using("iceberg").createOrReplace()

    count = spark.table(BRONZE_TABLE).count()
    print(f"Bronze: wrote {count} rows to {BRONZE_TABLE}")


if __name__ == "__main__":
    run()
