# Live Flights Map

Live Flights Map is a local-first aviation operations desk for exploring aircraft traffic, inspecting flight and airport details, and replaying recent movement from archived data.

The app uses live public data providers. Provider coverage and rate limits vary, so the interface identifies the source and freshness of each snapshot and keeps the last available data when a provider is temporarily unavailable.

![Live Flights Map showing current traffic over central Europe](docs/live-flights-map.webp)

## What you can do

- Explore live aircraft positions on a Leaflet map, with map styles, airport markers, weather and density-aware aircraft rendering.
- Search by callsign, ICAO24, registration, airline, route, airport or named location; filter traffic by altitude, speed, type and activity.
- Inspect aircraft identity, route, photos, position history and estimated direction of travel.
- Open airport dashboards with nearby traffic, recorded movements, weather and CSV export.
- Replay archived traffic, compare snapshots, save map views, annotate aircraft and manage watchlists.
- Configure browser and webhook alerts for aircraft and traffic transitions.
- Export traffic and airport reports as CSV or printable HTML, and share a map view or embed link.

## Architecture

```text
Browser
  └── Nginx: built Svelte app + same-origin API proxy
        └── Flask API
              ├── OpenSky → ADSB.lol fallback for live positions
              ├── route, aircraft metadata, airport, weather and photo providers
              └── SQLite archive, workspace, and provider caches

Background services: regional snapshot collector + archive retention and maintenance
```

The frontend uses Svelte, Leaflet and a WebGL overlay for dense traffic. The backend uses Flask and SQLite. API responses remain under `/api`; `/health` reports provider, collector, archive and cache diagnostics.

## Run the full app with Docker

Docker Engine and the Docker Compose plugin are required.

```bash
docker compose up --build -d
```

Open <http://localhost:5174>. The API is reached through the frontend proxy and is not published as a separate host port. SQLite data and caches persist in a named Docker volume. Set `FRONTEND_PORT` in `.env` to override the port.

To use authenticated OpenSky access, create `.env` from the example and add the account credentials. Anonymous OpenSky access and the ADSB.lol fallback are used when credentials are empty.

```bash
cp .env.example .env
# Set OPENSKY_USERNAME and OPENSKY_PASSWORD if available.
docker compose up --build -d
```

The snapshot collector requests one global OpenSky snapshot every 15 minutes and stores it in the shared cache. Positions older than two minutes are marked as delayed in the API and UI. The global request is intentionally limited to OpenSky rather than fanning out into dozens of regional ADSB requests. To add an extra cached region, set `SNAPSHOT_COLLECTOR_SECTORS=global_world,poland_focus`. The persisted alert sweeper remains opt-in:

```bash
docker compose --profile workers up --build -d alert-worker
```

Useful commands:

```bash
docker compose ps
docker compose logs -f api frontend
docker compose logs -f collector alert-worker
docker compose down
```

The frontend is bound to loopback by default. Workspace profiles are local saved desks, not authenticated user accounts or an access-control boundary. Do not expose this local demo directly to the public internet.

## Run for development

### Backend

Python 3.12 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m backend.entrypoints.api
```

The backend listens on <http://127.0.0.1:5000> by default.

### Frontend

```bash
cd frontend
npm ci
npx playwright install chromium  # only needed for browser tests
npm run dev
```

Open <http://127.0.0.1:5173>. The Vite development proxy forwards `/api` and `/health` to the backend. Use `VITE_API_BASE_URL` only when intentionally connecting to a different API origin.

## Main API routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/flights` | Current traffic for a bounding box |
| `GET` | `/api/flights/stream` | Server-sent live updates |
| `GET` | `/api/flights/{icao24}/details` | Aircraft, route and photo details |
| `GET` | `/api/flights/{icao24}/trail` | Archived positions for an aircraft |
| `GET` | `/api/history/replay` | Archived snapshots for a map area |
| `GET` | `/api/search` | Search recent traffic and known entities |
| `GET` | `/api/airports` | Airports visible in a map area, with catalog status |
| `GET` | `/api/airports/{code}` | Airport traffic dashboard |
| `GET` | `/api/airports/{code}/weather` | Current METAR where available |
| `GET/POST/PUT` | `/api/workspace/*` | Local workspace profiles and saved state |
| `GET` | `/api/traffic/leaderboard` | Regional traffic summary |
| `GET` | `/health` | Runtime diagnostics |

Bounding-box coordinates use `lamin`, `lamax`, `lomin` and `lomax`. The airport list is capped server-side to keep broad map views responsive.

## Configuration and data

Copy `.env.example` to `.env` to configure provider credentials and retention. Compose also supports standard environment overrides, including `FRONTEND_PORT`, `FLIGHT_DATA_PROVIDERS`, `FLIGHT_ARCHIVE_RETENTION_HOURS` and `FLIGHT_ARCHIVE_MAX_SNAPSHOTS`.

| Source | Use |
| --- | --- |
| [OpenSky Network](https://opensky-network.org/) | Aircraft state vectors |
| [ADSB.lol](https://adsb.lol/) | Position fallback and aircraft metadata |
| [OurAirports](https://ourairports.com/data/) | Airport catalog |
| [Aviation Weather Center](https://aviationweather.gov/data/api/) | METAR weather |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Map data and attribution |
| Wikimedia Commons, Openverse and Planespotting | Aircraft imagery, when a match is available |

Live traffic is not complete coverage and route enrichment is best-effort. A missing route, photo or airport movement means the provider did not return enough matching data; it does not mean the flight or event did not happen. The app shows provider warnings and stale-cache state rather than presenting cached positions as live.

## Quality checks

From the repository root:

```bash
docker compose config --quiet
docker compose build
docker compose run --rm --no-deps api python -m unittest discover -s backend/tests -v
cd frontend
npm test
npm run build
npm run test:e2e
```

The same backend tests, frontend unit tests, production build and browser flow run in GitHub Actions. The Playwright flow mocks external API responses so it does not depend on live feeds.
