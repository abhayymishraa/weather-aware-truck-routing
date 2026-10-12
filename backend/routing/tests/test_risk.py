import pytest

from routing.services.risk import (
    Level,
    Segment,
    avg_risk,
    checkpoint_level,
    miles_by_level,
    rain_level,
    snow_level,
    wind_level,
)


@pytest.mark.parametrize(
    ("mph", "expected"),
    [
        (0, Level.LOW),
        (24.9, Level.LOW),
        (25, Level.MODERATE),
        (34.5, Level.MODERATE),
        (35, Level.HIGH),
        (44.9, Level.HIGH),
        (45, Level.SEVERE),
        (54.9, Level.SEVERE),
        (55, Level.NO_TRAVEL),
        (90, Level.NO_TRAVEL),
    ],
)
def test_wind_level(mph, expected):
    assert wind_level(mph) == expected


@pytest.mark.parametrize(
    ("in_hr", "expected"),
    [
        (0, Level.LOW),
        (0.09, Level.LOW),
        (0.10, Level.MODERATE),
        (0.249, Level.MODERATE),
        (0.25, Level.HIGH),
        (0.49, Level.HIGH),
        (0.50, Level.SEVERE),
        (1.00, Level.SEVERE),
        (1.01, Level.NO_TRAVEL),
    ],
)
def test_rain_level(in_hr, expected):
    assert rain_level(in_hr) == expected


@pytest.mark.parametrize(
    ("in_hr", "expected"),
    [
        (0, Level.LOW),
        (0.49, Level.LOW),
        (0.5, Level.MODERATE),
        (0.99, Level.MODERATE),
        (1.0, Level.HIGH),
        (1.99, Level.HIGH),
        (2.0, Level.SEVERE),
        (3.0, Level.SEVERE),
        (3.01, Level.NO_TRAVEL),
    ],
)
def test_snow_level(in_hr, expected):
    assert snow_level(in_hr) == expected


@pytest.mark.parametrize(
    ("wind", "rain", "snow", "load", "expected"),
    [
        (10, 0.3, 0, 1_000, Level.HIGH),
        (10, 0, 2.5, 1_000, Level.SEVERE),
        (50, 0, 0, 30_000, Level.SEVERE),
        (50, 0, 0, 30_001, Level.NO_TRAVEL),
        (45, 0, 0, 30_001, Level.NO_TRAVEL),
        (40, 0, 0, 40_000, Level.HIGH),
        (40, 0, 0, 40_001, Level.SEVERE),
        (35, 0, 0, 40_001, Level.SEVERE),
        (44.9, 0, 0, 80_000, Level.SEVERE),
        (55, 0, 0, 1, Level.NO_TRAVEL),
        (40, 1.5, 0, 50_000, Level.NO_TRAVEL),
        (30, 0, 0, 80_000, Level.MODERATE),
    ],
)
def test_checkpoint_level(wind, rain, snow, load, expected):
    assert checkpoint_level(wind, rain, snow, load) == expected


def test_miles_by_level_and_avg_risk():
    segments = [
        Segment(Level.LOW, 10),
        Segment(Level.SEVERE, 20),
        Segment(None, 5),
        Segment(Level.HIGH, 10),
    ]
    assert miles_by_level(segments) == {
        "low": 10,
        "moderate": 0,
        "high": 10,
        "severe": 20,
        "no_travel": 0,
        "no_data": 5,
    }
    assert avg_risk(segments) == pytest.approx(2.0)


def test_avg_risk_without_data_is_none():
    assert avg_risk([Segment(None, 10)]) is None
