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
        self._match_state_by_profile: dict[str, dict[str, set[str]]] = {}
        self._previous_flights_by_icao24: dict[str, dict[str, object]] = {}

    def run_once(self) -> dict[str, object]:
        flights, warnings = self._fetch_live_flights()
        profiles_scanned = 0
        events_written = 0

        for account in self.workspace_service.list_accounts().get("accounts") or []:
            account_id = account.get("id")
            profiles = self.workspace_service.list_profiles(account_id).get("profiles") or []
            for profile in profiles:
                profile_id = profile.get("id")
                if not profile_id:
                    continue

                profiles_scanned += 1
                state_payload = self.workspace_service.get_workspace_state(profile_id).get("state") or {}
                next_events = self._evaluate_profile_alerts(
                    profile_id=profile_id,
                    alert_rules=state_payload.get("alertRules") or [],
                    existing_events=state_payload.get("alertEvents") or [],
                    flights=flights,
                )
                if not next_events:
                    continue

                state_payload["alertEvents"] = next_events
                self.workspace_service.save_workspace_state(profile_id, state_payload)
                events_written += 1

        self._previous_flights_by_icao24 = {
            str(flight.get("icao24") or "").strip().lower(): flight
            for flight in flights
            if isinstance(flight, dict) and flight.get("icao24")
        }

        return {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "flight_count": len(flights),
            "profiles_scanned": profiles_scanned,
            "profiles_updated": events_written,
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
    ) -> list[dict[str, object]] | None:
        if not alert_rules:
            self._match_state_by_profile[profile_id] = {}
            return None

        previous_rule_state = self._match_state_by_profile.get(profile_id, {})
        next_rule_state: dict[str, set[str]] = {}
        new_events: list[dict[str, object]] = []

        for rule in alert_rules:
            rule_id = str(rule.get("id") or f"{rule.get('type')}:{rule.get('query')}")
            previous_match_ids = previous_rule_state.get(rule_id, set())
            matches = self._find_rule_matches(flights, rule)
            current_match_ids = {
                str(match.get("icao24") or "").strip().lower()
                for match in matches
                if isinstance(match, dict) and match.get("icao24")
            }
            next_rule_state[rule_id] = current_match_ids
            rule_label = self._get_rule_label(rule.get("type"))
            query = self._normalize_text(rule.get("query")) or "Visible traffic"

            if rule.get("type") in {"takeoff", "landing"}:
                for match in matches[:3]:
                    icao24 = str(match.get("icao24") or "").strip().lower()
                    if icao24 in previous_match_ids:
                        continue
                    new_events.append(self._build_event(
                        f"{rule_label} {query} matched {self._flight_label(match)}"
                    ))
                continue

            if matches and not previous_match_ids:
                new_events.append(
                    self._build_event(
                        f"{rule_label} {query} matched {self._flight_label(matches[0])}"
                    )
                )
                continue

            if not matches and previous_match_ids:
                new_events.append(
                    self._build_event(f"{rule_label} {query} is no longer visible")
                )

        self._match_state_by_profile[profile_id] = next_rule_state
        if not new_events:
            return None

        return [*new_events, *existing_events][:30]

    def _find_rule_matches(
        self,
        flights: list[dict[str, object]],
        rule: dict[str, object],
    ) -> list[dict[str, object]]:
        rule_type = rule.get("type")
        if rule_type in {"takeoff", "landing"}:
            return self._find_transition_matches(flights, rule_type)

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
    ) -> list[dict[str, object]]:
        transition_to_ground = rule_type == "landing"
        matches = []

        for flight in flights:
            icao24 = str(flight.get("icao24") or "").strip().lower()
            previous_flight = self._previous_flights_by_icao24.get(icao24)
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
    def _build_event(message: str) -> dict[str, object]:
        return {
            "id": str(uuid4()),
            "message": message,
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
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
