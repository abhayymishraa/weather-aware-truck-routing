import pytest

from routing.services.checkpoints import sample_checkpoints
from routing.services.geo import MILES_PER_DEG_LAT


def line(miles):
    return [(0.0, 0.0), (miles / MILES_PER_DEG_LAT, 0.0)]


def test_interval_25_on_100_miles():
    cps = sample_checkpoints(line(100), [0, 7200], 25)
    assert [c.mile for c in cps] == pytest.approx([0, 25, 50, 75, 100])
    assert [c.offset_s for c in cps] == pytest.approx([0, 1800, 3600, 5400, 7200])
    assert [c.segment_mi for c in cps] == pytest.approx([12.5, 25, 25, 25, 12.5])


def test_short_last_segment():
    cps = sample_checkpoints(line(100), [0, 7200], 30)
    assert [c.mile for c in cps] == pytest.approx([0, 30, 60, 90, 100])
    assert [c.segment_mi for c in cps] == pytest.approx([15, 30, 30, 20, 5])
    assert sum(c.segment_mi for c in cps) == pytest.approx(100)


def test_trip_shorter_than_interval():
    cps = sample_checkpoints(line(5), [0, 600], 10)
    assert [c.mile for c in cps] == pytest.approx([0, 5])
    assert [c.segment_mi for c in cps] == pytest.approx([2.5, 2.5])


def test_eta_follows_uneven_speed():
    mid = 50 / MILES_PER_DEG_LAT
    coords = [(0.0, 0.0), (mid, 0.0), (2 * mid, 0.0)]
    cps = sample_checkpoints(coords, [0, 3600, 5400], 25)
    assert cps[3].mile == pytest.approx(75)
    assert cps[3].offset_s == pytest.approx(4500)


def test_checkpoint_position():
    cps = sample_checkpoints(line(100), [0, 7200], 50)
    assert cps[1].lat == pytest.approx(50 / MILES_PER_DEG_LAT)
    assert cps[1].lon == pytest.approx(0)
