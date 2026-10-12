from dataclasses import dataclass


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


@dataclass(frozen=True)
class RawRoute:
    coords: list[tuple[float, float]]
    cum_time_s: list[float]
    distance_mi: float
    duration_s: float
    source: str
