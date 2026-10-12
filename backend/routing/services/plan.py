import math
from datetime import UTC, datetime

from ..clients import open_meteo, osrm, tomtom
from ..clients.http import UpstreamError
from .checkpoints import sample_checkpoints
from .geo import corridor_points, snap
from .risk import (
    LEVEL_NAMES,
    Level,
    RouteScore,
    Segment,
    avg_risk,
    checkpoint_level,
    miles_by_level,
    rank_routes,
)
from .types import LatLon, RawRoute

WANTED_ROUTES = 3


def build_plan(
    origin: LatLon,
    destination: LatLon,
    departure: datetime,
    load_lb: int,
    interval_mi: int,
    now: datetime,
) -> dict:
    warnings: list[str] = []
    try:
        raws = tomtom.fetch_routes(origin, destination, departure, load_lb)
    except UpstreamError:
        raws = osrm.fetch_routes(origin, destination)
        warnings.append("fallback_routing")
    if len(raws) < WANTED_ROUTES:
        warnings.append("fewer_routes")

    start = int(now.timestamp()) // 3600 * 3600
    sampled = [sample_checkpoints(r.coords, r.cum_time_s, interval_mi) for r in raws]
    corridor = {snap(*p) for r in raws for p in corridor_points(r.coords)}
    checkpoint_cells = {snap(c.lat, c.lon) for cps in sampled for c in cps}
    weather = open_meteo.fetch_hourly(sorted(corridor | checkpoint_cells), start)

    routes = []
    beyond = False
    for route_id, (raw, cps) in enumerate(zip(raws, sampled)):
        out, segments = [], []
        for c in cps:
            eta = departure.timestamp() + c.offset_s
            hour = math.floor((eta - start) / 3600 + 0.5)
            values = (None, None, None, None)
            if 0 <= hour < open_meteo.HOURS:
                values = weather[snap(c.lat, c.lon)].at(hour)
            else:
                beyond = True
            level = _level(values, load_lb)
            segments.append(Segment(level, c.segment_mi))
            wind, gust, rain, snow = values
            out.append(
                {
                    "mile": round(c.mile, 1),
                    "lat": round(c.lat, 5),
                    "lon": round(c.lon, 5),
                    "eta": datetime.fromtimestamp(eta, UTC).isoformat(),
                    "wind_mph": wind,
                    "gust_mph": gust,
                    "rain_in_hr": rain,
                    "snow_in_hr": snow,
                    "level": None if level is None else LEVEL_NAMES[level],
                    "segment_mi": round(c.segment_mi, 2),
                }
            )
        routes.append(_route_payload(route_id, raw, out, segments))

    ranked = rank_routes(
        [RouteScore(r["id"], r["miles_by_level"], r["avg_risk"], r["duration_s"]) for r in routes]
    )
    by_id = {r["id"]: r for r in routes}
    ordered = []
    for item in ranked:
        route = by_id[item.id]
        route.update(rank=item.rank, recommended=item.rank == 1, reason=item.reason)
        ordered.append(route)

    if beyond:
        warnings.append("beyond_forecast")
    if all(r["miles_by_level"]["no_travel"] > 0 for r in ordered):
        warnings.append("no_safe_route")

    cells = [
        {
            "lat": lat,
            "lon": lon,
            "levels": [
                _score(_level(weather[(lat, lon)].at(h), load_lb)) for h in range(open_meteo.HOURS)
            ],
        }
        for lat, lon in sorted(corridor)
    ]
    return {
        "routes": ordered,
        "heatmap": {"start_hour": datetime.fromtimestamp(start, UTC).isoformat(), "cells": cells},
        "warnings": warnings,
    }


def _level(values: tuple, load_lb: int) -> Level | None:
    wind, _gust, rain, snow = values
    if wind is None or rain is None or snow is None:
        return None
    return checkpoint_level(wind, rain, snow, load_lb)


def _score(level: Level | None) -> int:
    return -1 if level is None else int(level)


def _route_payload(route_id: int, raw: RawRoute, checkpoints: list, segments: list) -> dict:
    return {
        "id": route_id,
        "geometry": {
            "type": "LineString",
            "coordinates": [[round(lon, 5), round(lat, 5)] for lat, lon in raw.coords],
        },
        "distance_mi": round(raw.distance_mi, 1),
        "duration_s": round(raw.duration_s),
        "source": raw.source,
        "checkpoints": checkpoints,
        "miles_by_level": {k: round(v, 1) for k, v in miles_by_level(segments).items()},
        "avg_risk": None if (a := avg_risk(segments)) is None else round(a, 3),
    }
