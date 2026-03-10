const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function createApiUrl(pathname) {
  return new URL(`${API_BASE_URL}${pathname}`, window.location.origin);
}

function buildApiUrl(pathname, bbox) {
  const url = createApiUrl(pathname);

  if (bbox) {
    url.searchParams.set("lamin", bbox.lamin.toFixed(4));
    url.searchParams.set("lamax", bbox.lamax.toFixed(4));
    url.searchParams.set("lomin", bbox.lomin.toFixed(4));
    url.searchParams.set("lomax", bbox.lomax.toFixed(4));
  }

  if (!API_BASE_URL) {
    return `${url.pathname}${url.search}`;
  }

  return url.toString();
}

function buildFlightsUrl(bbox) {
  return buildApiUrl("/api/flights", bbox);
}

function buildFlightDetailsUrl(flight) {
  const pathname = `/api/flights/${encodeURIComponent(flight.icao24)}/details`;
  const url = new URL(`${API_BASE_URL}${pathname}`, window.location.origin);

  if (flight.callsign) {
    url.searchParams.set("callsign", flight.callsign.trim().toUpperCase());
  }

  if (flight.registration) {
    url.searchParams.set("registration", flight.registration.trim().toUpperCase());
  }

  if (flight.type_code) {
    url.searchParams.set("type_code", flight.type_code.trim().toUpperCase());
  }

  if (flight.origin_country) {
    url.searchParams.set("origin_country", flight.origin_country);
  }

  if (Number.isFinite(flight.latitude)) {
    url.searchParams.set("lat", Number(flight.latitude).toFixed(5));
  }

  if (Number.isFinite(flight.longitude)) {
    url.searchParams.set("lon", Number(flight.longitude).toFixed(5));
  }

  if (!API_BASE_URL) {
    return `${url.pathname}${url.search}`;
  }

  return url.toString();
}

export function buildFlightsStreamUrl(bbox) {
  return buildApiUrl("/api/flights/stream", bbox);
}

async function parseApiResponse(response, fallbackMessage) {
  const rawBody = await response.text();
  let payload = null;

  if (rawBody) {
    try {
      payload = JSON.parse(rawBody);
    } catch {
      if (!response.ok) {
        throw new Error(fallbackMessage);
      }
      throw new Error("Received an invalid API response.");
    }
  }

  if (!response.ok) {
    throw new Error(payload?.error ?? fallbackMessage);
  }

  if (!payload || typeof payload !== "object") {
    throw new Error("Received an empty API response.");
  }

  return payload;
}

export async function fetchFlights(bbox) {
  const response = await fetch(buildFlightsUrl(bbox));
  return parseApiResponse(response, "Failed to load flight positions.");
}

export async function fetchFlightDetails(flight) {
  const response = await fetch(buildFlightDetailsUrl(flight));
  return parseApiResponse(response, "Failed to load aircraft details.");
}

export async function fetchFlightTrail(icao24, options = {}) {
  const url = createApiUrl(`/api/flights/${encodeURIComponent(icao24)}/trail`);

  if (options.hours) {
    url.searchParams.set("hours", String(options.hours));
  }
  if (options.limit) {
    url.searchParams.set("limit", String(options.limit));
  }

  const response = await fetch(API_BASE_URL ? url.toString() : `${url.pathname}${url.search}`);
  return parseApiResponse(response, "Failed to load the archived flight trail.");
}

export async function fetchReplayHistory(bbox, options = {}) {
  const url = createApiUrl("/api/history/replay");

  if (bbox) {
    url.searchParams.set("lamin", bbox.lamin.toFixed(4));
    url.searchParams.set("lamax", bbox.lamax.toFixed(4));
    url.searchParams.set("lomin", bbox.lomin.toFixed(4));
    url.searchParams.set("lomax", bbox.lomax.toFixed(4));
  }
  if (options.minutes) {
    url.searchParams.set("minutes", String(options.minutes));
  }
  if (options.limit) {
    url.searchParams.set("limit", String(options.limit));
  }

  const response = await fetch(API_BASE_URL ? url.toString() : `${url.pathname}${url.search}`);
  return parseApiResponse(response, "Failed to load replay history.");
}

export async function searchFlights(query, options = {}) {
  const url = createApiUrl("/api/search");
  url.searchParams.set("q", query);
  if (options.limit) {
    url.searchParams.set("limit", String(options.limit));
  }

  const response = await fetch(API_BASE_URL ? url.toString() : `${url.pathname}${url.search}`);
  return parseApiResponse(response, "Failed to search archived flights.");
}
