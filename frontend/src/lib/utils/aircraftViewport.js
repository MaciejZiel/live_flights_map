function normalizeLongitude(longitude) {
  return ((longitude + 180) % 360 + 360) % 360;
}

function isLongitudeInside(longitude, west, east) {
  const span = east - west;
  if (span >= 360) {
    return true;
  }

  const offset = (normalizeLongitude(longitude) - normalizeLongitude(west) + 360) % 360;
  return offset <= span;
}

export function filterFlightsForMapViewport(flights, bbox) {
  if (!bbox) {
    return flights ?? [];
  }

  return (flights ?? []).filter((flight) =>
    flight?.icao24 &&
    Number.isFinite(flight.latitude) &&
    Number.isFinite(flight.longitude) &&
    flight.latitude >= bbox.lamin &&
    flight.latitude <= bbox.lamax &&
    isLongitudeInside(flight.longitude, bbox.lomin, bbox.lomax)
  );
}
