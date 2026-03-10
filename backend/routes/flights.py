import json
from time import sleep

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from backend.services.airport_weather import AirportWeatherError
from backend.services.provider_base import FlightProviderError

api = Blueprint("api", __name__)


def _build_sse_event(event_name: str, payload: dict[str, object]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"


def _parse_bbox():
    defaults = {
        "lamin": current_app.config["MAP_DEFAULT_LAMIN"],
        "lamax": current_app.config["MAP_DEFAULT_LAMAX"],
        "lomin": current_app.config["MAP_DEFAULT_LOMIN"],
        "lomax": current_app.config["MAP_DEFAULT_LOMAX"],
    }

    bbox = {}
    for key, default in defaults.items():
        raw_value = request.args.get(key)
        if raw_value is None:
            bbox[key] = default
            continue
        try:
            bbox[key] = float(raw_value)
        except ValueError as exc:
            raise ValueError(f"Invalid '{key}' query parameter.") from exc

    if bbox["lamin"] >= bbox["lamax"]:
        raise ValueError("'lamin' must be lower than 'lamax'.")
    if bbox["lomin"] >= bbox["lomax"]:
        raise ValueError("'lomin' must be lower than 'lomax'.")
    if not (-90 <= bbox["lamin"] <= 90 and -90 <= bbox["lamax"] <= 90):
        raise ValueError("Latitude must be between -90 and 90.")
    if not (-180 <= bbox["lomin"] <= 180 and -180 <= bbox["lomax"] <= 180):
        raise ValueError("Longitude must be between -180 and 180.")

    return bbox


def _parse_optional_float(name: str) -> float | None:
    raw_value = request.args.get(name)
    if raw_value is None or raw_value == "":
        return None

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"Invalid '{name}' query parameter.") from exc


def _parse_optional_int(name: str, default: int) -> int:
    raw_value = request.args.get(name)
    if raw_value is None or raw_value == "":
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Invalid '{name}' query parameter.") from exc

    if value < 1:
        raise ValueError(f"'{name}' must be greater than 0.")

    return value


def _normalize_text(raw_value: str | None, uppercase: bool = False) -> str | None:
    if raw_value is None:
        return None
    cleaned = raw_value.strip()
    if not cleaned:
        return None
    return cleaned.upper() if uppercase else cleaned


def _parse_json_body() -> dict[str, object]:
    payload = request.get_json(silent=True)
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object body.")
    return payload


def _enrich_live_payload(payload: dict[str, object]) -> dict[str, object]:
    flights = payload.get("flights")
    if not isinstance(flights, list) or not flights:
        return payload

    service = current_app.extensions.get("traffic_intelligence_service")
    if service is None:
        return payload

    try:
        enriched_flights = service.enrich_flights(flights)
    except Exception:
        return payload

    meta = payload.get("meta")
    if isinstance(meta, dict):
        meta = {
            **meta,
            "intelligence_enriched": sum(
                1
                for flight in enriched_flights
                if isinstance(flight, dict) and flight.get("intelligence_updated_at")
            ),
        }

    return {
        **payload,
        "flights": enriched_flights,
        "count": len(enriched_flights),
        **({"meta": meta} if isinstance(meta, dict) else {}),
    }


@api.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = current_app.config[
        "CORS_ALLOWED_ORIGIN"
    ]
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS"
    return response


@api.get("/flights")
def list_flights():
    try:
        bbox = _parse_bbox()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    service = current_app.extensions["flight_snapshot_service"]

    try:
        flights_payload = service.get_flights(bbox=bbox)
    except FlightProviderError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(_enrich_live_payload(flights_payload))


@api.get("/flights/<icao24>/details")
def flight_details(icao24: str):
    normalized_icao24 = _normalize_text(icao24, uppercase=False)
    if not normalized_icao24 or len(normalized_icao24) < 6:
        return jsonify({"error": "Invalid aircraft identifier."}), 400

    try:
        latitude = _parse_optional_float("lat")
        longitude = _parse_optional_float("lon")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    service = current_app.extensions["flight_details_service"]
    details_payload = service.get_details(
        icao24=normalized_icao24,
        callsign=_normalize_text(request.args.get("callsign"), uppercase=True),
        registration=_normalize_text(request.args.get("registration"), uppercase=True),
        type_code=_normalize_text(request.args.get("type_code"), uppercase=True),
        latitude=latitude,
        longitude=longitude,
        origin_country=_normalize_text(request.args.get("origin_country")),
    )
    current_app.extensions["traffic_intelligence_service"].store_flight_enrichment(
        details_payload
    )
    return jsonify(details_payload)


@api.get("/flights/<icao24>/trail")
def flight_trail(icao24: str):
    normalized_icao24 = _normalize_text(icao24, uppercase=False)
    if not normalized_icao24 or len(normalized_icao24) < 6:
        return jsonify({"error": "Invalid aircraft identifier."}), 400

    try:
        hours = _parse_optional_int("hours", default=2)
        limit = _parse_optional_int("limit", default=240)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    archive_service = current_app.extensions["flight_archive_service"]
    return jsonify(
        archive_service.get_flight_trail(
            icao24=normalized_icao24,
            hours=hours,
            limit=limit,
        )
    )


@api.get("/history/replay")
def replay_history():
    try:
        bbox = _parse_bbox()
        minutes = _parse_optional_int("minutes", default=30)
        limit = _parse_optional_int("limit", default=60)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    archive_service = current_app.extensions["flight_archive_service"]
    return jsonify(
        archive_service.list_replay_snapshots(
            bbox=bbox,
            minutes=minutes,
            limit=limit,
        )
    )


@api.get("/search")
def search_flights():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing 'q' query parameter."}), 400

    try:
        limit = _parse_optional_int("limit", default=10)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    search_service = current_app.extensions["entity_search_service"]
    return jsonify(search_service.search(query=query, limit=limit))


@api.get("/airports")
def list_airports():
    try:
        bbox = _parse_bbox()
        limit = _parse_optional_int("limit", default=16)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    service = current_app.extensions["airport_workflow_service"]
    return jsonify(service.list_airports(bbox=bbox, limit=limit))


@api.get("/airports/<airport_code>")
def airport_dashboard(airport_code: str):
    normalized_code = _normalize_text(airport_code, uppercase=True)
    if not normalized_code:
        return jsonify({"error": "Invalid airport identifier."}), 400

    try:
        hours = _parse_optional_int("hours", default=6)
        limit = _parse_optional_int("limit", default=8)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    payload = current_app.extensions["airport_workflow_service"].get_airport_dashboard(
        airport_code=normalized_code,
        hours=hours,
        limit=limit,
    )
    if payload is None:
        return jsonify({"error": "Airport not found."}), 404
    return jsonify(payload)


@api.get("/airports/<airport_code>/weather")
def airport_weather(airport_code: str):
    normalized_code = _normalize_text(airport_code, uppercase=True)
    if not normalized_code:
        return jsonify({"error": "Invalid airport identifier."}), 400

    service = current_app.extensions["airport_weather_service"]

    try:
        payload = service.get_weather(normalized_code)
    except AirportWeatherError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(payload)


@api.get("/workspace/profiles")
def list_workspace_profiles():
    service = current_app.extensions["workspace_service"]
    return jsonify(service.list_profiles())


@api.post("/workspace/profiles")
def create_workspace_profile():
    try:
        payload = _parse_json_body()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    display_name = _normalize_text(payload.get("display_name") if isinstance(payload, dict) else None)
    if not display_name:
        return jsonify({"error": "Missing 'display_name'."}), 400
    role = _normalize_text(payload.get("role") if isinstance(payload, dict) else None)
    if not role:
        role = "analyst"

    try:
        profile = current_app.extensions["workspace_service"].create_profile(
            display_name,
            role=role,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"profile": profile}), 201


@api.get("/workspace/state")
def get_workspace_state():
    profile_id = _normalize_text(request.args.get("profile_id"))
    payload = current_app.extensions["workspace_service"].get_workspace_state(profile_id)
    return jsonify(payload)


@api.put("/workspace/state")
def save_workspace_state():
    try:
        payload = _parse_json_body()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    profile_id = _normalize_text(payload.get("profile_id") if isinstance(payload, dict) else None)
    if not profile_id:
        return jsonify({"error": "Missing 'profile_id'."}), 400

    state = payload.get("state")
    if state is not None and not isinstance(state, dict):
        return jsonify({"error": "Expected 'state' to be a JSON object."}), 400

    return jsonify(
        current_app.extensions["workspace_service"].save_workspace_state(
            profile_id=profile_id,
            state=state,
        )
    )


@api.get("/traffic/leaderboard")
def global_traffic_leaderboard():
    try:
        limit = _parse_optional_int("limit", default=8)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    service = current_app.extensions["global_traffic_board_service"]

    try:
        payload = service.get_board(limit=limit)
    except FlightProviderError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(_enrich_live_payload(payload))


@api.get("/flights/stream")
def stream_flights():
    try:
        bbox = _parse_bbox()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    service = current_app.extensions["flight_snapshot_service"]
    interval_seconds = current_app.config["FLIGHT_STREAM_INTERVAL_SECONDS"]

    @stream_with_context
    def generate():
        yield "retry: 5000\n\n"

        while True:
            try:
                flights_payload = service.get_flights(bbox=bbox)
                yield _build_sse_event("snapshot", _enrich_live_payload(flights_payload))
            except FlightProviderError as exc:
                yield _build_sse_event("upstream_error", {"error": str(exc)})

            sleep(interval_seconds)

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response
