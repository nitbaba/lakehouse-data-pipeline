import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

from lakehouse.quality.expectations import validate_landing, validate_silver

LANDING_SCHEMA = StructType(
    [
        StructField("date", StringType()),
        StructField("location", StringType()),
        StructField("temperature_2m_max", DoubleType()),
        StructField("temperature_2m_min", DoubleType()),
        StructField("precipitation_sum", DoubleType()),
        StructField("_dlt_load_id", StringType()),
    ]
)

SILVER_SCHEMA = StructType(
    [
        StructField("date", StringType()),
        StructField("location", StringType()),
        StructField("temperature_2m_max", DoubleType()),
        StructField("temperature_2m_min", DoubleType()),
        StructField("precipitation_sum", DoubleType()),
    ]
)

GOOD_LANDING_ROW = ("2024-01-01", "new_york", 5.0, -1.0, 0.0, "1")
GOOD_SILVER_ROW = ("2024-01-01", "new_york", 5.0, -1.0, 0.0)


def test_validate_landing_passes_for_good_data(spark: SparkSession) -> None:
    df = spark.createDataFrame([GOOD_LANDING_ROW], schema=LANDING_SCHEMA)
    validate_landing(df)  # must not raise


def test_validate_landing_rejects_null_date(spark: SparkSession) -> None:
    df = spark.createDataFrame([(None, "new_york", 5.0, -1.0, 0.0, "1")], schema=LANDING_SCHEMA)
    with pytest.raises(ValueError):
        validate_landing(df)


def test_validate_landing_rejects_unknown_location(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [("2024-01-01", "atlantis", 5.0, -1.0, 0.0, "1")], schema=LANDING_SCHEMA
    )
    with pytest.raises(ValueError):
        validate_landing(df)


def test_validate_landing_rejects_implausible_temperature(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [("2024-01-01", "new_york", 500.0, -1.0, 0.0, "1")], schema=LANDING_SCHEMA
    )
    with pytest.raises(ValueError):
        validate_landing(df)


def test_validate_landing_rejects_negative_precipitation(spark: SparkSession) -> None:
    df = spark.createDataFrame(
        [("2024-01-01", "new_york", 5.0, -1.0, -0.5, "1")], schema=LANDING_SCHEMA
    )
    with pytest.raises(ValueError):
        validate_landing(df)


def test_validate_silver_passes_for_good_data(spark: SparkSession) -> None:
    df = spark.createDataFrame([GOOD_SILVER_ROW], schema=SILVER_SCHEMA)
    validate_silver(df)  # must not raise


def test_validate_silver_rejects_duplicate_date_location(spark: SparkSession) -> None:
    df = spark.createDataFrame([GOOD_SILVER_ROW, GOOD_SILVER_ROW], schema=SILVER_SCHEMA)
    with pytest.raises(ValueError):
        validate_silver(df)


def test_validate_silver_rejects_max_below_min(spark: SparkSession) -> None:
    df = spark.createDataFrame([("2024-01-01", "new_york", 3.0, 6.0, 0.0)], schema=SILVER_SCHEMA)
    with pytest.raises(ValueError):
        validate_silver(df)
