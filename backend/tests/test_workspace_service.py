from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.services.workspace import WorkspaceService


class WorkspaceServiceRoleTests(unittest.TestCase):
    def test_create_profile_persists_explicit_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = WorkspaceService(str(Path(temp_dir) / "workspace.sqlite3"))

            profile = service.create_profile("Ops Desk", role="admin")
            payload = service.get_workspace_state(profile["id"])

            self.assertEqual(profile["role"], "admin")
            self.assertEqual(payload["profile"]["role"], "admin")

    def test_existing_database_is_migrated_with_default_role(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "workspace.sqlite3"
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE profiles (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE workspace_state (
                    profile_id TEXT PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                INSERT INTO profiles (id, display_name, created_at, updated_at)
                VALUES ('desk-1', 'Legacy Desk', '2026-03-10T00:00:00+00:00', '2026-03-10T00:00:00+00:00');
                """
            )
            connection.commit()
            connection.close()

            service = WorkspaceService(str(db_path))
            payload = service.list_profiles()

            self.assertEqual(payload["profiles"][0]["role"], "analyst")

    def test_invalid_role_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = WorkspaceService(str(Path(temp_dir) / "workspace.sqlite3"))

            with self.assertRaises(ValueError):
                service.create_profile("Desk", role="owner")


if __name__ == "__main__":
    unittest.main()
