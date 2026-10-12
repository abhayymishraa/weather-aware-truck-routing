import bisect
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from ..services.geo import cumulative_miles, lerp
from ..services.types import LatLon, RawRoute
from . import http

URL = "https://api.tomtom.com/routing/1/calculateRoute/{a}:{b}/json"
CACHE_S = 3600
METERS_PER_MILE = 1609.344
KG_PER_LB = 0.45359237
# ponytail: typical empty tractor-trailer; vehicleWeight is gross weight. Add a form field if users need it.
EMPTY_TRUCK_LB = 35_000


def fetch_routes(
    origin: LatLon, destination: LatLon, departure: datetime, load_lb: int, wanted: int = 3
) -> list[RawRoute]:
    if not settings.TOMTOM_API_KEY:
        raise http.UpstreamError()
    url = URL.format(
        a=f"{round(origin.lat, 5)},{round(origin.lon, 5)}",
        b=f"{round(destination.lat, 5)},{round(destination.lon, 5)}",
    )
    params = {
        "travelMode": "truck",
        "vehicleCommercial": "true",
        "vehicleWeight": round((load_lb + EMPTY_TRUCK_LB) * KG_PER_LB),
        "maxAlternatives": wanted - 1,
        "departAt": departure.isoformat(timespec="seconds")
        if departure > timezone.now()
        else "now",
        "routeRepresentation": "polyline",
        "extendedRouteRepresentation": "travelTime",
    }

    def load() -> list[RawRoute]:
        data = http.request_json("GET", url, params={"key": settings.TOMTOM_API_KEY, **params})
        return [_parse(route) for route in data["routes"][:wanted]]

    return cache.get_or_set(http.cache_key("tomtom", url, params), load, CACHE_S)


def _parse(route: dict) -> RawRoute:
    coords = [(p["latitude"], p["longitude"]) for p in route["legs"][0]["points"]]
    cum = cumulative_miles(coords)
    known = sorted((p["pointIndex"], p["travelTimeInSeconds"]) for p in route["progress"])
    indexes = [i for i, _ in known]
    cum_time = []
    for i in range(len(coords)):
        k = min(max(bisect.bisect_right(indexes, i) - 1, 0), len(known) - 2)
        (i0, t0), (i1, t1) = known[k], known[k + 1]
        span = cum[i1] - cum[i0]
        cum_time.append(lerp(t0, t1, (cum[i] - cum[i0]) / span if span else 0.0))
    return RawRoute(
        coords=coords,
        cum_time_s=cum_time,
        distance_mi=route["summary"]["lengthInMeters"] / METERS_PER_MILE,
        duration_s=route["summary"]["travelTimeInSeconds"],
        source="tomtom",
    )
