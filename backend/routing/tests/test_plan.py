from datetime import UTC, datetime, timedelta

import pytest

from routing.clients import http, open_meteo, osrm, tomtom
from routing.services import plan
from routing.services.geo import MILES_PER_DEG_LAT
from routing.services.types import LatLon, RawRoute

NOW = datetime(2026, 10, 12, 4, 20, tzinfo=UTC)
START = int(NOW.timestamp()) // 3600 * 3600
A, B = LatLon(30.0, -97.0), LatLon(30.0 + 100 / MILES_PER_DEG_LAT, -97.0)


def route(miles=100, hours=2.0, source="tomtom"):
    return RawRoute(
        coords=[(A.lat, A.lon), (A.lat + miles / MILES_PER_DEG_LAT, A.lon)],
        cum_time_s=[0, hours * 3600],
        distance_mi=miles,
        duration_s=hours * 3600,
        source=source,
    )


def weather(wind=5.0, rain=0.0, snow=0.0, rain_at=None):
    rain_list = [rain] * open_meteo.HOURS
    if rain_at is not None:
        rain_list = rain_at
    return open_meteo.HourlyWeather(
        wind_mph=[wind] * open_meteo.HOURS,
        gust_mph=[wind] * open_meteo.HOURS,
        rain_in=rain_list,
        snow_in=[snow] * open_meteo.HOURS,
    )


@pytest.fixture
def calm(monkeypatch):
    seen = {}

    def fake(cells, start):
        seen["start"] = start
        return {cell: weather() for cell in cells}

    monkeypatch.setattr(open_meteo, "fetch_hourly", fake)
    return seen


def build(**overrides):
    args = {
        "origin": A,
        "destination": B,
        "departure": NOW,
        "load_lb": 20_000,
        "interval_mi": 25,
        "now": NOW,
    }
    return plan.build_plan(**(args | overrides))


def test_calm_plan_shape(monkeypatch, calm):
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: [route(), route(120, 2.5)])
    result = build()

    assert calm["start"] == START
    assert result["warnings"] == ["fewer_routes"]
    best = result["routes"][0]
    assert best["id"] == 0 and best["rank"] == 1 and best["recommended"] is True
    assert best["reason"] == "Shortest travel time"
    assert len(best["checkpoints"]) == 5
    assert best["checkpoints"][0]["level"] == "low"
    assert best["checkpoints"][0]["eta"] == NOW.isoformat()
    assert best["miles_by_level"]["low"] == pytest.approx(100)
    assert best["avg_risk"] == 0
    assert best["geometry"]["coordinates"][0] == [A.lon, A.lat]
    assert result["heatmap"]["start_hour"] == datetime.fromtimestamp(START, UTC).isoformat()
    assert all(len(c["levels"]) == open_meteo.HOURS for c in result["heatmap"]["cells"])


def test_load_rule_changes_level(monkeypatch):
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: [route()])
    monkeypatch.setattr(
        open_meteo, "fetch_hourly", lambda cells, s: {c: weather(wind=50) for c in cells}
    )
    light = build(load_lb=30_000)
    heavy = build(load_lb=30_001)
    assert light["routes"][0]["checkpoints"][0]["level"] == "severe"
    assert heavy["routes"][0]["checkpoints"][0]["level"] == "no_travel"
    assert "no_safe_route" in heavy["warnings"]
    assert heavy["heatmap"]["cells"][0]["levels"][0] == 4


def test_eta_uses_forecast_hour_after_midnight(monkeypatch):
    late = datetime(2026, 10, 12, 23, 30, tzinfo=UTC)
    rain = [0.0] * open_meteo.HOURS
    rain[3] = 0.3
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: [route(100, 2.0)])
    monkeypatch.setattr(
        open_meteo, "fetch_hourly", lambda cells, s: {c: weather(rain_at=rain) for c in cells}
    )
    result = build(departure=late, now=late, interval_mi=50)
    cps = result["routes"][0]["checkpoints"]
    assert cps[-1]["eta"] == (late + timedelta(hours=2)).isoformat()
    assert cps[-1]["level"] == "high"
    assert cps[0]["level"] == "low"


def test_beyond_forecast_is_no_data(monkeypatch, calm):
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: [route(100, 10.0)])
    result = build(departure=NOW + timedelta(hours=45))
    cps = result["routes"][0]["checkpoints"]
    assert cps[0]["level"] == "low"
    assert cps[-1]["level"] is None
    assert result["routes"][0]["miles_by_level"]["no_data"] > 0
    assert "beyond_forecast" in result["warnings"]


def test_null_weather_is_no_data(monkeypatch):
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: [route()])
    rain = [None] * open_meteo.HOURS
    monkeypatch.setattr(
        open_meteo, "fetch_hourly", lambda cells, s: {c: weather(rain_at=rain) for c in cells}
    )
    result = build()
    assert result["routes"][0]["checkpoints"][0]["level"] is None
    assert result["heatmap"]["cells"][0]["levels"][0] == -1


def test_routing_gets_departure_and_load(monkeypatch, calm):
    seen = []
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: seen.append(a) or [route()])
    build(load_lb=42_000)
    assert seen[0][2:] == (NOW, 42_000)


def test_falls_back_to_osrm(monkeypatch, calm):
    def fail(*args):
        raise http.UpstreamError()

    monkeypatch.setattr(tomtom, "fetch_routes", fail)
    monkeypatch.setattr(
        osrm, "fetch_routes", lambda o, d: [route(source="osrm"), route(110, 2.2, "osrm")]
    )
    result = build()
    assert result["warnings"][:2] == ["fallback_routing", "fewer_routes"]
    assert result["routes"][0]["source"] == "osrm"
