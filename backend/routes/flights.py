from flask import Blueprint, current_app, jsonify, request

from backend.services.opensky import OpenSkyError

api = Blueprint("api", __name__)


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
    except OpenSkyError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(flights_payload)
