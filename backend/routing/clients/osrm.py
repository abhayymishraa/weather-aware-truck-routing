import itertools

from django.core.cache import cache

from ..services.types import LatLon, RawRoute
from . import http

URL = "https://router.project-osrm.org/route/v1/driving/{a};{b}"
METERS_PER_MILE = 1609.344
CACHE_S = 3600


def fetch_routes(origin: LatLon, destination: LatLon, wanted: int = 3) -> list[RawRoute]:
    url = URL.format(
        a=f"{round(origin.lon, 5)},{round(origin.lat, 5)}",
        b=f"{round(destination.lon, 5)},{round(destination.lat, 5)}",
    )
    params = {
        "alternatives": wanted,
        "overview": "full",
        "geometries": "geojson",
        "annotations": "duration",
    }

    def load() -> dict:
        return http.request_json("GET", url, params=params, bad_request_error=http.NoRouteError)

    data = cache.get_or_set(http.cache_key("osrm", url, params), load, CACHE_S)
    return [
        RawRoute(
            coords=[(lat, lon) for lon, lat in route["geometry"]["coordinates"]],
            cum_time_s=list(
                itertools.accumulate(route["legs"][0]["annotation"]["duration"], initial=0.0)
            ),
            distance_mi=route["distance"] / METERS_PER_MILE,
            duration_s=route["duration"],
            source="osrm",
        )
        for route in data["routes"][:wanted]
    ]
