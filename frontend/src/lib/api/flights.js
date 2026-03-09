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
