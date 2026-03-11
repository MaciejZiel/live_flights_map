from __future__ import annotations

import math
from datetime import datetime, timezone
from uuid import uuid4

from .provider_base import FlightProviderError
from .snapshot_collector import SnapshotCollectorService


class AlertSweepService:
    DEFAULT_SECTORS = SnapshotCollectorService.DEFAULT_SECTORS

    def __init__(
        self,
        snapshot_service,
        traffic_intelligence_service,
        workspace_service,
        sectors: tuple[dict[str, object], ...] | None = None,
    ) -> None:
        self.snapshot_service = snapshot_service
        self.traffic_intelligence_service = traffic_intelligence_service
        self.workspace_service = workspace_service
        self.sectors = sectors or self.DEFAULT_SECTORS

    def run_once(self) -> dict[str, object]:
        flights, warnings = self._fetch_live_flights()
        profiles_scanned = 0
        events_written = 0
        states_persisted = 0

        for account in self.workspace_service.list_accounts().get("accounts") or []:
            account_id = account.get("id")
            profiles = self.workspace_service.list_profiles(account_id).get("profiles") or []
            for profile in profiles:
                profile_id = profile.get("id")
                if not profile_id:
                    continue

                profiles_scanned += 1
                state_payload = self.workspace_service.get_workspace_state(profile_id).get("state") or {}
                evaluation = self._evaluate_profile_alerts(
                    profile_id=profile_id,
                    alert_rules=state_payload.get("alertRules") or [],
                    existing_events=state_payload.get("alertEvents") or [],
                    flights=flights,
                    engine_state=state_payload.get("_alertEngineState"),
                )
                if not evaluation["state_changed"]:
                    continue

                state_payload["alertEvents"] = evaluation["alertEvents"]
                state_payload["_alertEngineState"] = evaluation["engine_state"]
                self.workspace_service.save_workspace_state(profile_id, state_payload)
                states_persisted += 1
                if evaluation["events_changed"]:
                    events_written += 1

        return {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "flight_count": len(flights),
            "profiles_scanned": profiles_scanned,
            "profiles_updated": events_written,
            "profiles_persisted": states_persisted,
            "warnings": warnings,
        }

    def _fetch_live_flights(self) -> tuple[list[dict[str, object]], list[str]]:
        merged: dict[str, dict[str, object]] = {}
        warnings: list[str] = []

        for sector in self.sectors:
            try:
                payload = self.snapshot_service.get_flights(sector["bbox"])
            except FlightProviderError as exc:
                warnings.append(f"{sector['key']}: {exc}")
                continue

            flights = [flight for flight in payload.get("flights") or [] if isinstance(flight, dict)]
            try:
                flights = self.traffic_intelligence_service.enrich_flights(flights)
            except Exception:
                pass

            for flight in flights:
                icao24 = str(flight.get("icao24") or "").strip().lower()
                if not icao24:
                    continue

                existing = merged.get(icao24)
                if existing is None or self._is_better_candidate(flight, existing):
                    merged[icao24] = {
                        **flight,
                        "icao24": icao24,
                    }

        return list(merged.values()), warnings

    def _evaluate_profile_alerts(
        self,
        *,
        profile_id: str,
        alert_rules: list[dict[str, object]],
        existing_events: list[dict[str, object]],
        flights: list[dict[str, object]],
        engine_state: object,
    ) -> dict[str, object]:
        normalized_engine_state = self._normalize_engine_state(engine_state)
        previous_rule_state = self._deserialize_rule_matches(
            normalized_engine_state.get("ruleMatches")
        )
        previous_flights_by_icao24 = self._normalize_previous_flights(
            normalized_engine_state.get("previousFlightsByIcao24")
        )

        if not alert_rules:
            cleared_engine_state = self._empty_engine_state()
            return {
                "alertEvents": existing_events,
                "engine_state": cleared_engine_state,
                "events_changed": False,
                "state_changed": normalized_engine_state != cleared_engine_state,
            }

        next_rule_state: dict[str, set[str]] = {}
        new_events: list[dict[str, object]] = []
        needs_transition_state = False

        for rule in alert_rules:
            rule_id = str(rule.get("id") or f"{rule.get('type')}:{rule.get('query')}")
            previous_match_ids = previous_rule_state.get(rule_id, set())
            rule_type = str(rule.get("type") or "")
            if rule_type in {"takeoff", "landing"}:
                needs_transition_state = True
            matches = self._find_rule_matches(flights, rule, previous_flights_by_icao24)
            current_match_ids = {
                str(match.get("icao24") or "").strip().lower()
                for match in matches
                if isinstance(match, dict) and match.get("icao24")
            }
            next_rule_state[rule_id] = current_match_ids
            rule_label = self._get_rule_label(rule_type)
            query = self._normalize_text(rule.get("query")) or "Visible traffic"

            if rule_type in {"takeoff", "landing"}:
                for match in matches[:3]:
                    icao24 = str(match.get("icao24") or "").strip().lower()
                    if icao24 in previous_match_ids:
                        continue
                    new_events.append(
                        self._build_event(
                            f"{rule_label} {query} matched {self._flight_label(match)}",
                            severity=self._get_rule_severity(rule),
                            fingerprint=f"{rule_id}:{rule_type}:{icao24}",
                        )
                    )
                continue

            if matches and not previous_match_ids:
                new_events.append(
                    self._build_event(
                        f"{rule_label} {query} matched {self._flight_label(matches[0])}",
                        severity=self._get_rule_severity(rule),
                        fingerprint=f"{rule_id}:enter:{self._normalize_text(matches[0].get('icao24')).lower()}",
                    )
                )
                continue

            if not matches and previous_match_ids:
                new_events.append(
                    self._build_event(
                        f"{rule_label} {query} is no longer visible",
                        severity=self._get_rule_severity(rule),
                        fingerprint=f"{rule_id}:exit",
                    )
                )

        next_engine_state = {
            "ruleMatches": self._serialize_rule_matches(next_rule_state),
            "previousFlightsByIcao24": self._build_previous_flight_state(flights)
            if needs_transition_state
            else {},
        }
        next_events = [*new_events, *existing_events][:30] if new_events else existing_events

        return {
            "alertEvents": next_events,
            "engine_state": next_engine_state,
            "events_changed": bool(new_events),
            "state_changed": bool(new_events)
            or normalized_engine_state != next_engine_state,
        }

    def _find_rule_matches(
        self,
        flights: list[dict[str, object]],
        rule: dict[str, object],
        previous_flights_by_icao24: dict[str, dict[str, object]],
    ) -> list[dict[str, object]]:
        rule_type = rule.get("type")
        if rule_type in {"takeoff", "landing"}:
            return self._find_transition_matches(
                flights,
                rule_type,
                previous_flights_by_icao24,
            )

        return [
            flight
            for flight in flights
            if self._matches_rule(flight, rule)
        ]

    def _matches_rule(self, flight: dict[str, object], rule: dict[str, object]) -> bool:
        normalized_query = self._normalize_text(rule.get("query")).lower()
        rule_type = rule.get("type")
        threshold = self._normalize_number((rule.get("payload") or {}).get("threshold", rule.get("query")))

        if rule_type == "callsign":
            return normalized_query in self._normalize_text(flight.get("callsign")).lower()

        if rule_type == "airline":
            return normalized_query in self._derive_operator_code(flight).lower()

        if rule_type == "country":
            return normalized_query in self._normalize_text(flight.get("origin_country")).lower()

        if rule_type == "registration":
            return normalized_query in self._normalize_text(flight.get("registration")).lower()

        if rule_type == "type_code":
            return normalized_query in self._normalize_text(flight.get("type_code")).lower()

        if rule_type == "route":
            normalized_route_query = self._normalize_search_blob(rule.get("query"))
            for field_name in (
                "route_label",
                "route_verbose",
                "airport_codes",
                "iata_codes",
                "origin",
                "destination",
                "origin_iata",
                "origin_icao",
                "destination_iata",
                "destination_icao",
            ):
                field_value = flight.get(field_name)
                if not field_value:
                    continue
                raw_value = self._normalize_text(field_value).lower()
                if normalized_query in raw_value or normalized_route_query in self._normalize_search_blob(field_value):
                    return True
            return False

        if rule_type == "airport":
            payload = rule.get("payload") or {}
            latitude = self._normalize_number(payload.get("latitude"))
            longitude = self._normalize_number(payload.get("longitude"))
            radius_km = self._normalize_number(payload.get("radiusKm", 48))
            if latitude is None or longitude is None or radius_km is None:
                return False
            return self._calculate_distance_km(
                self._normalize_number(flight.get("latitude")),
                self._normalize_number(flight.get("longitude")),
                latitude,
                longitude,
            ) <= radius_km

        if rule_type == "area":
            return self._is_flight_inside_bbox(flight, (rule.get("payload") or {}).get("bbox"))

        if rule_type == "altitude_min":
            altitude = self._normalize_number(flight.get("altitude"))
            return threshold is not None and altitude is not None and altitude >= threshold

        if rule_type == "speed_min":
            speed = self._normalize_number(flight.get("velocity"))
            return threshold is not None and speed is not None and speed * 3.6 >= threshold

        return normalized_query in self._normalize_text(flight.get("icao24")).lower()

    def _find_transition_matches(
        self,
        flights: list[dict[str, object]],
        rule_type: object,
        previous_flights_by_icao24: dict[str, dict[str, object]],
    ) -> list[dict[str, object]]:
        transition_to_ground = rule_type == "landing"
        matches = []

        for flight in flights:
            icao24 = str(flight.get("icao24") or "").strip().lower()
            previous_flight = previous_flights_by_icao24.get(icao24)
            if not previous_flight:
                continue

            previous_on_ground = bool(previous_flight.get("on_ground"))
            current_on_ground = bool(flight.get("on_ground"))

            if transition_to_ground and not previous_on_ground and current_on_ground:
                matches.append(flight)
                continue

            if not transition_to_ground and previous_on_ground and not current_on_ground:
                matches.append(flight)

        return matches

    @classmethod
    def _empty_engine_state(cls) -> dict[str, object]:
        return {
            "ruleMatches": {},
            "previousFlightsByIcao24": {},
        }

    @classmethod
    def _normalize_engine_state(cls, engine_state: object) -> dict[str, object]:
        normalized = cls._empty_engine_state()
        if not isinstance(engine_state, dict):
            return normalized

        normalized["ruleMatches"] = cls._serialize_rule_matches(
            cls._deserialize_rule_matches(engine_state.get("ruleMatches"))
        )
        normalized["previousFlightsByIcao24"] = cls._normalize_previous_flights(
            engine_state.get("previousFlightsByIcao24")
        )
        return normalized

    @staticmethod
    def _deserialize_rule_matches(raw_matches: object) -> dict[str, set[str]]:
        if not isinstance(raw_matches, dict):
            return {}

        normalized: dict[str, set[str]] = {}
        for rule_id, match_ids in raw_matches.items():
            normalized_rule_id = str(rule_id or "").strip()
            if not normalized_rule_id or not isinstance(match_ids, (list, tuple, set)):
                continue
            normalized_match_ids = {
                str(match_id or "").strip().lower()
                for match_id in match_ids
                if str(match_id or "").strip()
            }
            normalized[normalized_rule_id] = normalized_match_ids
        return normalized

    @staticmethod
    def _serialize_rule_matches(rule_matches: dict[str, set[str]]) -> dict[str, list[str]]:
        serialized: dict[str, list[str]] = {}
        for rule_id, match_ids in rule_matches.items():
            normalized_rule_id = str(rule_id or "").strip()
            if not normalized_rule_id:
                continue
            serialized[normalized_rule_id] = sorted(
                {
                    str(match_id or "").strip().lower()
                    for match_id in match_ids
                    if str(match_id or "").strip()
                }
            )
        return serialized

    @classmethod
    def _normalize_previous_flights(cls, raw_previous_flights: object) -> dict[str, dict[str, object]]:
        if not isinstance(raw_previous_flights, dict):
            return {}

        normalized: dict[str, dict[str, object]] = {}
        for icao24, flight in raw_previous_flights.items():
            if not isinstance(flight, dict):
                continue
            normalized_icao24 = str(icao24 or flight.get("icao24") or "").strip().lower()
            if not normalized_icao24:
                continue
            normalized[normalized_icao24] = cls._compact_flight_state(
                {
                    **flight,
                    "icao24": normalized_icao24,
                }
            )
        return normalized

    @classmethod
    def _build_previous_flight_state(cls, flights: list[dict[str, object]]) -> dict[str, dict[str, object]]:
        return {
            compacted["icao24"]: compacted
            for compacted in (
                cls._compact_flight_state(flight)
                for flight in flights
                if isinstance(flight, dict)
            )
            if compacted.get("icao24")
        }

    @staticmethod
    def _compact_flight_state(flight: dict[str, object]) -> dict[str, object]:
        return {
            "icao24": str(flight.get("icao24") or "").strip().lower(),
            "callsign": AlertSweepService._normalize_text(flight.get("callsign")),
            "registration": AlertSweepService._normalize_text(flight.get("registration")),
            "on_ground": bool(flight.get("on_ground")),
        }

    @staticmethod
    def _is_better_candidate(candidate: dict[str, object], existing: dict[str, object]) -> bool:
        candidate_last_contact = candidate.get("last_contact")
        existing_last_contact = existing.get("last_contact")
        if isinstance(candidate_last_contact, int) and isinstance(existing_last_contact, int):
            if candidate_last_contact != existing_last_contact:
                return candidate_last_contact > existing_last_contact
        if bool(candidate.get("on_ground")) != bool(existing.get("on_ground")):
            return not bool(candidate.get("on_ground"))
        return float(candidate.get("velocity") or 0) > float(existing.get("velocity") or 0)

    @staticmethod
    def _build_event(
        message: str,
        *,
        severity: str = "info",
        fingerprint: str | None = None,
    ) -> dict[str, object]:
        return {
            "id": str(uuid4()),
            "message": message,
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "severity": severity,
            "fingerprint": fingerprint,
            "delivery": {},
        }

    @staticmethod
    def _flight_label(flight: dict[str, object]) -> str:
        return (
            AlertSweepService._normalize_text(flight.get("callsign"))
            or AlertSweepService._normalize_text(flight.get("registration"))
            or AlertSweepService._normalize_text(flight.get("icao24"))
            or "unknown"
        )

    @staticmethod
    def _get_rule_label(rule_type: object) -> str:
        return {
            "callsign": "Callsign",
            "icao24": "ICAO24",
            "airline": "Airline",
            "country": "Country",
            "registration": "Registration",
            "type_code": "Type",
            "route": "Route",
            "airport": "Airport",
            "area": "Area",
            "altitude_min": "Altitude",
            "speed_min": "Speed",
            "takeoff": "Takeoff",
            "landing": "Landing",
        }.get(str(rule_type or ""), "Rule")

    @staticmethod
    def _get_rule_severity(rule: dict[str, object]) -> str:
        severity = str(rule.get("severity") or "").strip().lower()
        if severity in {"info", "important", "critical"}:
            return severity
        if str(rule.get("type") or "") in {"takeoff", "landing"}:
            return "critical"
        if str(rule.get("type") or "") in {"callsign", "icao24", "registration", "route"}:
            return "important"
        return "info"

    @staticmethod
    def _normalize_text(value: object) -> str:
        return str(value or "").strip()

    @staticmethod
    def _normalize_search_blob(value: object) -> str:
        return "".join(
            character
            for character in AlertSweepService._normalize_text(value).lower()
            if character.isalnum()
        )

    @staticmethod
    def _normalize_number(value: object) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @staticmethod
    def _derive_operator_code(flight: dict[str, object]) -> str:
        callsign = AlertSweepService._normalize_text(flight.get("callsign")).upper()
        if len(callsign) < 3 or not callsign[:3].isalpha():
            return ""
        return callsign[:3]

    @staticmethod
    def _calculate_distance_km(
        latitude: float | None,
        longitude: float | None,
        center_latitude: float,
        center_longitude: float,
    ) -> float:
        if latitude is None or longitude is None:
            return float("inf")

        earth_radius_km = 6371.0
        start_latitude = math.radians(latitude)
        end_latitude = math.radians(center_latitude)
        delta_latitude = math.radians(center_latitude - latitude)
        delta_longitude = math.radians(center_longitude - longitude)
        haversine = (
            math.sin(delta_latitude / 2) ** 2
            + math.cos(start_latitude)
            * math.cos(end_latitude)
            * math.sin(delta_longitude / 2) ** 2
        )
        return 2 * earth_radius_km * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))

    @staticmethod
    def _is_flight_inside_bbox(flight: dict[str, object], bbox: object) -> bool:
        if not isinstance(bbox, dict):
            return False

        latitude = AlertSweepService._normalize_number(flight.get("latitude"))
        longitude = AlertSweepService._normalize_number(flight.get("longitude"))
        lamin = AlertSweepService._normalize_number(bbox.get("lamin"))
        lamax = AlertSweepService._normalize_number(bbox.get("lamax"))
        lomin = AlertSweepService._normalize_number(bbox.get("lomin"))
        lomax = AlertSweepService._normalize_number(bbox.get("lomax"))
        if None in {latitude, longitude, lamin, lamax, lomin, lomax}:
            return False

        return bool(lamin <= latitude <= lamax and lomin <= longitude <= lomax)
