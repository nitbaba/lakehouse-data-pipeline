from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from lakehouse.processing.silver import SILVER_TABLE
from lakehouse.processing.spark_session import CATALOG, build_spark_session

GOLD_TABLE = f"{CATALOG}.gold.monthly_location_climate_summary"


def compute_monthly_summary(silver_df: DataFrame) -> DataFrame:
    return silver_df.groupBy(
        F.date_format("date", "yyyy-MM").alias("year_month"),
        "location",
    ).agg(
        F.round(F.avg("temperature_2m_max"), 2).alias("avg_temp_max_c"),
        F.round(F.avg("temperature_2m_min"), 2).alias("avg_temp_min_c"),
        F.round(F.max("temperature_2m_max"), 2).alias("max_temp_max_c"),
        F.round(F.min("temperature_2m_min"), 2).alias("min_temp_min_c"),
        F.round(F.sum("precipitation_sum"), 2).alias("total_precipitation_mm"),
        F.round(F.avg("precipitation_sum"), 2).alias("avg_precipitation_mm"),
        F.sum(F.when(F.col("precipitation_sum") > 0, 1).otherwise(0)).alias(
            "days_with_precipitation"
        ),
        F.count(F.lit(1)).alias("days_observed"),
    )


def run() -> None:
    spark = build_spark_session("gold_weather")
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {CATALOG}.gold")

    summary = compute_monthly_summary(spark.table(SILVER_TABLE))
    summary.writeTo(GOLD_TABLE).using("iceberg").createOrReplace()

    count = spark.table(GOLD_TABLE).count()
    print(f"Gold: wrote {count} rows to {GOLD_TABLE}")


if __name__ == "__main__":
    run()
