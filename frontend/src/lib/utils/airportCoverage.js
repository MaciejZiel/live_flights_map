const AIRPORT_COVERAGE_LEVELS = [
  { maxZoom: 5, cellDegrees: 100, limit: 300 },
  { maxZoom: 7, cellDegrees: 20, limit: 600 },
  { maxZoom: 9, cellDegrees: 5, limit: 1000 },
  { maxZoom: Infinity, cellDegrees: 2, limit: 1500 },
];

export function buildAirportCoverageRequest(viewBbox, zoom) {
  if (!viewBbox || !Number.isFinite(zoom)) {
    return null;
  }

  const level = AIRPORT_COVERAGE_LEVELS.find((candidate) => zoom < candidate.maxZoom) ??
    AIRPORT_COVERAGE_LEVELS[AIRPORT_COVERAGE_LEVELS.length - 1];
  const { cellDegrees, limit } = level;
  const centerLatitude = Math.max(-90, Math.min(90, (viewBbox.lamin + viewBbox.lamax) / 2));
  const centerLongitude = Math.max(-180, Math.min(180, (viewBbox.lomin + viewBbox.lomax) / 2));
  const latitudeIndex = Math.min(
    Math.ceil(180 / cellDegrees) - 1,
    Math.floor((centerLatitude + 90) / cellDegrees)
  );
  const longitudeIndex = Math.min(
    Math.ceil(360 / cellDegrees) - 1,
    Math.floor((centerLongitude + 180) / cellDegrees)
  );
  const lamin = -90 + latitudeIndex * cellDegrees;
  const lomin = -180 + longitudeIndex * cellDegrees;

  return {
    key: `${cellDegrees}:${latitudeIndex}:${longitudeIndex}`,
    bbox: {
      lamin,
      lamax: Math.min(90, lamin + cellDegrees),
      lomin,
      lomax: Math.min(180, lomin + cellDegrees),
    },
    limit,
  };
}
