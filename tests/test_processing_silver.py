from pyspark.sql import SparkSession
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

from lakehouse.processing.silver import dedupe_bronze

BRONZE_LIKE_SCHEMA = StructType(
    [
        StructField("date", StringType()),
        StructField("location", StringType()),
        StructField("temperature_2m_max", DoubleType()),
        StructField("temperature_2m_min", DoubleType()),
        StructField("precipitation_sum", DoubleType()),
        StructField("_dlt_load_id", StringType()),
    ]
)


def test_dedupe_bronze_keeps_latest_load_per_date_location(spark: SparkSession) -> None:
    rows = [
        ("2024-01-01", "new_york", 5.0, -1.0, 0.0, "1"),
        ("2024-01-01", "new_york", 6.0, 0.0, 1.0, "2"),  # newer load, should win
        ("2024-01-02", "london", 3.0, 1.0, 0.0, "1"),
    ]
    df = spark.createDataFrame(rows, schema=BRONZE_LIKE_SCHEMA)

    result = dedupe_bronze(df).collect()

    assert len(result) == 2
    ny_row = next(r for r in result if r["location"] == "new_york")
    assert ny_row["ingestion_load_id"] == "2"
    assert ny_row["temperature_2m_max"] == 6.0
    assert str(ny_row["date"]) == "2024-01-01"


def test_dedupe_bronze_drops_rows_with_null_key(spark: SparkSession) -> None:
    rows = [
        ("2024-01-01", "new_york", 5.0, -1.0, 0.0, "1"),
        (None, "london", 3.0, 1.0, 0.0, "1"),
        ("2024-01-02", None, 3.0, 1.0, 0.0, "1"),
    ]
    df = spark.createDataFrame(rows, schema=BRONZE_LIKE_SCHEMA)

    result = dedupe_bronze(df).collect()

    assert len(result) == 1
    assert result[0]["location"] == "new_york"
