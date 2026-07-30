from datetime import date

from pyspark.sql import SparkSession
from pyspark.sql.types import DateType, DoubleType, StringType, StructField, StructType

from lakehouse.processing.gold import compute_monthly_summary

SILVER_LIKE_SCHEMA = StructType(
    [
        StructField("date", DateType()),
        StructField("location", StringType()),
        StructField("temperature_2m_max", DoubleType()),
        StructField("temperature_2m_min", DoubleType()),
        StructField("precipitation_sum", DoubleType()),
    ]
)


def test_compute_monthly_summary_aggregates_correctly(spark: SparkSession) -> None:
    rows = [
        (date(2024, 1, 1), "new_york", 10.0, 0.0, 0.0),
        (date(2024, 1, 2), "new_york", 20.0, 10.0, 5.0),
        (date(2024, 2, 1), "new_york", 15.0, 5.0, 0.0),
    ]
    df = spark.createDataFrame(rows, schema=SILVER_LIKE_SCHEMA)

    result = {(r["year_month"], r["location"]): r for r in compute_monthly_summary(df).collect()}

    jan = result[("2024-01", "new_york")]
    assert jan["avg_temp_max_c"] == 15.0
    assert jan["avg_temp_min_c"] == 5.0
    assert jan["max_temp_max_c"] == 20.0
    assert jan["min_temp_min_c"] == 0.0
    assert jan["total_precipitation_mm"] == 5.0
    assert jan["avg_precipitation_mm"] == 2.5
    assert jan["days_with_precipitation"] == 1
    assert jan["days_observed"] == 2

    feb = result[("2024-02", "new_york")]
    assert feb["days_observed"] == 1
    assert feb["avg_temp_max_c"] == 15.0
    assert feb["days_with_precipitation"] == 0
