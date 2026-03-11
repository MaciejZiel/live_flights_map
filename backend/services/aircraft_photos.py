from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .provider_base import FlightProviderError


class AircraftPhotoService:
    def __init__(self, providers: Iterable[object]) -> None:
        self.providers = list(providers)

    def fetch_photo(
        self,
        registration: str | None,
        *,
        type_code: str | None = None,
        operator_code: str | None = None,
        airline_code: str | None = None,
        airline_name: str | None = None,
    ) -> dict[str, Any] | None:
        warnings: list[str] = []
        exact_registration_variants = self._build_registration_variants(registration)
        contextual_exact_queries = self._build_contextual_exact_queries(
            exact_registration_variants,
            type_code,
        )
        representative_queries = self._build_representative_queries(
            type_code=type_code,
            operator_code=operator_code,
            airline_code=airline_code,
            airline_name=airline_name,
        )

        for provider in self.providers:
            for candidate_registration in exact_registration_variants:
                try:
                    photo = provider.fetch_photo(candidate_registration)
                except FlightProviderError as exc:
                    warnings.append(str(exc))
                    break

                if photo:
                    photo.setdefault("match_type", "registration")
                    return photo

        for provider in self.providers:
            fetch_photo_query = getattr(provider, "fetch_photo_query", None)
            if not callable(fetch_photo_query):
                continue

            for query in contextual_exact_queries:
                try:
                    photo = fetch_photo_query(
                        query,
                        registration=registration,
                        type_code=type_code,
                        operator_code=operator_code,
                        airline_code=airline_code,
                        airline_name=airline_name,
                    )
                except FlightProviderError as exc:
                    warnings.append(str(exc))
                    break

                if photo:
                    photo.setdefault("match_type", "registration")
                    return photo

        for provider in self.providers:
            fetch_photo_query = getattr(provider, "fetch_photo_query", None)
            if not callable(fetch_photo_query):
                continue

            for query in representative_queries:
                try:
                    photo = fetch_photo_query(
                        query,
                        registration=registration,
                        type_code=type_code,
                        operator_code=operator_code,
                        airline_code=airline_code,
                        airline_name=airline_name,
                    )
                except FlightProviderError as exc:
                    warnings.append(str(exc))
                    break

                if photo:
                    photo["match_type"] = "representative"
                    return photo

        if warnings:
            raise FlightProviderError(" ".join(warnings))

        return None

    @staticmethod
    def _build_registration_variants(registration: str | None) -> list[str]:
        normalized_registration = AircraftPhotoService._normalize_text(registration, uppercase=True)
        if not normalized_registration:
            return []

        compact_registration = "".join(
            character for character in normalized_registration if character.isalnum()
        )
        return list(
            dict.fromkeys(
                value
                for value in (
                    normalized_registration,
                    compact_registration,
                )
                if value
            )
        )

    @staticmethod
    def _build_contextual_exact_queries(
        registration_variants: list[str],
        type_code: str | None,
    ) -> list[str]:
        normalized_type_code = AircraftPhotoService._normalize_text(type_code, uppercase=True)
        if not normalized_type_code:
            return []

        return list(
            dict.fromkeys(
                f"{registration_variant} {normalized_type_code}"
                for registration_variant in registration_variants
                if registration_variant
            )
        )

    @staticmethod
    def _build_representative_queries(
        *,
        type_code: str | None,
        operator_code: str | None,
        airline_code: str | None,
        airline_name: str | None,
    ) -> list[str]:
        normalized_type_code = AircraftPhotoService._normalize_text(type_code, uppercase=True)
        if not normalized_type_code:
            return []

        carriers = [
            AircraftPhotoService._normalize_text(airline_name),
            AircraftPhotoService._normalize_text(airline_code, uppercase=True),
            AircraftPhotoService._normalize_text(operator_code, uppercase=True),
        ]
        carriers = [carrier for carrier in carriers if carrier]

        queries = []
        for carrier in carriers:
            queries.extend(
                [
                    f"{carrier} {normalized_type_code}",
                    f"{carrier} {normalized_type_code} aircraft",
                    f"{carrier} {normalized_type_code} airplane",
                ]
            )

        return list(dict.fromkeys(queries))

    @staticmethod
    def _normalize_text(value: object, uppercase: bool = False) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        return cleaned.upper() if uppercase else cleaned
