from routing.clients import http, photon


def feature(name=None, lat=32.7, lon=-96.8, state="Texas", cc="US", **props):
    return {
        "geometry": {"coordinates": [lon, lat]},
        "properties": {"name": name, "state": state, "countrycode": cc, **props},
    }


def test_search_builds_labels_and_filters_us(monkeypatch):
    seen = {}

    def fake(method, url, **kwargs):
        seen.update(kwargs["params"])
        return {
            "features": [
                feature("Dallas", city="Dallas"),
                feature("Dallas", cc="CA"),
                feature(
                    None,
                    housenumber="1600",
                    street="Pennsylvania Ave",
                    city="Washington",
                    state="District of Columbia",
                    lat=38.9,
                    lon=-77.0,
                ),
            ]
        }

    monkeypatch.setattr(http, "request_json", fake)
    results = photon.search("dallas")

    assert seen["q"] == "dallas"
    assert seen["bbox"] == photon.US_BBOX
    assert results == [
        {"label": "Dallas, Texas", "lat": 32.7, "lon": -96.8},
        {
            "label": "1600 Pennsylvania Ave, Washington, District of Columbia",
            "lat": 38.9,
            "lon": -77.0,
        },
    ]


def test_search_dedupes_labels(monkeypatch):
    monkeypatch.setattr(
        http, "request_json", lambda *a, **k: {"features": [feature("Laredo"), feature("Laredo")]}
    )
    assert len(photon.search("laredo")) == 1
