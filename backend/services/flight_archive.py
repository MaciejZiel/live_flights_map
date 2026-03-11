from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock


class FlightArchiveService:
    def __init__(
        self,
        archive_path: str,
        retention_hours: float,
        max_snapshots: int,
    ) -> None:
        self.archive_path = Path(archive_path).expanduser()
        self.retention_hours = max(retention_hours, 0.0)
        self.max_snapshots = max(max_snapshots, 1)
        self._lock = Lock()
        self._initialize_database()

    def store_snapshot(self, payload: dict[str, object]) -> None:
        fetched_at = self._normalize_timestamp(payload.get("fetched_at"))
        bbox = self._normalize_bbox(payload.get("bbox"))
        flights = payload.get("flights")

        if fetched_at is None or bbox is None or not isinstance(flights, list):
            return

        snapshot_payload = {
            "fetched_at": fetched_at.isoformat(),
            "bbox": bbox,
            "count": int(payload.get("count") or len(flights)),
            "flights": flights,
        }

        bbox_key = self._bbox_key(bbox)
        cutoff_timestamp = (
            datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        ).isoformat()

        with self._lock:
            try:
                connection = self._connect()
                cursor = connection.cursor()
                cursor.execute(
                    """
                    INSERT INTO snapshots (
                        fetched_at,
                        bbox_key,
                        bbox_lamin,
                        bbox_lamax,
                        bbox_lomin,
                        bbox_lomax,
                        flight_count,
                        payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_payload["fetched_at"],
                        bbox_key,
                        bbox["lamin"],
                        bbox["lamax"],
                        bbox["lomin"],
                        bbox["lomax"],
                        snapshot_payload["count"],
                        json.dumps(snapshot_payload),
                    ),
                )
                snapshot_id = cursor.lastrowid
                position_rows = []
                for flight in flights:
                    if not isinstance(flight, dict):
                        continue
                    try:
                        position_rows.append(
                            self._build_position_row(snapshot_id, fetched_at, flight)
                        )
                    except ValueError:
                        continue

                if position_rows:
                    cursor.executemany(
                        """
                        INSERT INTO positions (
                            snapshot_id,
                            fetched_at,
                            icao24,
                            callsign,
                            registration,
                            type_code,
                            origin_country,
                            latitude,
                            longitude,
                            altitude,
                            velocity,
                            vertical_rate,
                            true_track,
                            last_contact,
                            on_ground
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        position_rows,
                    )
                self._prune_locked(cursor, cutoff_timestamp)
                connection.commit()
            except sqlite3.Error:
                return
            finally:
                if "connection" in locals():
                    connection.close()

    def run_maintenance(self, vacuum: bool = False) -> dict[str, object]:
        cutoff_timestamp = (
            datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        ).isoformat()

        with self._lock:
            connection = self._connect()
            try:
                cursor = connection.cursor()
                snapshot_rows_before = cursor.execute(
                    "SELECT COUNT(*) FROM snapshots"
                ).fetchone()[0]
                position_rows_before = cursor.execute(
                    "SELECT COUNT(*) FROM positions"
                ).fetchone()[0]
                latest_position_rows_before = cursor.execute(
                    "SELECT COUNT(*) FROM latest_positions"
                ).fetchone()[0]
                self._prune_locked(cursor, cutoff_timestamp)
                connection.commit()

                if vacuum:
                    connection.execute("VACUUM")

                snapshot_rows_after = cursor.execute(
                    "SELECT COUNT(*) FROM snapshots"
                ).fetchone()[0]
                position_rows_after = cursor.execute(
                    "SELECT COUNT(*) FROM positions"
                ).fetchone()[0]
                latest_position_rows_after = cursor.execute(
                    "SELECT COUNT(*) FROM latest_positions"
                ).fetchone()[0]
            finally:
                connection.close()

        return {
            "cutoff_timestamp": cutoff_timestamp,
            "vacuumed": vacuum,
            "snapshot_rows_before": snapshot_rows_before,
            "snapshot_rows_after": snapshot_rows_after,
            "position_rows_before": position_rows_before,
            "position_rows_after": position_rows_after,
            "latest_position_rows_before": latest_position_rows_before,
            "latest_position_rows_after": latest_position_rows_after,
            "snapshots_pruned": max(0, snapshot_rows_before - snapshot_rows_after),
            "positions_pruned": max(0, position_rows_before - position_rows_after),
            "latest_positions_pruned": max(
                0,
                latest_position_rows_before - latest_position_rows_after,
            ),
        }

    def list_replay_snapshots(
        self,
        bbox: dict[str, float],
        minutes: int,
        limit: int,
        end_at: object | None = None,
    ) -> dict[str, object]:
        normalized_bbox = self._normalize_bbox(bbox)
        if normalized_bbox is None:
            return {"bbox": bbox, "count": 0, "snapshots": []}

        normalized_limit = min(max(limit, 1), self.max_snapshots)
        normalized_minutes = max(minutes, 1)
        normalized_end_at = self._normalize_timestamp(end_at) or datetime.now(timezone.utc)
        cutoff_timestamp = (
            normalized_end_at - timedelta(minutes=normalized_minutes)
        ).isoformat()

        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    """
                    SELECT payload_json
                    FROM snapshots
                    WHERE bbox_key = ? AND fetched_at BETWEEN ? AND ?
                    ORDER BY fetched_at DESC
                    LIMIT ?
                    """,
                    (
                        self._bbox_key(normalized_bbox),
                        cutoff_timestamp,
                        normalized_end_at.isoformat(),
                        normalized_limit,
                    ),
                ).fetchall()
            finally:
                connection.close()

        snapshots = []
        for row in reversed(rows):
            try:
                snapshots.append(json.loads(row["payload_json"]))
            except (TypeError, json.JSONDecodeError):
                continue

        return {
            "bbox": normalized_bbox,
            "count": len(snapshots),
            "end_at": normalized_end_at.isoformat(),
            "lookback_minutes": normalized_minutes,
            "snapshots": snapshots,
        }

    def get_flight_trail(
        self,
        icao24: str,
        hours: int,
        limit: int,
    ) -> dict[str, object]:
        normalized_icao24 = str(icao24).strip().lower()
        if not normalized_icao24:
            return {"icao24": normalized_icao24, "count": 0, "points": []}

        normalized_limit = min(max(limit, 1), 2000)
        normalized_hours = max(hours, 1)
        cutoff_timestamp = (
            datetime.now(timezone.utc) - timedelta(hours=normalized_hours)
        ).isoformat()

        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    """
                    SELECT
                        fetched_at,
                        latitude,
                        longitude,
                        altitude,
                        velocity,
                        vertical_rate,
                        true_track,
                        on_ground
                    FROM positions
                    WHERE icao24 = ? AND fetched_at >= ?
                    ORDER BY fetched_at DESC
                    LIMIT ?
                    """,
                    (normalized_icao24, cutoff_timestamp, normalized_limit),
                ).fetchall()
            finally:
                connection.close()

        points = [
            {
                "timestamp": row["fetched_at"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "altitude": row["altitude"],
                "velocity": row["velocity"],
                "vertical_rate": row["vertical_rate"],
                "true_track": row["true_track"],
                "on_ground": bool(row["on_ground"]),
            }
            for row in reversed(rows)
        ]

        return {
            "icao24": normalized_icao24,
            "count": len(points),
            "points": points,
        }

    def search_recent_flights(
        self,
        query: str,
        limit: int,
        lookback_hours: float,
    ) -> dict[str, object]:
        normalized_query = str(query).strip()
        if not normalized_query:
            return {"query": normalized_query, "count": 0, "results": []}

        normalized_limit = min(max(limit, 1), 25)
        cutoff_timestamp = (
            datetime.now(timezone.utc) - timedelta(hours=max(lookback_hours, 0.5))
        ).isoformat()
        like_query = f"%{normalized_query.upper()}%"

        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    """
                    WITH ranked_positions AS (
                        SELECT
                            positions.icao24,
                            positions.callsign,
                            positions.registration,
                            positions.type_code,
                            positions.origin_country,
                            positions.latitude,
                            positions.longitude,
                            positions.altitude,
                            positions.true_track,
                            positions.on_ground,
                            positions.fetched_at,
                            ROW_NUMBER() OVER (
                                PARTITION BY positions.icao24
                                ORDER BY positions.fetched_at DESC
                            ) AS row_number
                        FROM positions
                        WHERE positions.fetched_at >= ?
                          AND (
                            UPPER(positions.icao24) LIKE ?
                            OR UPPER(COALESCE(positions.callsign, '')) LIKE ?
                            OR UPPER(COALESCE(positions.registration, '')) LIKE ?
                            OR UPPER(COALESCE(positions.type_code, '')) LIKE ?
                          )
                    )
                    SELECT
                        icao24,
                        callsign,
                        registration,
                        type_code,
                        origin_country,
                        latitude,
                        longitude,
                        altitude,
                        true_track,
                        on_ground,
                        fetched_at
                    FROM ranked_positions
                    WHERE row_number = 1
                    ORDER BY fetched_at DESC
                    LIMIT ?
                    """,
                    (
                        cutoff_timestamp,
                        like_query,
                        like_query,
                        like_query,
                        like_query,
                        normalized_limit,
                    ),
                ).fetchall()
            finally:
                connection.close()

        results = [
            {
                "icao24": row["icao24"],
                "callsign": row["callsign"],
                "registration": row["registration"],
                "type_code": row["type_code"],
                "origin_country": row["origin_country"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "altitude": row["altitude"],
                "true_track": row["true_track"],
                "on_ground": bool(row["on_ground"]),
                "fetched_at": row["fetched_at"],
            }
            for row in rows
        ]

        return {
            "query": normalized_query,
            "count": len(results),
            "results": results,
        }

    def list_hot_flights(
        self,
        limit: int,
        lookback_minutes: int,
    ) -> dict[str, object]:
        normalized_limit = min(max(limit, 1), 100)
        normalized_minutes = max(lookback_minutes, 5)
        cutoff_timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=normalized_minutes)
        ).isoformat()

        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    """
                    WITH ranked_positions AS (
                        SELECT
                            positions.icao24,
                            positions.callsign,
                            positions.registration,
                            positions.type_code,
                            positions.origin_country,
                            positions.latitude,
                            positions.longitude,
                            positions.altitude,
                            positions.velocity,
                            positions.vertical_rate,
                            positions.true_track,
                            positions.last_contact,
                            positions.on_ground,
                            positions.fetched_at,
                            COUNT(*) OVER (
                                PARTITION BY positions.icao24
                            ) AS tracking_count,
                            ROW_NUMBER() OVER (
                                PARTITION BY positions.icao24
                                ORDER BY positions.fetched_at DESC
                            ) AS row_number
                        FROM positions
                        WHERE positions.fetched_at >= ?
                    )
                    SELECT
                        icao24,
                        callsign,
                        registration,
                        type_code,
                        origin_country,
                        latitude,
                        longitude,
                        altitude,
                        velocity,
                        vertical_rate,
                        true_track,
                        last_contact,
                        on_ground,
                        fetched_at,
                        tracking_count
                    FROM ranked_positions
                    WHERE row_number = 1
                    ORDER BY tracking_count DESC, fetched_at DESC
                    LIMIT ?
                    """,
                    (cutoff_timestamp, normalized_limit),
                ).fetchall()
            finally:
                connection.close()

        flights = [
            {
                "icao24": row["icao24"],
                "callsign": row["callsign"],
                "registration": row["registration"],
                "type_code": row["type_code"],
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
                "tracking_count": row["tracking_count"],
            }
            for row in rows
        ]

        return {
            "count": len(flights),
            "lookback_minutes": normalized_minutes,
            "flights": flights,
        }

    def store_latest_snapshot(
        self,
        payload: dict[str, object],
        sector_key: str | None = None,
    ) -> dict[str, object]:
        fetched_at = self._normalize_timestamp(payload.get("fetched_at"))
        flights = payload.get("flights")

        if fetched_at is None or not isinstance(flights, list):
            return {"stored": 0}

        stored = 0
        cutoff_timestamp = (
            datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        ).isoformat()

        with self._lock:
            try:
                connection = self._connect()
                cursor = connection.cursor()
                for flight in flights:
                    if not isinstance(flight, dict):
                        continue
                    try:
                        row = self._build_latest_position_row(
                            fetched_at=fetched_at,
                            flight=flight,
                            sector_key=sector_key,
                        )
                    except ValueError:
                        continue

                    cursor.execute(
                        """
                        INSERT INTO latest_positions (
                            icao24,
                            fetched_at,
                            sector_key,
                            callsign,
                            registration,
                            type_code,
                            origin_country,
                            latitude,
                            longitude,
                            altitude,
                            velocity,
                            vertical_rate,
                            true_track,
                            last_contact,
                            on_ground,
                            payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(icao24) DO UPDATE SET
                            fetched_at = excluded.fetched_at,
                            sector_key = excluded.sector_key,
                            callsign = excluded.callsign,
                            registration = excluded.registration,
                            type_code = excluded.type_code,
                            origin_country = excluded.origin_country,
                            latitude = excluded.latitude,
                            longitude = excluded.longitude,
                            altitude = excluded.altitude,
                            velocity = excluded.velocity,
                            vertical_rate = excluded.vertical_rate,
                            true_track = excluded.true_track,
                            last_contact = excluded.last_contact,
                            on_ground = excluded.on_ground,
                            payload_json = excluded.payload_json
                        WHERE latest_positions.fetched_at IS NULL
                           OR excluded.fetched_at >= latest_positions.fetched_at
                        """,
                        row,
                    )
                    if cursor.rowcount > 0:
                        stored += 1

                cursor.execute(
                    "DELETE FROM latest_positions WHERE fetched_at < ?",
                    (cutoff_timestamp,),
                )
                connection.commit()
            except sqlite3.Error:
                return {"stored": 0}
            finally:
                if "connection" in locals():
                    connection.close()

        return {
            "stored": stored,
            "fetched_at": fetched_at.isoformat(),
            "sector_key": sector_key,
        }

    def list_latest_flights(
        self,
        bbox: dict[str, float],
        max_age_seconds: float,
        limit: int | None = None,
    ) -> dict[str, object]:
        normalized_bbox = self._normalize_bbox(bbox)
        if normalized_bbox is None:
            return {"bbox": bbox, "count": 0, "flights": [], "cache_meta": {"fresh": False}}

        normalized_limit = None if limit is None else min(max(int(limit), 1), 10000)
        normalized_max_age_seconds = max(float(max_age_seconds or 0), 1.0)
        cutoff_timestamp = (
            datetime.now(timezone.utc) - timedelta(seconds=normalized_max_age_seconds)
        ).isoformat()

        query = """
            SELECT
                fetched_at,
                sector_key,
                payload_json
            FROM latest_positions
            WHERE fetched_at >= ?
              AND latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
            ORDER BY fetched_at DESC
        """
        parameters: list[object] = [
            cutoff_timestamp,
            normalized_bbox["lamin"],
            normalized_bbox["lamax"],
            normalized_bbox["lomin"],
            normalized_bbox["lomax"],
        ]
        if normalized_limit is not None:
            query += " LIMIT ?"
            parameters.append(normalized_limit)

        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(query, tuple(parameters)).fetchall()
            finally:
                connection.close()

        flights: list[dict[str, object]] = []
        sector_keys: set[str] = set()
        freshest_at = None

        for row in rows:
            try:
                flight = json.loads(row["payload_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(flight, dict):
                continue

            if freshest_at is None:
                freshest_at = row["fetched_at"]
            sector_key = self._normalize_text(row["sector_key"])
            if sector_key:
                sector_keys.add(sector_key)
            flights.append(flight)

        return {
            "bbox": normalized_bbox,
            "count": len(flights),
            "fetched_at": freshest_at or datetime.now(timezone.utc).isoformat(),
            "flights": flights,
            "cache_meta": {
                "fresh": bool(flights),
                "max_age_seconds": normalized_max_age_seconds,
                "sector_keys": sorted(sector_keys),
                "freshest_position_at": freshest_at,
            },
        }

    def _initialize_database(self) -> None:
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fetched_at TEXT NOT NULL,
                    bbox_key TEXT NOT NULL,
                    bbox_lamin REAL NOT NULL,
                    bbox_lamax REAL NOT NULL,
                    bbox_lomin REAL NOT NULL,
                    bbox_lomax REAL NOT NULL,
                    flight_count INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
                    fetched_at TEXT NOT NULL,
                    icao24 TEXT NOT NULL,
                    callsign TEXT,
                    registration TEXT,
                    type_code TEXT,
                    origin_country TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    altitude REAL,
                    velocity REAL,
                    vertical_rate REAL,
                    true_track REAL,
                    last_contact INTEGER,
                    on_ground INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS latest_positions (
                    icao24 TEXT PRIMARY KEY,
                    fetched_at TEXT NOT NULL,
                    sector_key TEXT,
                    callsign TEXT,
                    registration TEXT,
                    type_code TEXT,
                    origin_country TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    altitude REAL,
                    velocity REAL,
                    vertical_rate REAL,
                    true_track REAL,
                    last_contact INTEGER,
                    on_ground INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_snapshots_bbox_time
                    ON snapshots (bbox_key, fetched_at DESC);
                CREATE INDEX IF NOT EXISTS idx_positions_icao24_time
                    ON positions (icao24, fetched_at DESC);
                CREATE INDEX IF NOT EXISTS idx_positions_fetched_time
                    ON positions (fetched_at DESC);
                CREATE INDEX IF NOT EXISTS idx_positions_callsign_time
                    ON positions (callsign, fetched_at DESC);
                CREATE INDEX IF NOT EXISTS idx_positions_registration_time
                    ON positions (registration, fetched_at DESC);
                CREATE INDEX IF NOT EXISTS idx_latest_positions_fetched_time
                    ON latest_positions (fetched_at DESC);
                CREATE INDEX IF NOT EXISTS idx_latest_positions_bbox_time
                    ON latest_positions (latitude, longitude, fetched_at DESC);
                """
            )
            connection.commit()
        finally:
            connection.close()

    def _prune_locked(self, cursor: sqlite3.Cursor, cutoff_timestamp: str) -> None:
        cursor.execute(
            "DELETE FROM snapshots WHERE fetched_at < ?",
            (cutoff_timestamp,),
        )
        cursor.execute(
            """
            DELETE FROM snapshots
            WHERE id IN (
                SELECT id
                FROM snapshots
                ORDER BY fetched_at DESC
                LIMIT -1 OFFSET ?
            )
            """,
            (self.max_snapshots,),
        )
        cursor.execute(
            "DELETE FROM latest_positions WHERE fetched_at < ?",
            (cutoff_timestamp,),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.archive_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @staticmethod
    def _normalize_timestamp(value: object) -> datetime | None:
        if not value:
            return None

        try:
            timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)

    @staticmethod
    def _normalize_bbox(value: object) -> dict[str, float] | None:
        if not isinstance(value, dict):
            return None

        try:
            return {
                "lamin": round(float(value["lamin"]), 4),
                "lamax": round(float(value["lamax"]), 4),
                "lomin": round(float(value["lomin"]), 4),
                "lomax": round(float(value["lomax"]), 4),
            }
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _bbox_key(bbox: dict[str, float]) -> str:
        return "|".join(
            f"{bbox[key]:.4f}"
            for key in ("lamin", "lamax", "lomin", "lomax")
        )

    @staticmethod
    def _build_position_row(
        snapshot_id: int,
        fetched_at: datetime,
        flight: dict[str, object],
    ) -> tuple[object, ...]:
        icao24 = str(flight.get("icao24") or "").strip().lower()
        latitude = flight.get("latitude")
        longitude = flight.get("longitude")
        if not icao24 or latitude is None or longitude is None:
            raise ValueError("Cannot archive a flight without identifier and coordinates.")

        return (
            snapshot_id,
            fetched_at.isoformat(),
            icao24,
            FlightArchiveService._normalize_text(flight.get("callsign"), uppercase=True),
            FlightArchiveService._normalize_text(
                flight.get("registration"), uppercase=True
            ),
            FlightArchiveService._normalize_text(flight.get("type_code"), uppercase=True),
            FlightArchiveService._normalize_text(flight.get("origin_country")),
            float(latitude),
            float(longitude),
            FlightArchiveService._normalize_optional_float(flight.get("altitude")),
            FlightArchiveService._normalize_optional_float(flight.get("velocity")),
            FlightArchiveService._normalize_optional_float(
                flight.get("vertical_rate")
            ),
            FlightArchiveService._normalize_optional_float(flight.get("true_track")),
            FlightArchiveService._normalize_optional_int(flight.get("last_contact")),
            1 if bool(flight.get("on_ground")) else 0,
        )

    @staticmethod
    def _build_latest_position_row(
        fetched_at: datetime,
        flight: dict[str, object],
        sector_key: str | None,
    ) -> tuple[object, ...]:
        icao24 = str(flight.get("icao24") or "").strip().lower()
        latitude = flight.get("latitude")
        longitude = flight.get("longitude")
        if not icao24 or latitude is None or longitude is None:
            raise ValueError("Cannot cache a live flight without identifier and coordinates.")

        normalized_flight = {
            **flight,
            "icao24": icao24,
            "callsign": FlightArchiveService._normalize_text(
                flight.get("callsign"), uppercase=True
            ),
            "registration": FlightArchiveService._normalize_text(
                flight.get("registration"), uppercase=True
            ),
            "type_code": FlightArchiveService._normalize_text(
                flight.get("type_code"), uppercase=True
            ),
            "origin_country": FlightArchiveService._normalize_text(
                flight.get("origin_country")
            ),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "altitude": FlightArchiveService._normalize_optional_float(
                flight.get("altitude")
            ),
            "velocity": FlightArchiveService._normalize_optional_float(
                flight.get("velocity")
            ),
            "vertical_rate": FlightArchiveService._normalize_optional_float(
                flight.get("vertical_rate")
            ),
            "true_track": FlightArchiveService._normalize_optional_float(
                flight.get("true_track")
            ),
            "last_contact": FlightArchiveService._normalize_optional_int(
                flight.get("last_contact")
            ),
            "on_ground": bool(flight.get("on_ground")),
        }

        return (
            icao24,
            fetched_at.isoformat(),
            FlightArchiveService._normalize_text(sector_key),
            normalized_flight["callsign"],
            normalized_flight["registration"],
            normalized_flight["type_code"],
            normalized_flight["origin_country"],
            normalized_flight["latitude"],
            normalized_flight["longitude"],
            normalized_flight["altitude"],
            normalized_flight["velocity"],
            normalized_flight["vertical_rate"],
            normalized_flight["true_track"],
            normalized_flight["last_contact"],
            1 if normalized_flight["on_ground"] else 0,
            json.dumps(normalized_flight),
        )

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

    @staticmethod
    def _normalize_optional_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
