from dataclasses import dataclass
from datetime import UTC, datetime

from django.core.cache import cache

from . import http

URL = "https://api.open-meteo.com/v1/forecast"
HOURS = 48
BATCH = 100
CACHE_S = 3600
VARIABLES = ("wind_speed_10m", "wind_gusts_10m", "rain", "showers", "snowfall")


@dataclass(frozen=True)
class HourlyWeather:
    wind_mph: list[float | None]
    gust_mph: list[float | None]
    rain_in: list[float | None]
    snow_in: list[float | None]

    def at(self, hour: int) -> tuple[float | None, float | None, float | None, float | None]:
        return self.wind_mph[hour], self.gust_mph[hour], self.rain_in[hour], self.snow_in[hour]


def fetch_hourly(
    cells: list[tuple[float, float]], start_epoch: int
) -> dict[tuple[float, float], HourlyWeather]:
    keys = {cell: f"wx:{cell[0]}:{cell[1]}:{start_epoch}" for cell in cells}
    cached = cache.get_many(keys.values())
    result = {cell: cached[key] for cell, key in keys.items() if key in cached}
    missing = [cell for cell in cells if cell not in result]

    for i in range(0, len(missing), BATCH):
        batch = missing[i : i + BATCH]
        fetched = dict(zip(batch, _request(batch, start_epoch)))
        cache.set_many({keys[cell]: weather for cell, weather in fetched.items()}, CACHE_S)
        result.update(fetched)
    return result


def _request(cells: list[tuple[float, float]], start_epoch: int) -> list[HourlyWeather]:
    params = {
        "latitude": ",".join(str(lat) for lat, _ in cells),
        "longitude": ",".join(str(lon) for _, lon in cells),
        "hourly": ",".join(VARIABLES),
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timeformat": "unixtime",
        "start_hour": _iso_hour(start_epoch),
        "end_hour": _iso_hour(start_epoch + (HOURS - 1) * 3600),
    }
    data = http.request_json("GET", URL, params=params)
    locations = data if isinstance(data, list) else [data]
    return [_parse(location["hourly"]) for location in locations]


def _parse(hourly: dict) -> HourlyWeather:
    rain = [
        None if r is None or s is None else r + s for r, s in zip(hourly["rain"], hourly["showers"])
    ]
    return HourlyWeather(
        wind_mph=hourly["wind_speed_10m"],
        gust_mph=hourly["wind_gusts_10m"],
        rain_in=rain,
        snow_in=hourly["snowfall"],
    )


def _iso_hour(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%dT%H:%M")
