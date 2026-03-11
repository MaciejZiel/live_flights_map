export function getAircraftRenderMode({
  aircraftCount = 0,
  zoom = null,
  clusteringEnabled = false,
} = {}) {
  if (clusteringEnabled || aircraftCount <= 0) {
    return "detailed";
  }

  if (!Number.isFinite(zoom)) {
    return aircraftCount >= 1800 ? "lite" : "detailed";
  }

  if (aircraftCount >= 2800) {
    return "lite";
  }

  if (zoom <= 4.8 && aircraftCount >= 900) {
    return "lite";
  }

  if (zoom <= 5.8 && aircraftCount >= 1400) {
    return "lite";
  }

  if (zoom <= 6.8 && aircraftCount >= 2200) {
    return "lite";
  }

  return "detailed";
}

export function shouldUseDetailedAircraftMarker(renderMode, selected = false, watched = false) {
  return renderMode !== "lite" || selected || watched;
}
