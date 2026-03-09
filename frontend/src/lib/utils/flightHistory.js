const TRAIL_RETENTION_MS = 5 * 60 * 1000;

export function updateFlightHistory(history, flights, fetchedAt) {
  const nextHistory = new Map(history);
  const snapshotTimestamp = fetchedAt ? new Date(fetchedAt).getTime() : Date.now();
  const minTimestamp = snapshotTimestamp - TRAIL_RETENTION_MS;

  for (const flight of flights) {
    const currentHistory = nextHistory.get(flight.icao24) ?? [];
    const nextPoint = {
      latitude: flight.latitude,
      longitude: flight.longitude,
      altitude: flight.altitude,
      velocity: flight.velocity,
      vertical_rate: flight.vertical_rate,
      timestamp: snapshotTimestamp,
    };

    const lastPoint = currentHistory[currentHistory.length - 1];
    const deduplicatedHistory =
      lastPoint &&
      lastPoint.latitude === nextPoint.latitude &&
      lastPoint.longitude === nextPoint.longitude
        ? currentHistory
        : [...currentHistory, nextPoint];

    nextHistory.set(
      flight.icao24,
      deduplicatedHistory.filter((point) => point.timestamp >= minTimestamp)
    );
  }

  for (const [icao24, points] of nextHistory.entries()) {
    const trimmed = points.filter((point) => point.timestamp >= minTimestamp);
    if (trimmed.length === 0) {
      nextHistory.delete(icao24);
      continue;
    }

    nextHistory.set(icao24, trimmed);
  }

  return nextHistory;
}

export function getTrailPoints(history, icao24) {
  if (!icao24) {
    return [];
  }

  return history.get(icao24) ?? [];
}
