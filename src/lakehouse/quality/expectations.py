import os
from collections.abc import Sequence
from typing import Any

# Must be set before the great_expectations import to guarantee no telemetry
# network call, keeping offline pipeline steps (and tests) fully offline.
os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")

from pyspark.sql import DataFrame  # noqa: E402

import great_expectations as gx  # noqa: E402

KNOWN_LOCATIONS = ("new_york", "london", "mumbai", "philadelphia")
MIN_PLAUSIBLE_TEMP_C = -90.0
MAX_PLAUSIBLE_TEMP_C = 60.0


def _validate(df: DataFrame, suite_name: str, expectations: Sequence[Any]) -> None:
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_spark(name=f"{suite_name}_source")
    data_asset = data_source.add_dataframe_asset(name=f"{suite_name}_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe(f"{suite_name}_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
    for expectation in expectations:
        suite.add_expectation(expectation)

    result = batch.validate(suite)
    if not result.success:
        raise ValueError(f"data quality validation failed for suite '{suite_name}': {result}")


def validate_landing(df: DataFrame) -> None:
    _validate(
        df,
        "landing_weather",
        [
            gx.expectations.ExpectColumnValuesToNotBeNull(column="date"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="location"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="_dlt_load_id"),
            gx.expectations.ExpectColumnValuesToBeInSet(
                column="location", value_set=list(KNOWN_LOCATIONS)
            ),
            gx.expectations.ExpectColumnValuesToBeBetween(
                column="temperature_2m_max",
                min_value=MIN_PLAUSIBLE_TEMP_C,
                max_value=MAX_PLAUSIBLE_TEMP_C,
            ),
            gx.expectations.ExpectColumnValuesToBeBetween(
                column="temperature_2m_min",
                min_value=MIN_PLAUSIBLE_TEMP_C,
                max_value=MAX_PLAUSIBLE_TEMP_C,
            ),
            gx.expectations.ExpectColumnValuesToBeBetween(
                column="precipitation_sum", min_value=0.0
            ),
        ],
    )


def validate_silver(df: DataFrame) -> None:
    _validate(
        df,
        "silver_weather",
        [
            gx.expectations.ExpectColumnValuesToNotBeNull(column="date"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="location"),
            gx.expectations.ExpectCompoundColumnsToBeUnique(column_list=["date", "location"]),
            gx.expectations.ExpectColumnPairValuesAToBeGreaterThanB(
                column_A="temperature_2m_max", column_B="temperature_2m_min", or_equal=True
            ),
            gx.expectations.ExpectColumnValuesToBeBetween(
                column="temperature_2m_max",
                min_value=MIN_PLAUSIBLE_TEMP_C,
                max_value=MAX_PLAUSIBLE_TEMP_C,
            ),
            gx.expectations.ExpectColumnValuesToBeBetween(
                column="temperature_2m_min",
                min_value=MIN_PLAUSIBLE_TEMP_C,
                max_value=MAX_PLAUSIBLE_TEMP_C,
            ),
        ],
    )
