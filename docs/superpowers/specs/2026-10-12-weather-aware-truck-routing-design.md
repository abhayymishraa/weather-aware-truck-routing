# Weather-Aware Truck Routing: Design

Date: 2026-10-12
Status: Draft for review

## 1. Goal

A React + Django web app that helps a truck driver choose the safest route by weather, load weight, and travel time.

Grading weights: 40% routes, weather, risk, and ranking logic. 35% UI, map, and heatmap smoothness. 10% code quality. 5% docs and walkthrough.

Success:
- The risk rules and the ranking match the assessment PDF exactly, and tests prove it.
- The map and the forecast slider stay smooth on desktop and mobile.
- The app runs live on HTTPS, with a README and a 5–10 min Loom video.

Limits: 4 days, 16 work hours.

## 2. Scope

In scope:
- Input: origin, destination, departure date/time, load weight (lb), checkpoint interval (10 / 25 / 50 mi, default 25).
- 3 truck route options from a routing API.
- Weather at each checkpoint, at the truck's ETA.
- Risk level per checkpoint, with the load rules.
- Route ranking and one recommended route.
- A map with all routes, checkpoints, risk levels, ETAs, and route summaries.
- A corridor heatmap of the risk level with a 0–48 h forecast slider.

Out of scope: login, saved trips, a database of user data, non-US trips, a routing engine.

## 3. Stack

All dependencies use the latest stable version at install time, with exact pins in the lock files. Use library functions and follow the official docs and quickstarts before writing custom code.

- Frontend: React, TypeScript, Vite, MUI (components), Tailwind CSS (layout and spacing, integrated with CSS layers as the MUI docs describe), TanStack React Query, react-map-gl with MapLibre GL.
- Backend: Django, Django REST Framework, an HTTP client with built-in timeout and retry support, Redis cache in production, local memory cache in development.
- Outside APIs:
  - Routing: TomTom Calculate Route, `travelMode=truck`, `vehicleCommercial=true`, `vehicleWeight` (gross kg), `departAt`, `maxAlternatives=2`. Free tier: 20K requests/month, no credit card. The key `TOMTOM_API_KEY` stays in the backend env. Fallback (no key): OSRM public server (car profile).
  - Weather: Open-Meteo forecast API.
  - Geocoding: Photon.
- Hosting: Oracle Cloud VM, Docker Compose, Caddy (HTTPS and reverse proxy).

Verified facts:
- ORS alternative routes are limited to 100 km trips, so ORS is not used.
- Live test, Dallas to Denver: OSRM returned 2 routes.
- Valhalla's public server was rejected: it often returned 0 alternates for short trips and rejected trips over 1,500 km.
- TomTom docs: `maxAlternatives` 0–5, no general distance limit, and `extendedRouteRepresentation=travelTime` returns `progress[]` (travel time at route points).
- Nominatim's usage policy forbids autocomplete. Photon supports it and geocoded the test addresses correctly.
- Open-Meteo free use: 600 calls/min, 5,000/h, 10,000/day. Request weight grows with locations and variables.

## 4. Architecture and data flow

```
Browser (React)                    Django (DRF)                      Outside APIs
Address field ──GET /api/geocode──▶ photon client (cache 24 h) ─────▶ Photon
Trip form ─────POST /api/plan─────▶ services/plan.py
                                     1. tomtom client (cache 1 h) ───▶ TomTom
                                        fallback: osrm client ───────▶ OSRM
                                     2. checkpoints.py: points every N mi + ETA
                                     3. corridor points along and beside each route
                                     4. snap all points to the weather grid, dedupe
                                     5. open_meteo client (cache 1 h per cell) ▶ Open-Meteo
                                     6. risk.py: level per checkpoint and per cell per hour
                                     7. risk.py: rank the routes
◀──────────── one JSON response ────
```

### 4.1 `POST /api/plan`

Input:
| Field | Type | Rule |
|---|---|---|
| `origin` | `{lat, lon, label}` | Required |
| `destination` | `{lat, lon, label}` | Required, not equal to origin |
| `departure` | ISO 8601 datetime | From now to now + 48 h |
| `load_lb` | integer | 1 to 80,000 |
| `interval_mi` | integer | 10, 25, or 50 |

Output:
- `routes[]`: `id`, `geometry` (GeoJSON LineString), `distance_mi`, `duration_s`, `source` (`tomtom` or `osrm`), `checkpoints[]`, `miles_by_level`, `avg_risk`, `rank`, `recommended`, `reason`.
- `checkpoints[]`: `mile`, `lat`, `lon`, `eta` (UTC), `wind_mph`, `gust_mph`, `rain_in_hr`, `snow_in_hr`, `level`, `segment_mi`.
- `heatmap`: `start_hour` (UTC), `cells[]` with `lat`, `lon`, `levels` (48 integers, one per hour).
- `warnings[]`: for example `no_safe_route`, `beyond_forecast`, `fallback_routing`, `fewer_routes`.

### 4.2 `GET /api/geocode?q=`

Returns up to 5 US-biased Photon results: `label`, `lat`, `lon`. Cached 24 h. Fixed User-Agent.

### 4.3 Checkpoints and ETA

- Walk the route geometry and place a checkpoint every `interval_mi` miles, starting at mile 0 (the origin) and ending at the destination.
- Each checkpoint owns the segment from itself to the next checkpoint. The last segment can be shorter.
- ETA = departure + travel time to that point. The travel time comes from TomTom `progress[]` (time at route points) or OSRM per-segment times, interpolated by distance.
- The checkpoint uses the forecast hour nearest to its ETA.

### 4.4 Corridor grid

- Corridor points every ~10 mi along each route, plus points ~15 mi to the left and right of the route.
- Snap the checkpoints and corridor points to a ~0.25° grid and remove duplicates. Batch the unique cells into Open-Meteo requests.
- Each cell gets 48 hourly values: `wind_speed_10m`, `wind_gusts_10m`, `rain`, `showers`, `snowfall`, with `wind_speed_unit=mph`, `precipitation_unit=inch`, `timeformat=unixtime`, `forecast_hours=48`.
- Rain = `rain + showers`. Snow = `snowfall`. Both are sums of the preceding hour, which equals in/hr.
- Checkpoints read their weather from the same cell data. No second weather fetch.

## 5. Risk and ranking rules (`risk.py`, pure functions)

### 5.1 Levels

| Level | Score |
|---|---|
| Low | 0 |
| Moderate | 1 |
| High | 2 |
| Severe | 3 |
| No Travel | 4 |
| No Data | not scored |

### 5.2 Thresholds (from the PDF)

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | < 25 | 25 to < 35 | 35 to < 45 | 45 to < 55 | ≥ 55 |
| Rain (in/hr) | < 0.10 | 0.10 to < 0.25 | 0.25 to < 0.50 | 0.50 to ≤ 1.00 | > 1.00 |
| Snow (in/hr) | < 0.5 | 0.5 to < 1.0 | 1.0 to < 2.0 | 2.0 to ≤ 3.0 | > 3.0 |

Edge choices (the PDF ranges touch or leave gaps):
- Each lower bound is inclusive. A value below the next lower bound stays in the lower level. Example: 34.5 mph is Moderate.
- A shared bound goes to the higher level. Example: 0.25 in/hr rain is High.
- The No Travel rows follow the PDF: wind uses ≥ 55, rain and snow use > (strictly greater).
- Wind uses `wind_speed_10m`. Gusts are shown as information only.

### 5.3 Checkpoint level

1. Take the highest level of wind, rain, and snow.
2. Apply the load rules. They can only raise the level:
   - Wind ≥ 55 mph: No Travel for any load.
   - Wind 45 to < 55 mph and load > 30,000 lb: No Travel.
   - Wind 35 to < 45 mph and load > 40,000 lb: Severe.
3. If the ETA is beyond the forecast range: No Data.

The heatmap cells use the same function with the same load.

### 5.4 Route metrics

- `miles_by_level`: the sum of segment miles per level.
- `avg_risk`: the mile-weighted average of the level scores. No Data segments are excluded.

### 5.5 Ranking

Sort key, in order:
1. Routes with no No Travel miles come first. Routes with No Travel miles follow, ordered by fewest No Travel miles.
2. Fewest Severe miles.
3. Fewest High miles.
4. Lowest average risk.
5. Shortest travel time.

The first route is `recommended`. Each route gets a short `reason` that names the deciding key.
If all routes have No Travel miles, add the `no_safe_route` warning.

## 6. Frontend

### 6.1 Layout

- Desktop: left panel (~400 px) with the trip form and the route cards. Full-height map. The slider, time label, play button, and legend at the bottom of the map.
- Tablet: same as desktop, with a narrower panel.
- Mobile portrait: map first, with the panel as a bottom sheet.
- Mobile landscape: side panel, so the map keeps its height.
- Touch targets ≥ 44 px, safe-area insets, `dvh` units.

### 6.2 Features

| Feature | Content |
|---|---|
| `trip-form` | Photon address fields (MUI Autocomplete, 300 ms debounce), departure picker, load input, 10 / 25 / 50 mi toggle |
| `routes` | 3 cards, best first: Recommended badge, distance, time, stacked bar of miles per level, average risk, reason |
| `map` | Route lines, checkpoint dots in risk colors, checkpoint popup (ETA, wind, gust, rain, snow, level), fit to bounds after a search |
| `weather-heatmap` | Corridor heatmap layer, 0–48 h slider, play button, legend |

Card hover or click highlights the route on the map, and the reverse.

### 6.3 Performance

- Routes, checkpoints, and heatmap cells are MapLibre GeoJSON sources.
- The slider sets the hour in the layer paint expression (`["at", hour, ["get", "levels"]]`). No React re-render of the map.
- The selected route uses `feature-state`.
- React Query holds the plan result. The selected route and the slider hour are local state.

### 6.4 Look

- MUI primary: Spotter teal `#063D4B`.
- One risk color scale everywhere, checked for contrast and color-blind safety.
- Light and dark mode.

## 7. Errors and edge cases

| Case | Behavior |
|---|---|
| TomTom fails, times out (10 s), has no key, or hits the quota | Use OSRM. Add the `fallback_routing` warning (car routes). |
| Fewer than 3 routes | Show what exists. Add the `fewer_routes` warning. |
| Both routing services fail | HTTP 502, clear message, "Try again" button |
| Open-Meteo fails | HTTP 502. Never return routes without risk data. |
| Checkpoint ETA beyond 48 h | Level No Data (gray), excluded from the ranking, `beyond_forecast` warning |
| Invalid departure or load | Validated in the form and in DRF, HTTP 400 |
| Same origin and destination, or no road | HTTP 400, clear message |
| All routes have No Travel miles | Ranked, with a red "No safe route in this window" banner |
| Abuse | DRF throttle per IP, about 20 plans per minute |

- One error shape: `{ "detail": "...", "code": "..." }`.
- Clients use timeouts and the HTTP library's own retry support.
- Loading: skeleton cards and a thin progress bar on the map.

## 8. Code structure

As defined in `CLAUDE.md`:
- Backend: `config/` (split settings), one `routing` app with thin `apis.py`, `serializers.py`, `services/` (`plan.py`, `risk.py`, `checkpoints.py`), `clients/` (one module per outside API), `tests/`.
- Frontend: `app/`, `components/`, `config/`, `lib/`, `theme/`, `types/`, `utils/`, `features/` (`trip-form`, `routes`, `map`, `weather-heatmap`). No cross-feature imports, no barrel files.

## 9. Testing

| Level | Scope | Tool |
|---|---|---|
| Unit | `risk.py`: every threshold edge, the 3 load rules, max of conditions, No Travel and No Data, mile-weighted average, ranking with ties | pytest |
| Unit | `checkpoints.py`: 10 / 25 / 50 mi, short last segment, ETA interpolation, trip shorter than one interval | pytest |
| API | `/api/plan` and `/api/geocode` with mocked clients: shape, validation, fallback | pytest + DRF test client |
| Frontend | Risk level to color mapping, route card component | Vitest + Testing Library |
| End to end | One real search: form, routes, slider move | Playwright |

## 10. Deploy

- `docker-compose.yml`: `backend` (gunicorn), `frontend` (static Vite build), `redis`, `caddy`.
- Caddy serves `/` from the frontend build and proxies `/api/*` to Django. One domain, so no CORS in production.
- Open ports 80 and 443 in the Oracle VCN security list and in the VM firewall.
- Settings from environment variables. No secrets in the repo.
- Open: the domain name for HTTPS.

## 11. Docs and walkthrough

- README: purpose, screenshot, live link, one-command local run, risk rules and edge choices, ranking, architecture diagram, limits.
- Loom (5–10 min): demo, then `risk.py`, then the slider performance design.
- No mention of outside repos that inspired the logic.

## 12. Skills by phase

| Phase | Skills |
|---|---|
| Plan | superpowers:brainstorming, superpowers:writing-plans |
| Backend logic | superpowers:test-driven-development, context7-mcp |
| UI | design-taste-frontend, frontend-design, emil-design-eng, vercel-react-best-practices, dataviz, context7-mcp |
| Check | superpowers:systematic-debugging, ponytail:ponytail-review, superpowers:verification-before-completion |
| Ship | run, agent-browser |
| Always | karpathy-guidelines |

## 13. Time budget

| Part | Hours |
|---|---|
| Backend logic and tests | 5 |
| Frontend, map, heatmap | 7 |
| Deploy | 2 |
| README and Loom | 2 |
