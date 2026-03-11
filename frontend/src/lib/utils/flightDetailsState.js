import { deriveOperatorCode } from "./flightMatching.js";

export function buildFlightDetailsKey(flight) {
  if (!flight?.icao24) {
    return null;
  }

  return [
    flight.icao24,
    (flight.callsign ?? "").trim().toUpperCase(),
    (flight.registration ?? "").trim().toUpperCase(),
  ].join(":");
}

export function buildFlightDetailsFallback(flight, warning = null) {
  if (!flight) {
    return null;
  }

  const operatorCode = deriveOperatorCode(flight);

  return {
    aircraft: {
      icao24: flight.icao24,
      callsign: flight.callsign ?? null,
      registration: flight.registration ?? null,
      type_code: flight.type_code ?? null,
      origin_country: flight.origin_country ?? null,
      operator_code: operatorCode || null,
    },
    route: null,
    photo: null,
    meta: {
      fetched_at: null,
      warning,
      detail_quality: {
        band: "live_only",
        score: 0,
        summary: "Live track only. Route and photo are still missing.",
        route_state: "pending",
        route_confidence: "pending",
        route_label: "Live track only",
        photo_state: "missing",
        photo_match: "missing",
        photo_label: "No aircraft photo",
        photo_source: null,
        identity_score: 0,
      },
    },
  };
}

export function mergeFlightDetails(flight, details) {
  if (!flight) {
    return details;
  }

  const fallbackDetails = buildFlightDetailsFallback(flight, details?.meta?.warning ?? null);
  const operatorCode = details?.aircraft?.operator_code || fallbackDetails?.aircraft?.operator_code || null;

  return {
    ...fallbackDetails,
    ...details,
    aircraft: {
      ...fallbackDetails?.aircraft,
      ...details?.aircraft,
      operator_code: operatorCode,
    },
    meta: {
      ...fallbackDetails?.meta,
      ...details?.meta,
    },
  };
}

export function shouldRefreshCachedFlightDetails(details) {
  if (!details) {
    return true;
  }

  return !details?.photo?.thumbnail_url;
}
