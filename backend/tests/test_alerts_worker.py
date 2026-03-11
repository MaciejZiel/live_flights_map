from __future__ import annotations

import unittest

from backend.services.alerts_worker import AlertSweepService


class _SnapshotServiceStub:
    def __init__(self, payloads: list[dict[str, object]]) -> None:
        self.payloads = list(payloads)

    def get_flights(self, bbox: dict[str, float]) -> dict[str, object]:
        if self.payloads:
            return self.payloads.pop(0)
        return {"flights": [], "count": 0}


class _TrafficIntelligenceStub:
    def enrich_flights(self, flights: list[dict[str, object]]) -> list[dict[str, object]]:
        return flights


class _WorkspaceServiceStub:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state
        self.saved_states: list[dict[str, object]] = []

    def list_accounts(self) -> dict[str, object]:
        return {"accounts": [{"id": "acc-1"}]}

    def list_profiles(self, account_id: str | None = None) -> dict[str, object]:
        return {"profiles": [{"id": "profile-1", "account_id": account_id or "acc-1"}]}

    def get_workspace_state(self, profile_id: str | None = None, account_id: str | None = None) -> dict[str, object]:
        return {"state": self.state}

    def save_workspace_state(self, profile_id: str, state: dict[str, object]) -> dict[str, object]:
        self.state = state
        self.saved_states.append(state)
        return {"state": state}


class AlertSweepServiceTests(unittest.TestCase):
    def test_writes_event_when_callsign_rule_matches_live_traffic(self) -> None:
        workspace_service = _WorkspaceServiceStub(
            {
                "alertRules": [
                    {"id": "rule-1", "type": "callsign", "query": "LOT"},
                ],
                "alertEvents": [],
            }
        )
        service = AlertSweepService(
            snapshot_service=_SnapshotServiceStub(
                [
                    {
                        "count": 1,
                        "flights": [
                            {
                                "icao24": "48af06",
                                "callsign": "LOT123",
                                "registration": "SP-LVG",
                                "on_ground": False,
                            }
                        ],
                    }
                ]
            ),
            traffic_intelligence_service=_TrafficIntelligenceStub(),
            workspace_service=workspace_service,
            sectors=({"key": "local", "bbox": {"lamin": 50.0, "lamax": 54.0, "lomin": 18.0, "lomax": 22.0}},),
        )

        payload = service.run_once()

        self.assertEqual(payload["profiles_updated"], 1)
        self.assertEqual(len(workspace_service.saved_states), 1)
        self.assertEqual(len(workspace_service.state["alertEvents"]), 1)
        self.assertIn("Callsign LOT matched LOT123", workspace_service.state["alertEvents"][0]["message"])

    def test_detects_takeoff_transition_between_sweeps(self) -> None:
        workspace_service = _WorkspaceServiceStub(
            {
                "alertRules": [
                    {"id": "rule-2", "type": "takeoff", "query": "Visible traffic"},
                ],
                "alertEvents": [],
            }
        )
        service = AlertSweepService(
            snapshot_service=_SnapshotServiceStub(
                [
                    {
                        "count": 1,
                        "flights": [
                            {
                                "icao24": "48af06",
                                "callsign": "LOT123",
                                "registration": "SP-LVG",
                                "on_ground": True,
                            }
                        ],
                    },
                    {
                        "count": 1,
                        "flights": [
                            {
                                "icao24": "48af06",
                                "callsign": "LOT123",
                                "registration": "SP-LVG",
                                "on_ground": False,
                            }
                        ],
                    },
                ]
            ),
            traffic_intelligence_service=_TrafficIntelligenceStub(),
            workspace_service=workspace_service,
            sectors=({"key": "local", "bbox": {"lamin": 50.0, "lamax": 54.0, "lomin": 18.0, "lomax": 22.0}},),
        )

        first_payload = service.run_once()
        second_payload = service.run_once()

        self.assertEqual(first_payload["profiles_updated"], 0)
        self.assertEqual(first_payload["profiles_persisted"], 1)
        self.assertEqual(second_payload["profiles_updated"], 1)
        self.assertEqual(len(workspace_service.state["alertEvents"]), 1)
        self.assertIn(
            "Takeoff Visible traffic matched LOT123",
            workspace_service.state["alertEvents"][0]["message"],
        )

    def test_restored_worker_uses_persisted_transition_state(self) -> None:
        workspace_service = _WorkspaceServiceStub(
            {
                "alertRules": [
                    {"id": "rule-3", "type": "takeoff", "query": "Visible traffic"},
                ],
                "alertEvents": [],
            }
        )
        first_worker = AlertSweepService(
            snapshot_service=_SnapshotServiceStub(
                [
                    {
                        "count": 1,
                        "flights": [
                            {
                                "icao24": "48af06",
                                "callsign": "LOT123",
                                "registration": "SP-LVG",
                                "on_ground": True,
                            }
                        ],
                    }
                ]
            ),
            traffic_intelligence_service=_TrafficIntelligenceStub(),
            workspace_service=workspace_service,
            sectors=({"key": "local", "bbox": {"lamin": 50.0, "lamax": 54.0, "lomin": 18.0, "lomax": 22.0}},),
        )

        first_payload = first_worker.run_once()

        self.assertEqual(first_payload["profiles_updated"], 0)
        self.assertEqual(first_payload["profiles_persisted"], 1)
        self.assertEqual(
            workspace_service.state["_alertEngineState"]["previousFlightsByIcao24"]["48af06"]["on_ground"],
            True,
        )

        restarted_worker = AlertSweepService(
            snapshot_service=_SnapshotServiceStub(
                [
                    {
                        "count": 1,
                        "flights": [
                            {
                                "icao24": "48af06",
                                "callsign": "LOT123",
                                "registration": "SP-LVG",
                                "on_ground": False,
                            }
                        ],
                    }
                ]
            ),
            traffic_intelligence_service=_TrafficIntelligenceStub(),
            workspace_service=workspace_service,
            sectors=({"key": "local", "bbox": {"lamin": 50.0, "lamax": 54.0, "lomin": 18.0, "lomax": 22.0}},),
        )

        second_payload = restarted_worker.run_once()

        self.assertEqual(second_payload["profiles_updated"], 1)
        self.assertEqual(second_payload["profiles_persisted"], 1)
        self.assertEqual(len(workspace_service.state["alertEvents"]), 1)
        self.assertIn(
            "Takeoff Visible traffic matched LOT123",
            workspace_service.state["alertEvents"][0]["message"],
        )


if __name__ == "__main__":
    unittest.main()
