import pytest

from routing.services.geo import (
    MILES_PER_DEG_LAT,
    corridor_points,
    cumulative_miles,
    haversine_mi,
    locate,
    snap,
)


def test_haversine_one_degree_latitude():
    assert haversine_mi((0, 0), (1, 0)) == pytest.approx(MILES_PER_DEG_LAT)
    assert MILES_PER_DEG_LAT == pytest.approx(69.09, abs=0.01)


def test_cumulative_miles():
    coords = [(0, 0), (1, 0), (2, 0)]
    assert cumulative_miles(coords) == pytest.approx([0, MILES_PER_DEG_LAT, 2 * MILES_PER_DEG_LAT])


def test_locate_inside_and_at_ends():
    cum = [0, 10, 30]
    assert locate(cum, 0) == (0, 0)
    assert locate(cum, 20) == (1, pytest.approx(0.5))
    assert locate(cum, 30) == (1, pytest.approx(1.0))


def test_snap_to_quarter_degree():
    assert snap(32.76, -96.88) == (32.75, -97.0)
    assert snap(32.874, -96.874) == (32.75, -96.75)


def test_corridor_points_on_north_line():
    end = 30 / MILES_PER_DEG_LAT
    points = corridor_points([(0, 0), (end, 0)], step_mi=10, offset_mi=15)
    assert len(points) == 12
    center, left, right = points[0], points[1], points[2]
    assert center == pytest.approx((0, 0))
    assert left[1] == pytest.approx(-15 / MILES_PER_DEG_LAT)
    assert right[1] == pytest.approx(15 / MILES_PER_DEG_LAT)
