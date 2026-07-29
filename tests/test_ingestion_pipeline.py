from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import dlt

from lakehouse.ingestion.open_meteo import Location, open_meteo_source

FAKE_DAILY_RESPONSE = {
    "daily": {
        "time": ["2024-01-01", "2024-01-02"],
        "temperature_2m_max": [5.1, 6.2],
        "temperature_2m_min": [-1.0, 0.5],
        "precipitation_sum": [0.0, 2.3],
    }
}


def _fake_response() -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = FAKE_DAILY_RESPONSE
    return response


def test_pipeline_loads_daily_weather_rows(tmp_path: Path) -> None:
    with patch(
        "lakehouse.ingestion.open_meteo.requests.get", return_value=_fake_response()
    ) as mock_get:
        pipeline = dlt.pipeline(
            pipeline_name="test_open_meteo_ingestion",
            destination=dlt.destinations.duckdb(credentials=str(tmp_path / "pipeline.duckdb")),
            dataset_name="open_meteo",
            pipelines_dir=str(tmp_path),
        )
        source = open_meteo_source(
            locations=(Location("test_city", 0.0, 0.0),),
            start_date="2023-12-31",
        )
        load_info = pipeline.run(source)

    assert not load_info.has_failed_jobs
    assert mock_get.call_count == 1

    with pipeline.sql_client() as client:
        with client.execute_query(
            "select date, location, temperature_2m_max from daily_weather_test_city order by date"
        ) as cursor:
            rows: list[tuple[Any, ...]] = cursor.fetchall()

    assert rows == [
        ("2024-01-01", "test_city", 5.1),
        ("2024-01-02", "test_city", 6.2),
    ]


def test_pipeline_skips_fetch_when_already_up_to_date(tmp_path: Path) -> None:
    with patch("lakehouse.ingestion.open_meteo.requests.get") as mock_get:
        pipeline = dlt.pipeline(
            pipeline_name="test_open_meteo_ingestion_uptodate",
            destination=dlt.destinations.duckdb(credentials=str(tmp_path / "pipeline.duckdb")),
            dataset_name="open_meteo",
            pipelines_dir=str(tmp_path),
        )
        # A start_date of "today" means start_date > end_date (yesterday) for
        # every location, so fetch_daily_weather should skip the HTTP call.
        from datetime import UTC, datetime

        today = datetime.now(UTC).date().isoformat()
        source = open_meteo_source(
            locations=(Location("test_city", 0.0, 0.0),),
            start_date=today,
        )
        load_info = pipeline.run(source)

    assert not load_info.has_failed_jobs
    assert mock_get.call_count == 0
