from rest_framework.test import APIClient

from routing.clients import photon


def test_health():
    response = APIClient().get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_geocode(monkeypatch):
    monkeypatch.setattr(photon, "search", lambda q: [{"label": q, "lat": 1.0, "lon": 2.0}])
    response = APIClient().get("/api/geocode", {"q": "Dallas"})
    assert response.status_code == 200
    assert response.json() == {"results": [{"label": "Dallas", "lat": 1.0, "lon": 2.0}]}


def test_geocode_requires_query():
    response = APIClient().get("/api/geocode", {"q": "a"})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "invalid"
    assert "q" in body["errors"]
