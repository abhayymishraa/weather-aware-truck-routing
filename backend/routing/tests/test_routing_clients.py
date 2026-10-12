from datetime import UTC, datetime, timedelta

import pytest

from routing.clients import http, osrm, tomtom
from routing.services.types import LatLon

A = LatLon(0.0, 0.0)
B = LatLon(0.2, 0.0)
NOW = datetime(2026, 10, 12, 4, 20, tzinfo=UTC)


def tomtom_route(points, meters=22_530, seconds=1200, progress=None):
    return {
        "summary": {"lengthInMeters": meters, "travelTimeInSeconds": seconds},
        "legs": [{"points": [{"latitude": lat, "longitude": lon} for lat, lon in points]}],
        "progress": progress
        or [
            {"pointIndex": 0, "travelTimeInSeconds": 0},
            {"pointIndex": len(points) - 1, "travelTimeInSeconds": seconds},
        ],
    }


@pytest.fixture(autouse=True)
def tomtom_key(settings):
    settings.TOMTOM_API_KEY = "test-key"


@pytest.fixture
def clock(monkeypatch):
    monkeypatch.setattr(tomtom.timezone, "now", lambda: NOW)


def test_tomtom_request_and_parse(monkeypatch, clock):
    seen = {}

    def fake(method, url, **kwargs):
        seen["url"] = url
        seen["params"] = kwargs["params"]
        return {
            "routes": [
                tomtom_route([(0, 0), (0.1, 0), (0.2, 0)]),
                tomtom_route([(0, 0), (0.1, 0.1), (0.2, 0)], 25_000, 1500),
            ]
        }

    monkeypatch.setattr(http, "request_json", fake)
    routes = tomtom.fetch_routes(A, B, NOW + timedelta(hours=1), load_lb=40_000)

    assert seen["url"].endswith("/calculateRoute/0.0,0.0:0.2,0.0/json")
    params = seen["params"]
    assert params["key"] == "test-key"
    assert params["travelMode"] == "truck"
    assert params["vehicleCommercial"] == "true"
    assert params["vehicleWeight"] == 34_019
    assert params["maxAlternatives"] == 2
    assert params["departAt"] == "2026-10-12T05:20:00+00:00"
    assert params["extendedRouteRepresentation"] == "travelTime"
    assert len(routes) == 2
    route = routes[0]
    assert route.coords == [(0, 0), (0.1, 0), (0.2, 0)]
    assert route.cum_time_s == pytest.approx([0, 600, 1200])
    assert route.distance_mi == pytest.approx(14.0, abs=0.01)
    assert route.duration_s == 1200
    assert route.source == "tomtom"


def test_tomtom_progress_keeps_uneven_speed(monkeypatch, clock):
    progress = [
        {"pointIndex": 0, "travelTimeInSeconds": 0},
        {"pointIndex": 1, "travelTimeInSeconds": 900},
        {"pointIndex": 2, "travelTimeInSeconds": 1200},
    ]
    route = tomtom_route([(0, 0), (0.1, 0), (0.2, 0)], progress=progress)
    monkeypatch.setattr(http, "request_json", lambda *a, **k: {"routes": [route]})
    assert tomtom.fetch_routes(A, B, NOW, 1)[0].cum_time_s == [0, 900, 1200]


def test_tomtom_past_departure_uses_now(monkeypatch, clock):
    seen = {}

    def fake(method, url, **kwargs):
        seen.update(kwargs["params"])
        return {"routes": [tomtom_route([(0, 0), (0.2, 0)])]}

    monkeypatch.setattr(http, "request_json", fake)
    tomtom.fetch_routes(A, B, NOW - timedelta(minutes=5), 1)
    assert seen["departAt"] == "now"


def test_tomtom_without_key_is_upstream_error(monkeypatch, settings):
    settings.TOMTOM_API_KEY = ""
    monkeypatch.setattr(http, "request_json", lambda *a, **k: pytest.fail("no request"))
    with pytest.raises(http.UpstreamError):
        tomtom.fetch_routes(A, B, NOW, 1)


def test_tomtom_routes_are_cached_without_the_key(monkeypatch, clock):
    calls = []

    def fake(method, url, **kwargs):
        calls.append(kwargs["params"])
        return {"routes": [tomtom_route([(0, 0), (0.2, 0)])]}

    monkeypatch.setattr(http, "request_json", fake)
    tomtom.fetch_routes(A, B, NOW, 1)
    tomtom.fetch_routes(A, B, NOW, 1)
    assert len(calls) == 1


def test_osrm_parses_routes(monkeypatch):
    seen = {}

    def fake(method, url, **kwargs):
        seen["url"] = url
        seen["kwargs"] = kwargs
        return {
            "routes": [
                {
                    "distance": 22_530.0,
                    "duration": 1200.0,
                    "geometry": {"coordinates": [[0, 0], [0, 0.1], [0, 0.2]]},
                    "legs": [{"annotation": {"duration": [500.0, 700.0]}}],
                }
            ]
        }

    monkeypatch.setattr(http, "request_json", fake)
    routes = osrm.fetch_routes(A, B)

    assert seen["url"].endswith("/route/v1/driving/0.0,0.0;0.0,0.2")
    assert seen["kwargs"]["bad_request_error"] is http.NoRouteError
    route = routes[0]
    assert route.coords == [(0, 0), (0.1, 0), (0.2, 0)]
    assert route.cum_time_s == [0.0, 500.0, 1200.0]
    assert route.distance_mi == pytest.approx(14.0, abs=0.01)
    assert route.source == "osrm"
