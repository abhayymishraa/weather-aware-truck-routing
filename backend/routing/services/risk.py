import math
from collections.abc import Iterable
from dataclasses import dataclass
from enum import IntEnum


class Level(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


LEVEL_NAMES = {
    Level.LOW: "low",
    Level.MODERATE: "moderate",
    Level.HIGH: "high",
    Level.SEVERE: "severe",
    Level.NO_TRAVEL: "no_travel",
}


def _band(value: float, moderate: float, high: float, severe: float) -> Level:
    if value >= severe:
        return Level.SEVERE
    if value >= high:
        return Level.HIGH
    if value >= moderate:
        return Level.MODERATE
    return Level.LOW


def wind_level(mph: float) -> Level:
    return Level.NO_TRAVEL if mph >= 55 else _band(mph, 25, 35, 45)


def rain_level(in_hr: float) -> Level:
    return Level.NO_TRAVEL if in_hr > 1.0 else _band(in_hr, 0.10, 0.25, 0.50)


def snow_level(in_hr: float) -> Level:
    return Level.NO_TRAVEL if in_hr > 3.0 else _band(in_hr, 0.5, 1.0, 2.0)


def checkpoint_level(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_lb: int) -> Level:
    level = max(wind_level(wind_mph), rain_level(rain_in_hr), snow_level(snow_in_hr))
    if 45 <= wind_mph < 55 and load_lb > 30_000:
        level = max(level, Level.NO_TRAVEL)
    elif 35 <= wind_mph < 45 and load_lb > 40_000:
        level = max(level, Level.SEVERE)
    return level


@dataclass(frozen=True)
class Segment:
    level: Level | None
    miles: float


def miles_by_level(segments: Iterable[Segment]) -> dict[str, float]:
    totals = {name: 0.0 for name in LEVEL_NAMES.values()} | {"no_data": 0.0}
    for segment in segments:
        key = "no_data" if segment.level is None else LEVEL_NAMES[segment.level]
        totals[key] += segment.miles
    return totals


def avg_risk(segments: Iterable[Segment]) -> float | None:
    scored = [s for s in segments if s.level is not None]
    total_miles = sum(s.miles for s in scored)
    if not total_miles:
        return None
    return sum(int(s.level) * s.miles for s in scored) / total_miles


@dataclass(frozen=True)
class RouteScore:
    id: int
    miles: dict[str, float]
    avg_risk: float | None
    duration_s: float


@dataclass(frozen=True)
class RankedRoute:
    id: int
    rank: int
    reason: str


WIN_REASONS = (
    "Fewest No Travel miles",
    "Fewest Severe miles",
    "Fewest High miles",
    "Lowest average risk",
    "Shortest travel time",
)
LOSE_REASONS = (
    "More No Travel miles",
    "More Severe miles",
    "More High miles",
    "Higher average risk",
    "Longer travel time",
)


def _key(score: RouteScore) -> tuple[float, ...]:
    return (
        round(score.miles["no_travel"], 1),
        round(score.miles["severe"], 1),
        round(score.miles["high"], 1),
        math.inf if score.avg_risk is None else round(score.avg_risk, 3),
        round(score.duration_s),
    )


def _first_difference(a: tuple, b: tuple) -> int | None:
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)


def rank_routes(scores: list[RouteScore]) -> list[RankedRoute]:
    ordered = sorted(scores, key=_key)
    best_key = _key(ordered[0])
    ranked = []
    for rank, score in enumerate(ordered, start=1):
        if rank == 1:
            if len(ordered) == 1:
                reason = "Only route found"
            else:
                i = _first_difference(best_key, _key(ordered[1]))
                reason = (
                    "Tied with the other routes on risk and time" if i is None else WIN_REASONS[i]
                )
        else:
            i = _first_difference(_key(score), best_key)
            reason = "Same risk and time as the recommended route" if i is None else LOSE_REASONS[i]
        ranked.append(RankedRoute(score.id, rank, reason))
    return ranked
