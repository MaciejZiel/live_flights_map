const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function buildApiUrl(pathname, bbox) {
  const url = new URL(`${API_BASE_URL}${pathname}`, window.location.origin);

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

export async function fetchFlights(bbox) {
  const response = await fetch(buildFlightsUrl(bbox));
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error ?? "Failed to load flight positions.");
  }

  return payload;
}

export async function fetchFlightDetails(flight) {
  const response = await fetch(buildFlightDetailsUrl(flight));
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.error ?? "Failed to load aircraft details.");
  }

  return payload;
}
