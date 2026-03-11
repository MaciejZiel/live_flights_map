from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.services.workspace import WorkspaceService


class WorkspaceServiceTests(unittest.TestCase):
    def test_create_account_provisions_default_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = WorkspaceService(str(Path(temp_dir) / "workspace.sqlite3"))

            payload = service.create_account("Ops Team", email="ops@example.com")
            accounts = service.list_accounts()
            profiles = service.list_profiles(payload["account"]["id"])

            self.assertEqual(payload["account"]["display_name"], "Ops Team")
            self.assertEqual(payload["account"]["email"], "ops@example.com")
            self.assertEqual(payload["profile"]["display_name"], "Main Desk")
            self.assertEqual(accounts["accounts"][0]["display_name"], "Ops Team")
            self.assertEqual(profiles["profiles"][0]["account_id"], payload["account"]["id"])

    def test_create_profile_persists_explicit_role_and_account(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = WorkspaceService(str(Path(temp_dir) / "workspace.sqlite3"))

            account = service.create_account("Spotters")
            profile = service.create_profile(
                "Ops Desk",
                role="admin",
                account_id=account["account"]["id"],
            )
            payload = service.get_workspace_state(profile["id"])

            self.assertEqual(profile["role"], "admin")
            self.assertEqual(profile["account_id"], account["account"]["id"])
            self.assertEqual(payload["profile"]["role"], "admin")
            self.assertEqual(payload["account"]["id"], account["account"]["id"])

    def test_default_workspace_state_keeps_map_density_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = WorkspaceService(str(Path(temp_dir) / "workspace.sqlite3"))

            account = service.create_account("Ops Team")
            payload = service.get_workspace_state(account["profile"]["id"])

            self.assertFalse(payload["state"]["aircraftClusteringEnabled"])
            self.assertTrue(payload["state"]["showAirportMarkers"])

    def test_list_profiles_is_scoped_to_account(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = WorkspaceService(str(Path(temp_dir) / "workspace.sqlite3"))

            alpha = service.create_account("Alpha")
            beta = service.create_account("Beta")
            service.create_profile("Alpha Cargo", account_id=alpha["account"]["id"])
            service.create_profile("Beta Cargo", account_id=beta["account"]["id"])

            alpha_profiles = service.list_profiles(alpha["account"]["id"])
            beta_profiles = service.list_profiles(beta["account"]["id"])

            self.assertTrue(
                all(
                    profile["account_id"] == alpha["account"]["id"]
                    for profile in alpha_profiles["profiles"]
                )
            )
            self.assertTrue(
                all(
                    profile["account_id"] == beta["account"]["id"]
                    for profile in beta_profiles["profiles"]
                )
            )

    def test_workspace_state_persists_hidden_alert_engine_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = WorkspaceService(str(Path(temp_dir) / "workspace.sqlite3"))

            account = service.create_account("Ops Team")
            payload = service.save_workspace_state(
                account["profile"]["id"],
                {
                    "alertRules": [{"id": "rule-1", "type": "takeoff", "query": "Visible traffic"}],
                    "_alertEngineState": {
                        "ruleMatches": {"rule-1": ["48af06"]},
                        "previousFlightsByIcao24": {
                            "48af06": {
                                "icao24": "48AF06",
                                "callsign": "LOT123",
                                "registration": "SP-LVG",
                                "on_ground": True,
                            }
                        },
                    },
                },
            )

            self.assertEqual(
                payload["state"]["_alertEngineState"]["ruleMatches"]["rule-1"],
                ["48af06"],
            )
            self.assertEqual(
                payload["state"]["_alertEngineState"]["previousFlightsByIcao24"]["48af06"]["on_ground"],
                True,
            )

    def test_existing_database_is_migrated_with_default_role_and_account(self) -> None:
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
            profiles = service.list_profiles()
            accounts = service.list_accounts()

            self.assertEqual(profiles["profiles"][0]["role"], "analyst")
            self.assertTrue(profiles["profiles"][0]["account_id"])
            self.assertEqual(accounts["count"], 1)

    def test_invalid_role_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = WorkspaceService(str(Path(temp_dir) / "workspace.sqlite3"))

            with self.assertRaises(ValueError):
                service.create_profile("Desk", role="owner")

    def test_invalid_email_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = WorkspaceService(str(Path(temp_dir) / "workspace.sqlite3"))

            with self.assertRaises(ValueError):
                service.create_account("Desk", email="broken-email")

    def test_unknown_account_is_rejected_when_requested_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = WorkspaceService(str(Path(temp_dir) / "workspace.sqlite3"))

            with self.assertRaises(ValueError):
                service.list_profiles("missing-account")


if __name__ == "__main__":
    unittest.main()
