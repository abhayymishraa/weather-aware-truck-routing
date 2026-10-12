from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from routing.clients import photon
from routing.clients.http import UpstreamError
from routing.services import plan as plan_service


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


def plan_body(**overrides):
    body = {
        "origin": {"lat": 32.78, "lon": -96.8, "label": "Dallas, Texas"},
        "destination": {"lat": 39.74, "lon": -104.99, "label": "Denver, Colorado"},
        "departure": (timezone.now() + timedelta(hours=1)).isoformat(),
        "load_lb": 35_000,
        "interval_mi": 25,
    }
    return body | overrides


def test_plan_calls_service(monkeypatch):
    seen = {}

    def fake(**kwargs):
        seen.update(kwargs)
        return {"routes": [], "heatmap": {"start_hour": "x", "cells": []}, "warnings": []}

    monkeypatch.setattr(plan_service, "build_plan", fake)
    response = APIClient().post("/api/plan", plan_body(), format="json")
    assert response.status_code == 200
    assert seen["load_lb"] == 35_000
    assert seen["interval_mi"] == 25
    assert seen["origin"].lat == 32.78


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"load_lb": 0}, "load_lb"),
        ({"load_lb": 80_001}, "load_lb"),
        ({"interval_mi": 30}, "interval_mi"),
        ({"departure": (timezone.now() + timedelta(hours=49)).isoformat()}, "departure"),
        ({"departure": (timezone.now() - timedelta(hours=1)).isoformat()}, "departure"),
        ({"destination": {"lat": 32.78, "lon": -96.8}}, "non_field_errors"),
    ],
)
def test_plan_validation(override, field):
    response = APIClient().post("/api/plan", plan_body(**override), format="json")
    assert response.status_code == 400
    assert field in response.json()["errors"]


def test_plan_upstream_error_shape(monkeypatch):
    def fail(**kwargs):
        raise UpstreamError()

    monkeypatch.setattr(plan_service, "build_plan", fail)
    response = APIClient().post("/api/plan", plan_body(), format="json")
    assert response.status_code == 502
    assert response.json() == {
        "detail": "An outside service did not respond. Try again.",
        "code": "upstream_error",
    }


@pytest.mark.parametrize(
    ("override", "detail"),
    [
        (
            {"destination": {"lat": 32.78, "lon": -96.8}},
            "Origin and destination must be different places.",
        ),
        (
            {"departure": (timezone.now() + timedelta(hours=49)).isoformat()},
            "Departure must be within the next 48 hours.",
        ),
    ],
)
def test_plan_validation_detail_is_readable(override, detail):
    response = APIClient().post("/api/plan", plan_body(**override), format="json")
    assert response.json()["detail"] == detail
