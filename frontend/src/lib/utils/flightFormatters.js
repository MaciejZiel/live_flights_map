export function formatAltitude(value) {
  if (value === null || value === undefined) {
    return "unknown";
  }

  return `${Math.round(value)} m`;
}

export function formatSpeed(value) {
  if (value === null || value === undefined) {
    return "unknown";
  }

  return `${Math.round(value * 3.6)} km/h`;
}

export function formatHeading(value) {
  if (value === null || value === undefined) {
    return "unknown";
  }

  return `${Math.round(value)}°`;
}

export function formatVerticalRate(value) {
  if (value === null || value === undefined) {
    return "unknown";
  }

  return `${value.toFixed(1)} m/s`;
}

export function formatCoordinates(latitude, longitude) {
  return `${latitude.toFixed(3)}, ${longitude.toFixed(3)}`;
}

export function formatFlightStatus(flight) {
  return flight.on_ground ? "On ground" : "Airborne";
}
