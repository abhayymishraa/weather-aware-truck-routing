# Project rules

- Do not add unnecessary comments. Add a comment only when the code cannot explain the "why".
- Follow the karpathy-guidelines: simplest working code, surgical changes, no speculative features.
- Create only the folders and files that the code needs. The trees below are a target shape, not scaffolding.
- Never mention in code, docs, or commits which outside repos inspired the logic. Write all code ourselves.

## Libraries and docs

- If a library or package already has a function for the job, use it. Do not write a manual version.
- Follow each library's official docs, quickstart, and recommended workflow. Check the docs with Context7 before you use an API.
- Use the latest stable version of every dependency (React, MUI, Tailwind, Django, DRF, and the rest). Check the version at install time. No beta, RC, or canary versions.
- Pin exact versions in the lock files.

## Performance

- Build the most performant way that the docs and widely used projects recommend.
- Choose the tool that works best for the job, for example React Query for server state.
- Measure before you optimize. Do not add speculative optimizations.

## Stack

- Frontend: React + TypeScript + Vite + MUI + Tailwind CSS + React Query + react-map-gl (MapLibre).
- MUI provides the components. Tailwind provides layout and spacing. Integrate them the way the MUI docs say (CSS layers).
- Backend: Django + Django REST Framework.
- External APIs: TomTom Routing API (truck mode, free tier) for routes, OSRM as fallback. Open-Meteo for weather and Photon for geocoding (no keys).
- The TomTom key lives only in the backend env var `TOMTOM_API_KEY`. Never send it to the browser, log it, or commit it.
- Hosting: Oracle Cloud VM, Docker Compose, Caddy.

## Repo layout

```
backend/
frontend/
docker-compose.yml
Caddyfile
README.md
```

## Backend structure

Reference: HackSoftware/Django-Styleguide (business logic in services, thin APIs) and cookiecutter-django (config package, split settings).

```
backend/
  config/                 # Django project: settings/, urls.py, wsgi.py
    settings/base.py
    settings/local.py
    settings/production.py
  routing/                # one Django app for the domain
    apis.py               # thin DRF views: validate input, call a service, return output
    serializers.py        # input/output serializers only
    urls.py
    services/
      plan.py             # orchestrates: geocode -> routes -> checkpoints -> weather -> risk -> rank
      risk.py             # pure functions: risk rules, load rules, ranking. No I/O.
      checkpoints.py      # pure functions: sample points every N miles and their ETAs
    clients/
      tomtom.py           # one module per external API, with caching and timeouts
      osrm.py
      open_meteo.py
      photon.py
    tests/
      test_risk.py
      test_checkpoints.py
      test_apis.py
  manage.py
  pyproject.toml
```

Rules:
- Business logic lives in `services/`. Views and serializers stay thin.
- `risk.py` and `checkpoints.py` are pure: no network, no Django imports. Test them first.
- Each external API has one client module. Only clients do HTTP.
- Use the Django cache for external API results.
- Settings come from environment variables. No secrets in the repo.

## Frontend structure

Reference: alan2207/bulletproof-react (feature folders, no cross-feature imports, no barrel files).

```
frontend/src/
  app/                    # App.tsx, providers (MUI theme, React Query)
  components/             # shared UI used by more than one feature
  config/                 # env values, constants
  lib/                    # preconfigured clients (api client, query client)
  theme/                  # MUI theme, risk color scale
  types/                  # shared API types
  utils/                  # shared pure helpers
  features/
    trip-form/            # origin, destination, departure, load, interval
    routes/               # route cards, recommendation, summaries
    map/                  # map, route lines, checkpoint markers
    weather-heatmap/      # corridor heatmap and 0-48 h slider
```

Each feature folder contains only what it needs: `api/`, `components/`, `hooks/`, `types/`, `utils/`.

Rules:
- Do not import from one feature into another. Compose features in `app/`.
- Import files directly. Do not use barrel `index.ts` files.
- Server data goes through React Query. Keep local UI state local.
- Keep map layers in GPU paint properties. Update the slider with layer filters or paint changes, not with a React re-render of the map.

## UI and design

- Build skills: design-taste-frontend, frontend-design, emil-design-eng, vercel-react-best-practices, dataviz.
- Optimize for every screen: desktop, tablet, and mobile, in portrait and landscape. Test each one.
- Desktop: left panel (form and route cards), full-height map, slider and legend at the bottom of the map.
- Mobile: map first, with the panel as a bottom sheet. In landscape, use a side panel so the map keeps its height.
- Use touch targets of at least 44 px, safe-area insets, and `dvh` units so mobile browser bars do not hide the UI.
- MUI primary color: Spotter teal `#063D4B`. Use one risk color scale everywhere, safe for color-blind users. Support light and dark mode.
