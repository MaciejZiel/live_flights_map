# Live Flights Map

Minimalne MVP aplikacji do śledzenia samolotów w czasie rzeczywistym:

- `backend/`: Flask proxy do OpenSky Network
- `frontend/`: Svelte + Leaflet do wizualizacji samolotów na mapie

## Architektura

### Backend

- `GET /api/flights`
- pobiera świeży snapshot z OpenSky przy każdym wywołaniu
- filtruje odpowiedź do pól:
  - `icao24`
  - `callsign`
  - `longitude`
  - `latitude`
  - `true_track`
  - `altitude`
- wspiera domyślny bounding box z `.env`

### Frontend

- odpytuje backend co 12 sekund
- wysyła aktualny bounding box mapy po przesunięciu lub zoomie
- renderuje samoloty jako markery Leaflet
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

Frontend będzie dostępny pod:

```text
http://127.0.0.1:5173
```

## Konfiguracja OpenSky

Wpisz dane do istniejącego `.env`:

```env
OPENSKY_USERNAME=
OPENSKY_PASSWORD=
```

Obecna integracja zakłada standardowe dane logowania OpenSky (`username` + `password`), nie osobny token API.

Jeżeli pola zostaną puste, backend spróbuje połączenia anonimowego, ale limity będą ostrzejsze.
