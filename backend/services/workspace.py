from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4


class WorkspaceService:
    VALID_ROLES = {"viewer", "analyst", "admin"}

    def __init__(self, workspace_path: str) -> None:
        self.workspace_path = Path(workspace_path).expanduser()
        self._lock = Lock()
        self._initialize_database()

    def list_profiles(self) -> dict[str, object]:
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    """
                    SELECT id, display_name, role, created_at, updated_at
                    FROM profiles
                    ORDER BY updated_at DESC, created_at ASC
                    """
                ).fetchall()
            finally:
                connection.close()

        profiles = [dict(row) for row in rows]
        return {
            "count": len(profiles),
            "profiles": profiles,
        }

    def create_profile(
        self,
        display_name: str,
        role: str = "analyst",
    ) -> dict[str, object]:
        normalized_name = " ".join(str(display_name).split()).strip()
        if not normalized_name:
            raise ValueError("Display name is required.")
        normalized_role = self._normalize_role(role)

        timestamp = self._timestamp()
        profile = {
            "id": str(uuid4()),
            "display_name": normalized_name[:48],
            "role": normalized_role,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        with self._lock:
            connection = self._connect()
            try:
                connection.execute(
                    """
                    INSERT INTO profiles (id, display_name, role, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        profile["id"],
                        profile["display_name"],
                        profile["role"],
                        profile["created_at"],
                        profile["updated_at"],
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO workspace_state (profile_id, payload_json, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        profile["id"],
                        json.dumps(self._default_state()),
                        timestamp,
                    ),
                )
                connection.commit()
            finally:
                connection.close()

        return profile

    def get_workspace_state(self, profile_id: str | None = None) -> dict[str, object]:
        resolved_profile = self._resolve_profile(profile_id)
        with self._lock:
            connection = self._connect()
            try:
                row = connection.execute(
                    """
                    SELECT payload_json, updated_at
                    FROM workspace_state
                    WHERE profile_id = ?
                    """,
                    (resolved_profile["id"],),
                ).fetchone()
            finally:
                connection.close()

        payload = self._default_state()
        updated_at = resolved_profile["updated_at"]
        if row:
            try:
                payload = self._normalize_state(json.loads(row["payload_json"]))
            except (TypeError, json.JSONDecodeError):
                payload = self._default_state()
            updated_at = row["updated_at"]

        return {
            "profile": resolved_profile,
            "state": payload,
            "updated_at": updated_at,
        }

    def save_workspace_state(
        self,
        profile_id: str,
        state: dict[str, object] | None,
    ) -> dict[str, object]:
        resolved_profile = self._resolve_profile(profile_id)
        normalized_state = self._normalize_state(state)
        timestamp = self._timestamp()

        with self._lock:
            connection = self._connect()
            try:
                connection.execute(
                    """
                    INSERT INTO workspace_state (profile_id, payload_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(profile_id) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        resolved_profile["id"],
                        json.dumps(normalized_state),
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    UPDATE profiles
                    SET updated_at = ?
                    WHERE id = ?
                    """,
                    (timestamp, resolved_profile["id"]),
                )
                connection.commit()
            finally:
                connection.close()

        return self.get_workspace_state(resolved_profile["id"])

    def _resolve_profile(self, profile_id: str | None) -> dict[str, object]:
        with self._lock:
            connection = self._connect()
            try:
                if profile_id:
                    row = connection.execute(
                        """
                        SELECT id, display_name, role, created_at, updated_at
                        FROM profiles
                        WHERE id = ?
                        """,
                        (profile_id,),
                    ).fetchone()
                    if row:
                        return dict(row)

                row = connection.execute(
                    """
                    SELECT id, display_name, role, created_at, updated_at
                    FROM profiles
                    ORDER BY created_at ASC
                    LIMIT 1
                    """
                ).fetchone()
                if row:
                    return dict(row)
            finally:
                connection.close()

        profile = self.create_profile("Radar Desk")
        return profile

    def _initialize_database(self) -> None:
        self.workspace_path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'analyst',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workspace_state (
                    profile_id TEXT PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._ensure_role_column(connection)
            connection.commit()
        finally:
            connection.close()

        self._resolve_profile(None)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.workspace_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _normalize_role(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in cls.VALID_ROLES:
            raise ValueError("Invalid profile role.")
        return normalized

    @classmethod
    def _ensure_role_column(cls, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(profiles)").fetchall()
        }
        if "role" in columns:
            return

        connection.execute(
            "ALTER TABLE profiles ADD COLUMN role TEXT NOT NULL DEFAULT 'analyst'"
        )

    @staticmethod
    def _default_state() -> dict[str, object]:
        return {
            "filters": {},
            "mapStyle": "standard",
            "mapViewport": None,
            "filterPresets": [],
            "sortBy": "altitude_desc",
            "theme": "dark",
            "watchlist": [],
            "watchModeEnabled": False,
            "flightAnnotations": {},
            "alertRules": [],
            "alertEvents": [],
            "monitoringSessions": [],
            "savedViews": [],
            "onboardingDismissed": False,
        }

    @classmethod
    def _normalize_state(cls, state: dict[str, object] | None) -> dict[str, object]:
        normalized = cls._default_state()
        if isinstance(state, dict):
            normalized.update(state)
        return normalized
