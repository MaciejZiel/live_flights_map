export function getReplayHistoryRequestLimit(windowMinutes = 90) {
  const normalizedWindow = Math.max(Number(windowMinutes) || 0, 30);
  return Math.max(120, Math.min(720, Math.round(normalizedWindow * 2)));
}

export function findClosestReplaySnapshotIndex(snapshots = [], targetValue = null) {
  if (!snapshots.length || !targetValue) {
    return -1;
  }

  const targetTimestamp =
    typeof targetValue === "number" ? targetValue : new Date(targetValue).getTime();
  if (!Number.isFinite(targetTimestamp)) {
    return -1;
  }

  let bestIndex = -1;
  let smallestDistance = Number.POSITIVE_INFINITY;

  for (let index = 0; index < snapshots.length; index += 1) {
    const snapshot = snapshots[index];
    const snapshotTimestamp = new Date(snapshot?.fetchedAt ?? snapshot?.fetched_at ?? "").getTime();
    if (!Number.isFinite(snapshotTimestamp)) {
      continue;
    }

    const distance = Math.abs(snapshotTimestamp - targetTimestamp);
    if (distance < smallestDistance) {
      smallestDistance = distance;
      bestIndex = index;
    }
  }

  return bestIndex;
}

export function buildReplayCompareSummary(baseSnapshot = null, activeSnapshot = null) {
  if (!baseSnapshot || !activeSnapshot) {
    return null;
  }

  const baseFlights = Array.isArray(baseSnapshot.flights) ? baseSnapshot.flights : [];
  const activeFlights = Array.isArray(activeSnapshot.flights) ? activeSnapshot.flights : [];
  const baseIds = new Set(
    baseFlights
      .map((flight) => String(flight?.icao24 ?? "").trim().toLowerCase())
      .filter(Boolean)
  );
  const activeIds = new Set(
    activeFlights
      .map((flight) => String(flight?.icao24 ?? "").trim().toLowerCase())
      .filter(Boolean)
  );

  let persisted = 0;
  let arrivals = 0;
  let departures = 0;

  for (const icao24 of activeIds) {
    if (baseIds.has(icao24)) {
      persisted += 1;
    } else {
      arrivals += 1;
    }
  }

  for (const icao24 of baseIds) {
    if (!activeIds.has(icao24)) {
      departures += 1;
    }
  }

  return {
    baseLabel: baseSnapshot.fetchedAt ?? baseSnapshot.fetched_at ?? null,
    activeLabel: activeSnapshot.fetchedAt ?? activeSnapshot.fetched_at ?? null,
    baseCount: baseSnapshot.count ?? baseFlights.length,
    activeCount: activeSnapshot.count ?? activeFlights.length,
    persisted,
    arrivals,
    departures,
    trafficDelta:
      (activeSnapshot.count ?? activeFlights.length) - (baseSnapshot.count ?? baseFlights.length),
  };
}
