import bisect
import itertools
import math

EARTH_RADIUS_MI = 3958.7613
MILES_PER_DEG_LAT = 2 * math.pi * EARTH_RADIUS_MI / 360
GRID_DEG = 0.25
METERS_PER_MILE = 1609.344


def haversine_mi(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def cumulative_miles(coords: list[tuple[float, float]]) -> list[float]:
    steps = (haversine_mi(a, b) for a, b in itertools.pairwise(coords))
    return list(itertools.accumulate(steps, initial=0.0))


def locate(cum: list[float], mile: float) -> tuple[int, float]:
    i = min(max(bisect.bisect_right(cum, mile) - 1, 0), len(cum) - 2)
    span = cum[i + 1] - cum[i]
    return i, (mile - cum[i]) / span if span else 0.0


def lerp(a: float, b: float, f: float) -> float:
    return a + (b - a) * f


def corridor_points(
    coords: list[tuple[float, float]], step_mi: float = 10, offset_mi: float = 15
) -> list[tuple[float, float]]:
    cum = cumulative_miles(coords)
    points = []
    for k in range(int(cum[-1] // step_mi) + 1):
        i, f = locate(cum, k * step_mi)
        (lat1, lon1), (lat2, lon2) = coords[i], coords[i + 1]
        lat, lon = lerp(lat1, lat2, f), lerp(lon1, lon2, f)
        points.append((lat, lon))
        cos_lat = math.cos(math.radians(lat))
        east, north = (lon2 - lon1) * cos_lat, lat2 - lat1
        norm = math.hypot(east, north)
        if not norm or not cos_lat:
            continue
        d_north = east / norm * offset_mi / MILES_PER_DEG_LAT
        d_east = -north / norm * offset_mi / MILES_PER_DEG_LAT / cos_lat
        points.append((lat + d_north, lon + d_east))
        points.append((lat - d_north, lon - d_east))
    return points


def snap(lat: float, lon: float) -> tuple[float, float]:
    return round(lat / GRID_DEG) * GRID_DEG, round(lon / GRID_DEG) * GRID_DEG
