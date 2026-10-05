export function getFlightPositionAgeSeconds(flight, now = Date.now()) {
  const lastContact = Number(flight?.last_contact);
  if (!Number.isFinite(lastContact) || lastContact <= 0) {
    return null;
  }

  const lastContactMs = lastContact > 1_000_000_000_000 ? lastContact : lastContact * 1000;
  return Math.max(0, (now - lastContactMs) / 1000);
}

export function getFlightPositionAgeBand(ageSeconds) {
  if (!Number.isFinite(ageSeconds)) {
    return "unknown";
  }
  if (ageSeconds < 30) {
    return "fresh";
  }
  if (ageSeconds < 120) {
    return "recent";
  }
  if (ageSeconds < 300) {
    return "delayed";
  }
  if (ageSeconds < 900) {
    return "old";
  }
  return "very-old";
}

export function getFlightPositionOpacity(ageSeconds) {
  const band = getFlightPositionAgeBand(ageSeconds);
  return {
    fresh: 1,
    recent: 0.72,
    delayed: 0.46,
    old: 0.24,
    "very-old": 0.12,
    unknown: 1,
  }[band];
}

export function formatFlightPositionAge(ageSeconds, historical = false) {
  if (historical) {
    return "historical position";
  }
  if (!Number.isFinite(ageSeconds)) {
    return "position age unknown";
  }
  if (ageSeconds < 60) {
    return `seen ${Math.round(ageSeconds)}s ago`;
  }
  if (ageSeconds < 3600) {
    return `seen ${Math.floor(ageSeconds / 60)}m ago`;
  }
  return `seen ${Math.floor(ageSeconds / 3600)}h ago`;
}
