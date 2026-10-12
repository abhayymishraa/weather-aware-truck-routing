# Weather-Aware Truck Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A React + Django app that gives a truck driver 3 routes, scores the weather risk at each checkpoint ETA with the PDF rules, recommends the safest route, and shows a 0–48 h corridor risk heatmap.

**Architecture:** One Django app (`routing`) with pure domain functions (`risk.py`, `checkpoints.py`, `geo.py`), one client module per outside API, and one orchestrating service behind `POST /api/plan`. The React app (feature folders) renders one plan response on a MapLibre map. The forecast slider changes a MapLibre paint property and does not re-render React.

**Tech Stack:** Python, Django, DRF, httpx, polyline, Redis, pytest. React, TypeScript, Vite, MUI, Tailwind CSS v4, TanStack React Query, react-map-gl (MapLibre), Vitest, Playwright. Docker Compose, Caddy, Oracle Cloud VM.

**Spec:** `docs/superpowers/specs/2026-10-12-weather-aware-truck-routing-design.md`

## Global Constraints

- Install the latest stable version of every dependency at install time. No beta, RC, or canary. Commit the lock files (`uv.lock`, `package-lock.json`).
- If a library has the function, use it. Follow the official docs and quickstarts. Check an API with Context7 before first use.
- No unnecessary comments. No mention of outside repos that inspired the logic.
- Commits: conventional commit messages, the user's own git identity, no AI attribution lines of any kind.
- Risk thresholds and load rules exactly as spec section 5.
- Routing: TomTom Calculate Route `https://api.tomtom.com/routing/1/calculateRoute` (free tier, 20K requests/month, no credit card). The key is `TOMTOM_API_KEY` in the backend env only. Never send it to the browser, log it, or commit it.
- Outside APIs with no keys: OSRM (routing fallback) `https://router.project-osrm.org`, Open-Meteo `https://api.open-meteo.com/v1/forecast`, Photon `https://photon.komoot.io/api/`.
- Error response shape: `{"detail": str, "code": str}` (validation errors add `"errors"`).
- UI: desktop, tablet, and mobile, in portrait and landscape. Touch targets ≥ 44 px. `dvh` units. Light and dark mode. MUI primary `#063D4B`.

## Spec adjustments found during planning

Verified with live API calls on 2026-10-12. These refine the approved spec:

1. **Routing provider:** TomTom truck routing replaces Valhalla. Valhalla's public server often returned 0 alternates for short trips and rejected trips over 1,500 km. TomTom gives up to 5 alternatives in one request (`maxAlternatives`), uses the load weight and the departure time, and returns the travel time at route points (`progress`).
2. **Fallback:** any TomTom failure (no key, 400, 403 bad key, 429 quota, timeout) triggers the OSRM car fallback. An OSRM 400 (`NoRoute`) is a real "no route".
3. **Segment ownership:** each checkpoint owns the miles from the midpoint with the previous checkpoint to the midpoint with the next. The origin and destination checkpoints then count, and the miles still sum to the route length.
4. **Selected route on the map:** a filter on a separate "selected" line layer, not `feature-state`. A filter also draws the selected route on top.
5. **Deploy:** the Caddy image serves the frontend build, so Compose has 3 services (`backend`, `redis`, `web`).

## Review Focus

1. **A trip that crosses midnight or time zones:** ETAs and forecast hours must use UTC epoch math. Test: a departure at 23:30 UTC with a 2 h trip maps to the forecast hours of the next day (Task 7).
2. **A departure near the end of the 48 h window:** later checkpoints become No Data and do not count in the ranking, and the `beyond_forecast` warning shows (Task 7).
3. **A short trip (shorter than one interval):** it still gets an origin and a destination checkpoint, and both own half the miles (Task 3).
4. **Open-Meteo returns `null` for a value:** that checkpoint becomes No Data, not Low (Task 7).
5. **Two routes with equal risk and time:** the order is stable (router order) and the reason text says they are tied (Task 2).

## File map

```
backend/
  pyproject.toml, uv.lock, manage.py, Dockerfile, conftest.py
  config/__init__.py, urls.py, wsgi.py
  config/settings/__init__.py, base.py, local.py, production.py
  routing/__init__.py, urls.py, apis.py, serializers.py
  routing/services/__init__.py, types.py, geo.py, risk.py, checkpoints.py, plan.py
  routing/clients/__init__.py, http.py, tomtom.py, osrm.py, open_meteo.py, photon.py
  routing/tests/__init__.py, test_risk.py, test_ranking.py, test_checkpoints.py, test_geo.py,
                test_routing_clients.py, test_open_meteo.py, test_photon.py, test_plan.py, test_apis.py
frontend/
  package.json, package-lock.json, vite.config.ts, tsconfig*.json, index.html, Dockerfile, playwright.config.ts
  src/main.tsx, src/index.css, src/vite-env.d.ts
  src/app/App.tsx, src/app/providers.tsx, src/app/AppShell.tsx
  src/config/constants.ts
  src/lib/api.ts, src/lib/query-client.ts
  src/theme/theme.ts, src/theme/risk.ts, src/theme/risk.test.ts
  src/types/plan.ts
  src/utils/format.ts, src/utils/format.test.ts
  src/components/WarningBanner.tsx
  src/features/trip-form/api/geocode.ts
  src/features/trip-form/components/TripForm.tsx, PlaceField.tsx
  src/features/routes/api/plan.ts
  src/features/routes/components/RouteCards.tsx, RouteCard.tsx, RouteCard.test.tsx, RiskBar.tsx
  src/features/map/components/RouteMap.tsx, CheckpointPopup.tsx
  src/features/map/utils/to-geojson.ts
  src/features/weather-heatmap/components/HeatmapLayer.tsx, ForecastSlider.tsx, RiskLegend.tsx
  src/features/weather-heatmap/utils/heat.ts, heat.test.ts
  src/test/setup.ts
  e2e/plan.spec.ts
docker-compose.yml, Caddyfile, .env.example, .gitignore, README.md
```

---

## Phase 1: Backend (skills: superpowers:test-driven-development, context7-mcp, karpathy-guidelines)

### Task 1: Backend scaffold and health endpoint

**Files:**
- Create: `backend/pyproject.toml`, `backend/manage.py`, `backend/conftest.py`, `backend/config/**`, `backend/routing/__init__.py`, `backend/routing/urls.py`, `backend/routing/apis.py`, `backend/routing/tests/__init__.py`, `backend/routing/tests/test_apis.py`, `.gitignore`

**Interfaces:**
- Produces: `GET /api/health` → `{"status": "ok"}`. Settings module `config.settings.local` (dev, tests) and `config.settings.production`. `routing.apis.exception_handler`.

- [ ] **Step 1: Create the project with uv**

Check the uv and Django docs with Context7 first (`uv init`, `django-admin startproject`).

```bash
cd backend 2>/dev/null || mkdir backend && cd backend
uv init --app --no-readme --name backend .
rm -f main.py hello.py
uv add django djangorestframework httpx polyline redis gunicorn
uv add --dev pytest pytest-django ruff
uv run django-admin startproject config .
```

Then convert `config/settings.py` into a package: delete `config/settings.py`, create `config/settings/__init__.py` (empty).

- [ ] **Step 2: Write the settings**

`backend/config/settings/base.py`:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = False
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "rest_framework"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {}

USE_TZ = True
TIME_ZONE = "UTC"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_RATES": {"plan": "20/min", "geocode": "60/min"},
    "EXCEPTION_HANDLER": "routing.apis.exception_handler",
}
```

`backend/config/settings/local.py`:

```python
from .base import *  # noqa: F403

DEBUG = True
```

`backend/config/settings/production.py`:

```python
import os

from .base import *  # noqa: F403

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ["REDIS_URL"],
    }
}
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
REST_FRAMEWORK = {**REST_FRAMEWORK, "NUM_PROXIES": 1}  # noqa: F405
```

In `manage.py` and `config/wsgi.py`, set the default settings module: `manage.py` → `"config.settings.local"`, `wsgi.py` → `"config.settings.production"`.

`backend/config/urls.py`:

```python
from django.urls import include, path

urlpatterns = [path("api/", include("routing.urls"))]
```

- [ ] **Step 3: Configure pytest**

Add to `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.local"
python_files = ["test_*.py"]

[tool.ruff]
line-length = 100
```

`backend/conftest.py`:

```python
import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()
```

- [ ] **Step 4: Write the failing test**

`backend/routing/tests/test_apis.py`:

```python
from rest_framework.test import APIClient


def test_health():
    response = APIClient().get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: Run it and see it fail**

Run: `cd backend && uv run pytest routing/tests/test_apis.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'routing.urls'` or similar).

- [ ] **Step 6: Write the health view, the URLs, and the error handler**

`backend/routing/__init__.py`: empty. `backend/routing/tests/__init__.py`: empty.

`backend/routing/apis.py`:

```python
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ValidationError):
        response.data = {"detail": "Invalid input.", "code": "invalid", "errors": response.data}
    else:
        response.data = {"detail": str(exc.detail), "code": exc.get_codes()}
    return response


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})
```

`backend/routing/urls.py`:

```python
from django.urls import path

from . import apis

urlpatterns = [path("health", apis.health)]
```

`.gitignore` (repo root):

```
.venv/
__pycache__/
*.pyc
node_modules/
dist/
.env
test-results/
playwright-report/
.DS_Store
```

- [ ] **Step 7: Run the test and see it pass**

Run: `cd backend && uv run pytest -v && uv run ruff check .`
Expected: 1 passed, ruff clean.

- [ ] **Step 8: Commit**

```bash
git add .gitignore backend
git commit -m "chore: scaffold django backend with health endpoint"
```

---

### Task 2: Risk levels, route metrics, and ranking (`risk.py`)

**Files:**
- Create: `backend/routing/services/__init__.py`, `backend/routing/services/risk.py`
- Test: `backend/routing/tests/test_risk.py`, `backend/routing/tests/test_ranking.py`

**Interfaces:**
- Produces:
  - `class Level(IntEnum)`: `LOW=0, MODERATE=1, HIGH=2, SEVERE=3, NO_TRAVEL=4`
  - `LEVEL_NAMES: dict[Level, str]` → `"low" | "moderate" | "high" | "severe" | "no_travel"`
  - `wind_level(mph: float) -> Level`, `rain_level(in_hr: float) -> Level`, `snow_level(in_hr: float) -> Level`
  - `checkpoint_level(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_lb: int) -> Level`
  - `@dataclass(frozen=True) Segment(level: Level | None, miles: float)` (`None` = No Data)
  - `miles_by_level(segments) -> dict[str, float]` with keys `low, moderate, high, severe, no_travel, no_data`
  - `avg_risk(segments) -> float | None`
  - `@dataclass(frozen=True) RouteScore(id: int, miles: dict[str, float], avg_risk: float | None, duration_s: float)`
  - `@dataclass(frozen=True) RankedRoute(id: int, rank: int, reason: str)`
  - `rank_routes(scores: list[RouteScore]) -> list[RankedRoute]` (best first, `rank` starts at 1)

- [ ] **Step 1: Write the failing level tests**

`backend/routing/tests/test_risk.py`:

```python
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
```

- [ ] **Step 2: Run and see it fail**

Run: `cd backend && uv run pytest routing/tests/test_risk.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'routing.services'`).

- [ ] **Step 3: Write the failing ranking tests**

`backend/routing/tests/test_ranking.py`:

```python
from routing.services.risk import RouteScore, rank_routes


def miles(no_travel=0, severe=0, high=0):
    return {
        "low": 0,
        "moderate": 0,
        "high": high,
        "severe": severe,
        "no_travel": no_travel,
        "no_data": 0,
    }


def ids(ranked):
    return [r.id for r in ranked]


def test_no_travel_routes_rank_last():
    ranked = rank_routes(
        [
            RouteScore(0, miles(no_travel=5), 0.5, 3600),
            RouteScore(1, miles(severe=50), 2.0, 7200),
        ]
    )
    assert ids(ranked) == [1, 0]
    assert ranked[0].reason == "Fewest No Travel miles"
    assert ranked[1].reason == "More No Travel miles"


def test_fewer_no_travel_miles_wins_among_no_travel_routes():
    ranked = rank_routes(
        [RouteScore(0, miles(no_travel=20), 1, 1), RouteScore(1, miles(no_travel=5), 1, 1)]
    )
    assert ids(ranked) == [1, 0]


def test_severe_then_high_miles():
    ranked = rank_routes(
        [
            RouteScore(0, miles(severe=10), 1.0, 3600),
            RouteScore(1, miles(high=100), 1.5, 3600),
            RouteScore(2, miles(high=50), 1.5, 3600),
        ]
    )
    assert ids(ranked) == [2, 1, 0]
    assert [r.rank for r in ranked] == [1, 2, 3]
    assert ranked[0].reason == "Fewest High miles"
    assert ranked[2].reason == "More Severe miles"


def test_avg_risk_then_duration():
    ranked = rank_routes(
        [
            RouteScore(0, miles(), 1.0, 3600),
            RouteScore(1, miles(), 0.5, 7200),
            RouteScore(2, miles(), 0.5, 5400),
        ]
    )
    assert ids(ranked) == [2, 1, 0]
    assert ranked[0].reason == "Shortest travel time"
    assert ranked[2].reason == "Higher average risk"


def test_ties_keep_router_order():
    ranked = rank_routes([RouteScore(0, miles(), 1.0, 3600), RouteScore(1, miles(), 1.0, 3600)])
    assert ids(ranked) == [0, 1]
    assert ranked[0].reason == "Tied with the other routes on risk and time"
    assert ranked[1].reason == "Same risk and time as the recommended route"


def test_single_route():
    ranked = rank_routes([RouteScore(0, miles(), 1.0, 3600)])
    assert ranked[0].reason == "Only route found"


def test_unknown_avg_risk_ranks_after_known():
    ranked = rank_routes([RouteScore(0, miles(), None, 3600), RouteScore(1, miles(), 3.0, 3600)])
    assert ids(ranked) == [1, 0]
```

- [ ] **Step 4: Run and see it fail**

Run: `cd backend && uv run pytest routing/tests/test_ranking.py -v`
Expected: FAIL (import error).

- [ ] **Step 5: Write `risk.py`**

`backend/routing/services/__init__.py`: empty.

`backend/routing/services/risk.py`:

```python
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
                reason = "Tied with the other routes on risk and time" if i is None else WIN_REASONS[i]
        else:
            i = _first_difference(_key(score), best_key)
            reason = "Same risk and time as the recommended route" if i is None else LOSE_REASONS[i]
        ranked.append(RankedRoute(score.id, rank, reason))
    return ranked
```

- [ ] **Step 6: Run both test files and see them pass**

Run: `cd backend && uv run pytest routing/tests/test_risk.py routing/tests/test_ranking.py -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/routing/services backend/routing/tests/test_risk.py backend/routing/tests/test_ranking.py
git commit -m "feat: add weather risk levels, load rules, and route ranking"
```

---

### Task 3: Geometry helpers and checkpoints (`geo.py`, `checkpoints.py`)

**Files:**
- Create: `backend/routing/services/types.py`, `backend/routing/services/geo.py`, `backend/routing/services/checkpoints.py`
- Test: `backend/routing/tests/test_geo.py`, `backend/routing/tests/test_checkpoints.py`

**Interfaces:**
- Produces:
  - `types.py`: `@dataclass(frozen=True) LatLon(lat: float, lon: float)`; `@dataclass(frozen=True) RawRoute(coords: list[tuple[float, float]], cum_time_s: list[float], distance_mi: float, duration_s: float, source: str)` (coords are `(lat, lon)`, `cum_time_s[i]` = seconds from start to vertex `i`)
  - `geo.py`: `MILES_PER_DEG_LAT: float`, `haversine_mi(a: tuple[float, float], b: tuple[float, float]) -> float`, `cumulative_miles(coords) -> list[float]`, `locate(cum: list[float], mile: float) -> tuple[int, float]`, `corridor_points(coords, step_mi=10, offset_mi=15) -> list[tuple[float, float]]`, `GRID_DEG = 0.25`, `snap(lat: float, lon: float) -> tuple[float, float]`
  - `checkpoints.py`: `@dataclass(frozen=True) Checkpoint(mile: float, lat: float, lon: float, offset_s: float, segment_mi: float)`, `sample_checkpoints(coords, cum_time_s, interval_mi) -> list[Checkpoint]`

- [ ] **Step 1: Write the failing geo tests**

`backend/routing/tests/test_geo.py`:

```python
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
```

- [ ] **Step 2: Write the failing checkpoint tests**

`backend/routing/tests/test_checkpoints.py`:

```python
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
```

- [ ] **Step 3: Run and see them fail**

Run: `cd backend && uv run pytest routing/tests/test_geo.py routing/tests/test_checkpoints.py -v`
Expected: FAIL (import errors).

- [ ] **Step 4: Write `types.py`, `geo.py`, and `checkpoints.py`**

`backend/routing/services/types.py`:

```python
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
```

`backend/routing/services/geo.py`:

```python
import bisect
import itertools
import math

EARTH_RADIUS_MI = 3958.7613
MILES_PER_DEG_LAT = 2 * math.pi * EARTH_RADIUS_MI / 360
GRID_DEG = 0.25


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
```

Check of the sign in the test: a line due north has `east = 0`, `north > 0`. Then `d_north = 0` and `d_east = -offset`. The first offset point is west (`lon < 0`), the second is east. This matches `left[1] < 0` and `right[1] > 0`.

`backend/routing/services/checkpoints.py`:

```python
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
```

Note: for a trip of exactly one interval or less, `marks` starts as `[0]`, then gets `total` appended, so a trip always has at least an origin and a destination checkpoint.

- [ ] **Step 5: Run and see them pass**

Run: `cd backend && uv run pytest routing/tests/test_geo.py routing/tests/test_checkpoints.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/routing/services backend/routing/tests/test_geo.py backend/routing/tests/test_checkpoints.py
git commit -m "feat: sample route checkpoints with ETAs and corridor grid points"
```

---

### Task 4: HTTP helper and routing clients (TomTom, OSRM)

**Files:**
- Create: `backend/routing/clients/__init__.py`, `backend/routing/clients/http.py`, `backend/routing/clients/tomtom.py`, `backend/routing/clients/osrm.py`
- Modify: `backend/config/settings/base.py` (add `TOMTOM_API_KEY`)
- Test: `backend/routing/tests/test_routing_clients.py`

**Interfaces:**
- Consumes: `LatLon`, `RawRoute` (Task 3), `cumulative_miles`, `lerp` (Task 3).
- Produces:
  - `http.py`: `class UpstreamError(APIException)` (502, code `upstream_error`), `class NoRouteError(APIException)` (400, code `no_route`), `request_json(method: str, url: str, *, bad_request_error: type[APIException] = UpstreamError, **kwargs) -> Any`, `cache_key(prefix: str, *parts) -> str`
  - `tomtom.fetch_routes(origin: LatLon, destination: LatLon, departure: datetime, load_lb: int, wanted: int = 3) -> list[RawRoute]` (raises `UpstreamError` on any failure, including a missing key, HTTP 400, 403, and 429)
  - `osrm.fetch_routes(origin: LatLon, destination: LatLon, wanted: int = 3) -> list[RawRoute]` (raises `NoRouteError` on HTTP 400, `UpstreamError` otherwise)

- [ ] **Step 1: Check the docs**

Use Context7 for: httpx `HTTPTransport(retries=...)` and timeouts; Django cache `get_or_set`; pytest-django `settings` fixture; OSRM `annotations=duration`.

Read the TomTom Calculate Route docs (https://docs.tomtom.com/routing-api/documentation/tomtom-maps/calculate-route). Facts checked on 2026-10-12:
- `GET https://api.tomtom.com/routing/1/calculateRoute/{lat,lon}:{lat,lon}/json?key=...`
- `travelMode=truck`, `vehicleCommercial=true`, `vehicleWeight` (integer, kg, gross weight), `maxAlternatives` (0–5), `departAt` (RFC 3339 or `now`, must not be in the past).
- `extendedRouteRepresentation=travelTime` adds `routes[].progress[]` with `pointIndex` and `travelTimeInSeconds`. The first and last points are always in it. Interpolate by distance for the other points.
- `routes[].summary.lengthInMeters`, `routes[].summary.travelTimeInSeconds`, `routes[].legs[].points[]` with `latitude` and `longitude`.
- Errors: `detailedError.code` (for example `NO_ROUTE_FOUND`). 403 = bad key, 429 = quota.

- [ ] **Step 2: Add the setting**

Add to `backend/config/settings/base.py`:

```python
TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY", "")
```

- [ ] **Step 3: Write the failing tests**

`backend/routing/tests/test_routing_clients.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest

from routing.clients import http, osrm, tomtom
from routing.services.types import LatLon

A = LatLon(0.0, 0.0)
B = LatLon(0.2, 0.0)
NOW = datetime(2026, 10, 12, 4, 20, tzinfo=UTC)


def tomtom_route(points, meters=22_530, seconds=1200, progress=None):
    return {
        "summary": {"lengthInMeters": meters, "travelTimeInSeconds": seconds},
        "legs": [{"points": [{"latitude": lat, "longitude": lon} for lat, lon in points]}],
        "progress": progress
        or [
            {"pointIndex": 0, "travelTimeInSeconds": 0},
            {"pointIndex": len(points) - 1, "travelTimeInSeconds": seconds},
        ],
    }


@pytest.fixture(autouse=True)
def tomtom_key(settings):
    settings.TOMTOM_API_KEY = "test-key"


@pytest.fixture
def clock(monkeypatch):
    monkeypatch.setattr(tomtom.timezone, "now", lambda: NOW)


def test_tomtom_request_and_parse(monkeypatch, clock):
    seen = {}

    def fake(method, url, **kwargs):
        seen["url"] = url
        seen["params"] = kwargs["params"]
        return {
            "routes": [
                tomtom_route([(0, 0), (0.1, 0), (0.2, 0)]),
                tomtom_route([(0, 0), (0.1, 0.1), (0.2, 0)], 25_000, 1500),
            ]
        }

    monkeypatch.setattr(http, "request_json", fake)
    routes = tomtom.fetch_routes(A, B, NOW + timedelta(hours=1), load_lb=40_000)

    assert seen["url"].endswith("/calculateRoute/0.0,0.0:0.2,0.0/json")
    params = seen["params"]
    assert params["key"] == "test-key"
    assert params["travelMode"] == "truck"
    assert params["vehicleCommercial"] == "true"
    assert params["vehicleWeight"] == 34_019
    assert params["maxAlternatives"] == 2
    assert params["departAt"] == "2026-10-12T05:20:00+00:00"
    assert params["extendedRouteRepresentation"] == "travelTime"
    assert len(routes) == 2
    route = routes[0]
    assert route.coords == [(0, 0), (0.1, 0), (0.2, 0)]
    assert route.cum_time_s == pytest.approx([0, 600, 1200])
    assert route.distance_mi == pytest.approx(14.0, abs=0.01)
    assert route.duration_s == 1200
    assert route.source == "tomtom"


def test_tomtom_progress_keeps_uneven_speed(monkeypatch, clock):
    progress = [
        {"pointIndex": 0, "travelTimeInSeconds": 0},
        {"pointIndex": 1, "travelTimeInSeconds": 900},
        {"pointIndex": 2, "travelTimeInSeconds": 1200},
    ]
    route = tomtom_route([(0, 0), (0.1, 0), (0.2, 0)], progress=progress)
    monkeypatch.setattr(http, "request_json", lambda *a, **k: {"routes": [route]})
    assert tomtom.fetch_routes(A, B, NOW, 1)[0].cum_time_s == [0, 900, 1200]


def test_tomtom_past_departure_uses_now(monkeypatch, clock):
    seen = {}

    def fake(method, url, **kwargs):
        seen.update(kwargs["params"])
        return {"routes": [tomtom_route([(0, 0), (0.2, 0)])]}

    monkeypatch.setattr(http, "request_json", fake)
    tomtom.fetch_routes(A, B, NOW - timedelta(minutes=5), 1)
    assert seen["departAt"] == "now"


def test_tomtom_without_key_is_upstream_error(monkeypatch, settings):
    settings.TOMTOM_API_KEY = ""
    monkeypatch.setattr(http, "request_json", lambda *a, **k: pytest.fail("no request"))
    with pytest.raises(http.UpstreamError):
        tomtom.fetch_routes(A, B, NOW, 1)


def test_tomtom_routes_are_cached_without_the_key(monkeypatch, clock):
    calls = []

    def fake(method, url, **kwargs):
        calls.append(kwargs["params"])
        return {"routes": [tomtom_route([(0, 0), (0.2, 0)])]}

    monkeypatch.setattr(http, "request_json", fake)
    tomtom.fetch_routes(A, B, NOW, 1)
    tomtom.fetch_routes(A, B, NOW, 1)
    assert len(calls) == 1


def test_osrm_parses_routes(monkeypatch):
    seen = {}

    def fake(method, url, **kwargs):
        seen["url"] = url
        seen["kwargs"] = kwargs
        return {
            "routes": [
                {
                    "distance": 22_530.0,
                    "duration": 1200.0,
                    "geometry": {"coordinates": [[0, 0], [0, 0.1], [0, 0.2]]},
                    "legs": [{"annotation": {"duration": [500.0, 700.0]}}],
                }
            ]
        }

    monkeypatch.setattr(http, "request_json", fake)
    routes = osrm.fetch_routes(A, B)

    assert seen["url"].endswith("/route/v1/driving/0.0,0.0;0.0,0.2")
    assert seen["kwargs"]["bad_request_error"] is http.NoRouteError
    route = routes[0]
    assert route.coords == [(0, 0), (0.1, 0), (0.2, 0)]
    assert route.cum_time_s == [0.0, 500.0, 1200.0]
    assert route.distance_mi == pytest.approx(14.0, abs=0.01)
    assert route.source == "osrm"
```

`vehicleWeight`: (40,000 lb load + 35,000 lb empty truck) × 0.45359237 = 34,019 kg.

- [ ] **Step 4: Run and see it fail**

Run: `cd backend && uv run pytest routing/tests/test_routing_clients.py -v`
Expected: FAIL (import errors).

- [ ] **Step 5: Write `http.py`**

`backend/routing/clients/__init__.py`: empty.

`backend/routing/clients/http.py`:

```python
import hashlib
import json
from typing import Any

import httpx
from rest_framework.exceptions import APIException

USER_AGENT = "weather-aware-truck-routing/1.0"
TIMEOUT_S = 10.0


class UpstreamError(APIException):
    status_code = 502
    default_detail = "An outside service did not respond. Try again."
    default_code = "upstream_error"


class NoRouteError(APIException):
    status_code = 400
    default_detail = "No road route connects these places."
    default_code = "no_route"


def request_json(
    method: str, url: str, *, bad_request_error: type[APIException] = UpstreamError, **kwargs
) -> Any:
    transport = httpx.HTTPTransport(retries=1)
    try:
        with httpx.Client(
            transport=transport, timeout=TIMEOUT_S, headers={"User-Agent": USER_AGENT}
        ) as client:
            response = client.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        raise UpstreamError() from exc
    if response.status_code == 400:
        raise bad_request_error()
    if response.is_error:
        raise UpstreamError()
    return response.json()


def cache_key(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()
    return f"{prefix}:{digest}"
```

- [ ] **Step 6: Write `tomtom.py`**

`backend/routing/clients/tomtom.py`:

```python
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
        data = http.request_json(
            "GET", url, params={"key": settings.TOMTOM_API_KEY, **params}
        )
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
```

Notes:
- A TomTom 400 (`NO_ROUTE_FOUND` or a bad parameter), 403, or 429 raises the default `UpstreamError`, so the plan service falls back to OSRM. An OSRM 400 is the real "no route".
- The API key is not in the cache key, and it never leaves the backend.

- [ ] **Step 7: Write `osrm.py`**

`backend/routing/clients/osrm.py`:

```python
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
        return http.request_json(
            "GET", url, params=params, bad_request_error=http.NoRouteError
        )

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
```

- [ ] **Step 8: Run and see it pass**

Run: `cd backend && uv run pytest routing/tests/test_routing_clients.py -v`
Expected: all pass.

- [ ] **Step 9: Live check (needs the key)**

Run with a real `TOMTOM_API_KEY` in the shell:

```bash
cd backend && uv run python -c "
import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local'); django.setup()
from django.utils import timezone
from routing.clients import tomtom
from routing.services.types import LatLon
for b in (LatLon(39.74, -104.99), LatLon(40.71, -74.01)):
    rs = tomtom.fetch_routes(LatLon(32.78, -96.8), b, timezone.now(), 35_000)
    print(len(rs), [(round(r.distance_mi), round(r.duration_s / 3600, 1), round(r.cum_time_s[-1])) for r in rs])
"
```

Expected: Dallas to Denver and Dallas to New York each print up to 3 routes, and the last `cum_time_s` equals `duration_s`. If `progress` has a different shape, fix `_parse` and its test before you continue.

- [ ] **Step 10: Commit**

```bash
git add backend/config/settings/base.py backend/routing/clients backend/routing/tests/test_routing_clients.py
git commit -m "feat: add tomtom truck routing client with osrm fallback client"
```

---

### Task 5: Open-Meteo client

**Files:**
- Create: `backend/routing/clients/open_meteo.py`
- Test: `backend/routing/tests/test_open_meteo.py`

**Interfaces:**
- Consumes: `http.request_json`, `http.cache_key` (Task 4).
- Produces:
  - `HOURS = 48`
  - `@dataclass(frozen=True) HourlyWeather(wind_mph: list[float | None], gust_mph: list[float | None], rain_in: list[float | None], snow_in: list[float | None])` with `at(hour: int) -> tuple[float | None, float | None, float | None, float | None]` returning `(wind, gust, rain, snow)`
  - `fetch_hourly(cells: list[tuple[float, float]], start_epoch: int) -> dict[tuple[float, float], HourlyWeather]`

- [ ] **Step 1: Check the docs**

Use Context7 (`/websites/open-meteo_en`) for `start_hour`, `end_hour`, multi-location responses (a list), `timeformat=unixtime`, and the units.

- [ ] **Step 2: Write the failing tests**

`backend/routing/tests/test_open_meteo.py`:

```python
import pytest

from routing.clients import http, open_meteo

START = 1_791_777_600


def location(wind, rain, showers, snow):
    hours = open_meteo.HOURS
    return {
        "hourly": {
            "time": [START + 3600 * i for i in range(hours)],
            "wind_speed_10m": [wind] * hours,
            "wind_gusts_10m": [wind + 10] * hours,
            "rain": [rain] * hours,
            "showers": [showers] * hours,
            "snowfall": [snow] * hours,
        }
    }


def test_fetch_maps_cells_and_sums_rain(monkeypatch):
    seen = {}

    def fake(method, url, **kwargs):
        seen.update(kwargs["params"])
        return [location(10, 0.1, 0.05, 0), location(40, 0, 0, 1.2)]

    monkeypatch.setattr(http, "request_json", fake)
    result = open_meteo.fetch_hourly([(32.75, -97.0), (33.0, -97.0)], START)

    assert seen["latitude"] == "32.75,33.0"
    assert seen["longitude"] == "-97.0,-97.0"
    assert seen["wind_speed_unit"] == "mph"
    assert seen["precipitation_unit"] == "inch"
    assert seen["start_hour"] == "2026-10-12T04:00"
    assert seen["end_hour"] == "2026-10-14T03:00"
    wind, gust, rain, snow = result[(32.75, -97.0)].at(0)
    assert (wind, gust, snow) == (10, 20, 0)
    assert rain == pytest.approx(0.15)
    assert result[(33.0, -97.0)].at(47)[3] == 1.2


def test_single_location_response_is_a_dict(monkeypatch):
    monkeypatch.setattr(http, "request_json", lambda *a, **k: location(5, 0, 0, 0))
    result = open_meteo.fetch_hourly([(32.75, -97.0)], START)
    assert result[(32.75, -97.0)].at(3)[0] == 5


def test_null_values_stay_none(monkeypatch):
    data = location(5, 0, 0, 0)
    data["hourly"]["rain"][2] = None
    monkeypatch.setattr(http, "request_json", lambda *a, **k: data)
    result = open_meteo.fetch_hourly([(32.75, -97.0)], START)
    assert result[(32.75, -97.0)].at(2)[2] is None


def test_batches_and_cache(monkeypatch):
    calls = []

    def fake(method, url, **kwargs):
        count = len(kwargs["params"]["latitude"].split(","))
        calls.append(count)
        result = [location(5, 0, 0, 0) for _ in range(count)]
        return result if count > 1 else result[0]

    monkeypatch.setattr(http, "request_json", fake)
    monkeypatch.setattr(open_meteo, "BATCH", 2)
    cells = [(30.0, -97.0), (30.25, -97.0), (30.5, -97.0)]
    open_meteo.fetch_hourly(cells, START)
    assert calls == [2, 1]
    open_meteo.fetch_hourly(cells, START)
    assert calls == [2, 1]
```

`START = 1_791_777_600` is `2026-10-12T04:00Z`.

- [ ] **Step 3: Run and see it fail**

Run: `cd backend && uv run pytest routing/tests/test_open_meteo.py -v`
Expected: FAIL (import error).

- [ ] **Step 4: Write `open_meteo.py`**

`backend/routing/clients/open_meteo.py`:

```python
from dataclasses import dataclass
from datetime import UTC, datetime

from django.core.cache import cache

from . import http

URL = "https://api.open-meteo.com/v1/forecast"
HOURS = 48
BATCH = 100
CACHE_S = 3600
VARIABLES = ("wind_speed_10m", "wind_gusts_10m", "rain", "showers", "snowfall")


@dataclass(frozen=True)
class HourlyWeather:
    wind_mph: list[float | None]
    gust_mph: list[float | None]
    rain_in: list[float | None]
    snow_in: list[float | None]

    def at(self, hour: int) -> tuple[float | None, float | None, float | None, float | None]:
        return self.wind_mph[hour], self.gust_mph[hour], self.rain_in[hour], self.snow_in[hour]


def fetch_hourly(
    cells: list[tuple[float, float]], start_epoch: int
) -> dict[tuple[float, float], HourlyWeather]:
    keys = {cell: f"wx:{cell[0]}:{cell[1]}:{start_epoch}" for cell in cells}
    cached = cache.get_many(keys.values())
    result = {cell: cached[key] for cell, key in keys.items() if key in cached}
    missing = [cell for cell in cells if cell not in result]

    for i in range(0, len(missing), BATCH):
        batch = missing[i : i + BATCH]
        fetched = dict(zip(batch, _request(batch, start_epoch)))
        cache.set_many({keys[cell]: weather for cell, weather in fetched.items()}, CACHE_S)
        result.update(fetched)
    return result


def _request(cells: list[tuple[float, float]], start_epoch: int) -> list[HourlyWeather]:
    params = {
        "latitude": ",".join(str(lat) for lat, _ in cells),
        "longitude": ",".join(str(lon) for _, lon in cells),
        "hourly": ",".join(VARIABLES),
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timeformat": "unixtime",
        "start_hour": _iso_hour(start_epoch),
        "end_hour": _iso_hour(start_epoch + (HOURS - 1) * 3600),
    }
    data = http.request_json("GET", URL, params=params)
    locations = data if isinstance(data, list) else [data]
    return [_parse(location["hourly"]) for location in locations]


def _parse(hourly: dict) -> HourlyWeather:
    rain = [
        None if r is None or s is None else r + s
        for r, s in zip(hourly["rain"], hourly["showers"])
    ]
    return HourlyWeather(
        wind_mph=hourly["wind_speed_10m"],
        gust_mph=hourly["wind_gusts_10m"],
        rain_in=rain,
        snow_in=hourly["snowfall"],
    )


def _iso_hour(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%dT%H:%M")
```

- [ ] **Step 5: Run and see it pass**

Run: `cd backend && uv run pytest routing/tests/test_open_meteo.py -v`
Expected: all pass.

- [ ] **Step 6: Live check (one call)**

Run:

```bash
cd backend && uv run python -c "
import django, os, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local'); django.setup()
from routing.clients import open_meteo
start = int(time.time()) // 3600 * 3600
r = open_meteo.fetch_hourly([(32.75, -97.0), (39.75, -105.0)], start)
print({k: v.at(0) for k, v in r.items()})"
```

Expected: two cells with 4 numbers each.

- [ ] **Step 7: Commit**

```bash
git add backend/routing/clients/open_meteo.py backend/routing/tests/test_open_meteo.py
git commit -m "feat: add open-meteo hourly weather client with per-cell cache"
```

---

### Task 6: Photon geocoding client and `/api/geocode`

**Files:**
- Create: `backend/routing/clients/photon.py`, `backend/routing/serializers.py`
- Modify: `backend/routing/apis.py`, `backend/routing/urls.py`
- Test: `backend/routing/tests/test_photon.py`, `backend/routing/tests/test_apis.py`

**Interfaces:**
- Produces: `photon.search(query: str, limit: int = 5) -> list[dict]` with items `{"label": str, "lat": float, "lon": float}`. `GET /api/geocode?q=` → `{"results": [...]}`. `GeocodeInputSerializer` (`q`: 2–200 chars).

- [ ] **Step 1: Write the failing tests**

`backend/routing/tests/test_photon.py`:

```python
from routing.clients import http, photon


def feature(name=None, lat=32.7, lon=-96.8, state="Texas", cc="US", **props):
    return {
        "geometry": {"coordinates": [lon, lat]},
        "properties": {"name": name, "state": state, "countrycode": cc, **props},
    }


def test_search_builds_labels_and_filters_us(monkeypatch):
    seen = {}

    def fake(method, url, **kwargs):
        seen.update(kwargs["params"])
        return {
            "features": [
                feature("Dallas", city="Dallas"),
                feature("Dallas", cc="CA"),
                feature(None, housenumber="1600", street="Pennsylvania Ave", city="Washington",
                        state="District of Columbia", lat=38.9, lon=-77.0),
            ]
        }

    monkeypatch.setattr(http, "request_json", fake)
    results = photon.search("dallas")

    assert seen["q"] == "dallas"
    assert seen["bbox"] == photon.US_BBOX
    assert results == [
        {"label": "Dallas, Texas", "lat": 32.7, "lon": -96.8},
        {"label": "1600 Pennsylvania Ave, Washington, District of Columbia", "lat": 38.9,
         "lon": -77.0},
    ]


def test_search_dedupes_labels(monkeypatch):
    monkeypatch.setattr(
        http, "request_json", lambda *a, **k: {"features": [feature("Laredo"), feature("Laredo")]}
    )
    assert len(photon.search("laredo")) == 1
```

Add to `backend/routing/tests/test_apis.py`:

```python
from routing.clients import photon


def test_geocode(monkeypatch):
    monkeypatch.setattr(photon, "search", lambda q: [{"label": q, "lat": 1.0, "lon": 2.0}])
    response = APIClient().get("/api/geocode", {"q": "Dallas"})
    assert response.status_code == 200
    assert response.json() == {"results": [{"label": "Dallas", "lat": 1.0, "lon": 2.0}]}


def test_geocode_requires_query():
    response = APIClient().get("/api/geocode", {"q": "a"})
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "invalid"
    assert "q" in body["errors"]
```

- [ ] **Step 2: Run and see them fail**

Run: `cd backend && uv run pytest routing/tests/test_photon.py routing/tests/test_apis.py -v`
Expected: FAIL.

- [ ] **Step 3: Write `photon.py`**

`backend/routing/clients/photon.py`:

```python
from django.core.cache import cache

from . import http

URL = "https://photon.komoot.io/api/"
US_BBOX = "-125,24,-66,50"
CACHE_S = 86_400


def search(query: str, limit: int = 5) -> list[dict]:
    params = {"q": query, "limit": 10, "bbox": US_BBOX, "lang": "en"}

    def load() -> list[dict]:
        data = http.request_json("GET", URL, params=params)
        results: list[dict] = []
        for item in data["features"]:
            props = item["properties"]
            if props.get("countrycode") != "US":
                continue
            label = _label(props)
            if any(r["label"] == label for r in results):
                continue
            lon, lat = item["geometry"]["coordinates"]
            results.append({"label": label, "lat": lat, "lon": lon})
        return results[:limit]

    return cache.get_or_set(http.cache_key("photon", query.strip().lower()), load, CACHE_S)


def _label(props: dict) -> str:
    name = props.get("name") or " ".join(
        p for p in (props.get("housenumber"), props.get("street")) if p
    )
    city = props.get("city")
    parts = [name, city if city != name else None, props.get("state")]
    return ", ".join(p for p in parts if p)
```

- [ ] **Step 4: Write the serializer, view, and URL**

`backend/routing/serializers.py`:

```python
from rest_framework import serializers


class GeocodeInputSerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=200, trim_whitespace=True)
```

Add to `backend/routing/apis.py`:

```python
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .clients import photon
from .serializers import GeocodeInputSerializer


class GeocodeApi(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "geocode"

    def get(self, request):
        serializer = GeocodeInputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response({"results": photon.search(serializer.validated_data["q"])})
```

Add to `urlpatterns` in `backend/routing/urls.py`: `path("geocode", apis.GeocodeApi.as_view()),`

- [ ] **Step 5: Run and see them pass**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/routing
git commit -m "feat: add photon geocoding endpoint"
```

---

### Task 7: Plan service and `POST /api/plan`

**Files:**
- Create: `backend/routing/services/plan.py`
- Modify: `backend/routing/serializers.py`, `backend/routing/apis.py`, `backend/routing/urls.py`
- Test: `backend/routing/tests/test_plan.py`, `backend/routing/tests/test_apis.py`

**Interfaces:**
- Consumes: everything from Tasks 2–5.
- Produces:
  - `build_plan(origin: LatLon, destination: LatLon, departure: datetime, load_lb: int, interval_mi: int, now: datetime) -> dict` with the shape in spec section 4.1:
    - `routes`: list sorted by `rank`; each `{id, geometry: {"type": "LineString", "coordinates": [[lon, lat], ...]}, distance_mi, duration_s, source, checkpoints, miles_by_level, avg_risk, rank, recommended, reason}`
    - checkpoint: `{mile, lat, lon, eta, wind_mph, gust_mph, rain_in_hr, snow_in_hr, level, segment_mi}` where `level` is a `LEVEL_NAMES` value or `None`
    - `heatmap`: `{"start_hour": iso str, "cells": [{"lat", "lon", "levels": [int, ...48]}]}` where a level is 0–4, or -1 for No Data
    - `warnings`: list of `"fallback_routing" | "fewer_routes" | "beyond_forecast" | "no_safe_route"`
  - `PlanInputSerializer`, `PlanApi` at `POST /api/plan`.

- [ ] **Step 1: Write the failing service tests**

`backend/routing/tests/test_plan.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest

from routing.clients import http, open_meteo, osrm, tomtom
from routing.services import plan
from routing.services.geo import MILES_PER_DEG_LAT
from routing.services.types import LatLon, RawRoute

NOW = datetime(2026, 10, 12, 4, 20, tzinfo=UTC)
START = int(NOW.timestamp()) // 3600 * 3600
A, B = LatLon(30.0, -97.0), LatLon(30.0 + 100 / MILES_PER_DEG_LAT, -97.0)


def route(miles=100, hours=2.0, source="tomtom"):
    return RawRoute(
        coords=[(A.lat, A.lon), (A.lat + miles / MILES_PER_DEG_LAT, A.lon)],
        cum_time_s=[0, hours * 3600],
        distance_mi=miles,
        duration_s=hours * 3600,
        source=source,
    )


def weather(wind=5.0, rain=0.0, snow=0.0, rain_at=None):
    rain_list = [rain] * open_meteo.HOURS
    if rain_at is not None:
        rain_list = rain_at
    return open_meteo.HourlyWeather(
        wind_mph=[wind] * open_meteo.HOURS,
        gust_mph=[wind] * open_meteo.HOURS,
        rain_in=rain_list,
        snow_in=[snow] * open_meteo.HOURS,
    )


@pytest.fixture
def calm(monkeypatch):
    seen = {}

    def fake(cells, start):
        seen["start"] = start
        return {cell: weather() for cell in cells}

    monkeypatch.setattr(open_meteo, "fetch_hourly", fake)
    return seen


def build(**overrides):
    args = dict(
        origin=A, destination=B, departure=NOW, load_lb=20_000, interval_mi=25, now=NOW
    )
    return plan.build_plan(**(args | overrides))


def test_calm_plan_shape(monkeypatch, calm):
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: [route(), route(120, 2.5)])
    result = build()

    assert calm["start"] == START
    assert result["warnings"] == ["fewer_routes"]
    best = result["routes"][0]
    assert best["id"] == 0 and best["rank"] == 1 and best["recommended"] is True
    assert best["reason"] == "Shortest travel time"
    assert len(best["checkpoints"]) == 5
    assert best["checkpoints"][0]["level"] == "low"
    assert best["checkpoints"][0]["eta"] == NOW.isoformat()
    assert best["miles_by_level"]["low"] == pytest.approx(100)
    assert best["avg_risk"] == 0
    assert best["geometry"]["coordinates"][0] == [A.lon, A.lat]
    assert result["heatmap"]["start_hour"] == datetime.fromtimestamp(START, UTC).isoformat()
    assert all(len(c["levels"]) == open_meteo.HOURS for c in result["heatmap"]["cells"])


def test_load_rule_changes_level(monkeypatch):
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: [route()])
    monkeypatch.setattr(
        open_meteo, "fetch_hourly", lambda cells, s: {c: weather(wind=50) for c in cells}
    )
    light = build(load_lb=30_000)
    heavy = build(load_lb=30_001)
    assert light["routes"][0]["checkpoints"][0]["level"] == "severe"
    assert heavy["routes"][0]["checkpoints"][0]["level"] == "no_travel"
    assert "no_safe_route" in heavy["warnings"]
    assert heavy["heatmap"]["cells"][0]["levels"][0] == 4


def test_eta_uses_forecast_hour_after_midnight(monkeypatch):
    late = datetime(2026, 10, 12, 23, 30, tzinfo=UTC)
    rain = [0.0] * open_meteo.HOURS
    rain[3] = 0.3
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: [route(100, 2.0)])
    monkeypatch.setattr(
        open_meteo, "fetch_hourly", lambda cells, s: {c: weather(rain_at=rain) for c in cells}
    )
    result = build(departure=late, now=late, interval_mi=50)
    cps = result["routes"][0]["checkpoints"]
    assert cps[-1]["eta"] == (late + timedelta(hours=2)).isoformat()
    assert cps[-1]["level"] == "high"
    assert cps[0]["level"] == "low"


def test_beyond_forecast_is_no_data(monkeypatch, calm):
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: [route(100, 10.0)])
    result = build(departure=NOW + timedelta(hours=45))
    cps = result["routes"][0]["checkpoints"]
    assert cps[0]["level"] == "low"
    assert cps[-1]["level"] is None
    assert result["routes"][0]["miles_by_level"]["no_data"] > 0
    assert "beyond_forecast" in result["warnings"]


def test_null_weather_is_no_data(monkeypatch):
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: [route()])
    rain = [None] * open_meteo.HOURS
    monkeypatch.setattr(
        open_meteo, "fetch_hourly", lambda cells, s: {c: weather(rain_at=rain) for c in cells}
    )
    result = build()
    assert result["routes"][0]["checkpoints"][0]["level"] is None
    assert result["heatmap"]["cells"][0]["levels"][0] == -1


def test_routing_gets_departure_and_load(monkeypatch, calm):
    seen = []
    monkeypatch.setattr(tomtom, "fetch_routes", lambda *a: seen.append(a) or [route()])
    build(load_lb=42_000)
    assert seen[0][2:] == (NOW, 42_000)


def test_falls_back_to_osrm(monkeypatch, calm):
    def fail(*args):
        raise http.UpstreamError()

    monkeypatch.setattr(tomtom, "fetch_routes", fail)
    monkeypatch.setattr(
        osrm, "fetch_routes", lambda o, d: [route(source="osrm"), route(110, 2.2, "osrm")]
    )
    result = build()
    assert result["warnings"][:2] == ["fallback_routing", "fewer_routes"]
    assert result["routes"][0]["source"] == "osrm"
```

Midnight test: `start` = 23:00. The origin ETA 23:30 maps to hour index `floor(0.5 + 0.5) = 1` (00:00), rain 0 → Low. The destination ETA 01:30 maps to `floor(2.5 + 0.5) = 3` (02:00), rain 0.3 → High. The service uses `floor(x + 0.5)`, not `round()`, because Python's `round()` rounds half to even.

- [ ] **Step 2: Run and see it fail**

Run: `cd backend && uv run pytest routing/tests/test_plan.py -v`
Expected: FAIL (import error).

- [ ] **Step 3: Write `plan.py`**

`backend/routing/services/plan.py`:

```python
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
```

- [ ] **Step 4: Run and see it pass**

Run: `cd backend && uv run pytest routing/tests/test_plan.py -v`
Expected: all pass.

- [ ] **Step 5: Write the failing API tests**

Add to `backend/routing/tests/test_apis.py`:

```python
from datetime import timedelta

from django.utils import timezone

from routing.services import plan as plan_service


def plan_body(**overrides):
    body = {
        "origin": {"lat": 32.78, "lon": -96.8, "label": "Dallas, Texas"},
        "destination": {"lat": 39.74, "lon": -104.99, "label": "Denver, Colorado"},
        "departure": (timezone.now() + timedelta(hours=1)).isoformat(),
        "load_lb": 35_000,
        "interval_mi": 25,
    }
    return body | overrides


def test_plan_calls_service(monkeypatch):
    seen = {}

    def fake(**kwargs):
        seen.update(kwargs)
        return {"routes": [], "heatmap": {"start_hour": "x", "cells": []}, "warnings": []}

    monkeypatch.setattr(plan_service, "build_plan", fake)
    response = APIClient().post("/api/plan", plan_body(), format="json")
    assert response.status_code == 200
    assert seen["load_lb"] == 35_000
    assert seen["interval_mi"] == 25
    assert seen["origin"].lat == 32.78


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"load_lb": 0}, "load_lb"),
        ({"load_lb": 80_001}, "load_lb"),
        ({"interval_mi": 30}, "interval_mi"),
        ({"departure": (timezone.now() + timedelta(hours=49)).isoformat()}, "departure"),
        ({"departure": (timezone.now() - timedelta(hours=1)).isoformat()}, "departure"),
        ({"destination": {"lat": 32.78, "lon": -96.8}}, "non_field_errors"),
    ],
)
def test_plan_validation(override, field):
    response = APIClient().post("/api/plan", plan_body(**override), format="json")
    assert response.status_code == 400
    assert field in response.json()["errors"]


def test_plan_upstream_error_shape(monkeypatch):
    from routing.clients.http import UpstreamError

    def fail(**kwargs):
        raise UpstreamError()

    monkeypatch.setattr(plan_service, "build_plan", fail)
    response = APIClient().post("/api/plan", plan_body(), format="json")
    assert response.status_code == 502
    assert response.json() == {
        "detail": "An outside service did not respond. Try again.",
        "code": "upstream_error",
    }
```

Add `import pytest` at the top of `test_apis.py`.

- [ ] **Step 6: Run and see them fail**

Run: `cd backend && uv run pytest routing/tests/test_apis.py -v`
Expected: the new tests FAIL (404).

- [ ] **Step 7: Write the serializer, view, and URL**

Add to `backend/routing/serializers.py`:

```python
from datetime import timedelta

from django.utils import timezone

from .clients.open_meteo import HOURS
from .services.geo import haversine_mi


class PlaceSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    label = serializers.CharField(max_length=200, required=False, allow_blank=True)


class PlanInputSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.IntegerField(min_value=1, max_value=80_000)
    interval_mi = serializers.ChoiceField(choices=(10, 25, 50))

    def validate_departure(self, value):
        now = timezone.now()
        if not now - timedelta(minutes=15) <= value <= now + timedelta(hours=HOURS):
            raise serializers.ValidationError("Departure must be within the next 48 hours.")
        return value

    def validate(self, data):
        o, d = data["origin"], data["destination"]
        if haversine_mi((o["lat"], o["lon"]), (d["lat"], d["lon"])) < 1:
            raise serializers.ValidationError("Origin and destination must be different places.")
        return data
```

Add to `backend/routing/apis.py`:

```python
from django.utils import timezone

from .serializers import PlanInputSerializer
from .services import plan as plan_service
from .services.types import LatLon


class PlanApi(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "plan"

    def post(self, request):
        serializer = PlanInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = plan_service.build_plan(
            origin=LatLon(data["origin"]["lat"], data["origin"]["lon"]),
            destination=LatLon(data["destination"]["lat"], data["destination"]["lon"]),
            departure=data["departure"],
            load_lb=data["load_lb"],
            interval_mi=data["interval_mi"],
            now=timezone.now(),
        )
        return Response(result)
```

Add to `urlpatterns`: `path("plan", apis.PlanApi.as_view()),`

- [ ] **Step 8: Run all backend tests and lint**

Run: `cd backend && uv run pytest -v && uv run ruff check . && uv run ruff format --check .`
Expected: all pass, ruff clean (run `uv run ruff format .` if needed).

- [ ] **Step 9: Live smoke test**

Run in one terminal: `cd backend && uv run python manage.py runserver`
Run in another:

```bash
curl -s -X POST localhost:8000/api/plan -H 'Content-Type: application/json' -d "{\"origin\":{\"lat\":32.7767,\"lon\":-96.797},\"destination\":{\"lat\":39.7392,\"lon\":-104.9903},\"departure\":\"$(date -u -v+1H +%Y-%m-%dT%H:%M:%SZ)\",\"load_lb\":35000,\"interval_mi\":25}" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['warnings']);[print(r['rank'],r['distance_mi'],r['miles_by_level'],r['reason']) for r in d['routes']];print(len(d['heatmap']['cells']),'cells')"
```

Expected: 3 ranked routes, a reason on each, a few hundred heatmap cells, total time under ~10 s on a cold cache. Record the time and the number of cells for the README.

- [ ] **Step 10: Commit**

```bash
git add backend/routing
git commit -m "feat: add plan endpoint with checkpoint risk, ranking, and corridor heatmap"
```

---

## Phase 2: Frontend (skills: design-taste-frontend, frontend-design, emil-design-eng, vercel-react-best-practices, dataviz, context7-mcp)

Load these skills at the start of Task 8, and keep them active for Tasks 8–12. They decide the final look (fonts, spacing, color values, motion). The code below is the working structure; the skills polish it. Do not add features that the spec does not have.

### Task 8: Frontend scaffold, theme, risk scale, and API layer

**Files:**
- Create: `frontend/` (Vite React TS template), `frontend/vite.config.ts`, `frontend/src/index.css`, `frontend/src/main.tsx`, `frontend/src/app/providers.tsx`, `frontend/src/app/App.tsx`, `frontend/src/config/constants.ts`, `frontend/src/lib/api.ts`, `frontend/src/lib/query-client.ts`, `frontend/src/theme/theme.ts`, `frontend/src/theme/risk.ts`, `frontend/src/types/plan.ts`, `frontend/src/utils/format.ts`, `frontend/src/test/setup.ts`
- Test: `frontend/src/theme/risk.test.ts`, `frontend/src/utils/format.test.ts`

**Interfaces:**
- Produces:
  - `types/plan.ts`: `LevelName`, `RiskKey = LevelName | 'no_data'`, `Place`, `Checkpoint`, `Route`, `HeatCell`, `Plan`, `PlanRequest`, `Interval = 10 | 25 | 50`
  - `theme/risk.ts`: `LEVELS: readonly LevelName[]`, `RISK_COLORS: Record<RiskKey, string>`, `RISK_LABELS: Record<RiskKey, string>`, `riskKey(level: LevelName | null): RiskKey`, `levelFromScore(score: number): RiskKey`
  - `lib/api.ts`: `class ApiError extends Error { code: string }`, `api<T>(path: string, init?: RequestInit): Promise<T>`
  - `utils/format.ts`: `formatDuration(seconds: number): string`, `formatMiles(miles: number): string`, `formatTime(iso: string): string`, `toLocalInputValue(date: Date): string`
  - `config/constants.ts`: `FORECAST_HOURS = 48`, `INTERVALS = [10, 25, 50] as const`, `DEFAULT_LOAD_LB = 40000`, `MAP_STYLES = { light: string, dark: string }`, `US_VIEW`

- [ ] **Step 1: Create the app with the official template**

Check the Vite, MUI (Vite install and Tailwind v4 integration), Tailwind v4 (Vite plugin), TanStack Query, and react-map-gl (MapLibre) quickstarts with Context7 first.

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install @mui/material @emotion/react @emotion/styled @mui/icons-material @tanstack/react-query react-map-gl maplibre-gl
npm install -D tailwindcss @tailwindcss/vite vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event @playwright/test
```

Delete the template demo files: `src/App.tsx`, `src/App.css`, `src/assets/`, `public/vite.svg`.

- [ ] **Step 2: Configure Vite, Tailwind, the dev proxy, and Vitest**

`frontend/vite.config.ts`:

```ts
/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
```

`frontend/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest'
```

`frontend/src/index.css` (layer order from the MUI Tailwind v4 guide; confirm with Context7):

```css
@layer theme, base, mui, components, utilities;
@import 'tailwindcss';

html,
body,
#root {
  height: 100%;
}
```

Add scripts to `package.json`: `"test": "vitest run"`, `"e2e": "playwright test"`.

- [ ] **Step 3: Write the failing tests**

`frontend/src/theme/risk.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { levelFromScore, riskKey, RISK_COLORS, RISK_LABELS } from './risk'

describe('risk scale', () => {
  it('maps scores to keys', () => {
    expect(levelFromScore(0)).toBe('low')
    expect(levelFromScore(4)).toBe('no_travel')
    expect(levelFromScore(-1)).toBe('no_data')
  })

  it('maps null to no_data', () => {
    expect(riskKey(null)).toBe('no_data')
    expect(riskKey('severe')).toBe('severe')
  })

  it('has a color and a label for every key', () => {
    for (const key of ['low', 'moderate', 'high', 'severe', 'no_travel', 'no_data'] as const) {
      expect(RISK_COLORS[key]).toMatch(/^#[0-9a-f]{6}$/i)
      expect(RISK_LABELS[key]).toBeTruthy()
    }
  })
})
```

`frontend/src/utils/format.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { formatDuration, formatMiles, toLocalInputValue } from './format'

describe('format', () => {
  it('formats durations', () => {
    expect(formatDuration(45 * 60)).toBe('45 min')
    expect(formatDuration(13 * 3600 + 5 * 60)).toBe('13 h 5 min')
    expect(formatDuration(2 * 3600)).toBe('2 h')
  })

  it('formats miles', () => {
    expect(formatMiles(808.44)).toBe('808 mi')
    expect(formatMiles(4.26)).toBe('4.3 mi')
  })

  it('builds a datetime-local value in local time', () => {
    const date = new Date(2026, 9, 12, 7, 5)
    expect(toLocalInputValue(date)).toBe('2026-10-12T07:05')
  })
})
```

- [ ] **Step 4: Run and see them fail**

Run: `cd frontend && npm test`
Expected: FAIL (modules not found).

- [ ] **Step 5: Write types, risk scale, formatters, constants, API layer**

`frontend/src/types/plan.ts`:

```ts
import type { LineString } from 'geojson'

export type LevelName = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel'
export type RiskKey = LevelName | 'no_data'
export type Interval = 10 | 25 | 50

export type Place = { label: string; lat: number; lon: number }

export type Checkpoint = {
  mile: number
  lat: number
  lon: number
  eta: string
  wind_mph: number | null
  gust_mph: number | null
  rain_in_hr: number | null
  snow_in_hr: number | null
  level: LevelName | null
  segment_mi: number
}

export type Route = {
  id: number
  geometry: LineString
  distance_mi: number
  duration_s: number
  source: 'tomtom' | 'osrm'
  checkpoints: Checkpoint[]
  miles_by_level: Record<RiskKey, number>
  avg_risk: number | null
  rank: number
  recommended: boolean
  reason: string
}

export type HeatCell = { lat: number; lon: number; levels: number[] }

export type Plan = {
  routes: Route[]
  heatmap: { start_hour: string; cells: HeatCell[] }
  warnings: string[]
}

export type PlanRequest = {
  origin: Place
  destination: Place
  departure: string
  load_lb: number
  interval_mi: Interval
}
```

If `geojson` types are missing, run `npm install -D @types/geojson`.

`frontend/src/theme/risk.ts` (starting values; the `dataviz` skill validates and may replace them):

```ts
import type { LevelName, RiskKey } from '../types/plan'

export const LEVELS: readonly LevelName[] = ['low', 'moderate', 'high', 'severe', 'no_travel']

export const RISK_COLORS: Record<RiskKey, string> = {
  low: '#2e9e5b',
  moderate: '#e3b505',
  high: '#ee7b22',
  severe: '#d1343f',
  no_travel: '#6b2c91',
  no_data: '#9aa5ad',
}

export const RISK_LABELS: Record<RiskKey, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  severe: 'Severe',
  no_travel: 'No Travel',
  no_data: 'No data',
}

export function riskKey(level: LevelName | null): RiskKey {
  return level ?? 'no_data'
}

export function levelFromScore(score: number): RiskKey {
  return score < 0 ? 'no_data' : LEVELS[score]
}
```

`frontend/src/utils/format.ts`:

```ts
const timeFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (!hours) return `${minutes} min`
  return minutes ? `${hours} h ${minutes} min` : `${hours} h`
}

export function formatMiles(miles: number): string {
  return miles >= 10 ? `${Math.round(miles)} mi` : `${miles.toFixed(1)} mi`
}

export function formatTime(iso: string): string {
  return timeFormat.format(new Date(iso))
}

export function toLocalInputValue(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}
```

`frontend/src/config/constants.ts` (OpenFreeMap styles returned HTTP 200 on 2026-10-12):

```ts
export const FORECAST_HOURS = 48
export const INTERVALS = [10, 25, 50] as const
export const DEFAULT_INTERVAL = 25
export const DEFAULT_LOAD_LB = 40_000
export const MAX_LOAD_LB = 80_000
export const MAP_STYLES = {
  light: 'https://tiles.openfreemap.org/styles/positron',
  dark: 'https://tiles.openfreemap.org/styles/dark',
}
export const US_VIEW = { longitude: -98.5, latitude: 39.5, zoom: 3.4 }
```

`frontend/src/lib/api.ts`:

```ts
export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
  ) {
    super(message)
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new ApiError(body.detail ?? 'Something went wrong. Try again.', body.code ?? 'error')
  }
  return body as T
}
```

`frontend/src/lib/query-client.ts`:

```ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5 * 60_000, retry: 1, refetchOnWindowFocus: false },
  },
})
```

- [ ] **Step 6: Write the theme, providers, and an empty App**

`frontend/src/theme/theme.ts`:

```ts
import { createTheme } from '@mui/material/styles'

export const BRAND_PRIMARY = { light: '#063D4B', dark: '#5FB7CC' }

export const theme = createTheme({
  cssVariables: { colorSchemeSelector: 'class' },
  colorSchemes: {
    light: { palette: { primary: { main: BRAND_PRIMARY.light } } },
    dark: { palette: { primary: { main: BRAND_PRIMARY.dark } } },
  },
  shape: { borderRadius: 10 },
})
```

`frontend/src/app/providers.tsx` (confirm `StyledEngineProvider enableCssLayer` with Context7):

```tsx
import CssBaseline from '@mui/material/CssBaseline'
import { StyledEngineProvider, ThemeProvider } from '@mui/material/styles'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { queryClient } from '../lib/query-client'
import { theme } from '../theme/theme'

export function Providers({ children }: { children: ReactNode }) {
  return (
    <StyledEngineProvider enableCssLayer>
      <ThemeProvider theme={theme} defaultMode="system">
        <CssBaseline />
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </ThemeProvider>
    </StyledEngineProvider>
  )
}
```

`frontend/src/app/App.tsx`:

```tsx
export function App() {
  return <div className="h-dvh w-full">Weather-Aware Truck Routing</div>
}
```

`frontend/src/main.tsx`:

```tsx
import 'maplibre-gl/dist/maplibre-gl.css'
import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import { Providers } from './app/providers'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Providers>
      <App />
    </Providers>
  </StrictMode>,
)
```

Set `<title>Weather-Aware Truck Routing</title>` and `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />` in `frontend/index.html`.

- [ ] **Step 7: Run tests, type check, and build**

Run: `cd frontend && npm test && npx tsc -b && npm run build`
Expected: tests pass, no type errors, build succeeds.

- [ ] **Step 8: Commit**

```bash
git add frontend
git commit -m "chore: scaffold react frontend with mui, tailwind, and react query"
```

---

### Task 9: Trip form with Photon autocomplete

**Files:**
- Create: `frontend/src/features/trip-form/api/geocode.ts`, `frontend/src/features/trip-form/components/PlaceField.tsx`, `frontend/src/features/trip-form/components/TripForm.tsx`, `frontend/src/features/routes/api/plan.ts`
- Modify: `frontend/src/app/App.tsx`

**Interfaces:**
- Consumes: `api`, `Place`, `PlanRequest`, `Interval`, constants, `toLocalInputValue`.
- Produces:
  - `useGeocode(query: string)` → React Query result of `Place[]` (enabled when `query.trim().length >= 3`)
  - `<PlaceField label: string; value: Place | null; onChange: (place: Place | null) => void />`
  - `<TripForm onSubmit: (request: PlanRequest) => void; loading: boolean />`
  - `usePlan()` → `useMutation<Plan, ApiError, PlanRequest>`

- [ ] **Step 1: Write the API hooks**

`frontend/src/features/trip-form/api/geocode.ts`:

```ts
import { useQuery } from '@tanstack/react-query'
import { api } from '../../../lib/api'
import type { Place } from '../../../types/plan'

export function useGeocode(query: string) {
  const q = query.trim()
  return useQuery({
    queryKey: ['geocode', q.toLowerCase()],
    queryFn: ({ signal }) =>
      api<{ results: Place[] }>(`/geocode?q=${encodeURIComponent(q)}`, { signal }).then(
        (body) => body.results,
      ),
    enabled: q.length >= 3,
    staleTime: Infinity,
    placeholderData: (previous) => previous,
  })
}
```

`frontend/src/features/routes/api/plan.ts`:

```ts
import { useMutation } from '@tanstack/react-query'
import { api, type ApiError } from '../../../lib/api'
import type { Plan, PlanRequest } from '../../../types/plan'

export function usePlan() {
  return useMutation<Plan, ApiError, PlanRequest>({
    mutationFn: (request) => api<Plan>('/plan', { method: 'POST', body: JSON.stringify(request) }),
  })
}
```

- [ ] **Step 2: Write `PlaceField` (MUI Autocomplete, debounce from `@mui/material/utils`)**

Check the MUI "Search as you type" Autocomplete example with Context7 first.

`frontend/src/features/trip-form/components/PlaceField.tsx`:

```tsx
import Autocomplete from '@mui/material/Autocomplete'
import TextField from '@mui/material/TextField'
import { debounce } from '@mui/material/utils'
import { useEffect, useMemo, useState } from 'react'
import type { Place } from '../../../types/plan'
import { useGeocode } from '../api/geocode'

type Props = { label: string; value: Place | null; onChange: (place: Place | null) => void }

export function PlaceField({ label, value, onChange }: Props) {
  const [query, setQuery] = useState('')
  const updateQuery = useMemo(() => debounce(setQuery, 300), [])
  useEffect(() => () => updateQuery.clear(), [updateQuery])
  const { data = [], isFetching } = useGeocode(query)

  return (
    <Autocomplete
      value={value}
      options={value && !data.some((p) => p.label === value.label) ? [value, ...data] : data}
      filterOptions={(options) => options}
      getOptionLabel={(option) => option.label}
      isOptionEqualToValue={(a, b) => a.label === b.label}
      loading={isFetching}
      noOptionsText={query.trim().length < 3 ? 'Type 3 or more letters' : 'No US places found'}
      onInputChange={(_, text) => updateQuery(text)}
      onChange={(_, place) => onChange(place)}
      renderInput={(params) => <TextField {...params} label={label} required />}
    />
  )
}
```

- [ ] **Step 3: Write `TripForm`**

`frontend/src/features/trip-form/components/TripForm.tsx`:

```tsx
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import Typography from '@mui/material/Typography'
import { useState, type FormEvent } from 'react'
import {
  DEFAULT_INTERVAL,
  DEFAULT_LOAD_LB,
  FORECAST_HOURS,
  INTERVALS,
  MAX_LOAD_LB,
} from '../../../config/constants'
import type { Interval, Place, PlanRequest } from '../../../types/plan'
import { toLocalInputValue } from '../../../utils/format'
import { PlaceField } from './PlaceField'

type Props = { onSubmit: (request: PlanRequest) => void; loading: boolean }

export function TripForm({ onSubmit, loading }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(() => toLocalInputValue(new Date()))
  const [load, setLoad] = useState(String(DEFAULT_LOAD_LB))
  const [interval, setInterval] = useState<Interval>(DEFAULT_INTERVAL)

  const now = new Date()
  const loadValue = Number(load)
  const loadValid = Number.isInteger(loadValue) && loadValue >= 1 && loadValue <= MAX_LOAD_LB
  const canSubmit = origin && destination && departure && loadValid && !loading

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!origin || !destination || !canSubmit) return
    onSubmit({
      origin,
      destination,
      departure: new Date(departure).toISOString(),
      load_lb: loadValue,
      interval_mi: interval,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <PlaceField label="Origin" value={origin} onChange={setOrigin} />
      <PlaceField label="Destination" value={destination} onChange={setDestination} />
      <TextField
        label="Departure"
        type="datetime-local"
        value={departure}
        onChange={(e) => setDeparture(e.target.value)}
        slotProps={{
          inputLabel: { shrink: true },
          htmlInput: {
            min: toLocalInputValue(now),
            max: toLocalInputValue(new Date(now.getTime() + FORECAST_HOURS * 3_600_000)),
          },
        }}
        required
      />
      <TextField
        label="Load weight"
        type="number"
        value={load}
        onChange={(e) => setLoad(e.target.value)}
        error={!loadValid}
        helperText={loadValid ? 'Pounds' : `Enter 1 to ${MAX_LOAD_LB.toLocaleString()} lb`}
        slotProps={{ htmlInput: { min: 1, max: MAX_LOAD_LB, step: 500, inputMode: 'numeric' } }}
        required
      />
      <div className="flex flex-col gap-1">
        <Typography variant="caption" color="text.secondary">
          Weather checkpoint every
        </Typography>
        <ToggleButtonGroup
          exclusive
          fullWidth
          value={interval}
          onChange={(_, value: Interval | null) => value && setInterval(value)}
        >
          {INTERVALS.map((miles) => (
            <ToggleButton key={miles} value={miles} sx={{ minHeight: 44 }}>
              {miles} mi
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </div>
      <Button type="submit" variant="contained" size="large" disabled={!canSubmit} loading={loading}>
        Find safest route
      </Button>
    </form>
  )
}
```

Check with Context7 that `Button` has the `loading` prop in the installed MUI version. If not, use `disabled` plus a `CircularProgress` start icon.

- [ ] **Step 4: Wire the form into App to check it by hand**

`frontend/src/app/App.tsx`:

```tsx
import { TripForm } from '../features/trip-form/components/TripForm'
import { usePlan } from '../features/routes/api/plan'

export function App() {
  const plan = usePlan()
  return (
    <div className="mx-auto max-w-md p-4">
      <TripForm onSubmit={plan.mutate} loading={plan.isPending} />
      <pre className="text-xs">{plan.data ? `${plan.data.routes.length} routes` : plan.error?.message}</pre>
    </div>
  )
}
```

- [ ] **Step 5: Check by hand**

Run the backend (`cd backend && uv run python manage.py runserver`) and the frontend (`cd frontend && npm run dev`). Type "Dallas", pick it, type "Denver", pick it, submit.
Expected: suggestions after 3 letters with no request per key press (check the Network tab), then "3 routes".

- [ ] **Step 6: Type check and commit**

Run: `cd frontend && npx tsc -b && npm test`

```bash
git add frontend/src
git commit -m "feat: add trip form with place autocomplete"
```

---

### Task 10: Route map with checkpoints and popups

**Files:**
- Create: `frontend/src/features/map/utils/to-geojson.ts`, `frontend/src/features/map/components/RouteMap.tsx`, `frontend/src/features/map/components/CheckpointPopup.tsx`

**Interfaces:**
- Consumes: `Route`, `Checkpoint`, `RISK_COLORS`, `BRAND_PRIMARY`, `MAP_STYLES`, `US_VIEW`.
- Produces:
  - `routesToGeoJSON(routes: Route[]): FeatureCollection<LineString, { id: number; recommended: boolean }>`
  - `checkpointsToGeoJSON(routes: Route[]): FeatureCollection<Point, CheckpointFeatureProps>` where `CheckpointFeatureProps = Omit<Checkpoint, 'level'> & { routeId: number; level: RiskKey }`
  - `<RouteMap routes: Route[]; selectedId: number | null; onSelect: (id: number) => void; children?: ReactNode />` rendering `<Map id="main">`. `children` render first, so they sit under the routes.

- [ ] **Step 1: Write the GeoJSON helpers**

`frontend/src/features/map/utils/to-geojson.ts`:

```ts
import type { FeatureCollection, LineString, Point } from 'geojson'
import { riskKey } from '../../../theme/risk'
import type { Checkpoint, RiskKey, Route } from '../../../types/plan'

export type CheckpointFeatureProps = Omit<Checkpoint, 'level'> & { routeId: number; level: RiskKey }

export function routesToGeoJSON(
  routes: Route[],
): FeatureCollection<LineString, { id: number; recommended: boolean }> {
  return {
    type: 'FeatureCollection',
    features: routes.map((route) => ({
      type: 'Feature',
      geometry: route.geometry,
      properties: { id: route.id, recommended: route.recommended },
    })),
  }
}

export function checkpointsToGeoJSON(
  routes: Route[],
): FeatureCollection<Point, CheckpointFeatureProps> {
  return {
    type: 'FeatureCollection',
    features: routes.flatMap((route) =>
      route.checkpoints.map((checkpoint) => ({
        type: 'Feature' as const,
        geometry: { type: 'Point' as const, coordinates: [checkpoint.lon, checkpoint.lat] },
        properties: { ...checkpoint, routeId: route.id, level: riskKey(checkpoint.level) },
      })),
    ),
  }
}
```

- [ ] **Step 2: Write `CheckpointPopup`**

`frontend/src/features/map/components/CheckpointPopup.tsx`:

```tsx
import { Popup } from 'react-map-gl/maplibre'
import { RISK_COLORS, RISK_LABELS } from '../../../theme/risk'
import { formatTime } from '../../../utils/format'
import type { CheckpointFeatureProps } from '../utils/to-geojson'

type Props = { checkpoint: CheckpointFeatureProps; onClose: () => void }

function value(n: number | null, unit: string, digits = 0) {
  return n === null ? '—' : `${n.toFixed(digits)} ${unit}`
}

export function CheckpointPopup({ checkpoint, onClose }: Props) {
  return (
    <Popup
      longitude={checkpoint.lon}
      latitude={checkpoint.lat}
      onClose={onClose}
      closeOnClick={false}
      maxWidth="260px"
    >
      <div className="flex flex-col gap-1 text-sm text-neutral-900">
        <div className="flex items-center gap-2 font-semibold">
          <span
            className="inline-block size-3 rounded-full"
            style={{ background: RISK_COLORS[checkpoint.level] }}
          />
          {RISK_LABELS[checkpoint.level]} · mile {Math.round(checkpoint.mile)}
        </div>
        <div>ETA {formatTime(checkpoint.eta)}</div>
        <div>
          Wind {value(checkpoint.wind_mph, 'mph')} (gust {value(checkpoint.gust_mph, 'mph')})
        </div>
        <div>Rain {value(checkpoint.rain_in_hr, 'in/hr', 2)}</div>
        <div>Snow {value(checkpoint.snow_in_hr, 'in/hr', 2)}</div>
      </div>
    </Popup>
  )
}
```

- [ ] **Step 3: Write `RouteMap`**

Check with Context7: react-map-gl `Map` from `react-map-gl/maplibre`, `Source`, `Layer`, `interactiveLayerIds`, `onClick` features, `useMap`, `fitBounds`; MapLibre `LngLatBounds`.

`frontend/src/features/map/components/RouteMap.tsx`:

```tsx
import { useColorScheme } from '@mui/material/styles'
import { LngLatBounds } from 'maplibre-gl'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import Map, {
  Layer,
  NavigationControl,
  Source,
  type MapLayerMouseEvent,
  type MapRef,
} from 'react-map-gl/maplibre'
import { MAP_STYLES, US_VIEW } from '../../../config/constants'
import { RISK_COLORS } from '../../../theme/risk'
import { BRAND_PRIMARY } from '../../../theme/theme'
import type { Route } from '../../../types/plan'
import {
  checkpointsToGeoJSON,
  routesToGeoJSON,
  type CheckpointFeatureProps,
} from '../utils/to-geojson'
import { CheckpointPopup } from './CheckpointPopup'

type Props = {
  routes: Route[]
  selectedId: number | null
  onSelect: (id: number) => void
  children?: ReactNode
}

const levelColor = [
  'match',
  ['get', 'level'],
  ...Object.entries(RISK_COLORS).flat(),
  RISK_COLORS.no_data,
] as unknown as string

export function RouteMap({ routes, selectedId, onSelect, children }: Props) {
  const mapRef = useRef<MapRef>(null)
  const { mode, systemMode } = useColorScheme()
  const dark = (mode === 'system' ? systemMode : mode) === 'dark'
  const [popup, setPopup] = useState<CheckpointFeatureProps | null>(null)
  const [cursor, setCursor] = useState('')

  const routeData = useMemo(() => routesToGeoJSON(routes), [routes])
  const checkpointData = useMemo(() => checkpointsToGeoJSON(routes), [routes])

  useEffect(() => {
    setPopup(null)
    if (!routes.length) return
    const bounds = new LngLatBounds()
    for (const route of routes) {
      for (const [lon, lat] of route.geometry.coordinates) bounds.extend([lon, lat])
    }
    mapRef.current?.fitBounds(bounds, { padding: 48, duration: 800 })
  }, [routes])

  function handleClick(event: MapLayerMouseEvent) {
    const feature = event.features?.[0]
    if (!feature) return
    if (feature.layer.id === 'checkpoints') {
      const props = feature.properties as CheckpointFeatureProps
      setPopup(props)
      onSelect(props.routeId)
    } else {
      onSelect(feature.properties.id as number)
    }
  }

  const selectedFilter = ['==', ['get', 'id'], selectedId ?? -1] as unknown as boolean

  return (
    <Map
      id="main"
      ref={mapRef}
      initialViewState={US_VIEW}
      mapStyle={dark ? MAP_STYLES.dark : MAP_STYLES.light}
      interactiveLayerIds={['route-hit', 'checkpoints']}
      onClick={handleClick}
      onMouseEnter={() => setCursor('pointer')}
      onMouseLeave={() => setCursor('')}
      cursor={cursor}
      style={{ width: '100%', height: '100%' }}
    >
      <NavigationControl position="top-right" showCompass={false} />
      {children}
      <Source id="routes" type="geojson" data={routeData}>
        <Layer
          id="route-line"
          type="line"
          layout={{ 'line-join': 'round', 'line-cap': 'round' }}
          paint={{ 'line-color': '#7d8b93', 'line-width': 4, 'line-opacity': 0.8 }}
        />
        <Layer
          id="route-selected-casing"
          type="line"
          filter={selectedFilter}
          layout={{ 'line-join': 'round', 'line-cap': 'round' }}
          paint={{ 'line-color': '#ffffff', 'line-width': 9 }}
        />
        <Layer
          id="route-selected"
          type="line"
          filter={selectedFilter}
          layout={{ 'line-join': 'round', 'line-cap': 'round' }}
          paint={{ 'line-color': BRAND_PRIMARY[dark ? 'dark' : 'light'], 'line-width': 6 }}
        />
        <Layer
          id="route-hit"
          type="line"
          paint={{ 'line-color': '#000000', 'line-width': 18, 'line-opacity': 0 }}
        />
      </Source>
      <Source id="checkpoints" type="geojson" data={checkpointData}>
        <Layer
          id="checkpoints"
          type="circle"
          paint={{
            'circle-color': levelColor,
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 4, 10, 8],
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 1.5,
          }}
        />
      </Source>
      {popup && <CheckpointPopup checkpoint={popup} onClose={() => setPopup(null)} />}
    </Map>
  )
}
```

MapLibre needs real color values, not MUI CSS variables, so the map reads `BRAND_PRIMARY` and `RISK_COLORS` directly.

- [ ] **Step 4: Show the map in App to check by hand**

`frontend/src/app/App.tsx`:

```tsx
import { useState } from 'react'
import { RouteMap } from '../features/map/components/RouteMap'
import { usePlan } from '../features/routes/api/plan'
import { TripForm } from '../features/trip-form/components/TripForm'

export function App() {
  const plan = usePlan()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const routes = plan.data?.routes ?? []

  return (
    <div className="flex h-dvh">
      <aside className="w-[400px] overflow-y-auto p-4">
        <TripForm
          onSubmit={(request) =>
            plan.mutate(request, {
              onSuccess: (data) => setSelectedId(data.routes[0]?.id ?? null),
            })
          }
          loading={plan.isPending}
        />
      </aside>
      <main className="relative flex-1">
        <RouteMap routes={routes} selectedId={selectedId} onSelect={setSelectedId} />
      </main>
    </div>
  )
}
```

- [ ] **Step 5: Check by hand**

Run both servers. Plan Dallas → Denver.
Expected: the map fits the 3 routes; the recommended route is drawn on top in teal; checkpoint dots show risk colors; a click on a dot opens the popup with ETA and weather; a click on a gray route selects it.

- [ ] **Step 6: Type check and commit**

Run: `cd frontend && npx tsc -b && npm test`

```bash
git add frontend/src
git commit -m "feat: show routes and checkpoint risk on the map"
```

---

### Task 11: Route cards, warnings, and the recommendation

**Files:**
- Create: `frontend/src/features/routes/components/RiskBar.tsx`, `frontend/src/features/routes/components/RouteCard.tsx`, `frontend/src/features/routes/components/RouteCards.tsx`, `frontend/src/components/WarningBanner.tsx`
- Test: `frontend/src/features/routes/components/RouteCard.test.tsx`

**Interfaces:**
- Consumes: `Route`, `RISK_COLORS`, `RISK_LABELS`, `LEVELS`, formatters.
- Produces:
  - `<RiskBar miles: Route['miles_by_level'] />`
  - `<RouteCard route: Route; letter: string; selected: boolean; onSelect: () => void />`
  - `<RouteCards routes: Route[]; selectedId: number | null; onSelect: (id: number) => void />`
  - `<WarningBanner warnings: string[] />`
  - `routeLetter(id: number): string` (exported from `RouteCards.tsx`): 0 → "A", 1 → "B", 2 → "C"

- [ ] **Step 1: Write the failing component test**

`frontend/src/features/routes/components/RouteCard.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Route } from '../../../types/plan'
import { RouteCard } from './RouteCard'

const route: Route = {
  id: 0,
  geometry: { type: 'LineString', coordinates: [] },
  distance_mi: 808.4,
  duration_s: 13 * 3600 + 5 * 60,
  source: 'tomtom',
  checkpoints: [],
  miles_by_level: { low: 700, moderate: 58.4, high: 50, severe: 0, no_travel: 0, no_data: 0 },
  avg_risk: 0.2,
  rank: 1,
  recommended: true,
  reason: 'Fewest High miles',
}

describe('RouteCard', () => {
  it('shows the summary and the recommendation', () => {
    render(<RouteCard route={route} letter="A" selected={false} onSelect={() => {}} />)
    expect(screen.getByText('Recommended')).toBeInTheDocument()
    expect(screen.getByText('808 mi')).toBeInTheDocument()
    expect(screen.getByText('13 h 5 min')).toBeInTheDocument()
    expect(screen.getByText('Fewest High miles')).toBeInTheDocument()
    expect(screen.getByText(/50 mi High/)).toBeInTheDocument()
  })

  it('selects on click', async () => {
    const onSelect = vi.fn()
    render(<RouteCard route={route} letter="A" selected={false} onSelect={onSelect} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onSelect).toHaveBeenCalledOnce()
  })
})
```

- [ ] **Step 2: Run and see it fail**

Run: `cd frontend && npm test`
Expected: FAIL (module not found).

- [ ] **Step 3: Write the components**

`frontend/src/features/routes/components/RiskBar.tsx`:

```tsx
import { LEVELS, RISK_COLORS, RISK_LABELS } from '../../../theme/risk'
import type { Route } from '../../../types/plan'
import { formatMiles } from '../../../utils/format'

const KEYS = [...LEVELS, 'no_data'] as const

export function RiskBar({ miles }: { miles: Route['miles_by_level'] }) {
  const total = KEYS.reduce((sum, key) => sum + miles[key], 0) || 1
  const shown = KEYS.filter((key) => miles[key] > 0)
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex h-2 w-full overflow-hidden rounded-full" role="img" aria-label="Miles by risk level">
        {shown.map((key) => (
          <div key={key} style={{ width: `${(miles[key] / total) * 100}%`, background: RISK_COLORS[key] }} />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs opacity-80">
        {shown.map((key) => (
          <span key={key}>
            {formatMiles(miles[key])} {RISK_LABELS[key]}
          </span>
        ))}
      </div>
    </div>
  )
}
```

`frontend/src/features/routes/components/RouteCard.tsx`:

```tsx
import Card from '@mui/material/Card'
import CardActionArea from '@mui/material/CardActionArea'
import Chip from '@mui/material/Chip'
import Typography from '@mui/material/Typography'
import type { Route } from '../../../types/plan'
import { formatDuration, formatMiles } from '../../../utils/format'
import { RiskBar } from './RiskBar'

type Props = { route: Route; letter: string; selected: boolean; onSelect: () => void }

export function RouteCard({ route, letter, selected, onSelect }: Props) {
  return (
    <Card
      variant="outlined"
      sx={{ borderColor: selected ? 'primary.main' : undefined, borderWidth: selected ? 2 : 1 }}
    >
      <CardActionArea onClick={onSelect} aria-pressed={selected} sx={{ p: 2 }}>
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-2">
            <Typography variant="subtitle1" fontWeight={600}>
              Route {letter}
            </Typography>
            {route.recommended && <Chip label="Recommended" color="primary" size="small" />}
          </div>
          <div className="flex gap-4 text-sm">
            <span>{formatMiles(route.distance_mi)}</span>
            <span>{formatDuration(route.duration_s)}</span>
            <span>
              Avg risk {route.avg_risk === null ? '—' : route.avg_risk.toFixed(2)}
            </span>
          </div>
          <RiskBar miles={route.miles_by_level} />
          <Typography variant="body2" color="text.secondary">
            {route.reason}
          </Typography>
        </div>
      </CardActionArea>
    </Card>
  )
}
```

`frontend/src/features/routes/components/RouteCards.tsx`:

```tsx
import type { Route } from '../../../types/plan'
import { RouteCard } from './RouteCard'

export function routeLetter(id: number): string {
  return String.fromCharCode(65 + id)
}

type Props = { routes: Route[]; selectedId: number | null; onSelect: (id: number) => void }

export function RouteCards({ routes, selectedId, onSelect }: Props) {
  return (
    <div className="flex flex-col gap-3">
      {routes.map((route) => (
        <RouteCard
          key={route.id}
          route={route}
          letter={routeLetter(route.id)}
          selected={route.id === selectedId}
          onSelect={() => onSelect(route.id)}
        />
      ))}
    </div>
  )
}
```

`frontend/src/components/WarningBanner.tsx`:

```tsx
import Alert from '@mui/material/Alert'

const MESSAGES: Record<string, { severity: 'error' | 'warning' | 'info'; text: string }> = {
  no_safe_route: { severity: 'error', text: 'No safe route in this window. Every route has No Travel miles.' },
  beyond_forecast: { severity: 'warning', text: 'Part of the trip is past the 48 h forecast. Those miles show as No data.' },
  fallback_routing: { severity: 'info', text: 'Truck routing was not available. These are car routes, so times can be short for a truck.' },
  fewer_routes: { severity: 'info', text: 'Fewer than 3 different routes exist for this trip.' },
}

export function WarningBanner({ warnings }: { warnings: string[] }) {
  return (
    <div className="flex flex-col gap-2">
      {warnings
        .filter((code) => code in MESSAGES)
        .map((code) => (
          <Alert key={code} severity={MESSAGES[code].severity} variant="outlined">
            {MESSAGES[code].text}
          </Alert>
        ))}
    </div>
  )
}
```

- [ ] **Step 4: Run and see it pass**

Run: `cd frontend && npm test`
Expected: all pass.

- [ ] **Step 5: Add the cards, the warnings, and the error to App**

In `frontend/src/app/App.tsx`, under `<TripForm ... />` in the `aside`, add:

```tsx
{plan.error && <Alert severity="error">{plan.error.message}</Alert>}
{plan.data && <WarningBanner warnings={plan.data.warnings} />}
<RouteCards routes={routes} selectedId={selectedId} onSelect={setSelectedId} />
```

Wrap the `aside` children in `<div className="flex flex-col gap-4">`. Import `Alert` from `@mui/material/Alert`, `WarningBanner`, `RouteCards`.

- [ ] **Step 6: Check by hand, type check, commit**

Check: a click on a card highlights that route on the map; a click on a route on the map highlights its card.
Run: `cd frontend && npx tsc -b && npm test`

```bash
git add frontend/src
git commit -m "feat: add route cards with risk breakdown and warnings"
```

---

### Task 12: Corridor heatmap and 0–48 h slider

**Files:**
- Create: `frontend/src/features/weather-heatmap/utils/heat.ts`, `frontend/src/features/weather-heatmap/components/HeatmapLayer.tsx`, `frontend/src/features/weather-heatmap/components/ForecastSlider.tsx`, `frontend/src/features/weather-heatmap/components/RiskLegend.tsx`
- Test: `frontend/src/features/weather-heatmap/utils/heat.test.ts`

**Interfaces:**
- Consumes: `HeatCell`, `RISK_COLORS`, `RISK_LABELS`, `LEVELS`, `FORECAST_HOURS`, `formatTime`, `useMap` (react-map-gl, map id `main` from Task 10).
- Produces:
  - `HEAT_LAYER_ID = 'corridor-heat'`
  - `cellsToGeoJSON(cells: HeatCell[]): FeatureCollection<Point, Record<string, number>>` with properties `h0`..`h47`
  - `heatWeight(hour: number): ExpressionSpecification` → `['/', ['max', ['get', 'h{hour}'], 0], 4]`
  - `<HeatmapLayer cells: HeatCell[] />` (child of `RouteMap`)
  - `<ForecastSlider startHour: string />` (inside `MapProvider`)
  - `<RiskLegend />`

- [ ] **Step 1: Write the failing test**

`frontend/src/features/weather-heatmap/utils/heat.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { cellsToGeoJSON, heatWeight } from './heat'

describe('heat', () => {
  it('flattens hourly levels into properties', () => {
    const levels = Array.from({ length: 48 }, (_, i) => (i === 5 ? 3 : 0))
    const data = cellsToGeoJSON([{ lat: 30, lon: -97, levels }])
    const feature = data.features[0]
    expect(feature.geometry.coordinates).toEqual([-97, 30])
    expect(feature.properties.h5).toBe(3)
    expect(feature.properties.h47).toBe(0)
  })

  it('builds the weight expression for an hour', () => {
    expect(heatWeight(12)).toEqual(['/', ['max', ['get', 'h12'], 0], 4])
  })
})
```

- [ ] **Step 2: Run and see it fail**

Run: `cd frontend && npm test`
Expected: FAIL.

- [ ] **Step 3: Write `heat.ts`**

`frontend/src/features/weather-heatmap/utils/heat.ts`:

```ts
import type { FeatureCollection, Point } from 'geojson'
import type { ExpressionSpecification } from 'maplibre-gl'
import type { HeatCell } from '../../../types/plan'

export const HEAT_LAYER_ID = 'corridor-heat'

export function cellsToGeoJSON(cells: HeatCell[]): FeatureCollection<Point, Record<string, number>> {
  return {
    type: 'FeatureCollection',
    features: cells.map((cell) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [cell.lon, cell.lat] },
      properties: Object.fromEntries(cell.levels.map((level, hour) => [`h${hour}`, level])),
    })),
  }
}

export function heatWeight(hour: number): ExpressionSpecification {
  return ['/', ['max', ['get', `h${hour}`], 0], 4]
}
```

- [ ] **Step 4: Write `HeatmapLayer`**

Check the MapLibre heatmap layer paint properties with Context7 (`heatmap-weight`, `heatmap-radius`, `heatmap-color`, `heatmap-opacity`).

`frontend/src/features/weather-heatmap/components/HeatmapLayer.tsx`:

```tsx
import { memo, useMemo } from 'react'
import { Layer, Source } from 'react-map-gl/maplibre'
import { RISK_COLORS } from '../../../theme/risk'
import type { HeatCell } from '../../../types/plan'
import { cellsToGeoJSON, HEAT_LAYER_ID, heatWeight } from '../utils/heat'

export const HeatmapLayer = memo(function HeatmapLayer({ cells }: { cells: HeatCell[] }) {
  const data = useMemo(() => cellsToGeoJSON(cells), [cells])
  return (
    <Source id="corridor" type="geojson" data={data}>
      <Layer
        id={HEAT_LAYER_ID}
        type="heatmap"
        paint={{
          'heatmap-weight': heatWeight(0),
          'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 3, 0.6, 8, 1.2],
          'heatmap-radius': ['interpolate', ['exponential', 2], ['zoom'], 3, 10, 6, 40, 9, 160],
          'heatmap-opacity': 0.7,
          'heatmap-color': [
            'interpolate',
            ['linear'],
            ['heatmap-density'],
            0,
            'rgba(0,0,0,0)',
            0.15,
            RISK_COLORS.moderate,
            0.4,
            RISK_COLORS.high,
            0.65,
            RISK_COLORS.severe,
            0.9,
            RISK_COLORS.no_travel,
          ],
        }}
      />
    </Source>
  )
})
```

The `paint` object only changes when `cells` change, so the slider's `setPaintProperty` call is not overwritten by React.

- [ ] **Step 5: Write `ForecastSlider` and `RiskLegend`**

`frontend/src/features/weather-heatmap/components/ForecastSlider.tsx`:

```tsx
import PauseRounded from '@mui/icons-material/PauseRounded'
import PlayArrowRounded from '@mui/icons-material/PlayArrowRounded'
import IconButton from '@mui/material/IconButton'
import Slider from '@mui/material/Slider'
import Typography from '@mui/material/Typography'
import { useEffect, useState } from 'react'
import { useMap } from 'react-map-gl/maplibre'
import { FORECAST_HOURS } from '../../../config/constants'
import { formatTime } from '../../../utils/format'
import { HEAT_LAYER_ID, heatWeight } from '../utils/heat'

const MARKS = [0, 12, 24, 36, 47].map((value) => ({ value, label: `+${value}h` }))

export function ForecastSlider({ startHour }: { startHour: string }) {
  const { main } = useMap()
  const [hour, setHour] = useState(0)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    const map = main?.getMap()
    if (map?.getLayer(HEAT_LAYER_ID)) map.setPaintProperty(HEAT_LAYER_ID, 'heatmap-weight', heatWeight(hour))
  }, [main, hour])

  useEffect(() => {
    if (!playing) return
    const id = window.setInterval(() => setHour((h) => (h + 1) % FORECAST_HOURS), 500)
    return () => window.clearInterval(id)
  }, [playing])

  const label = formatTime(new Date(Date.parse(startHour) + hour * 3_600_000).toISOString())

  return (
    <div className="flex items-center gap-3">
      <IconButton
        onClick={() => setPlaying((p) => !p)}
        aria-label={playing ? 'Pause forecast' : 'Play forecast'}
        sx={{ width: 44, height: 44 }}
      >
        {playing ? <PauseRounded /> : <PlayArrowRounded />}
      </IconButton>
      <div className="flex min-w-0 flex-1 flex-col">
        <Typography variant="caption" aria-live="polite">
          Forecast {label} (+{hour} h)
        </Typography>
        <Slider
          value={hour}
          min={0}
          max={FORECAST_HOURS - 1}
          step={1}
          marks={MARKS}
          onChange={(_, value) => setHour(value as number)}
          aria-label="Forecast hour"
          valueLabelDisplay="off"
        />
      </div>
    </div>
  )
}
```

`frontend/src/features/weather-heatmap/components/RiskLegend.tsx`:

```tsx
import { LEVELS, RISK_COLORS, RISK_LABELS } from '../../../theme/risk'

export function RiskLegend() {
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-1 text-xs" aria-label="Risk levels">
      {LEVELS.map((level) => (
        <li key={level} className="flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-full" style={{ background: RISK_COLORS[level] }} />
          {RISK_LABELS[level]}
        </li>
      ))}
    </ul>
  )
}
```

- [ ] **Step 6: Add the heatmap and slider to App**

In `frontend/src/app/App.tsx`:
- Wrap the whole return in `<MapProvider>` (from `react-map-gl/maplibre`).
- Pass `<HeatmapLayer cells={plan.data.heatmap.cells} />` as the child of `RouteMap` when `plan.data` exists.
- In `main`, after the map, add an overlay when `plan.data` exists:

```tsx
<Paper className="absolute right-3 bottom-3 flex w-[min(420px,calc(100%-24px))] flex-col gap-1 p-3" elevation={3}>
  <ForecastSlider key={plan.data.heatmap.start_hour + plan.submittedAt} startHour={plan.data.heatmap.start_hour} />
  <RiskLegend />
</Paper>
```

The `key` resets the slider to hour 0 for each new plan, which matches the new layer's initial paint.

- [ ] **Step 7: Check smoothness by hand**

Run both servers and plan Dallas → Denver. Open Chrome DevTools → Performance, record while you drag the slider and while it plays.
Expected: no long tasks over 50 ms from React during the drag; the React DevTools Profiler shows only `ForecastSlider` re-rendering. The heatmap colors follow the corridor. If Low areas look washed out or a single Severe cell looks too strong, tune `heatmap-radius` and `heatmap-intensity` only.

- [ ] **Step 8: Test, type check, commit**

Run: `cd frontend && npm test && npx tsc -b`

```bash
git add frontend/src
git commit -m "feat: add corridor risk heatmap with 48 hour forecast slider"
```

---

### Task 13: Responsive app shell (desktop, tablet, mobile portrait and landscape)

**Files:**
- Create: `frontend/src/app/AppShell.tsx`
- Modify: `frontend/src/app/App.tsx`

**Interfaces:**
- Produces: `<AppShell panel: ReactNode; map: ReactNode; overlay?: ReactNode />`. Side panel when the screen is `md` or wider, or in landscape. Bottom sheet in portrait below `md`.

- [ ] **Step 1: Write `AppShell`**

`frontend/src/app/AppShell.tsx`:

```tsx
import KeyboardArrowDownRounded from '@mui/icons-material/KeyboardArrowDownRounded'
import KeyboardArrowUpRounded from '@mui/icons-material/KeyboardArrowUpRounded'
import IconButton from '@mui/material/IconButton'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import useMediaQuery from '@mui/material/useMediaQuery'
import { useTheme } from '@mui/material/styles'
import { useState, type ReactNode } from 'react'

type Props = { panel: ReactNode; map: ReactNode; overlay?: ReactNode }

export function AppShell({ panel, map, overlay }: Props) {
  const theme = useTheme()
  const wide = useMediaQuery(theme.breakpoints.up('md'))
  const landscape = useMediaQuery('(orientation: landscape)')
  const [open, setOpen] = useState(true)

  if (wide || landscape) {
    return (
      <div className="flex h-dvh w-full">
        <Paper
          square
          elevation={0}
          className="flex h-full w-[320px] shrink-0 flex-col overflow-y-auto border-r border-black/10 lg:w-[400px]"
          sx={{ pl: 'env(safe-area-inset-left)' }}
        >
          <div className="flex flex-col gap-4 p-4">{panel}</div>
        </Paper>
        <main className="relative min-w-0 flex-1">
          {map}
          {overlay && (
            <div className="absolute right-3 bottom-3 w-[min(420px,calc(100%-24px))]">{overlay}</div>
          )}
        </main>
      </div>
    )
  }

  return (
    <div className="relative h-dvh w-full overflow-hidden">
      <main className="absolute inset-0">{map}</main>
      <Paper
        elevation={8}
        className="absolute inset-x-0 bottom-0 flex flex-col rounded-t-2xl transition-[max-height] duration-300"
        sx={{ maxHeight: open ? '70dvh' : '120px', pb: 'env(safe-area-inset-bottom)' }}
      >
        <div className="flex items-center justify-between px-4 pt-2">
          <Typography variant="subtitle2">Trip and routes</Typography>
          <IconButton
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? 'Collapse panel' : 'Expand panel'}
            aria-expanded={open}
            sx={{ width: 44, height: 44 }}
          >
            {open ? <KeyboardArrowDownRounded /> : <KeyboardArrowUpRounded />}
          </IconButton>
        </div>
        <div className="flex flex-col gap-4 overflow-y-auto p-4 pt-1">
          {overlay}
          {panel}
        </div>
      </Paper>
    </div>
  )
}
```

In portrait mobile the slider and legend (`overlay`) move into the sheet, at the top, so they stay reachable without covering the map. `AppShell` alone decides where the overlay sits. Do not position it with Tailwind breakpoints in `App`, because Tailwind `md` (768 px) and MUI `md` (900 px) differ.

- [ ] **Step 2: Use `AppShell` in App**

Final `frontend/src/app/App.tsx`:

```tsx
import Alert from '@mui/material/Alert'
import Paper from '@mui/material/Paper'
import { useState } from 'react'
import { MapProvider } from 'react-map-gl/maplibre'
import { WarningBanner } from '../components/WarningBanner'
import { RouteMap } from '../features/map/components/RouteMap'
import { usePlan } from '../features/routes/api/plan'
import { RouteCards } from '../features/routes/components/RouteCards'
import { TripForm } from '../features/trip-form/components/TripForm'
import { ForecastSlider } from '../features/weather-heatmap/components/ForecastSlider'
import { HeatmapLayer } from '../features/weather-heatmap/components/HeatmapLayer'
import { RiskLegend } from '../features/weather-heatmap/components/RiskLegend'
import { AppShell } from './AppShell'

export function App() {
  const plan = usePlan()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const routes = plan.data?.routes ?? []

  const panel = (
    <>
      <TripForm
        onSubmit={(request) =>
          plan.mutate(request, { onSuccess: (data) => setSelectedId(data.routes[0]?.id ?? null) })
        }
        loading={plan.isPending}
      />
      {plan.error && <Alert severity="error">{plan.error.message}</Alert>}
      {plan.data && <WarningBanner warnings={plan.data.warnings} />}
      <RouteCards routes={routes} selectedId={selectedId} onSelect={setSelectedId} />
    </>
  )

  const overlay = plan.data && (
    <Paper elevation={3} className="flex flex-col gap-1 p-3">
      <ForecastSlider
        key={`${plan.data.heatmap.start_hour}-${plan.submittedAt}`}
        startHour={plan.data.heatmap.start_hour}
      />
      <RiskLegend />
    </Paper>
  )

  return (
    <MapProvider>
      <AppShell
        panel={panel}
        overlay={overlay}
        map={
          <RouteMap routes={routes} selectedId={selectedId} onSelect={setSelectedId}>
            {plan.data && <HeatmapLayer cells={plan.data.heatmap.cells} />}
          </RouteMap>
        }
      />
    </MapProvider>
  )
}
```

- [ ] **Step 3: Add a thin loading bar on the map**

In `AppShell` props add `loading?: boolean`, and render `{loading && <LinearProgress className="absolute inset-x-0 top-0 z-10" />}` inside both `main` elements. Pass `loading={plan.isPending}` from App.

In App, while `plan.isPending`, render 3 MUI `<Skeleton variant="rounded" height={132} />` in place of `RouteCards` (spec section 7: skeleton cards).

- [ ] **Step 4: Check every screen by hand (skill: agent-browser or run)**

Open the app in Chrome DevTools device mode, plan a trip, and check each size:

| Size | Orientation | Expected |
|---|---|---|
| 1440×900 | landscape | Side panel 400 px, slider overlay bottom right |
| 1024×768 | landscape | Side panel 320 px |
| 768×1024 | portrait | Bottom sheet, map fills the screen |
| 390×844 | portrait | Bottom sheet, slider at the top of the sheet, all touch targets ≥ 44 px |
| 844×390 | landscape | Side panel 320 px, full-height map, slider overlay |

Take a screenshot of each for the README.

- [ ] **Step 5: Polish pass with the design skills**

Run the design skills on the working UI: `design-taste-frontend` (overall direction and layout), `frontend-design` (type and visual identity), `emil-design-eng` (spacing, alignment, motion details), `dataviz` (validate `RISK_COLORS` for contrast and color-blind safety in light and dark), `vercel-react-best-practices` (re-render audit). Apply only changes inside the spec. Re-run `npm test && npx tsc -b`.

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat: add responsive layout for desktop, tablet, and mobile"
```

---

## Phase 3: Verify, deploy, document (skills: superpowers:verification-before-completion, ponytail:ponytail-review, superpowers:systematic-debugging, run, agent-browser)

### Task 14: End-to-end smoke test

**Files:**
- Create: `frontend/playwright.config.ts`, `frontend/e2e/plan.spec.ts`

- [ ] **Step 1: Install the browser**

Run: `cd frontend && npx playwright install chromium`

- [ ] **Step 2: Write the config and the test**

`frontend/playwright.config.ts`:

```ts
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: { baseURL: 'http://localhost:5173' },
  webServer: [
    { command: 'uv run python manage.py runserver 8000', cwd: '../backend', port: 8000, reuseExistingServer: true },
    { command: 'npm run dev', port: 5173, reuseExistingServer: true },
  ],
})
```

`frontend/e2e/plan.spec.ts`:

```ts
import { expect, test } from '@playwright/test'

test('plans a trip and moves the forecast slider', async ({ page }) => {
  await page.goto('/')

  await page.getByLabel('Origin').fill('Dallas')
  await page.getByRole('option', { name: /Dallas, Texas/ }).first().click()
  await page.getByLabel('Destination').fill('Denver')
  await page.getByRole('option', { name: /Denver/ }).first().click()
  await page.getByRole('button', { name: 'Find safest route' }).click()

  await expect(page.getByText('Recommended')).toBeVisible({ timeout: 45_000 })
  await expect(page.getByText(/^Route [ABC]$/)).toHaveCount(3)

  const slider = page.getByRole('slider', { name: 'Forecast hour' })
  await slider.focus()
  await page.keyboard.press('End')
  await expect(page.getByText(/\(\+47 h\)/)).toBeVisible()
})
```

- [ ] **Step 3: Run it**

Run: `cd frontend && npm run e2e`
Expected: 1 passed. It uses the live public APIs, so a failure from an outside outage is possible; run it again before you treat it as a bug.

- [ ] **Step 4: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e
git commit -m "test: add end-to-end smoke test for trip planning"
```

---

### Task 15: Docker, Caddy, and Oracle deploy

**Files:**
- Create: `backend/Dockerfile`, `backend/.dockerignore`, `frontend/Dockerfile`, `frontend/.dockerignore`, `docker-compose.yml`, `Caddyfile`, `.env.example`

- [ ] **Step 1: Check the current stable image tags**

Check Docker Hub (or Context7) for the current stable `python:<x.y>-slim`, `node:<lts>-alpine`, `redis:<major>-alpine`, `caddy:<major>-alpine`, and the uv image docs ("Using uv in Docker"). Use those tags below in place of the ones written here if newer stable ones exist.

- [ ] **Step 2: Write the backend image**

`backend/Dockerfile`:

```dockerfile
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY . .
ENV PATH="/app/.venv/bin:$PATH" DJANGO_SETTINGS_MODULE=config.settings.production
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60"]
```

Pin the uv image to the version shown by `uv --version` (for example `ghcr.io/astral-sh/uv:0.x.y`) instead of `latest`.

`backend/.dockerignore`:

```
.venv
__pycache__
.pytest_cache
.ruff_cache
```

- [ ] **Step 3: Write the web image (frontend build served by Caddy)**

`frontend/Dockerfile` (build context is the repo root):

```dockerfile
FROM node:24-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
```

`frontend/.dockerignore`:

```
node_modules
dist
test-results
playwright-report
```

`Caddyfile`:

```
{$SITE_ADDRESS:localhost} {
	encode zstd gzip
	handle /api/* {
		reverse_proxy backend:8000
	}
	handle {
		root * /srv
		try_files {path} /index.html
		file_server
	}
}
```

- [ ] **Step 4: Write Compose and the env example**

`docker-compose.yml`:

```yaml
services:
  backend:
    build: ./backend
    environment:
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:?set DJANGO_SECRET_KEY}
      DJANGO_ALLOWED_HOSTS: ${DJANGO_ALLOWED_HOSTS:-localhost}
      TOMTOM_API_KEY: ${TOMTOM_API_KEY:-}
      REDIS_URL: redis://redis:6379/0
    depends_on: [redis]
    restart: unless-stopped
  redis:
    image: redis:8-alpine
    restart: unless-stopped
  web:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports: ["80:80", "443:443"]
    environment:
      SITE_ADDRESS: ${SITE_ADDRESS:-localhost}
    volumes: [caddy_data:/data]
    depends_on: [backend]
    restart: unless-stopped
volumes:
  caddy_data:
```

`.env.example`:

```
DJANGO_SECRET_KEY=change-me
DJANGO_ALLOWED_HOSTS=your-domain.example
SITE_ADDRESS=your-domain.example
TOMTOM_API_KEY=
```

- [ ] **Step 5: Run the stack locally**

Run:

```bash
cp .env.example .env
sed -i '' "s/change-me/$(openssl rand -hex 32)/; s/your-domain.example/localhost/g" .env
docker compose up --build -d
curl -sk https://localhost/api/health
```

Expected: `{"status":"ok"}`. Open `https://localhost`, accept the local certificate, and plan a trip.

- [ ] **Step 6: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore frontend/Dockerfile frontend/.dockerignore docker-compose.yml Caddyfile .env.example
git commit -m "chore: add docker compose deploy with caddy and redis"
```

- [ ] **Step 7: Deploy to the Oracle VM**

**Caution:** These steps change a public server. Confirm the VM, the domain, and the open ports with the user before you run them.

On a new Oracle VM (Ubuntu, Ampere A1 works):
1. In the Oracle console, add ingress rules for TCP 80 and 443 to the VCN security list.
2. On the VM, open the same ports in the OS firewall:
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```
3. Install Docker with the official convenience script or apt repo (check docs.docker.com), and add the user to the `docker` group.
4. Clone the repo, create `.env` with a new secret, the `TOMTOM_API_KEY`, `DJANGO_ALLOWED_HOSTS` and `SITE_ADDRESS` set to the domain. With no domain, use `<public-ip>.sslip.io`.
5. Run `docker compose up --build -d`. Caddy gets the HTTPS certificate on the first request.
6. Check: `curl -s https://<domain>/api/health` returns `{"status":"ok"}`, and one full plan works in a phone browser.

---

### Task 16: README, final review, and Loom outline

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the README**

`README.md` sections, in this order (fill each with real values from the running app):
1. Title, one-line purpose, live link, one screenshot (desktop) and one (mobile).
2. **How to run locally:** backend (`cd backend && uv sync && uv run python manage.py runserver`), frontend (`cd frontend && npm ci && npm run dev`), tests (`uv run pytest`, `npm test`, `npm run e2e`), and Docker (`docker compose up --build`).
3. **How it works:** the data-flow diagram from spec section 4, and the APIs used (TomTom truck routing, OSRM fallback, Open-Meteo, Photon), and how to get a free TomTom key (developer.tomtom.com, no credit card) and set `TOMTOM_API_KEY`.
4. **Risk rules:** the threshold table, the edge choices (spec 5.2), the load rules, and No Data.
5. **Recommendation:** the ranking order, No Travel last, the mile-weighted average risk, and the segment ownership rule.
6. **Performance:** one plan response, the 0.25° grid snap and dedupe (with the cell count and timing from Task 7 Step 9), the per-cell cache, and the slider that changes a paint property with no React re-render.
7. **Limits:** the TomTom free quota (20K routing requests/month) and the OSRM car fallback, public demo servers (rate limits), the 48 h forecast, and the ~17 mi weather grid.

- [ ] **Step 2: Over-engineering review**

Run `ponytail:ponytail-review` on the whole repo. Apply only deletions that keep every test green.

- [ ] **Step 3: Final verification (skill: superpowers:verification-before-completion)**

Run and read the output of each:

```bash
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd ../frontend && npm test && npx tsc -b && npm run build && npm run e2e
curl -s https://<domain>/api/health
```

Expected: all green, and the live site plans Dallas → Denver with 3 routes.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add readme with rules, design, and run instructions"
```

- [ ] **Step 5: Loom outline (5–10 min)**

1. Demo (2 min): plan Dallas → Denver, explain the recommendation, click a checkpoint, play the slider, show mobile.
2. Logic (3 min): `risk.py` thresholds and load rules, the edge choices, the ranking key, and the tests.
3. Data flow (2 min): ETA per checkpoint, the grid snap and dedupe, the cache, the routing fallback.
4. Performance (1 min): the slider changes a paint property; show the React Profiler.
5. Limits and next steps (1 min).
