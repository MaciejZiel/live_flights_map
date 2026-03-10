from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock


class TrafficIntelligenceService:
    def __init__(self, archive_path: str) -> None:
        self.archive_path = Path(archive_path).expanduser()
        self._lock = Lock()
        self._initialize_database()

    def store_flight_enrichment(self, payload: dict[str, object]) -> None:
        aircraft = payload.get("aircraft")
        route = payload.get("route")
        if not isinstance(aircraft, dict):
            return

        icao24 = self._normalize_text(aircraft.get("icao24"), uppercase=False)
        if not icao24:
            return

        airports = route.get("airports") if isinstance(route, dict) else []
        normalized_airports = [
            self._normalize_airport(airport)
            for airport in airports
            if isinstance(airport, dict)
        ]
        normalized_airports = [airport for airport in normalized_airports if airport]
        updated_at = self._normalize_timestamp(
            payload.get("meta", {}).get("fetched_at")
            if isinstance(payload.get("meta"), dict)
            else None
        ) or datetime.now(timezone.utc)

        row = {
            "icao24": icao24,
            "callsign": self._normalize_text(aircraft.get("callsign"), uppercase=True),
            "registration": self._normalize_text(
                aircraft.get("registration"),
                uppercase=True,
            ),
            "type_code": self._normalize_text(aircraft.get("type_code"), uppercase=True),
            "operator_code": self._normalize_text(
                aircraft.get("operator_code"), uppercase=True
            ),
            "airline_code": self._normalize_text(
                route.get("airline_code") if isinstance(route, dict) else None,
                uppercase=True,
            ),
            "flight_number": self._normalize_text(
                route.get("flight_number") if isinstance(route, dict) else None,
                uppercase=True,
            ),
            "route_label": self._normalize_text(
                route.get("route_label") if isinstance(route, dict) else None,
                uppercase=True,
            ),
            "route_verbose": self._normalize_text(
                route.get("route_verbose") if isinstance(route, dict) else None
            ),
            "airport_codes": self._normalize_text(
                route.get("airport_codes") if isinstance(route, dict) else None,
                uppercase=True,
            ),
            "iata_codes": self._normalize_text(
                route.get("iata_codes") if isinstance(route, dict) else None,
                uppercase=True,
            ),
            "origin_icao": self._normalize_text(
                (normalized_airports[0] if normalized_airports else {}).get("icao"),
                uppercase=True,
            ),
            "origin_iata": self._normalize_text(
                (normalized_airports[0] if normalized_airports else {}).get("iata"),
                uppercase=True,
            ),
            "origin_name": self._normalize_text(
                (normalized_airports[0] if normalized_airports else {}).get("name")
                or (normalized_airports[0] if normalized_airports else {}).get("location")
            ),
            "destination_icao": self._normalize_text(
                (normalized_airports[-1] if normalized_airports else {}).get("icao"),
                uppercase=True,
            ),
            "destination_iata": self._normalize_text(
                (normalized_airports[-1] if normalized_airports else {}).get("iata"),
                uppercase=True,
            ),
            "destination_name": self._normalize_text(
                (normalized_airports[-1] if normalized_airports else {}).get("name")
                or (normalized_airports[-1] if normalized_airports else {}).get("location")
            ),
            "payload_json": json.dumps(payload),
            "updated_at": updated_at.isoformat(),
        }

        with self._lock:
            connection = self._connect()
            try:
                connection.execute(
                    """
                    INSERT INTO enriched_flights (
                        icao24,
                        callsign,
                        registration,
                        type_code,
                        operator_code,
                        airline_code,
                        flight_number,
                        route_label,
                        route_verbose,
                        airport_codes,
                        iata_codes,
                        origin_icao,
                        origin_iata,
                        origin_name,
                        destination_icao,
                        destination_iata,
                        destination_name,
                        payload_json,
                        updated_at
                    ) VALUES (
                        :icao24,
                        :callsign,
                        :registration,
                        :type_code,
                        :operator_code,
                        :airline_code,
                        :flight_number,
                        :route_label,
                        :route_verbose,
                        :airport_codes,
                        :iata_codes,
                        :origin_icao,
                        :origin_iata,
                        :origin_name,
                        :destination_icao,
                        :destination_iata,
                        :destination_name,
                        :payload_json,
                        :updated_at
                    )
                    ON CONFLICT(icao24) DO UPDATE SET
                        callsign = excluded.callsign,
                        registration = excluded.registration,
                        type_code = excluded.type_code,
                        operator_code = excluded.operator_code,
                        airline_code = excluded.airline_code,
                        flight_number = excluded.flight_number,
                        route_label = excluded.route_label,
                        route_verbose = excluded.route_verbose,
                        airport_codes = excluded.airport_codes,
                        iata_codes = excluded.iata_codes,
                        origin_icao = excluded.origin_icao,
                        origin_iata = excluded.origin_iata,
                        origin_name = excluded.origin_name,
                        destination_icao = excluded.destination_icao,
                        destination_iata = excluded.destination_iata,
                        destination_name = excluded.destination_name,
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    row,
                )

                for airport in normalized_airports:
                    airport_key = (
                        self._normalize_text(airport.get("iata"), uppercase=True)
                        or self._normalize_text(airport.get("icao"), uppercase=True)
                    )
                    if not airport_key:
                        continue

                    connection.execute(
                        """
                        INSERT INTO known_airports (
                            airport_key,
                            icao,
                            iata,
                            name,
                            location,
                            country_iso2,
                            latitude,
                            longitude,
                            source,
                            payload_json,
                            updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(airport_key) DO UPDATE SET
                            icao = excluded.icao,
                            iata = excluded.iata,
                            name = excluded.name,
                            location = excluded.location,
                            country_iso2 = excluded.country_iso2,
                            latitude = excluded.latitude,
                            longitude = excluded.longitude,
                            source = excluded.source,
                            payload_json = excluded.payload_json,
                            updated_at = excluded.updated_at
                        """,
                        (
                            airport_key,
                            self._normalize_text(airport.get("icao"), uppercase=True),
                            self._normalize_text(airport.get("iata"), uppercase=True),
                            self._normalize_text(airport.get("name")),
                            self._normalize_text(airport.get("location")),
                            self._normalize_text(
                                airport.get("country_iso2"), uppercase=True
                            ),
                            self._normalize_optional_float(airport.get("latitude")),
                            self._normalize_optional_float(airport.get("longitude")),
                            "route",
                            json.dumps(airport),
                            updated_at.isoformat(),
                        ),
                    )

                connection.commit()
            finally:
                connection.close()

    def search_airlines(
        self,
        query: str,
        limit: int,
        lookback_hours: float,
    ) -> list[dict[str, object]]:
        normalized_query = str(query).strip().upper()
        if not normalized_query:
            return []

        cutoff_timestamp = (
            datetime.now(timezone.utc) - timedelta(hours=max(lookback_hours, 1.0))
        ).isoformat()
        like_query = f"%{normalized_query}%"

        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    """
                    WITH latest_positions AS (
                        SELECT
                            p.icao24,
                            p.latitude,
                            p.longitude,
                            p.fetched_at,
                            ROW_NUMBER() OVER (
                                PARTITION BY p.icao24
                                ORDER BY p.fetched_at DESC
                            ) AS row_number
                        FROM positions p
                        WHERE p.fetched_at >= ?
                    ),
                    airline_matches AS (
                        SELECT
                            COALESCE(e.airline_code, e.operator_code, SUBSTR(e.callsign, 1, 3)) AS airline_code,
                            MAX(e.callsign) AS sample_callsign,
                            MAX(e.route_label) AS route_label,
                            MAX(e.route_verbose) AS route_verbose,
                            MAX(lp.latitude) AS latitude,
                            MAX(lp.longitude) AS longitude,
                            MAX(lp.fetched_at) AS fetched_at,
                            COUNT(*) AS traffic_count
                        FROM enriched_flights e
                        LEFT JOIN latest_positions lp
                            ON lp.icao24 = e.icao24
                           AND lp.row_number = 1
                        WHERE COALESCE(e.airline_code, e.operator_code, SUBSTR(e.callsign, 1, 3)) IS NOT NULL
                          AND (
                            UPPER(COALESCE(e.airline_code, '')) LIKE ?
                            OR UPPER(COALESCE(e.operator_code, '')) LIKE ?
                            OR UPPER(COALESCE(e.callsign, '')) LIKE ?
                            OR UPPER(COALESCE(e.route_verbose, '')) LIKE ?
                          )
                        GROUP BY COALESCE(e.airline_code, e.operator_code, SUBSTR(e.callsign, 1, 3))
                    )
                    SELECT *
                    FROM airline_matches
                    WHERE airline_code IS NOT NULL
                    ORDER BY traffic_count DESC, fetched_at DESC
                    LIMIT ?
                    """,
                    (
                        cutoff_timestamp,
                        like_query,
                        like_query,
                        like_query,
                        like_query,
                        max(limit, 1),
                    ),
                ).fetchall()
            finally:
                connection.close()

        return [
            {
                "entity_type": "airline",
                "entity_key": row["airline_code"],
                "label": row["airline_code"],
                "subtitle": row["route_verbose"]
                or row["route_label"]
                or row["sample_callsign"]
                or "Recent airline traffic",
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "traffic_count": row["traffic_count"],
                "fetched_at": row["fetched_at"],
            }
            for row in rows
            if row["airline_code"]
        ]

    def search_aircraft_profiles(
        self,
        query: str,
        limit: int,
        lookback_hours: float,
    ) -> list[dict[str, object]]:
        normalized_query = str(query).strip().upper()
        if not normalized_query:
            return []

        cutoff_timestamp = (
            datetime.now(timezone.utc) - timedelta(hours=max(lookback_hours, 1.0))
        ).isoformat()
        like_query = f"%{normalized_query}%"

        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    """
                    WITH latest_positions AS (
                        SELECT
                            p.icao24,
                            p.callsign,
                            p.registration,
                            p.type_code,
                            p.origin_country,
                            p.latitude,
                            p.longitude,
                            p.altitude,
                            p.velocity,
                            p.vertical_rate,
                            p.true_track,
                            p.last_contact,
                            p.on_ground,
                            p.fetched_at,
                            ROW_NUMBER() OVER (
                                PARTITION BY p.icao24
                                ORDER BY p.fetched_at DESC
                            ) AS row_number
                        FROM positions p
                        WHERE p.fetched_at >= ?
                    )
                    SELECT
                        lp.icao24,
                        COALESCE(e.registration, lp.registration) AS registration,
                        COALESCE(e.type_code, lp.type_code) AS type_code,
                        COALESCE(e.callsign, lp.callsign) AS callsign,
                        COALESCE(e.operator_code, e.airline_code, SUBSTR(COALESCE(e.callsign, lp.callsign, ''), 1, 3)) AS operator_code,
                        COALESCE(e.route_label, e.iata_codes, e.airport_codes) AS route_label,
                        lp.origin_country,
                        lp.latitude,
                        lp.longitude,
                        lp.altitude,
                        lp.velocity,
                        lp.vertical_rate,
                        lp.true_track,
                        lp.last_contact,
                        lp.on_ground,
                        lp.fetched_at
                    FROM latest_positions lp
                    LEFT JOIN enriched_flights e
                      ON e.icao24 = lp.icao24
                    WHERE lp.row_number = 1
                      AND (
                        UPPER(COALESCE(e.registration, lp.registration, '')) LIKE ?
                        OR UPPER(COALESCE(e.type_code, lp.type_code, '')) LIKE ?
                        OR UPPER(COALESCE(e.callsign, lp.callsign, '')) LIKE ?
                        OR UPPER(COALESCE(e.icao24, lp.icao24, '')) LIKE ?
                      )
                    ORDER BY
                        CASE
                            WHEN UPPER(COALESCE(e.registration, lp.registration, '')) = ? THEN 0
                            WHEN UPPER(COALESCE(e.icao24, lp.icao24, '')) = ? THEN 1
                            WHEN UPPER(COALESCE(e.callsign, lp.callsign, '')) = ? THEN 2
                            ELSE 3
                        END,
                        lp.fetched_at DESC
                    LIMIT ?
                    """,
                    (
                        cutoff_timestamp,
                        like_query,
                        like_query,
                        like_query,
                        like_query,
                        normalized_query,
                        normalized_query,
                        normalized_query,
                        max(limit, 1),
                    ),
                ).fetchall()
            finally:
                connection.close()

        return [
            {
                "entity_type": "aircraft",
                "entity_key": row["registration"] or row["icao24"],
                "label": row["registration"] or row["icao24"].upper(),
                "subtitle": " · ".join(
                    part
                    for part in (
                        row["type_code"],
                        row["operator_code"],
                        row["route_label"],
                    )
                    if part
                )
                or row["origin_country"]
                or "Tracked aircraft",
                "icao24": row["icao24"],
                "callsign": row["callsign"],
                "registration": row["registration"],
                "type_code": row["type_code"],
                "operator_code": row["operator_code"],
                "origin_country": row["origin_country"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "altitude": row["altitude"],
                "velocity": row["velocity"],
                "vertical_rate": row["vertical_rate"],
                "true_track": row["true_track"],
                "last_contact": row["last_contact"],
                "on_ground": bool(row["on_ground"]),
                "fetched_at": row["fetched_at"],
            }
            for row in rows
            if row["icao24"]
        ]

    def search_routes(self, query: str, limit: int) -> list[dict[str, object]]:
        normalized_query = str(query).strip().upper()
        if not normalized_query:
            return []

        like_query = f"%{normalized_query}%"

        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    """
                    WITH latest_positions AS (
                        SELECT
                            p.icao24,
                            p.latitude,
                            p.longitude,
                            p.fetched_at,
                            ROW_NUMBER() OVER (
                                PARTITION BY p.icao24
                                ORDER BY p.fetched_at DESC
                            ) AS row_number
                        FROM positions p
                    )
                    SELECT
                        e.route_label,
                        e.route_verbose,
                        e.airport_codes,
                        e.iata_codes,
                        e.origin_iata,
                        e.destination_iata,
                        e.origin_icao,
                        e.destination_icao,
                        MAX(lp.latitude) AS latitude,
                        MAX(lp.longitude) AS longitude,
                        MAX(lp.fetched_at) AS fetched_at,
                        COUNT(*) AS route_count
                    FROM enriched_flights e
                    LEFT JOIN latest_positions lp
                        ON lp.icao24 = e.icao24
                       AND lp.row_number = 1
                    WHERE (
                        UPPER(COALESCE(e.route_label, '')) LIKE ?
                        OR UPPER(COALESCE(e.route_verbose, '')) LIKE ?
                        OR UPPER(COALESCE(e.airport_codes, '')) LIKE ?
                        OR UPPER(COALESCE(e.iata_codes, '')) LIKE ?
                    )
                    GROUP BY
                        e.route_label,
                        e.route_verbose,
                        e.airport_codes,
                        e.iata_codes,
                        e.origin_iata,
                        e.destination_iata,
                        e.origin_icao,
                        e.destination_icao
                    ORDER BY route_count DESC, fetched_at DESC
                    LIMIT ?
                    """,
                    (
                        like_query,
                        like_query,
                        like_query,
                        like_query,
                        max(limit, 1),
                    ),
                ).fetchall()
            finally:
                connection.close()

        return [
            {
                "entity_type": "route",
                "entity_key": row["iata_codes"]
                or row["airport_codes"]
                or row["route_label"],
                "label": row["iata_codes"] or row["airport_codes"] or row["route_label"],
                "subtitle": row["route_verbose"] or row["route_label"] or "Recent route",
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "fetched_at": row["fetched_at"],
                "route_count": row["route_count"],
                "origin_iata": row["origin_iata"],
                "destination_iata": row["destination_iata"],
                "origin_icao": row["origin_icao"],
                "destination_icao": row["destination_icao"],
            }
            for row in rows
            if row["route_label"] or row["airport_codes"] or row["iata_codes"]
        ]

    def list_airport_movements(
        self,
        airport_codes: list[str],
        hours: int,
        limit: int,
    ) -> dict[str, list[dict[str, object]]]:
        normalized_codes = [
            str(code).strip().upper() for code in airport_codes if str(code).strip()
        ]
        if not normalized_codes:
            return {"arrivals": [], "departures": []}

        placeholders = ", ".join("?" for _ in normalized_codes)
        cutoff_timestamp = (
            datetime.now(timezone.utc) - timedelta(hours=max(hours, 1))
        ).isoformat()

        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    f"""
                    WITH latest_positions AS (
                        SELECT
                            p.icao24,
                            p.callsign,
                            p.registration,
                            p.type_code,
                            p.origin_country,
                            p.latitude,
                            p.longitude,
                            p.altitude,
                            p.velocity,
                            p.true_track,
                            p.on_ground,
                            p.fetched_at,
                            ROW_NUMBER() OVER (
                                PARTITION BY p.icao24
                                ORDER BY p.fetched_at DESC
                            ) AS row_number
                        FROM positions p
                        WHERE p.fetched_at >= ?
                    )
                    SELECT
                        e.icao24,
                        e.callsign,
                        e.registration,
                        e.type_code,
                        e.origin_name,
                        e.destination_name,
                        e.origin_icao,
                        e.origin_iata,
                        e.destination_icao,
                        e.destination_iata,
                        lp.origin_country,
                        lp.latitude,
                        lp.longitude,
                        lp.altitude,
                        lp.velocity,
                        lp.true_track,
                        lp.on_ground,
                        lp.fetched_at
                    FROM enriched_flights e
                    JOIN latest_positions lp
                      ON lp.icao24 = e.icao24
                     AND lp.row_number = 1
                    WHERE
                        e.origin_icao IN ({placeholders})
                        OR e.origin_iata IN ({placeholders})
                        OR e.destination_icao IN ({placeholders})
                        OR e.destination_iata IN ({placeholders})
                    ORDER BY lp.fetched_at DESC
                    LIMIT ?
                    """,
                    (
                        cutoff_timestamp,
                        *normalized_codes,
                        *normalized_codes,
                        *normalized_codes,
                        *normalized_codes,
                        max(limit * 3, limit),
                    ),
                ).fetchall()
            finally:
                connection.close()

        arrivals = []
        departures = []
        for row in rows:
            item = {
                "icao24": row["icao24"],
                "callsign": row["callsign"],
                "registration": row["registration"],
                "type_code": row["type_code"],
                "origin_country": row["origin_country"],
                "origin": row["origin_iata"] or row["origin_icao"] or row["origin_name"],
                "destination": row["destination_iata"]
                or row["destination_icao"]
                or row["destination_name"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "altitude": row["altitude"],
                "velocity": row["velocity"],
                "true_track": row["true_track"],
                "on_ground": bool(row["on_ground"]),
                "fetched_at": row["fetched_at"],
            }
            if row["destination_icao"] in normalized_codes or row["destination_iata"] in normalized_codes:
                arrivals.append(item)
            if row["origin_icao"] in normalized_codes or row["origin_iata"] in normalized_codes:
                departures.append(item)

        return {
            "arrivals": arrivals[: max(limit, 1)],
            "departures": departures[: max(limit, 1)],
        }

    def get_known_airport(self, code: str | None) -> dict[str, object] | None:
        normalized_code = self._normalize_text(code, uppercase=True)
        if not normalized_code:
            return None

        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    """
                    SELECT *
                    FROM known_airports
                    WHERE airport_key = ? OR icao = ? OR iata = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (normalized_code, normalized_code, normalized_code),
                ).fetchone()
            finally:
                connection.close()

        if not row:
            return None

        return {
            "entity_type": "airport",
            "entity_key": row["airport_key"],
            "icao": row["icao"],
            "iata": row["iata"],
            "name": row["name"],
            "city": row["location"],
            "country": row["country_iso2"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "label": row["iata"] or row["icao"] or row["airport_key"],
            "subtitle": row["location"] or row["name"],
        }

    def list_known_airports_in_bbox(
        self,
        bbox: dict[str, float],
        limit: int,
    ) -> list[dict[str, object]]:
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM known_airports
                    WHERE latitude BETWEEN ? AND ?
                      AND longitude BETWEEN ? AND ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (
                        bbox["lamin"],
                        bbox["lamax"],
                        bbox["lomin"],
                        bbox["lomax"],
                        max(limit, 1),
                    ),
                ).fetchall()
            finally:
                connection.close()

        return [
            {
                "entity_type": "airport",
                "entity_key": row["airport_key"],
                "icao": row["icao"],
                "iata": row["iata"],
                "name": row["name"],
                "city": row["location"],
                "country": row["country_iso2"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "label": row["iata"] or row["icao"] or row["airport_key"],
                "subtitle": row["location"] or row["name"],
            }
            for row in rows
        ]

    def _initialize_database(self) -> None:
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS enriched_flights (
                    icao24 TEXT PRIMARY KEY,
                    callsign TEXT,
                    registration TEXT,
                    type_code TEXT,
                    operator_code TEXT,
                    airline_code TEXT,
                    flight_number TEXT,
                    route_label TEXT,
                    route_verbose TEXT,
                    airport_codes TEXT,
                    iata_codes TEXT,
                    origin_icao TEXT,
                    origin_iata TEXT,
                    origin_name TEXT,
                    destination_icao TEXT,
                    destination_iata TEXT,
                    destination_name TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS known_airports (
                    airport_key TEXT PRIMARY KEY,
                    icao TEXT,
                    iata TEXT,
                    name TEXT,
                    location TEXT,
                    country_iso2 TEXT,
                    latitude REAL,
                    longitude REAL,
                    source TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_enriched_callsign
                    ON enriched_flights (callsign);
                CREATE INDEX IF NOT EXISTS idx_enriched_route_label
                    ON enriched_flights (route_label);
                CREATE INDEX IF NOT EXISTS idx_enriched_airline_code
                    ON enriched_flights (airline_code);
                CREATE INDEX IF NOT EXISTS idx_known_airports_codes
                    ON known_airports (icao, iata, updated_at DESC);
                """
            )
            connection.commit()
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.archive_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @staticmethod
    def _normalize_text(value: object, uppercase: bool = False) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.upper() if uppercase else cleaned

    @staticmethod
    def _normalize_optional_float(value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _normalize_airport(cls, payload: dict[str, object]) -> dict[str, object] | None:
        icao = cls._normalize_text(payload.get("icao"), uppercase=True)
        iata = cls._normalize_text(payload.get("iata"), uppercase=True)
        name = cls._normalize_text(payload.get("name"))
        location = cls._normalize_text(payload.get("location"))
        if not any((icao, iata, name, location)):
            return None

        return {
            "icao": icao,
            "iata": iata,
            "name": name,
            "location": location,
            "country_iso2": cls._normalize_text(payload.get("country_iso2"), uppercase=True),
            "latitude": cls._normalize_optional_float(payload.get("latitude")),
            "longitude": cls._normalize_optional_float(payload.get("longitude")),
        }

    @staticmethod
    def _normalize_timestamp(value: object) -> datetime | None:
        if not value:
            return None
        try:
            timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
