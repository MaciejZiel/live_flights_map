export function getAircraftRenderMode({
  aircraftCount = 0,
  zoom = null,
  clusteringEnabled = false,
} = {}) {
  if (clusteringEnabled || aircraftCount <= 0) {
    return "detailed";
  }

  if (!Number.isFinite(zoom)) {
    return aircraftCount >= 2200 ? "webgl" : aircraftCount >= 650 ? "lite" : "detailed";
  }

  if (aircraftCount >= 3600) {
    return "webgl";
  }

  if (zoom <= 4.8 && aircraftCount >= 850) {
    return "webgl";
  }

  if (zoom <= 5.8 && aircraftCount >= 1350) {
    return "webgl";
  }

  if (zoom <= 6.8 && aircraftCount >= 2100) {
    return "webgl";
  }

  if (aircraftCount >= 2200) {
    return "lite";
  }

  if (zoom <= 4.8 && aircraftCount >= 220) {
    return "lite";
  }

  if (zoom <= 5.8 && aircraftCount >= 320) {
    return "lite";
  }

  if (zoom <= 6.8 && aircraftCount >= 420) {
    return "lite";
  }

  if (zoom <= 8.2 && aircraftCount >= 650) {
    return "lite";
  }

  return "detailed";
}

export function shouldUseGpuAircraftLayer({
  aircraftCount = 0,
  clusteringEnabled = false,
  webglSupported = false,
  renderMode = "detailed",
} = {}) {
  return Boolean(
    webglSupported &&
      !clusteringEnabled &&
      aircraftCount > 0 &&
      renderMode === "webgl"
  );
}

export function shouldUseDetailedAircraftMarker(renderMode, selected = false, watched = false) {
  return renderMode === "detailed" || selected || watched;
}
