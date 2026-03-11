from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from time import time


class AircraftPhotoCacheService:
    def __init__(self, cache_path: str) -> None:
        self.cache_path = Path(cache_path).expanduser()
        self._lock = Lock()
        self._initialize_database()

    def get_lookup(self, cache_key: str) -> dict[str, object] | None:
        normalized_key = str(cache_key or "").strip()
        if not normalized_key:
            return None

        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    """
                    SELECT photo_json, expires_at_epoch
                    FROM photo_lookup_cache
                    WHERE cache_key = ?
                    """,
                    (normalized_key,),
                ).fetchone()
                if row is None:
                    return None
                if int(row["expires_at_epoch"] or 0) <= int(time()):
                    connection.execute(
                        "DELETE FROM photo_lookup_cache WHERE cache_key = ?",
                        (normalized_key,),
                    )
                    connection.commit()
                    return None
            finally:
                connection.close()

        try:
            payload = json.loads(row["photo_json"])
        except (TypeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def store_lookup(
        self,
        cache_key: str,
        photo: dict[str, object],
        ttl_seconds: float,
    ) -> None:
        normalized_key = str(cache_key or "").strip()
        if not normalized_key or not isinstance(photo, dict):
            return

        expires_at_epoch = int(time() + max(float(ttl_seconds or 0), 60.0))
        with self._lock:
            connection = self._connect()
            try:
                connection.execute(
                    """
                    INSERT INTO photo_lookup_cache (cache_key, photo_json, expires_at_epoch)
                    VALUES (?, ?, ?)
                    ON CONFLICT(cache_key) DO UPDATE SET
                        photo_json = excluded.photo_json,
                        expires_at_epoch = excluded.expires_at_epoch
                    """,
                    (normalized_key, json.dumps(photo), expires_at_epoch),
                )
                connection.commit()
            finally:
                connection.close()

    def get_asset(self, url: str) -> dict[str, object] | None:
        normalized_url = str(url or "").strip()
        if not normalized_url:
            return None

        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    """
                    SELECT body, content_type, etag, expires_at_epoch
                    FROM photo_asset_cache
                    WHERE url = ?
                    """,
                    (normalized_url,),
                ).fetchone()
                if row is None:
                    return None
                if int(row["expires_at_epoch"] or 0) <= int(time()):
                    connection.execute(
                        "DELETE FROM photo_asset_cache WHERE url = ?",
                        (normalized_url,),
                    )
                    connection.commit()
                    return None
            finally:
                connection.close()

        return {
            "body": row["body"],
            "content_type": row["content_type"],
            "etag": row["etag"],
        }

    def store_asset(
        self,
        url: str,
        *,
        body: bytes,
        content_type: str,
        etag: str | None,
        ttl_seconds: float,
    ) -> None:
        normalized_url = str(url or "").strip()
        if not normalized_url or not isinstance(body, (bytes, bytearray)) or not content_type:
            return

        expires_at_epoch = int(time() + max(float(ttl_seconds or 0), 300.0))
        with self._lock:
            connection = self._connect()
            try:
                connection.execute(
                    """
                    INSERT INTO photo_asset_cache (url, body, content_type, etag, expires_at_epoch)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        body = excluded.body,
                        content_type = excluded.content_type,
                        etag = excluded.etag,
                        expires_at_epoch = excluded.expires_at_epoch
                    """,
                    (normalized_url, bytes(body), content_type, etag, expires_at_epoch),
                )
                connection.commit()
            finally:
                connection.close()

    def summarize(self) -> dict[str, object]:
        payload = {
            "path": str(self.cache_path),
            "available": False,
            "file_present": self.cache_path.exists(),
        }

        if not self.cache_path.exists():
            return payload

        with self._lock:
            try:
                connection = self._connect()
                payload["lookup_rows"] = connection.execute(
                    "SELECT COUNT(*) FROM photo_lookup_cache"
                ).fetchone()[0]
                payload["asset_rows"] = connection.execute(
                    "SELECT COUNT(*) FROM photo_asset_cache"
                ).fetchone()[0]
                payload["latest_lookup_expiry_epoch"] = connection.execute(
                    "SELECT MAX(expires_at_epoch) FROM photo_lookup_cache"
                ).fetchone()[0]
                payload["latest_asset_expiry_epoch"] = connection.execute(
                    "SELECT MAX(expires_at_epoch) FROM photo_asset_cache"
                ).fetchone()[0]
                payload["available"] = True
            except sqlite3.Error as exc:
                payload["error"] = str(exc)
            finally:
                if "connection" in locals():
                    connection.close()

        return payload

    def _initialize_database(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            connection = self._connect()
            try:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS photo_lookup_cache (
                        cache_key TEXT PRIMARY KEY,
                        photo_json TEXT NOT NULL,
                        expires_at_epoch INTEGER NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS photo_asset_cache (
                        url TEXT PRIMARY KEY,
                        body BLOB NOT NULL,
                        content_type TEXT NOT NULL,
                        etag TEXT,
                        expires_at_epoch INTEGER NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_photo_lookup_expiry
                        ON photo_lookup_cache (expires_at_epoch DESC);
                    CREATE INDEX IF NOT EXISTS idx_photo_asset_expiry
                        ON photo_asset_cache (expires_at_epoch DESC);
                    """
                )
                connection.commit()
            finally:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.cache_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        return connection
