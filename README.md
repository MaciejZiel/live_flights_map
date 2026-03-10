# Live Flights Map

Minimalne MVP aplikacji do śledzenia samolotów w czasie rzeczywistym:

- `backend/`: Flask proxy do OpenSky Network z fallbackiem do ADSB.lol
- `frontend/`: Svelte + Leaflet do wizualizacji samolotów na mapie

## Architektura

### Backend

- `GET /api/flights`
- `GET /api/flights/stream` (SSE transport)
- `GET /api/history/replay` (ostatnie snapshoty dla aktualnego bboxa)
- `GET /api/flights/<icao24>/trail` (ślad lotu z archiwum)
- `GET /api/search?q=...` (wyszukiwanie po ostatnio widzianych lotach)
- pobiera świeży snapshot z łańcucha providerów `opensky -> adsb_lol`
- ma cache per `bbox`, cooldown przy rate-limitach i fallback do ostatniego snapshotu przy błędach upstreamu
- archiwizuje snapshoty i pozycje do lokalnej bazy SQLite pod replay, trail i search
- dla frontendu wspiera SSE z fallbackiem do zwykłego pollingu
- filtruje odpowiedź do pól:
  - `icao24`
  - `callsign`
  - `longitude`
  - `latitude`
  - `true_track`
  - `altitude`
- wspiera domyślny bounding box z `.env`

### Frontend

- odpytuje backend co 30 sekund
- domyślnie używa zwykłego pollingu; SSE można włączyć jawnie zmienną środowiskową
- wysyła aktualny bounding box mapy po przesunięciu lub zoomie
- renderuje samoloty jako markery Leaflet
- animuje pozycje markerów pomiędzy kolejnymi snapshotami
- pozwala filtrować loty po callsign, ICAO24, kraju i minimalnej wysokości
- pokazuje panel szczegółów zaznaczonego samolotu
- obraca ikonę na podstawie `true_track`
- usuwa markery nieobecne w nowej odpowiedzi i aktualizuje istniejące

## Uruchomienie

### 1. Backend

Edytuj plik `.env`. Jeżeli go usuniesz, możesz odtworzyć go z `.env.example`.

Zainstaluj zależności:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Uruchom backend:

```bash
.venv/bin/python app.py
```

Backend host i port możesz nadpisać:

```bash
HOST=127.0.0.1 PORT=5002 .venv/bin/python app.py
```

Backend będzie dostępny pod:

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

Stream SSE:

```text
http://127.0.0.1:5000/api/flights/stream
```

Przykład z własnym bounding boxem:

```text
http://127.0.0.1:5000/api/flights?lamin=49&lamax=55.1&lomin=14&lomax=24.5
```

### 2. Frontend

Zainstaluj zależności:

```bash
npm --prefix frontend install
```

Uruchom dev server:

```bash
npm --prefix frontend run dev
```

Frontend możesz skierować na inny backend bez edycji kodu:

```bash
VITE_API_BASE_URL=http://127.0.0.1:5002 npm --prefix frontend run dev
```

Albo zachować ścieżki względne `/api` i tylko przestawić dev proxy:

```bash
VITE_DEV_PROXY_TARGET=http://127.0.0.1:5002 npm --prefix frontend run dev
```

Frontend będzie dostępny pod:

```text
http://127.0.0.1:5173
```

## Konfiguracja providerów lotów

Wpisz dane do istniejącego `.env`:

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

`FLIGHT_DATA_PROVIDERS` określa kolejność upstreamów. Domyślnie backend próbuje najpierw OpenSky, a przy błędzie lub rate-limicie przechodzi do ADSB.lol.

Obecna integracja OpenSky zakłada standardowe dane logowania (`username` + `password`), nie osobny token API.

Jeżeli pola OpenSky zostaną puste, backend spróbuje połączenia anonimowego, ale limity będą ostrzejsze. ADSB.lol działa jako publiczny fallback i dla większych widoków typu Europa/World może zwracać tylko część ruchu, bo endpoint punktowy ma limit promienia `250nm`.
