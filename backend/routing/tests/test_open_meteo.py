import pytest

from routing.clients import http, open_meteo

START = 1_791_777_600


def location(wind, rain, showers, snow):
    hours = open_meteo.HOURS
    return {
        "hourly": {
            "time": [START + 3600 * i for i in range(hours)],
            "wind_speed_10m": [wind] * hours,
            "wind_gusts_10m": [wind + 10] * hours,
            "rain": [rain] * hours,
            "showers": [showers] * hours,
            "snowfall": [snow] * hours,
        }
    }


def test_fetch_maps_cells_and_sums_rain(monkeypatch):
    seen = {}

    def fake(method, url, **kwargs):
        seen.update(kwargs["params"])
        return [location(10, 0.1, 0.05, 0), location(40, 0, 0, 1.2)]

    monkeypatch.setattr(http, "request_json", fake)
    result = open_meteo.fetch_hourly([(32.75, -97.0), (33.0, -97.0)], START)

    assert seen["latitude"] == "32.75,33.0"
    assert seen["longitude"] == "-97.0,-97.0"
    assert seen["wind_speed_unit"] == "mph"
    assert seen["precipitation_unit"] == "inch"
    assert seen["start_hour"] == "2026-10-12T04:00"
    assert seen["end_hour"] == "2026-10-14T03:00"
    wind, gust, rain, snow = result[(32.75, -97.0)].at(0)
    assert (wind, gust, snow) == (10, 20, 0)
    assert rain == pytest.approx(0.15)
    assert result[(33.0, -97.0)].at(47)[3] == 1.2


def test_single_location_response_is_a_dict(monkeypatch):
    monkeypatch.setattr(http, "request_json", lambda *a, **k: location(5, 0, 0, 0))
    result = open_meteo.fetch_hourly([(32.75, -97.0)], START)
    assert result[(32.75, -97.0)].at(3)[0] == 5


def test_null_values_stay_none(monkeypatch):
    data = location(5, 0, 0, 0)
    data["hourly"]["rain"][2] = None
    monkeypatch.setattr(http, "request_json", lambda *a, **k: data)
    result = open_meteo.fetch_hourly([(32.75, -97.0)], START)
    assert result[(32.75, -97.0)].at(2)[2] is None


def test_batches_and_cache(monkeypatch):
    calls = []

    def fake(method, url, **kwargs):
        count = len(kwargs["params"]["latitude"].split(","))
        calls.append(count)
        result = [location(5, 0, 0, 0) for _ in range(count)]
        return result if count > 1 else result[0]

    monkeypatch.setattr(http, "request_json", fake)
    monkeypatch.setattr(open_meteo, "BATCH", 2)
    cells = [(30.0, -97.0), (30.25, -97.0), (30.5, -97.0)]
    open_meteo.fetch_hourly(cells, START)
    assert calls == [2, 1]
    open_meteo.fetch_hourly(cells, START)
    assert calls == [2, 1]
