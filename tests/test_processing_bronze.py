import gzip
import json
from pathlib import Path

from pyspark.sql import SparkSession

from lakehouse.processing.bronze import read_raw_weather


def _write_landing_fixture(tmp_path: Path) -> str:
    table_dir = tmp_path / "open_meteo" / "daily_weather_new_york"
    table_dir.mkdir(parents=True)
    rows = [
        {
            "date": "2024-01-01",
            "location": "new_york",
            "temperature_2m_max": 5.0,
            "temperature_2m_min": -1.0,
            "precipitation_sum": 0.0,
            "_dlt_load_id": "1",
            "_dlt_id": "a",
        },
        {
            "date": "2024-01-02",
            "location": "new_york",
            "temperature_2m_max": 6.0,
            "temperature_2m_min": 0.0,
            "precipitation_sum": 1.5,
            "_dlt_load_id": "1",
            "_dlt_id": "b",
        },
    ]
    content = "\n".join(json.dumps(row) for row in rows).encode()
    with gzip.open(table_dir / "data.jsonl.gz", "wb") as f:
        f.write(content)
    return f"file://{tmp_path}/"


def test_read_raw_weather_parses_landing_files_and_adds_metadata_columns(
    spark: SparkSession, tmp_path: Path
) -> None:
    landing_path = _write_landing_fixture(tmp_path)

    df = read_raw_weather(spark, landing_path)
    rows = sorted(df.collect(), key=lambda r: r["date"])

    assert len(rows) == 2
    assert rows[0]["date"] == "2024-01-01"
    assert rows[0]["location"] == "new_york"
    assert rows[0]["temperature_2m_max"] == 5.0
    assert rows[0]["_dlt_load_id"] == "1"
    assert rows[0]["_bronze_ingested_at"] is not None
    assert rows[0]["_bronze_source_file"].endswith("data.jsonl.gz")
