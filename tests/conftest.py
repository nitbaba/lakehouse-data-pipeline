import os
from collections.abc import Iterator

import pytest
from pyspark.sql import SparkSession

# Must be set before any great_expectations import happens (including
# transitively, via test modules), to guarantee no telemetry network call.
os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")


@pytest.fixture(scope="session")
def spark() -> Iterator[SparkSession]:
    session = SparkSession.builder.master("local[1]").appName("lakehouse-tests").getOrCreate()
    yield session
    session.stop()
