import itertools
from dataclasses import dataclass

from .geo import cumulative_miles, lerp, locate


@dataclass(frozen=True)
class Checkpoint:
    mile: float
    lat: float
    lon: float
    offset_s: float
    segment_mi: float


def sample_checkpoints(
    coords: list[tuple[float, float]], cum_time_s: list[float], interval_mi: float
) -> list[Checkpoint]:
    cum = cumulative_miles(coords)
    total = cum[-1]
    marks = [k * interval_mi for k in range(int(total // interval_mi) + 1)]
    if total - marks[-1] > 0.01:
        marks.append(total)
    else:
        marks[-1] = total
    bounds = [0.0, *((a + b) / 2 for a, b in itertools.pairwise(marks)), total]

    checkpoints = []
    for n, mile in enumerate(marks):
        i, f = locate(cum, mile)
        (lat1, lon1), (lat2, lon2) = coords[i], coords[i + 1]
        checkpoints.append(
            Checkpoint(
                mile=mile,
                lat=lerp(lat1, lat2, f),
                lon=lerp(lon1, lon2, f),
                offset_s=lerp(cum_time_s[i], cum_time_s[i + 1], f),
                segment_mi=bounds[n + 1] - bounds[n],
            )
        )
    return checkpoints
