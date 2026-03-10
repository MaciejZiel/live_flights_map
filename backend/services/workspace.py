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

    def list_accounts(self) -> dict[str, object]:
        with self._lock:
            connection = self._connect()
            try:
                rows = connection.execute(
                    """
                    SELECT
                        accounts.id,
                        accounts.display_name,
                        accounts.email,
                        accounts.created_at,
                        accounts.updated_at,
                        COUNT(profiles.id) AS profile_count
                    FROM accounts
                    LEFT JOIN profiles ON profiles.account_id = accounts.id
                    GROUP BY accounts.id
                    ORDER BY accounts.updated_at DESC, accounts.created_at ASC
                    """
                ).fetchall()
            finally:
                connection.close()

        accounts = [dict(row) for row in rows]
        return {
            "count": len(accounts),
            "accounts": accounts,
        }

    def create_account(
        self,
        display_name: str,
        email: str | None = None,
    ) -> dict[str, object]:
        normalized_name = self._normalize_display_name(display_name)
        normalized_email = self._normalize_email(email)
        timestamp = self._timestamp()

        with self._lock:
            connection = self._connect()
            try:
                account = self._create_account_locked(
                    connection,
                    display_name=normalized_name,
                    email=normalized_email,
                    timestamp=timestamp,
                )
                profile = self._create_profile_locked(
                    connection,
                    account_id=account["id"],
                    display_name="Main Desk",
                    role="analyst",
                    timestamp=timestamp,
                )
                connection.commit()
            finally:
                connection.close()

        return {
            "account": account,
            "profile": profile,
        }

    def list_profiles(self, account_id: str | None = None) -> dict[str, object]:
        with self._lock:
            connection = self._connect()
            try:
                account = self._resolve_account_locked(connection, account_id)
                rows = connection.execute(
                    """
                    SELECT id, account_id, display_name, role, created_at, updated_at
                    FROM profiles
                    WHERE account_id = ?
                    ORDER BY updated_at DESC, created_at ASC
                    """,
                    (account["id"],),
                ).fetchall()
            finally:
                connection.close()

        profiles = [dict(row) for row in rows]
        return {
            "count": len(profiles),
            "account": account,
            "profiles": profiles,
        }

    def create_profile(
        self,
        display_name: str,
        role: str = "analyst",
        account_id: str | None = None,
    ) -> dict[str, object]:
        normalized_name = self._normalize_display_name(display_name)
        normalized_role = self._normalize_role(role)
        timestamp = self._timestamp()

        with self._lock:
            connection = self._connect()
            try:
                account = self._resolve_account_locked(connection, account_id)
                profile = self._create_profile_locked(
                    connection,
                    account_id=account["id"],
                    display_name=normalized_name,
                    role=normalized_role,
                    timestamp=timestamp,
                )
                connection.commit()
            finally:
                connection.close()

        return profile

    def get_workspace_state(
        self,
        profile_id: str | None = None,
        account_id: str | None = None,
    ) -> dict[str, object]:
        with self._lock:
            connection = self._connect()
            try:
                profile = self._resolve_profile_locked(connection, profile_id, account_id)
                account = self._resolve_account_locked(connection, profile["account_id"])
                row = connection.execute(
                    """
                    SELECT payload_json, updated_at
                    FROM workspace_state
                    WHERE profile_id = ?
                    """,
                    (profile["id"],),
                ).fetchone()
            finally:
                connection.close()

        payload = self._default_state()
        updated_at = profile["updated_at"]
        if row:
            try:
                payload = self._normalize_state(json.loads(row["payload_json"]))
            except (TypeError, json.JSONDecodeError):
                payload = self._default_state()
            updated_at = row["updated_at"]

        return {
            "account": account,
            "profile": profile,
            "state": payload,
            "updated_at": updated_at,
        }

    def save_workspace_state(
        self,
        profile_id: str,
        state: dict[str, object] | None,
    ) -> dict[str, object]:
        normalized_profile_id = str(profile_id or "").strip()
        if not normalized_profile_id:
            raise ValueError("Profile id is required.")

        normalized_state = self._normalize_state(state)
        timestamp = self._timestamp()

        with self._lock:
            connection = self._connect()
            try:
                profile = self._resolve_profile_locked(connection, normalized_profile_id, None)
                connection.execute(
                    """
                    INSERT INTO workspace_state (profile_id, payload_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(profile_id) DO UPDATE SET
                        payload_json = excluded.payload_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        profile["id"],
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
                    (timestamp, profile["id"]),
                )
                connection.execute(
                    """
                    UPDATE accounts
                    SET updated_at = ?
                    WHERE id = ?
                    """,
                    (timestamp, profile["account_id"]),
                )
                connection.commit()
            finally:
                connection.close()

        return self.get_workspace_state(normalized_profile_id)

    def _initialize_database(self) -> None:
        self.workspace_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            connection = self._connect()
            try:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS accounts (
                        id TEXT PRIMARY KEY,
                        display_name TEXT NOT NULL,
                        email TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS profiles (
                        id TEXT PRIMARY KEY,
                        account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
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
                self._ensure_account_column(connection)
                default_account = self._resolve_account_locked(connection, None)
                self._backfill_profile_accounts_locked(connection, default_account["id"])
                profile_count = connection.execute(
                    "SELECT COUNT(*) FROM profiles"
                ).fetchone()[0]
                if profile_count == 0:
                    self._create_profile_locked(
                        connection,
                        account_id=default_account["id"],
                        display_name="Radar Desk",
                        role="analyst",
                        timestamp=self._timestamp(),
                    )
                connection.commit()
            finally:
                connection.close()

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
    def _normalize_display_name(cls, value: object) -> str:
        normalized_name = " ".join(str(value or "").split()).strip()
        if not normalized_name:
            raise ValueError("Display name is required.")
        return normalized_name[:48]

    @staticmethod
    def _normalize_email(value: object) -> str | None:
        normalized = str(value or "").strip().lower()
        if not normalized:
            return None
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid account email.")
        return normalized[:96]

    @classmethod
    def _normalize_role(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in cls.VALID_ROLES:
            raise ValueError("Invalid profile role.")
        return normalized

    @classmethod
    def _resolve_account_locked(
        cls,
        connection: sqlite3.Connection,
        account_id: str | None,
    ) -> dict[str, object]:
        normalized_account_id = str(account_id or "").strip()
        if normalized_account_id:
            row = connection.execute(
                """
                SELECT id, display_name, email, created_at, updated_at
                FROM accounts
                WHERE id = ?
                """,
                (normalized_account_id,),
            ).fetchone()
            if row:
                return dict(row)
            raise ValueError("Workspace account not found.")

        row = connection.execute(
            """
            SELECT id, display_name, email, created_at, updated_at
            FROM accounts
            ORDER BY created_at ASC
            LIMIT 1
            """
        ).fetchone()
        if row:
            return dict(row)

        return cls._create_account_locked(
            connection,
            display_name="Radar Desk",
            email=None,
            timestamp=cls._timestamp(),
        )

    @classmethod
    def _resolve_profile_locked(
        cls,
        connection: sqlite3.Connection,
        profile_id: str | None,
        account_id: str | None,
    ) -> dict[str, object]:
        normalized_profile_id = str(profile_id or "").strip()

        if normalized_profile_id:
            row = connection.execute(
                """
                SELECT id, account_id, display_name, role, created_at, updated_at
                FROM profiles
                WHERE id = ?
                """,
                (normalized_profile_id,),
            ).fetchone()
            if row:
                profile = dict(row)
                if not account_id or profile["account_id"] == str(account_id).strip():
                    return profile
                raise ValueError("Workspace profile does not belong to the selected account.")
            raise ValueError("Workspace profile not found.")

        account = cls._resolve_account_locked(connection, account_id)
        row = connection.execute(
            """
            SELECT id, account_id, display_name, role, created_at, updated_at
            FROM profiles
            WHERE account_id = ?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (account["id"],),
        ).fetchone()
        if row:
            return dict(row)

        return cls._create_profile_locked(
            connection,
            account_id=account["id"],
            display_name="Main Desk",
            role="analyst",
            timestamp=cls._timestamp(),
        )

    @classmethod
    def _create_account_locked(
        cls,
        connection: sqlite3.Connection,
        display_name: str,
        email: str | None,
        timestamp: str,
    ) -> dict[str, object]:
        account = {
            "id": str(uuid4()),
            "display_name": display_name,
            "email": email,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        connection.execute(
            """
            INSERT INTO accounts (id, display_name, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                account["id"],
                account["display_name"],
                account["email"],
                account["created_at"],
                account["updated_at"],
            ),
        )
        return account

    @classmethod
    def _create_profile_locked(
        cls,
        connection: sqlite3.Connection,
        account_id: str,
        display_name: str,
        role: str,
        timestamp: str,
    ) -> dict[str, object]:
        profile = {
            "id": str(uuid4()),
            "account_id": account_id,
            "display_name": display_name,
            "role": role,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        connection.execute(
            """
            INSERT INTO profiles (id, account_id, display_name, role, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                profile["id"],
                profile["account_id"],
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
                json.dumps(cls._default_state()),
                timestamp,
            ),
        )
        connection.execute(
            """
            UPDATE accounts
            SET updated_at = ?
            WHERE id = ?
            """,
            (timestamp, account_id),
        )
        return profile

    @classmethod
    def _ensure_role_column(cls, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(profiles)").fetchall()
        }
        if "role" not in columns:
            connection.execute(
                "ALTER TABLE profiles ADD COLUMN role TEXT NOT NULL DEFAULT 'analyst'"
            )

    @classmethod
    def _ensure_account_column(cls, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(profiles)").fetchall()
        }
        if "account_id" not in columns:
            connection.execute("ALTER TABLE profiles ADD COLUMN account_id TEXT")

    @staticmethod
    def _backfill_profile_accounts_locked(
        connection: sqlite3.Connection,
        account_id: str,
    ) -> None:
        connection.execute(
            """
            UPDATE profiles
            SET account_id = ?
            WHERE account_id IS NULL OR TRIM(account_id) = ''
            """,
            (account_id,),
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
            "savedEntities": [],
            "onboardingDismissed": False,
            "weatherLayerEnabled": False,
            "showAirportMarkers": True,
            "selectedAirportCode": None,
            "replayWindowMinutes": 90,
            "replayPlaybackSpeed": 1,
        }

    @classmethod
    def _normalize_state(cls, state: dict[str, object] | None) -> dict[str, object]:
        normalized = cls._default_state()
        if isinstance(state, dict):
            normalized.update(state)
        return normalized
