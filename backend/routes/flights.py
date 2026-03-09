import json
from time import sleep

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

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


def _normalize_text(raw_value: str | None, uppercase: bool = False) -> str | None:
    if raw_value is None:
        return None
    cleaned = raw_value.strip()
    if not cleaned:
        return None
    return cleaned.upper() if uppercase else cleaned


@api.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = current_app.config[
        "CORS_ALLOWED_ORIGIN"
    ]
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
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

    return jsonify(flights_payload)


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
    return jsonify(details_payload)


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
                yield _build_sse_event("snapshot", flights_payload)
            except FlightProviderError as exc:
                yield _build_sse_event("upstream_error", {"error": str(exc)})

            sleep(interval_seconds)

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    return response
