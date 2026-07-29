from lakehouse.ingestion.open_meteo import flatten_daily_response


def test_flatten_daily_response_zips_columnar_arrays_into_rows() -> None:
    payload = {
        "daily": {
            "time": ["2024-01-01", "2024-01-02"],
            "temperature_2m_max": [5.1, 6.2],
            "temperature_2m_min": [-1.0, 0.5],
            "precipitation_sum": [0.0, 2.3],
        }
    }

    rows = list(flatten_daily_response(payload, "new_york"))

    assert rows == [
        {
            "date": "2024-01-01",
            "location": "new_york",
            "temperature_2m_max": 5.1,
            "temperature_2m_min": -1.0,
            "precipitation_sum": 0.0,
        },
        {
            "date": "2024-01-02",
            "location": "new_york",
            "temperature_2m_max": 6.2,
            "temperature_2m_min": 0.5,
            "precipitation_sum": 2.3,
        },
    ]


def test_flatten_daily_response_handles_empty_daily_block() -> None:
    rows = list(flatten_daily_response({"daily": {"time": []}}, "london"))

    assert rows == []
