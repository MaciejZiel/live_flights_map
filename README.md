# Live Flights Map

Minimal MVP for real-time aircraft tracking:

- `backend/`: Flask proxy for OpenSky Network with ADSB.lol fallback
- `frontend/`: Svelte + Leaflet for aircraft visualization on the map

## Architecture

### Backend

- `GET /api/flights`
- `GET /api/flights/stream` (SSE transport)
- `GET /api/history/replay` (recent snapshots for the current bbox)
- `GET /api/flights/<icao24>/trail` (flight trail from the archive)
- `GET /api/search?q=...` (search across recently seen traffic)
- fetches fresh snapshots from the provider chain `opensky -> adsb_lol`
- keeps a per-`bbox` cache, applies cooldown during rate limits, and falls back to the latest cached snapshot on upstream errors
- archives snapshots and positions into a local SQLite database for replay, trail, and search
- supports SSE for the frontend with fallback to standard polling
- filters the response down to:
  - `icao24`
  - `callsign`
  - `longitude`
  - `latitude`
  - `true_track`
  - `altitude`
- supports a default bounding box from `.env`

### Frontend

- polls the backend every 30 seconds
- uses standard polling by default; SSE can be enabled explicitly with an environment variable
- sends the current map bounding box after pan or zoom
- renders aircraft as Leaflet markers
- animates marker positions between snapshots
- allows filtering by callsign, ICAO24, country, and minimum altitude
- shows a details panel for the selected aircraft
- rotates the aircraft icon based on `true_track`
- removes markers that are missing from the next response and updates the existing ones

## Running The Project

### 1. Backend

Edit the `.env` file. If you remove it, you can restore it from `.env.example`.

Install dependencies:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Start the backend:

```bash
.venv/bin/python app.py
```

You can override the backend host and port:

```bash
HOST=127.0.0.1 PORT=5002 .venv/bin/python app.py
```

The backend will be available at:

```text
http://127.0.0.1:5000
```

Healthcheck:

```text
http://127.0.0.1:5000/health
```

API:

```text
http://127.0.0.1:5000/api/flights
```

SSE stream:

```text
http://127.0.0.1:5000/api/flights/stream
```

Example with a custom bounding box:

```text
http://127.0.0.1:5000/api/flights?lamin=49&lamax=55.1&lomin=14&lomax=24.5
```

### 2. Frontend

Install dependencies:

```bash
npm --prefix frontend install
```

Start the dev server:

```bash
npm --prefix frontend run dev
```

You can point the frontend to a different backend without editing code:

```bash
VITE_API_BASE_URL=http://127.0.0.1:5002 npm --prefix frontend run dev
```

Or keep relative `/api` paths and only switch the dev proxy:

```bash
VITE_DEV_PROXY_TARGET=http://127.0.0.1:5002 npm --prefix frontend run dev
```

The frontend will be available at:

```text
http://127.0.0.1:5173
```

## Flight Provider Configuration

Add values to the existing `.env` file:

```env
FLIGHT_ARCHIVE_PATH=/tmp/live-flights-map-history.sqlite3
FLIGHT_ARCHIVE_RETENTION_HOURS=24
FLIGHT_ARCHIVE_MAX_SNAPSHOTS=720
FLIGHT_SEARCH_LOOKBACK_HOURS=6
FLIGHT_DATA_PROVIDERS=opensky,adsb_lol
OPENSKY_USERNAME=
OPENSKY_PASSWORD=
OPENSKY_RETRY_COUNT=1
ADSB_LOL_BASE_URL=https://api.adsb.lol
ADSB_LOL_TIMEOUT=10
ADSB_LOL_RETRY_COUNT=1
ADSB_LOL_RADIUS_LIMIT_NM=250
OPENSKY_CACHE_TTL=25
OPENSKY_COOLDOWN_SECONDS=75
FLIGHT_STREAM_INTERVAL_SECONDS=30
```

`FLIGHT_DATA_PROVIDERS` defines the upstream order. By default the backend tries OpenSky first and switches to ADSB.lol on errors or rate limits.

The current OpenSky integration expects standard credentials (`username` + `password`), not a separate API token.

If the OpenSky fields are left empty, the backend will try an anonymous connection, but the limits will be stricter. ADSB.lol works as a public fallback and, for wider views such as Europe or World, may return only part of the traffic because the point endpoint has a `250nm` radius cap.
