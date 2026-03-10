const STORAGE_KEY = "live-flights-map.preferences.v3";

const MAP_STYLE_OPTIONS = new Set(["standard", "satellite", "dark", "aviation"]);
const SORT_OPTIONS = new Set([
  "altitude_desc",
  "speed_desc",
  "distance_asc",
  "last_contact_desc",
]);
const THEME_OPTIONS = new Set(["dark", "light"]);
const RECENT_ACTIVITY_OPTIONS = new Set(["any", "30s", "2m", "5m", "15m"]);
const HEADING_BAND_OPTIONS = new Set(["any", "north", "east", "south", "west"]);
const TRAFFIC_CATEGORY_OPTIONS = new Set([
  "all",
  "passenger",
  "cargo",
  "business",
  "military",
  "government",
  "helicopter",
  "light",
  "glider",
]);

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function sanitizeString(value, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function sanitizeBoolean(value, fallback = false) {
  return typeof value === "boolean" ? value : fallback;
}

function sanitizeFiniteNumber(value, fallback = null) {
  return Number.isFinite(value) ? value : fallback;
}

function sanitizeStringArray(value) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((entry) => typeof entry === "string");
}

function sanitizeObjectRecord(value) {
  return isPlainObject(value) ? value : {};
}

function sanitizeOption(value, allowedValues, fallback) {
  return allowedValues.has(value) ? value : fallback;
}

function sanitizeViewport(value) {
  if (!isPlainObject(value)) {
    return null;
  }

  const center = Array.isArray(value.center) ? value.center : [];
  const latitude = sanitizeFiniteNumber(center[0]);
  const longitude = sanitizeFiniteNumber(center[1]);
  const zoom = sanitizeFiniteNumber(value.zoom);

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || !Number.isFinite(zoom)) {
    return null;
  }

  return {
    center: [latitude, longitude],
    zoom,
  };
}

function sanitizeFilters(value) {
  if (!isPlainObject(value)) {
    return {};
  }

  return {
    query: sanitizeString(value.query),
    minAltitude:
      typeof value.minAltitude === "string" || typeof value.minAltitude === "number"
        ? String(value.minAltitude)
        : "",
    minSpeed:
      typeof value.minSpeed === "string" || typeof value.minSpeed === "number"
        ? String(value.minSpeed)
        : "",
    country: sanitizeString(value.country),
    operator: sanitizeString(value.operator),
    trafficCategory: sanitizeOption(
      sanitizeString(value.trafficCategory, "all"),
      TRAFFIC_CATEGORY_OPTIONS,
      "all"
    ),
    headingBand: sanitizeOption(
      sanitizeString(value.headingBand, "any"),
      HEADING_BAND_OPTIONS,
      "any"
    ),
    hideGroundTraffic: sanitizeBoolean(value.hideGroundTraffic, true),
    recentActivity: sanitizeOption(
      sanitizeString(value.recentActivity, "any"),
      RECENT_ACTIVITY_OPTIONS,
      "any"
    ),
    dimFilteredTraffic: sanitizeBoolean(value.dimFilteredTraffic, true),
  };
}

export function normalizeUserPreferences(value) {
  if (!isPlainObject(value)) {
    return null;
  }

  const sanitized = {
    filters: sanitizeFilters(value.filters),
    mapStyle: sanitizeOption(sanitizeString(value.mapStyle, "standard"), MAP_STYLE_OPTIONS, "standard"),
    mapViewport: sanitizeViewport(value.mapViewport),
    filterPresets: Array.isArray(value.filterPresets) ? value.filterPresets : [],
    sortBy: sanitizeOption(sanitizeString(value.sortBy, "altitude_desc"), SORT_OPTIONS, "altitude_desc"),
    theme: sanitizeOption(sanitizeString(value.theme, "dark"), THEME_OPTIONS, "dark"),
    onboardingDismissed: sanitizeBoolean(value.onboardingDismissed, false),
    watchlist: sanitizeStringArray(value.watchlist),
    watchModeEnabled: sanitizeBoolean(value.watchModeEnabled, false),
    flightAnnotations: sanitizeObjectRecord(value.flightAnnotations),
    alertRules: Array.isArray(value.alertRules) ? value.alertRules : [],
    alertEvents: Array.isArray(value.alertEvents) ? value.alertEvents : [],
    monitoringSessions: Array.isArray(value.monitoringSessions) ? value.monitoringSessions : [],
    savedViews: Array.isArray(value.savedViews) ? value.savedViews : [],
    savedEntities: Array.isArray(value.savedEntities) ? value.savedEntities : [],
    weatherLayerEnabled: sanitizeBoolean(value.weatherLayerEnabled, false),
    showAirportMarkers: sanitizeBoolean(value.showAirportMarkers, true),
    selectedAirportCode:
      typeof value.selectedAirportCode === "string" && value.selectedAirportCode.trim()
        ? value.selectedAirportCode.trim().toUpperCase()
        : null,
    replayPlaybackSpeed:
      Number.isFinite(value.replayPlaybackSpeed) && value.replayPlaybackSpeed > 0
        ? value.replayPlaybackSpeed
        : 1,
  };

  return sanitized;
}

export function loadUserPreferences() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const rawValue = window.localStorage.getItem(STORAGE_KEY);
    if (!rawValue) {
      return null;
    }

    return normalizeUserPreferences(JSON.parse(rawValue));
  } catch {
    return null;
  }
}

export function saveUserPreferences(preferences) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  } catch {
    // Ignore storage write failures so the radar stays usable in private mode and tight quotas.
  }
}
