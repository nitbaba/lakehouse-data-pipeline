from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import dlt
from dlt.extract import DltResource
from dlt.sources.helpers import requests

ARCHIVE_API_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_METRICS = ("temperature_2m_max", "temperature_2m_min", "precipitation_sum")
# Exclusive cursor: the first run fetches starting the day after this.
DEFAULT_START_DATE = "2023-12-31"


@dataclass(frozen=True)
class Location:
    name: str
    latitude: float
    longitude: float


LOCATIONS: tuple[Location, ...] = (
    Location("new_york", 40.7128, -74.0060),
    Location("london", 51.5074, -0.1278),
    Location("mumbai", 19.0760, 72.8777),
    Location("philadelphia", 39.9526, -75.1652),
)


def flatten_daily_response(
    payload: Mapping[str, Any], location_name: str
) -> Iterator[dict[str, Any]]:
    daily = payload.get("daily", {})
    dates = daily.get("time", [])
    for i, date in enumerate(dates):
        row: dict[str, Any] = {"date": date, "location": location_name}
        for metric in DAILY_METRICS:
            values = daily.get(metric, [])
            row[metric] = values[i] if i < len(values) else None
        yield row


def fetch_daily_weather(
    location: Location,
    date: dlt.sources.incremental[str],
) -> Iterator[dict[str, Any]]:
    last_value = date.last_value
    assert last_value is not None
    start_date = datetime.strptime(last_value, "%Y-%m-%d").date() + timedelta(days=1)
    end_date = datetime.now(UTC).date() - timedelta(days=1)
    if start_date > end_date:
        print(f"[{location.name}] up to date (last loaded {last_value}); skipping fetch")
        return

    params: dict[str, str | float] = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ",".join(DAILY_METRICS),
        "timezone": "UTC",
    }
    response = requests.get(
        ARCHIVE_API_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    yield from flatten_daily_response(response.json(), location.name)


@dlt.source
def open_meteo_source(
    locations: Sequence[Location] = LOCATIONS,
    start_date: str = DEFAULT_START_DATE,
) -> Iterable[DltResource]:
    for location in locations:
        yield dlt.resource(
            fetch_daily_weather,
            name=f"daily_weather_{location.name}",
            write_disposition="append",
            schema_contract={"tables": "evolve", "columns": "evolve", "data_type": "freeze"},
        )(location, dlt.sources.incremental("date", initial_value=start_date))
