<script>
  import { onMount } from "svelte";

  import FlightDetailsPanel from "./lib/components/FlightDetailsPanel.svelte";
  import ComparisonPanel from "./lib/components/ComparisonPanel.svelte";
  import SavedViewsPanel from "./lib/components/SavedViewsPanel.svelte";
  import AlertPanel from "./lib/components/AlertPanel.svelte";
  import LegendPanel from "./lib/components/LegendPanel.svelte";
  import MonitoringSessionsPanel from "./lib/components/MonitoringSessionsPanel.svelte";
  import ReplayTimeline from "./lib/components/ReplayTimeline.svelte";
  import ShortcutsPanel from "./lib/components/ShortcutsPanel.svelte";
  import TrafficBoardPanel from "./lib/components/TrafficBoardPanel.svelte";
  import WatchlistPanel from "./lib/components/WatchlistPanel.svelte";
  import FlightMap from "./lib/components/FlightMap.svelte";
  import { fetchFlightDetails } from "./lib/api/flights.js";
  import { flightsStore } from "./lib/stores/flights.js";
  import { formatAltitude, formatHeading, formatSpeed } from "./lib/utils/flightFormatters.js";
  import { getTrailPoints, updateFlightHistory } from "./lib/utils/flightHistory.js";
  import { loadUserPreferences, saveUserPreferences } from "./lib/utils/userPreferences.js";

  let state = {
    status: "idle",
    flights: [],
    error: null,
    fetchedAt: null,
    count: 0,
    bbox: null,
  };

  const unsubscribe = flightsStore.subscribe((value) => {
    state = value;

    if (value.fetchedAt && value.fetchedAt !== lastHistoryFetchKey) {
      flightHistory = updateFlightHistory(flightHistory, value.flights ?? [], value.fetchedAt);
      lastHistoryFetchKey = value.fetchedAt;
    }

    if (value.fetchedAt && value.fetchedAt !== lastReplaySnapshotKey) {
      snapshotHistory = pushReplaySnapshot(snapshotHistory, value);
      lastReplaySnapshotKey = value.fetchedAt;
    }
  });

  let filters = {
    query: "",
    minAltitude: "",
    minSpeed: "",
    country: "",
    operator: "",
    headingBand: "any",
    hideGroundTraffic: true,
    recentActivity: "any",
  };
  let selectedIcao24 = null;
  let followAircraft = false;
  let mapStyle = "standard";
  let mapViewport = {
    center: [52.2297, 21.0122],
    zoom: 7.1,
  };
  let preferencesReady = false;
  let searchInput;
  let fullscreenRequestId = 0;
  let viewPresetRequest = null;
  let now = Date.now();
  let flightHistory = new Map();
  let lastHistoryFetchKey = null;
  let filterPresets = [];
  let presetName = "";
  let sortBy = "altitude_desc";
  let theme = "dark";
  let onboardingDismissed = false;
  let isMobileViewport = false;
  let mobileSidebarOpen = true;
  let inspectorTab = "details";
  let snapshotHistory = [];
  let replaySnapshotCursor = null;
  let lastReplaySnapshotKey = null;
  let replayPlaybackActive = false;
  let replayPlaybackTimer = null;
  let shareFeedback = "";
  let shareFeedbackTimer = null;
  let watchlist = [];
  let watchModeEnabled = false;
  let flightAnnotations = {};
  let alertRules = [];
  let alertEvents = [];
  let alertMatchState = {};
  let alertToast = null;
  let alertToastTimer = null;
  let lastAlertCheckKey = null;
  let monitoringSessions = [];
  let activeMonitoringSessionId = null;
  let savedViews = [];
  let savedViewName = "";
  let activeSavedViewId = null;
  let flightDetailsCache = new Map();
  let selectedFlightDetails = null;
  let selectedFlightDetailsStatus = "idle";
  let selectedFlightDetailsError = null;
  let selectedFlightDetailsRequestId = 0;
  let lastSelectedFlightDetailsKey = null;

  onMount(() => {
    const savedPreferences = loadUserPreferences();
    if (savedPreferences) {
      filters = {
        ...filters,
        ...savedPreferences.filters,
      };
      mapStyle = savedPreferences.mapStyle ?? mapStyle;
      mapViewport = savedPreferences.mapViewport ?? mapViewport;
      filterPresets = savedPreferences.filterPresets ?? filterPresets;
      sortBy = savedPreferences.sortBy ?? sortBy;
      theme = savedPreferences.theme ?? theme;
      onboardingDismissed = savedPreferences.onboardingDismissed ?? onboardingDismissed;
      watchlist = savedPreferences.watchlist ?? watchlist;
      watchModeEnabled = savedPreferences.watchModeEnabled ?? watchModeEnabled;
      flightAnnotations = savedPreferences.flightAnnotations ?? flightAnnotations;
      alertRules = savedPreferences.alertRules ?? alertRules;
      alertEvents = savedPreferences.alertEvents ?? alertEvents;
      monitoringSessions = savedPreferences.monitoringSessions ?? monitoringSessions;
      savedViews = savedPreferences.savedViews ?? savedViews;
    }

    applySharedStateFromUrl();

    syncThemeClass(theme);
    preferencesReady = true;
    flightsStore.start();
    window.addEventListener("keydown", handleKeyboardShortcut);
    const mobileViewportQuery = window.matchMedia("(max-width: 960px)");
    const syncViewportMode = (event) => {
      isMobileViewport = event.matches;
      mobileSidebarOpen = !event.matches;
    };
    syncViewportMode(mobileViewportQuery);
    mobileViewportQuery.addEventListener("change", syncViewportMode);
    const freshnessTimer = window.setInterval(() => {
      now = Date.now();
    }, 1000);

    return () => {
      window.removeEventListener("keydown", handleKeyboardShortcut);
      mobileViewportQuery.removeEventListener("change", syncViewportMode);
      window.clearInterval(freshnessTimer);
      if (replayPlaybackTimer) {
        window.clearInterval(replayPlaybackTimer);
      }
      if (shareFeedbackTimer) {
        window.clearTimeout(shareFeedbackTimer);
      }
      if (alertToastTimer) {
        window.clearTimeout(alertToastTimer);
      }
      unsubscribe();
      flightsStore.stop();
    };
  });

  function formatTimestamp(value) {
    if (!value) {
      return "waiting for first sync";
    }

    return new Intl.DateTimeFormat("pl-PL", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(value));
  }

  function formatCompactCount(value) {
    return new Intl.NumberFormat("en", {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value ?? 0);
  }

  function getStatusLabel(stateValue) {
    if (stateValue.status === "loading") {
      return "Syncing";
    }

    if (stateValue.status === "refreshing") {
      return "Live sync";
    }

    if (stateValue.status === "error") {
      return "Upstream error";
    }

    if (stateValue.reason === "rate_limit" || stateValue.reason === "cooldown") {
      return "Rate limited";
    }

    if (stateValue.source === "cache") {
      return "Cached";
    }

    if (stateValue.status === "success") {
      return "Live";
    }

    return "Idle";
  }

  function countActiveFilters(currentFilters) {
    return [
      currentFilters.query.trim(),
      currentFilters.minAltitude,
      currentFilters.minSpeed,
      currentFilters.country.trim(),
      currentFilters.operator.trim(),
      currentFilters.headingBand !== "any",
      !currentFilters.hideGroundTraffic,
      currentFilters.recentActivity !== "any",
    ].filter(Boolean).length;
  }

  function getTopValues(flights, getValue, limit = 4) {
    const counts = new Map();

    for (const flight of flights) {
      const value = getValue(flight);
      if (!value) {
        continue;
      }

      counts.set(value, (counts.get(value) ?? 0) + 1);
    }

    return [...counts.entries()]
      .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
      .slice(0, limit)
      .map(([value]) => value);
  }

  function buildCountryActivity(flights, limit = 3) {
    const grouped = new Map();

    for (const flight of flights) {
      const key = flight.origin_country ?? "Unknown";
      const current = grouped.get(key) ?? {
        country: key,
        count: 0,
        averageSpeed: 0,
        ground: 0,
      };

      current.count += 1;
      current.averageSpeed += (flight.velocity ?? 0) * 3.6;
      current.ground += flight.on_ground ? 1 : 0;
      grouped.set(key, current);
    }

    return [...grouped.values()]
      .map((entry) => ({
        ...entry,
        averageSpeed: entry.count ? Math.round(entry.averageSpeed / entry.count) : 0,
      }))
      .sort((left, right) => right.count - left.count || right.averageSpeed - left.averageSpeed)
      .slice(0, limit);
  }

  function handleBoundsChange(event) {
    flightsStore.setBbox(event.detail.bbox);
  }

  function handleFlightSelect(event) {
    selectedIcao24 = event.detail.flight.icao24;
    inspectorTab = "details";
    if (isMobileViewport) {
      mobileSidebarOpen = true;
    }
  }

  function handleViewportChange(event) {
    mapViewport = event.detail.viewport;
  }

  function syncThemeClass(nextTheme) {
    if (typeof document === "undefined") {
      return;
    }

    document.body.classList.toggle("theme-dark", nextTheme === "dark");
  }

  function applySharedStateFromUrl() {
    if (typeof window === "undefined") {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const nextFilters = { ...filters };
    const latitude = Number(params.get("lat"));
    const longitude = Number(params.get("lng"));
    const zoom = Number(params.get("z"));
    const sharedQuery = params.get("q");
    const sharedMinAltitude = params.get("minAlt");
    const sharedMinSpeed = params.get("minSpeed");
    const sharedCountry = params.get("country");
    const sharedOperator = params.get("operator");
    const sharedHeadingBand = params.get("heading");
    const sharedRecentActivity = params.get("recent");
    const sharedSort = params.get("sort");
    const sharedTheme = params.get("theme");
    const sharedMapStyle = params.get("map");
    const sharedSelectedIcao24 = params.get("sel");
    const sharedGroundFlag = params.get("ground");

    if (Number.isFinite(latitude) && Number.isFinite(longitude) && Number.isFinite(zoom)) {
      mapViewport = {
        center: [latitude, longitude],
        zoom,
      };
    }

    if (sharedQuery !== null) {
      nextFilters.query = sharedQuery;
    }

    if (sharedMinAltitude !== null) {
      nextFilters.minAltitude = sharedMinAltitude;
    }

    if (sharedMinSpeed !== null) {
      nextFilters.minSpeed = sharedMinSpeed;
    }

    if (sharedCountry !== null) {
      nextFilters.country = sharedCountry;
    }

    if (sharedOperator !== null) {
      nextFilters.operator = sharedOperator;
    }

    if (["any", "north", "east", "south", "west"].includes(sharedHeadingBand)) {
      nextFilters.headingBand = sharedHeadingBand;
    }

    if (["any", "30s", "2m", "5m", "15m"].includes(sharedRecentActivity)) {
      nextFilters.recentActivity = sharedRecentActivity;
    }

    if (["altitude_desc", "speed_desc", "distance_asc", "last_contact_desc"].includes(sharedSort)) {
      sortBy = sharedSort;
    }

    if (sharedTheme === "light" || sharedTheme === "dark") {
      theme = sharedTheme;
    }

    if (["standard", "satellite", "dark", "aviation"].includes(sharedMapStyle)) {
      mapStyle = sharedMapStyle;
    }

    if (sharedSelectedIcao24) {
      selectedIcao24 = sharedSelectedIcao24;
    }

    if (sharedGroundFlag === "0" || sharedGroundFlag === "1") {
      nextFilters.hideGroundTraffic = sharedGroundFlag === "1";
    }

    filters = nextFilters;
  }

  function syncShareUrl() {
    if (typeof window === "undefined") {
      return;
    }

    const url = new URL(window.location.href);
    const params = url.searchParams;

    if (filters.query.trim()) {
      params.set("q", filters.query.trim());
    } else {
      params.delete("q");
    }

    if (filters.minAltitude !== "") {
      params.set("minAlt", filters.minAltitude);
    } else {
      params.delete("minAlt");
    }

    if (filters.minSpeed !== "") {
      params.set("minSpeed", filters.minSpeed);
    } else {
      params.delete("minSpeed");
    }

    if (filters.country.trim()) {
      params.set("country", filters.country.trim());
    } else {
      params.delete("country");
    }

    if (filters.operator.trim()) {
      params.set("operator", filters.operator.trim());
    } else {
      params.delete("operator");
    }

    if (filters.headingBand !== "any") {
      params.set("heading", filters.headingBand);
    } else {
      params.delete("heading");
    }

    if (filters.recentActivity !== "any") {
      params.set("recent", filters.recentActivity);
    } else {
      params.delete("recent");
    }

    if (!filters.hideGroundTraffic) {
      params.set("ground", "0");
    } else {
      params.delete("ground");
    }

    if (sortBy !== "altitude_desc") {
      params.set("sort", sortBy);
    } else {
      params.delete("sort");
    }

    if (theme !== "light") {
      params.set("theme", theme);
    } else {
      params.delete("theme");
    }

    if (mapStyle !== "standard") {
      params.set("map", mapStyle);
    } else {
      params.delete("map");
    }

    if (selectedIcao24) {
      params.set("sel", selectedIcao24);
    } else {
      params.delete("sel");
    }

    if (mapViewport?.center && Number.isFinite(mapViewport.zoom)) {
      params.set("lat", mapViewport.center[0].toFixed(4));
      params.set("lng", mapViewport.center[1].toFixed(4));
      params.set("z", String(mapViewport.zoom));
    } else {
      params.delete("lat");
      params.delete("lng");
      params.delete("z");
    }

    window.history.replaceState({}, "", `${url.pathname}${url.search}`);
  }

  async function copyShareLink() {
    if (typeof window === "undefined") {
      return;
    }

    try {
      await window.navigator.clipboard.writeText(window.location.href);
      shareFeedback = "Link copied";
    } catch {
      shareFeedback = "Copy failed";
    }

    if (shareFeedbackTimer) {
      window.clearTimeout(shareFeedbackTimer);
    }

    shareFeedbackTimer = window.setTimeout(() => {
      shareFeedback = "";
      shareFeedbackTimer = null;
    }, 1800);
  }

  function pushAlertEvent(message) {
    const nextEvent = {
      id: crypto.randomUUID(),
      message,
      timestamp: Date.now(),
    };

    alertEvents = [nextEvent, ...alertEvents].slice(0, 30);
    alertToast = nextEvent;

    if (alertToastTimer) {
      window.clearTimeout(alertToastTimer);
    }

    alertToastTimer = window.setTimeout(() => {
      alertToast = null;
      alertToastTimer = null;
    }, 3500);
  }

  function addAlertRule(rule) {
    const normalizedQuery = rule.query.trim().toLowerCase();
    if (!normalizedQuery) {
      return;
    }

    const duplicate = alertRules.some(
      (existingRule) => existingRule.type === rule.type && existingRule.query.toLowerCase() === normalizedQuery
    );
    if (duplicate) {
      return;
    }

    alertRules = [
      {
        id: crypto.randomUUID(),
        type: rule.type,
        query: rule.query.trim(),
      },
      ...alertRules,
    ].slice(0, 12);
  }

  function removeAlertRule(ruleId) {
    alertRules = alertRules.filter((rule) => rule.id !== ruleId);
    const nextMatchState = { ...alertMatchState };
    delete nextMatchState[ruleId];
    alertMatchState = nextMatchState;
  }

  function clearAlertEvents() {
    alertEvents = [];
  }

  function saveCurrentView() {
    const normalizedName = savedViewName.trim();
    if (!normalizedName) {
      return;
    }

    const nextView = {
      id: crypto.randomUUID(),
      name: normalizedName,
      watchlistCount: watchlist.length,
      mapStyle,
      state: {
        filters: { ...filters },
        sortBy,
        theme,
        mapStyle,
        mapViewport,
        watchlist: [...watchlist],
        watchModeEnabled,
        selectedIcao24,
      },
    };

    savedViews = [nextView, ...savedViews.filter((view) => view.name !== normalizedName)].slice(0, 10);
    activeSavedViewId = nextView.id;
    savedViewName = "";
  }

  function loadSavedView(viewId) {
    const view = savedViews.find((entry) => entry.id === viewId);
    if (!view) {
      return;
    }

    filters = {
      ...filters,
      ...view.state.filters,
    };
    sortBy = view.state.sortBy ?? sortBy;
    theme = view.state.theme ?? theme;
    mapStyle = view.state.mapStyle ?? mapStyle;
    mapViewport = view.state.mapViewport ?? mapViewport;
    watchlist = view.state.watchlist ?? watchlist;
    watchModeEnabled = view.state.watchModeEnabled ?? watchModeEnabled;
    selectedIcao24 = view.state.selectedIcao24 ?? null;
    activeSavedViewId = view.id;
  }

  function deleteSavedView(viewId) {
    savedViews = savedViews.filter((view) => view.id !== viewId);
    if (activeSavedViewId === viewId) {
      activeSavedViewId = null;
    }
  }

  function evaluateAlertRules() {
    if (!alertRules.length) {
      alertMatchState = {};
      return;
    }

    const nextMatchState = {};
    for (const rule of alertRules) {
      const normalizedQuery = rule.query.toLowerCase();
      const matches = state.flights.filter((flight) => {
        if (rule.type === "callsign") {
          return (flight.callsign ?? "").toLowerCase().includes(normalizedQuery);
        }

        return flight.icao24.includes(normalizedQuery);
      });

      const previousMatches = alertMatchState[rule.id]?.count ?? 0;
      nextMatchState[rule.id] = {
        count: matches.length,
      };

      if (matches.length > 0 && previousMatches === 0) {
        const leadFlight = matches[0];
        pushAlertEvent(
          `${rule.type === "callsign" ? "Callsign" : "ICAO24"} ${rule.query} matched ${
            leadFlight.callsign ?? leadFlight.icao24
          }`
        );
      }

      if (matches.length === 0 && previousMatches > 0) {
        pushAlertEvent(
          `${rule.type === "callsign" ? "Callsign" : "ICAO24"} ${rule.query} is no longer visible`
        );
      }
    }

    alertMatchState = nextMatchState;
  }

  function toggleFollowAircraft() {
    if (!selectedFlight) {
      followAircraft = false;
      return;
    }

    followAircraft = !followAircraft;
  }

  function toggleSelectedFlightWatchlist() {
    if (!selectedFlight) {
      return;
    }

    if (watchlist.includes(selectedFlight.icao24)) {
      watchlist = watchlist.filter((icao24) => icao24 !== selectedFlight.icao24);
      return;
    }

    watchlist = [selectedFlight.icao24, ...watchlist.filter((icao24) => icao24 !== selectedFlight.icao24)].slice(0, 12);
  }

  function removeFromWatchlist(icao24) {
    watchlist = watchlist.filter((value) => value !== icao24);
  }

  function selectWatchedFlight(icao24) {
    selectedIcao24 = icao24;
    inspectorTab = "details";
    if (isMobileViewport) {
      mobileSidebarOpen = true;
    }
  }

  function openInspectorTab(tab) {
    inspectorTab = tab;
    if (isMobileViewport) {
      mobileSidebarOpen = true;
    }
  }

  function buildFlightDetailsKey(flight) {
    if (!flight?.icao24) {
      return null;
    }

    return [
      flight.icao24,
      (flight.callsign ?? "").trim().toUpperCase(),
      (flight.registration ?? "").trim().toUpperCase(),
    ].join(":");
  }

  function buildFlightDetailsFallback(flight, warning = null) {
    if (!flight) {
      return null;
    }

    const operatorCode = deriveOperatorCode(flight);

    return {
      aircraft: {
        icao24: flight.icao24,
        callsign: flight.callsign ?? null,
        registration: flight.registration ?? null,
        type_code: flight.type_code ?? null,
        origin_country: flight.origin_country ?? null,
        operator_code: operatorCode || null,
      },
      route: null,
      photo: null,
      meta: {
        fetched_at: null,
        warning,
      },
    };
  }

  function mergeFlightDetails(flight, details) {
    if (!flight) {
      return details;
    }

    const fallbackDetails = buildFlightDetailsFallback(flight, details?.meta?.warning ?? null);
    const operatorCode = details?.aircraft?.operator_code || fallbackDetails?.aircraft?.operator_code || null;

    return {
      ...fallbackDetails,
      ...details,
      aircraft: {
        ...fallbackDetails?.aircraft,
        ...details?.aircraft,
        operator_code: operatorCode,
      },
      meta: {
        ...fallbackDetails?.meta,
        ...details?.meta,
      },
    };
  }

  async function loadSelectedFlightDetails(flight, options = {}) {
    const key = buildFlightDetailsKey(flight);
    if (!key) {
      selectedFlightDetails = null;
      selectedFlightDetailsStatus = "idle";
      selectedFlightDetailsError = null;
      return;
    }

    const force = options.force ?? false;
    const cachedDetails = flightDetailsCache.get(key);
    if (cachedDetails && !force) {
      selectedFlightDetails = mergeFlightDetails(flight, cachedDetails);
      selectedFlightDetailsStatus = "success";
      selectedFlightDetailsError = null;
      return;
    }

    const requestId = ++selectedFlightDetailsRequestId;
    const fallbackDetails = mergeFlightDetails(flight, cachedDetails ?? buildFlightDetailsFallback(flight));
    selectedFlightDetails = fallbackDetails;
    selectedFlightDetailsStatus = cachedDetails ? "refreshing" : "loading";
    selectedFlightDetailsError = null;

    try {
      const detailsPayload = await fetchFlightDetails(flight);
      if (requestId !== selectedFlightDetailsRequestId || buildFlightDetailsKey(selectedFlight) !== key) {
        return;
      }

      const mergedDetails = mergeFlightDetails(flight, detailsPayload);
      const nextCache = new Map(flightDetailsCache);
      nextCache.set(key, mergedDetails);
      flightDetailsCache = nextCache;
      selectedFlightDetails = mergedDetails;
      selectedFlightDetailsStatus = "success";
      selectedFlightDetailsError = null;
    } catch (error) {
      if (requestId !== selectedFlightDetailsRequestId || buildFlightDetailsKey(selectedFlight) !== key) {
        return;
      }

      const message = error instanceof Error ? error.message : "Failed to load aircraft details.";
      selectedFlightDetails = mergeFlightDetails(flight, {
        ...fallbackDetails,
        meta: {
          ...fallbackDetails?.meta,
          warning: message,
        },
      });
      selectedFlightDetailsStatus = cachedDetails ? "success" : "error";
      selectedFlightDetailsError = cachedDetails ? null : message;
    }
  }

  function retrySelectedFlightDetails() {
    if (!selectedFlight) {
      return;
    }

    loadSelectedFlightDetails(selectedFlight, { force: true });
  }

  function toggleWatchMode() {
    watchModeEnabled = !watchModeEnabled;
  }

  function updateSelectedFlightNotes(notes) {
    if (!selectedFlight) {
      return;
    }

    flightAnnotations = {
      ...flightAnnotations,
      [selectedFlight.icao24]: {
        ...(flightAnnotations[selectedFlight.icao24] ?? { notes: "", tags: [] }),
        notes,
      },
    };
  }

  function addSelectedFlightTag(tag) {
    if (!selectedFlight) {
      return;
    }

    const currentAnnotation = flightAnnotations[selectedFlight.icao24] ?? { notes: "", tags: [] };
    const normalizedTag = tag.trim();
    if (!normalizedTag) {
      return;
    }

    flightAnnotations = {
      ...flightAnnotations,
      [selectedFlight.icao24]: {
        ...currentAnnotation,
        tags: [normalizedTag, ...currentAnnotation.tags.filter((value) => value !== normalizedTag)].slice(0, 8),
      },
    };
  }

  function removeSelectedFlightTag(tag) {
    if (!selectedFlight) {
      return;
    }

    const currentAnnotation = flightAnnotations[selectedFlight.icao24] ?? { notes: "", tags: [] };
    flightAnnotations = {
      ...flightAnnotations,
      [selectedFlight.icao24]: {
        ...currentAnnotation,
        tags: currentAnnotation.tags.filter((value) => value !== tag),
      },
    };
  }

  function resetFilters() {
    filters = {
      query: "",
      minAltitude: "",
      minSpeed: "",
      country: "",
      operator: "",
      headingBand: "any",
      hideGroundTraffic: true,
      recentActivity: "any",
    };
  }

  function applyQuickFilter(presetKey) {
    if (presetKey === "reset") {
      resetFilters();
      return;
    }

    if (presetKey === "fast") {
      filters = {
        ...filters,
        minSpeed: "700",
        hideGroundTraffic: true,
      };
      return;
    }

    if (presetKey === "high") {
      filters = {
        ...filters,
        minAltitude: "9000",
        hideGroundTraffic: true,
      };
      return;
    }

    if (presetKey === "recent") {
      filters = {
        ...filters,
        recentActivity: "2m",
      };
      return;
    }

    if (presetKey === "ground") {
      filters = {
        ...filters,
        hideGroundTraffic: false,
      };
    }
  }

  function clearFilterToken(tokenKey) {
    if (tokenKey === "query") {
      filters = { ...filters, query: "" };
      return;
    }

    if (tokenKey === "minAltitude") {
      filters = { ...filters, minAltitude: "" };
      return;
    }

    if (tokenKey === "minSpeed") {
      filters = { ...filters, minSpeed: "" };
      return;
    }

    if (tokenKey === "country") {
      filters = { ...filters, country: "" };
      return;
    }

    if (tokenKey === "operator") {
      filters = { ...filters, operator: "" };
      return;
    }

    if (tokenKey === "headingBand") {
      filters = { ...filters, headingBand: "any" };
      return;
    }

    if (tokenKey === "recentActivity") {
      filters = { ...filters, recentActivity: "any" };
      return;
    }

    if (tokenKey === "ground") {
      filters = { ...filters, hideGroundTraffic: true };
    }
  }

  function saveCurrentPreset() {
    const normalizedName = presetName.trim();
    if (!normalizedName) {
      return;
    }

    const nextPreset = {
      name: normalizedName,
      filters: { ...filters },
    };

    filterPresets = [
      nextPreset,
      ...filterPresets.filter((preset) => preset.name !== normalizedName),
    ].slice(0, 8);
    presetName = "";
  }

  function applyFilterPreset(preset) {
    filters = {
      ...filters,
      ...preset.filters,
    };
  }

  function deleteFilterPreset(name) {
    filterPresets = filterPresets.filter((preset) => preset.name !== name);
  }

  function triggerViewPreset(presetKey) {
    viewPresetRequest = {
      presetKey,
      id: Date.now(),
    };
  }

  function triggerFullscreenToggle() {
    fullscreenRequestId = Date.now();
  }

  function setTheme(nextTheme) {
    theme = nextTheme;
  }

  function cycleMapStyle() {
    const mapStyles = ["aviation", "dark", "satellite", "standard"];
    const currentIndex = mapStyles.indexOf(mapStyle);
    const nextIndex = currentIndex === -1 ? 0 : (currentIndex + 1) % mapStyles.length;
    mapStyle = mapStyles[nextIndex];
  }

  function dismissOnboarding() {
    onboardingDismissed = true;
  }

  function pushReplaySnapshot(history, snapshotState) {
    const snapshot = {
      fetchedAt: snapshotState.fetchedAt,
      count: snapshotState.count ?? 0,
      flights: (snapshotState.flights ?? []).map((flight) => ({ ...flight })),
    };

    return [...history.filter((entry) => entry.fetchedAt !== snapshot.fetchedAt), snapshot].slice(-90);
  }

  function buildSessionLabel(timestamp) {
    return new Intl.DateTimeFormat("pl-PL", {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(timestamp));
  }

  function toggleMobileSidebar() {
    mobileSidebarOpen = !mobileSidebarOpen;
  }

  function closeMobileSidebar() {
    mobileSidebarOpen = false;
  }

  function selectReplaySnapshot(index) {
    replayPlaybackActive = false;
    replaySnapshotCursor = replaySourceSnapshots[index]?.fetchedAt ?? null;
  }

  function returnToLiveReplay() {
    replayPlaybackActive = false;
    activeMonitoringSessionId = null;
    replaySnapshotCursor = null;
  }

  function setReplaySnapshotIndex(index) {
    if (!replaySourceSnapshots.length) {
      replaySnapshotCursor = null;
      return;
    }

    const boundedIndex = Math.max(0, Math.min(index, replaySourceSnapshots.length - 1));
    replaySnapshotCursor = replaySourceSnapshots[boundedIndex]?.fetchedAt ?? null;
  }

  function stepReplay(direction) {
    if (replaySourceSnapshots.length < 2) {
      return;
    }

    replayPlaybackActive = false;

    if (replaySnapshotIndex < 0) {
      if (direction < 0) {
        setReplaySnapshotIndex(replaySourceSnapshots.length - 2);
      } else {
        setReplaySnapshotIndex(0);
      }
      return;
    }

    const nextIndex = replaySnapshotIndex + direction;
    if (nextIndex >= replaySourceSnapshots.length - 1) {
      replaySnapshotCursor = null;
      return;
    }

    setReplaySnapshotIndex(nextIndex);
  }

  function toggleReplayPlayback() {
    if (replaySourceSnapshots.length < 2) {
      return;
    }

    if (replayPlaybackActive) {
      replayPlaybackActive = false;
      return;
    }

    if (replaySnapshotIndex < 0) {
      setReplaySnapshotIndex(0);
    }

    replayPlaybackActive = true;
  }

  function saveCurrentMonitoringSession() {
    if (snapshotHistory.length < 2) {
      return;
    }

    const createdAt = Date.now();
    const session = {
      id: crypto.randomUUID(),
      label: `Session ${buildSessionLabel(createdAt)}`,
      createdAt,
      snapshots: snapshotHistory.map((snapshot) => ({
        ...snapshot,
        flights: snapshot.flights.map((flight) => ({ ...flight })),
      })),
      viewport: mapViewport,
    };

    monitoringSessions = [session, ...monitoringSessions].slice(0, 8);
  }

  function loadMonitoringSession(sessionId) {
    const session = monitoringSessions.find((entry) => entry.id === sessionId);
    if (!session) {
      return;
    }

    replayPlaybackActive = false;
    activeMonitoringSessionId = sessionId;
    replaySnapshotCursor = session.snapshots[0]?.fetchedAt ?? null;
    if (session.viewport) {
      mapViewport = session.viewport;
    }
  }

  function deleteMonitoringSession(sessionId) {
    monitoringSessions = monitoringSessions.filter((session) => session.id !== sessionId);
    if (activeMonitoringSessionId === sessionId) {
      activeMonitoringSessionId = null;
      replaySnapshotCursor = null;
    }
  }

  function syncReplayPlaybackTimer() {
    if (typeof window === "undefined") {
      return;
    }

    if (replayPlaybackTimer) {
      window.clearInterval(replayPlaybackTimer);
      replayPlaybackTimer = null;
    }

    if (!replayPlaybackActive || replaySourceSnapshots.length < 2) {
      return;
    }

    replayPlaybackTimer = window.setInterval(() => {
      if (replaySnapshotIndex < 0) {
        setReplaySnapshotIndex(0);
        return;
      }

      const nextIndex = replaySnapshotIndex + 1;
      if (nextIndex >= replaySourceSnapshots.length - 1) {
        replayPlaybackActive = false;
        replaySnapshotCursor = null;
        return;
      }

      setReplaySnapshotIndex(nextIndex);
    }, 1200);
  }

  function handleKeyboardShortcut(event) {
    const target = event.target;
    const isTypingField =
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      target?.isContentEditable;

    if (event.key === "/") {
      event.preventDefault();
      searchInput?.focus();
      searchInput?.select();
      return;
    }

    if (isTypingField) {
      return;
    }

    if (event.key === "1") {
      mapStyle = "standard";
    } else if (event.key === "2") {
      mapStyle = "satellite";
    } else if (event.key === "3") {
      mapStyle = "dark";
    } else if (event.key === "4") {
      mapStyle = "aviation";
    } else if (event.key === "0") {
      resetFilters();
    } else if (event.key.toLowerCase() === "f") {
      toggleFollowAircraft();
    } else if (event.key.toLowerCase() === "m") {
      triggerFullscreenToggle();
    } else if (event.key.toLowerCase() === "p") {
      triggerViewPreset("poland");
    } else if (event.key.toLowerCase() === "e") {
      triggerViewPreset("europe");
    } else if (event.key.toLowerCase() === "w") {
      triggerViewPreset("world");
    } else {
      return;
    }

    event.preventDefault();
  }

  function getFreshnessLabel(value) {
    if (!value) {
      return "waiting";
    }

    const ageSeconds = Math.max(0, Math.round((now - new Date(value).getTime()) / 1000));
    return `${ageSeconds}s old`;
  }

  function getConfidenceLabel(stateValue) {
    if (stateValue.status === "error") {
      return "Unavailable";
    }

    if (stateValue.reason === "rate_limit" || stateValue.reason === "cooldown") {
      return "Reduced";
    }

    if (stateValue.source === "cache" || stateValue.stale) {
      return "Guarded";
    }

    return "High";
  }

  function deriveOperatorCode(flight) {
    const rawCallsign = (flight.callsign ?? "").trim().toUpperCase();
    const match = rawCallsign.match(/^[A-Z]{3}/);
    return match ? match[0] : "";
  }

  function matchesHeadingBand(track, band) {
    if (band === "any" || track === null || track === undefined) {
      return true;
    }

    if (band === "north") {
      return track >= 315 || track < 45;
    }

    if (band === "east") {
      return track >= 45 && track < 135;
    }

    if (band === "south") {
      return track >= 135 && track < 225;
    }

    if (band === "west") {
      return track >= 225 && track < 315;
    }

    return true;
  }

  function calculateDistanceKm(latitude, longitude, viewport) {
    const center = viewport?.center ?? [52.15, 19.4];
    const toRadians = (value) => (value * Math.PI) / 180;
    const earthRadiusKm = 6371;
    const deltaLatitude = toRadians(latitude - center[0]);
    const deltaLongitude = toRadians(longitude - center[1]);
    const startLatitude = toRadians(center[0]);
    const endLatitude = toRadians(latitude);
    const haversine =
      Math.sin(deltaLatitude / 2) ** 2 +
      Math.cos(startLatitude) * Math.cos(endLatitude) * Math.sin(deltaLongitude / 2) ** 2;

    return 2 * earthRadiusKm * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
  }

  function sortFlights(flights, mode, viewport) {
    const sortedFlights = [...flights];

    sortedFlights.sort((left, right) => {
      if (mode === "altitude_desc") {
        return (right.altitude ?? -Infinity) - (left.altitude ?? -Infinity);
      }

      if (mode === "speed_desc") {
        return (right.velocity ?? -Infinity) - (left.velocity ?? -Infinity);
      }

      if (mode === "distance_asc") {
        return (
          calculateDistanceKm(left.latitude, left.longitude, viewport) -
          calculateDistanceKm(right.latitude, right.longitude, viewport)
        );
      }

      if (mode === "last_contact_desc") {
        return (right.last_contact ?? -Infinity) - (left.last_contact ?? -Infinity);
      }

      return 0;
    });

    return sortedFlights;
  }

  function getDisplayLimitForZoom(zoom) {
    if (!Number.isFinite(zoom)) {
      return 240;
    }

    if (zoom <= 4) {
      return 120;
    }

    if (zoom <= 5) {
      return 220;
    }

    if (zoom <= 6) {
      return 360;
    }

    if (zoom <= 7) {
      return 520;
    }

    return null;
  }

  function prioritizeFlightsForMap(flights, limit, selectedIcao24, watchedIcao24s) {
    if (!limit || flights.length <= limit) {
      return flights;
    }

    const watchedSet = new Set(watchedIcao24s);
    const withPriority = flights
      .map((flight, index) => ({
        flight,
        index,
        priority:
          (flight.icao24 === selectedIcao24 ? 5000 : 0) +
          (watchedSet.has(flight.icao24) ? 2000 : 0) +
          (!flight.on_ground ? 600 : 0) +
          Math.max(0, Math.round(flight.altitude ?? 0) / 100) +
          Math.max(0, Math.round(flight.velocity ?? 0)),
      }))
      .sort((left, right) => right.priority - left.priority || left.index - right.index)
      .slice(0, limit)
      .sort((left, right) => left.index - right.index);

    return withPriority.map((entry) => entry.flight);
  }

  $: normalizedQuery = filters.query.trim().toLowerCase();
  $: minimumAltitude = Number(filters.minAltitude);
  $: hasMinimumAltitude = Number.isFinite(minimumAltitude) && filters.minAltitude !== "";
  $: minimumSpeed = Number(filters.minSpeed);
  $: hasMinimumSpeed = Number.isFinite(minimumSpeed) && filters.minSpeed !== "";
  $: normalizedCountryFilter = filters.country.trim().toLowerCase();
  $: normalizedOperatorFilter = filters.operator.trim().toLowerCase();
  $: activeMonitoringSession =
    monitoringSessions.find((session) => session.id === activeMonitoringSessionId) ?? null;
  $: replaySourceSnapshots = activeMonitoringSession?.snapshots ?? snapshotHistory;
  $: replaySnapshotIndex = replaySnapshotCursor
    ? replaySourceSnapshots.findIndex((snapshot) => snapshot.fetchedAt === replaySnapshotCursor)
    : -1;
  $: activeReplaySnapshot =
    replaySnapshotIndex >= 0 ? replaySourceSnapshots[replaySnapshotIndex] ?? null : null;
  $: replayFlights = activeReplaySnapshot?.flights ?? state.flights;
  $: filteredFlights = replayFlights.filter((flight) => {
    const operatorCode = deriveOperatorCode(flight).toLowerCase();
    const matchesQuery =
      !normalizedQuery ||
      flight.icao24.includes(normalizedQuery) ||
      (flight.callsign ?? "").toLowerCase().includes(normalizedQuery) ||
      (flight.origin_country ?? "").toLowerCase().includes(normalizedQuery) ||
      operatorCode.includes(normalizedQuery);

    const matchesAltitude =
      !hasMinimumAltitude ||
      (flight.altitude !== null && flight.altitude !== undefined && flight.altitude >= minimumAltitude);

    const matchesSpeed =
      !hasMinimumSpeed ||
      (flight.velocity !== null &&
        flight.velocity !== undefined &&
        flight.velocity * 3.6 >= minimumSpeed);

    const matchesCountry =
      !normalizedCountryFilter ||
      (flight.origin_country ?? "").toLowerCase().includes(normalizedCountryFilter);

    const matchesOperator =
      !normalizedOperatorFilter || operatorCode.includes(normalizedOperatorFilter);

    const matchesHeading = matchesHeadingBand(flight.true_track, filters.headingBand);

    const matchesGroundFilter = !filters.hideGroundTraffic || !flight.on_ground;
    const recentActivityLimitSeconds =
      filters.recentActivity === "30s"
        ? 30
        : filters.recentActivity === "2m"
          ? 120
          : filters.recentActivity === "5m"
            ? 300
            : filters.recentActivity === "15m"
              ? 900
              : null;
    const matchesRecentActivity =
      recentActivityLimitSeconds === null ||
      (flight.last_contact !== null &&
        flight.last_contact !== undefined &&
        Math.max(0, Math.round((now - flight.last_contact * 1000) / 1000)) <=
          recentActivityLimitSeconds);

    return (
      matchesQuery &&
      matchesAltitude &&
      matchesSpeed &&
      matchesCountry &&
      matchesOperator &&
      matchesHeading &&
      matchesGroundFilter &&
      matchesRecentActivity
    );
  });
  $: sortedFlights = sortFlights(filteredFlights, sortBy, mapViewport);
  $: displayLimit = getDisplayLimitForZoom(mapViewport?.zoom);
  $: renderedFlights = prioritizeFlightsForMap(sortedFlights, displayLimit, selectedIcao24, watchlist);
  $: watchedFlightEntries = watchlist.map((icao24) => {
    const flight = state.flights.find((candidate) => candidate.icao24 === icao24) ?? null;
    return {
      icao24,
      flight,
      isLive: Boolean(flight),
    };
  });
  $: comparisonFlights = watchedFlightEntries
    .filter((entry) => entry.flight)
    .map((entry) => entry.flight)
    .slice(0, 4);
  $: leaderboardFlights = sortFlights(filteredFlights, "speed_desc", mapViewport).slice(0, 6);
  $: airborneCount = filteredFlights.filter((flight) => !flight.on_ground).length;
  $: groundCount = Math.max(0, filteredFlights.length - airborneCount);
  $: averageSpeedKmh = filteredFlights.length
    ? Math.round(
        filteredFlights.reduce((total, flight) => total + (flight.velocity ?? 0) * 3.6, 0) /
          filteredFlights.length
      )
    : 0;
  $: activeFilterCount = countActiveFilters(filters);
  $: topOperatorSuggestions = getTopValues(replayFlights, (flight) => deriveOperatorCode(flight) || "", 4);
  $: topCountrySuggestions = getTopValues(replayFlights, (flight) => flight.origin_country ?? "", 4);
  $: activeFilterTokens = [
    filters.query.trim() ? { key: "query", label: `Search: ${filters.query.trim()}` } : null,
    filters.minAltitude ? { key: "minAltitude", label: `Min altitude ${filters.minAltitude} m` } : null,
    filters.minSpeed ? { key: "minSpeed", label: `Min speed ${filters.minSpeed} km/h` } : null,
    filters.country.trim() ? { key: "country", label: `Country: ${filters.country.trim()}` } : null,
    filters.operator.trim() ? { key: "operator", label: `Operator: ${filters.operator.trim().toUpperCase()}` } : null,
    filters.headingBand !== "any" ? { key: "headingBand", label: `Heading: ${filters.headingBand}` } : null,
    !filters.hideGroundTraffic ? { key: "ground", label: "Ground traffic visible" } : null,
    filters.recentActivity !== "any"
      ? { key: "recentActivity", label: `Recent: ${filters.recentActivity}` }
      : null,
  ].filter(Boolean);
  $: activeAlertEvents = alertEvents.slice(0, 4);
  $: compactLeaderboardFlights = leaderboardFlights.slice(0, 3);
  $: countryActivity = buildCountryActivity(filteredFlights, 3);
  $: leftBookmarks = savedViews.slice(0, 3);
  $: leftWatchPreview = watchedFlightEntries.slice(0, 3);
  $: leadFeedFlight = compactLeaderboardFlights[0] ?? null;
  $: statusLabel = getStatusLabel(state);
  $: mapCenterLabel = mapViewport?.center
    ? `${mapViewport.center[0].toFixed(2)}, ${mapViewport.center[1].toFixed(2)}`
    : "52.23, 21.01";
  $: zoomLabel = Number.isFinite(mapViewport?.zoom) ? mapViewport.zoom.toFixed(1) : "7.1";
  $: visibleTrackedCount = activeReplaySnapshot?.count ?? state.count;
  $: canStepReplayBackward =
    replaySourceSnapshots.length > 1 && (replaySnapshotIndex > 0 || replaySnapshotIndex === -1);
  $: canStepReplayForward = replaySourceSnapshots.length > 1 && replaySnapshotIndex !== -1;
  $: if (selectedIcao24 && !filteredFlights.some((flight) => flight.icao24 === selectedIcao24)) {
    selectedIcao24 = null;
  }
  $: selectedFlight = selectedIcao24
    ? sortedFlights.find((flight) => flight.icao24 === selectedIcao24) ?? null
    : null;
  $: selectedOperatorCode = selectedFlight ? deriveOperatorCode(selectedFlight) || "N/A" : "N/A";
  $: selectedFlightTrail = activeMonitoringSession
    ? replaySourceSnapshots.flatMap((snapshot) => {
        const flight = snapshot.flights.find((candidate) => candidate.icao24 === selectedIcao24);
        if (!flight) {
          return [];
        }

        return [
          {
            latitude: flight.latitude,
            longitude: flight.longitude,
            altitude: flight.altitude,
            velocity: flight.velocity,
            vertical_rate: flight.vertical_rate,
            timestamp: new Date(snapshot.fetchedAt).getTime(),
          },
        ];
      })
    : getTrailPoints(flightHistory, selectedIcao24);
  $: selectedFlightAnnotation = selectedIcao24
    ? flightAnnotations[selectedIcao24] ?? { notes: "", tags: [] }
    : { notes: "", tags: [] };
  $: selectedFlightDetailsKey = buildFlightDetailsKey(selectedFlight);
  $: if (!selectedFlightDetailsKey) {
    lastSelectedFlightDetailsKey = null;
    selectedFlightDetails = null;
    selectedFlightDetailsStatus = "idle";
    selectedFlightDetailsError = null;
  }
  $: if (selectedFlightDetailsKey && selectedFlightDetailsKey !== lastSelectedFlightDetailsKey) {
    lastSelectedFlightDetailsKey = selectedFlightDetailsKey;
    loadSelectedFlightDetails(selectedFlight);
  }
  $: if (!selectedFlight) {
    followAircraft = false;
  }
  $: if (activeReplaySnapshot && followAircraft) {
    followAircraft = false;
  }
  $: if (state.fetchedAt && state.fetchedAt !== lastAlertCheckKey && !activeReplaySnapshot) {
    lastAlertCheckKey = state.fetchedAt;
    evaluateAlertRules();
  }
  $: {
    replayPlaybackActive;
    replaySnapshotIndex;
    replaySourceSnapshots.length;
    syncReplayPlaybackTimer();
  }
  $: if (preferencesReady) {
    filters;
    sortBy;
    theme;
    mapStyle;
    selectedIcao24;
    mapViewport;
    syncShareUrl();
  }
  $: if (preferencesReady) {
    syncThemeClass(theme);
    saveUserPreferences({
      filters,
      mapStyle,
      mapViewport,
      filterPresets,
      sortBy,
      theme,
      onboardingDismissed,
      watchlist,
      watchModeEnabled,
      flightAnnotations,
      alertRules,
      alertEvents,
      monitoringSessions,
      savedViews,
    });
  }
</script>

<svelte:head>
  <title>Live Flights Radar</title>
  <meta
    name="description"
    content="Realtime aircraft tracking dashboard powered by Flask, Svelte and Leaflet."
  />
</svelte:head>

<div class="app-shell">
  <section class="radar-stage">
    <div class="map-layer">
      <FlightMap
        flights={renderedFlights}
        selectedIcao24={selectedIcao24}
        followAircraft={followAircraft}
        mapStyle={mapStyle}
        trailPoints={selectedFlightTrail}
        watchedIcao24s={watchlist}
        watchModeEnabled={watchModeEnabled}
        initialViewport={mapViewport}
        fullscreenRequestId={fullscreenRequestId}
        viewPresetRequest={viewPresetRequest}
        on:boundschange={handleBoundsChange}
        on:viewportchange={handleViewportChange}
        on:select={handleFlightSelect}
      />
    </div>

    <header class="radar-topbar">
      <div class="overlay-card center-bar">
        <div class="brand-inline">
          <div class="brand-mark">24</div>
          <div class="brand-copy">
            <strong>Live Flights</strong>
            <span>live air traffic</span>
          </div>
        </div>

        <label class="search-field">
          <span class="search-icon">⌕</span>
          <input
            bind:this={searchInput}
            bind:value={filters.query}
            type="text"
            placeholder="Find flights, airports and more"
            title="Search by callsign, ICAO24, origin country, or operator code"
          />
        </label>

        <div class="center-actions">
          <div class="status-strip compact">
            <div class:online={["success", "refreshing"].includes(state.status)} class="status-pill">
              {statusLabel}
            </div>
            <div class="status-stack">
              <strong class="status-number">{formatCompactCount(visibleTrackedCount)}</strong>
              <span class="status-inline-meta">{getConfidenceLabel(state)} · {getFreshnessLabel(state.fetchedAt)}</span>
            </div>
          </div>

          <button class="map-view-chip" type="button" on:click={() => triggerViewPreset("poland")}>
            View <strong>Map</strong>
          </button>

          <button
            class="overlay-card topbar-icon"
            type="button"
            title="Copy a link to the current map state and selected aircraft"
            on:click={copyShareLink}
          >
            ↗
          </button>
          <button class="overlay-card topbar-icon" type="button" on:click={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {theme === "dark" ? "☼" : "◐"}
          </button>

          {#if isMobileViewport}
            <button class="overlay-card topbar-icon" type="button" on:click={toggleMobileSidebar}>☰</button>
          {/if}

          {#if shareFeedback}
            <span class="share-feedback">{shareFeedback}</span>
          {/if}
        </div>
      </div>
    </header>

    <div class="floating-messages">
      {#if state.error}
        <div class="error-banner">{state.error}</div>
      {/if}

      {#if state.warning && (!state.flights.length || !["rate_limit", "cooldown"].includes(state.reason))}
        <div class="warning-banner">{state.warning}</div>
      {/if}

      {#if alertToast}
        <div class="alert-toast">{alertToast.message}</div>
      {/if}
    </div>

    <aside class="overlay-card radar-left-panel">
      <div class="panel-stack">
        <section class="widget-card">
          <div class="widget-header">
            <div class="widget-heading">
              <strong>Most tracked flights</strong>
              <span class="live-pill">LIVE</span>
            </div>
            <span class="widget-toggle">⌃</span>
          </div>

          {#if compactLeaderboardFlights.length}
            <div class="widget-list">
              {#each compactLeaderboardFlights as flight, index}
                <button class="widget-row" type="button" on:click={() => selectWatchedFlight(flight.icao24)}>
                  <span class="widget-rank">{index + 1}.</span>
                  <span class="widget-main">
                    <strong>{flight.callsign ?? flight.icao24}</strong>
                    <span class="widget-codes">
                      <small>{flight.icao24.toUpperCase()}</small>
                      {#if deriveOperatorCode(flight)}
                        <small>{deriveOperatorCode(flight)}</small>
                      {/if}
                    </span>
                    <span>{flight.origin_country ?? "Unknown"} · {formatAltitude(flight.altitude)}</span>
                  </span>
                  <span class="widget-highlight">{formatSpeed(flight.velocity).replace(" km/h", "")}</span>
                </button>
              {/each}
            </div>
          {:else}
            <p class="widget-empty">Waiting for flights in the active map view.</p>
          {/if}
        </section>

        <section class="widget-card">
          <div class="widget-header">
            <div class="widget-heading">
              <strong>Traffic hotspots</strong>
              <span class="live-pill">LIVE</span>
            </div>
            <span class="widget-toggle">⌃</span>
          </div>

          {#if countryActivity.length}
            <div class="mini-stat-list">
              {#each countryActivity as item}
                <div>
                  <span>{item.country}</span>
                  <strong>{item.count}</strong>
                  <small>{item.averageSpeed} km/h · {item.ground} ground</small>
                </div>
              {/each}
            </div>
          {:else}
            <p class="widget-empty">Traffic activity appears here after the first snapshot.</p>
          {/if}

          <button class="widget-footer-button" type="button" on:click={() => openInspectorTab("traffic")}>
            Open traffic list
          </button>
        </section>

        <section class="widget-card compact collapsed">
          <div class="widget-header">
            <div class="widget-heading">
              <strong>Bookmarks</strong>
              <span class="widget-ghost">{leftBookmarks.length || leftWatchPreview.length}</span>
            </div>
            <span class="widget-toggle">⌃</span>
          </div>

          {#if leftBookmarks.length}
            <div class="widget-chip-list">
              {#each leftBookmarks as view}
                <button class="bookmark-chip" type="button" on:click={() => loadSavedView(view.id)}>
                  {view.name}
                </button>
              {/each}
            </div>
          {:else if leftWatchPreview.length}
            <div class="widget-chip-list">
              {#each leftWatchPreview as entry}
                <button class="bookmark-chip" type="button" on:click={() => selectWatchedFlight(entry.icao24)}>
                  {entry.flight?.callsign ?? entry.icao24}
                </button>
              {/each}
            </div>
          {:else}
            <p class="widget-empty">Save a view or add aircraft to watchlist.</p>
          {/if}
        </section>
      </div>
    </aside>

    {#if isMobileViewport && mobileSidebarOpen}
      <button class="sidebar-backdrop" type="button" aria-label="Close panel" on:click={closeMobileSidebar}></button>
    {/if}

    <aside class:open={mobileSidebarOpen} class="overlay-card radar-right-panel">
      <div class="rail-header">
        <div class="rail-brand">
          <span>liveflights</span>
          <strong>24</strong>
        </div>
        <button
          class="rail-close"
          type="button"
          aria-label="Close selected aircraft"
          on:click={() => {
            selectedIcao24 = null;
            if (isMobileViewport) {
              closeMobileSidebar();
            }
          }}
        >
          ×
        </button>
      </div>

      {#if !selectedFlight && inspectorTab === "details" && !isMobileViewport}
        <div class="feed-rail">
          <section class="feed-hero">
            <div class="feed-hero-media">
              <div class="feed-plane-mark">✈</div>
            </div>
            <div class="feed-hero-copy">
              <strong>{leadFeedFlight ? leadFeedFlight.callsign ?? leadFeedFlight.icao24 : `Traffic around ${mapCenterLabel}`}</strong>
              <p>
                {leadFeedFlight
                  ? `${leadFeedFlight.origin_country ?? "Unknown country"} · ${formatAltitude(leadFeedFlight.altitude)} · ${formatSpeed(leadFeedFlight.velocity)}`
                  : `${visibleTrackedCount} tracked aircraft in the active radar view.`}
              </p>
            </div>
          </section>

          <article class="promo-card">
            <div>
              <strong>Open live traffic list</strong>
              <p>Jump into the densest flights, then narrow the map with fast filters.</p>
            </div>
            <button class="promo-action" type="button" on:click={() => openInspectorTab("traffic")}>
              Open list
            </button>
          </article>

          <article class="feed-card emphasis">
            <div class="feed-card-icon">◎</div>
            <div>
              <strong>Use radar filters</strong>
              <p>Sort flights by speed, altitude and recent movement to clean up the map.</p>
            </div>
          </article>

          <article class="feed-card">
            <div class="feed-card-icon">▶</div>
            <div>
              <strong>Playback session history</strong>
              <p>Replay captured snapshots and jump back to live traffic in one click.</p>
            </div>
          </article>

          <article class="feed-card">
            <div class="feed-card-icon">★</div>
            <div>
              <strong>Saved views and watchlist</strong>
              <p>Pin aircraft, keep workspaces, and reopen the same radar setup later.</p>
            </div>
          </article>

          <article class="feed-card">
            <div class="feed-card-icon">!</div>
            <div>
              <strong>Alert matching</strong>
              <p>Create callsign or ICAO alerts and let the panel keep a short event log.</p>
            </div>
          </article>
        </div>
      {:else}
        <div class="inspector-header">
          <div class="inspector-title">
            <p class="section-kicker">{selectedFlight ? "Selected aircraft" : "Traffic inspector"}</p>
            <h2>{selectedFlight ? selectedFlight.callsign ?? selectedFlight.icao24 : "No flight selected"}</h2>
            <p class="inspector-subtitle">
              {selectedFlight
                ? `${selectedFlight.origin_country ?? "Unknown country"} · operator ${selectedOperatorCode}`
                : "Choose an aircraft marker or use the tabs below to manage the radar."}
            </p>
          </div>
          {#if isMobileViewport}
            <button class="mobile-sidebar-close" type="button" on:click={closeMobileSidebar}>Close</button>
          {/if}
        </div>

        {#if selectedFlight}
          <section class="flight-hero">
            <div class="flight-hero-header">
              <div>
                <span class="hero-tag">{selectedFlight.on_ground ? "Ground" : "Airborne"}</span>
                <strong>{selectedFlight.callsign ?? selectedFlight.icao24}</strong>
              </div>
              <div class="hero-actions">
                <button class:active={followAircraft} class="hero-action" type="button" on:click={toggleFollowAircraft}>
                  {followAircraft ? "Following" : "Follow"}
                </button>
                <button
                  class:active={selectedFlight ? watchlist.includes(selectedFlight.icao24) : false}
                  class="hero-action primary"
                  type="button"
                  on:click={toggleSelectedFlightWatchlist}
                >
                  {selectedFlight && watchlist.includes(selectedFlight.icao24) ? "Watching" : "Watch"}
                </button>
              </div>
            </div>

            <div class="hero-metrics">
              <article class="hero-metric">
                <span>Altitude</span>
                <strong>{formatAltitude(selectedFlight.altitude)}</strong>
              </article>
              <article class="hero-metric">
                <span>Speed</span>
                <strong>{formatSpeed(selectedFlight.velocity)}</strong>
              </article>
              <article class="hero-metric">
                <span>Heading</span>
                <strong>{formatHeading(selectedFlight.true_track)}</strong>
              </article>
              <article class="hero-metric">
                <span>ICAO24</span>
                <strong>{selectedFlight.icao24}</strong>
              </article>
            </div>
          </section>
        {/if}

        <div class="inspector-tabs" role="tablist" aria-label="Radar inspector">
          <button class:active={inspectorTab === "details"} class="inspector-tab" type="button" on:click={() => openInspectorTab("details")}>
            Aircraft
          </button>
          <button class:active={inspectorTab === "filters"} class="inspector-tab" type="button" on:click={() => openInspectorTab("filters")}>
            Filters
          </button>
          <button class:active={inspectorTab === "traffic"} class="inspector-tab" type="button" on:click={() => openInspectorTab("traffic")}>
            Traffic
          </button>
          <button class:active={inspectorTab === "watchlist"} class="inspector-tab" type="button" on:click={() => openInspectorTab("watchlist")}>
            Watchlist
          </button>
          <button class:active={inspectorTab === "replay"} class="inspector-tab" type="button" on:click={() => openInspectorTab("replay")}>
            Playback
          </button>
          <button class:active={inspectorTab === "views"} class="inspector-tab" type="button" on:click={() => openInspectorTab("views")}>
            Views
          </button>
          <button class:active={inspectorTab === "alerts"} class="inspector-tab" type="button" on:click={() => openInspectorTab("alerts")}>
            Alerts
          </button>
          <button class:active={inspectorTab === "help"} class="inspector-tab" type="button" on:click={() => openInspectorTab("help")}>
            Help
          </button>
        </div>

        <div class="inspector-scroll">
          {#if inspectorTab === "details"}
            <FlightDetailsPanel
              flight={selectedFlight}
              details={selectedFlightDetails}
              detailsStatus={selectedFlightDetailsStatus}
              detailsError={selectedFlightDetailsError}
              followAircraft={followAircraft}
              trailPoints={selectedFlightTrail}
              isWatched={selectedFlight ? watchlist.includes(selectedFlight.icao24) : false}
              onToggleFollow={toggleFollowAircraft}
              onToggleWatch={toggleSelectedFlightWatchlist}
              onRetryDetails={retrySelectedFlightDetails}
            />
        {:else if inspectorTab === "traffic"}
          <TrafficBoardPanel
            flights={sortedFlights}
            selectedIcao24={selectedIcao24}
            viewport={mapViewport}
            title="Traffic list"
            subtitle="Current radar traffic"
            maxRows={24}
            onSelectFlight={selectWatchedFlight}
          />
        {:else if inspectorTab === "filters"}
          <section class="panel inspector-panel">
            <div class="card-header">
              <div>
                <p class="section-kicker">Search and filters</p>
                <h2>Traffic shaping</h2>
              </div>
              <span class="card-badge">{activeFilterCount}</span>
            </div>

            <label class="field">
              <span>Search query</span>
              <input
                bind:value={filters.query}
                type="text"
                placeholder="callsign, ICAO24, country, operator"
              />
            </label>

            <div class="filter-cluster">
              <div class="cluster-header">
                <strong>Quick presets</strong>
                <span>One click traffic shaping</span>
              </div>
              <div class="chip-list filter-chip-list">
                <button class="tool-chip" type="button" on:click={() => applyQuickFilter("reset")}>All traffic</button>
                <button class="tool-chip" type="button" on:click={() => applyQuickFilter("fast")}>Fast movers</button>
                <button class="tool-chip" type="button" on:click={() => applyQuickFilter("high")}>High altitude</button>
                <button class="tool-chip" type="button" on:click={() => applyQuickFilter("recent")}>Recent only</button>
                <button class="tool-chip" type="button" on:click={() => applyQuickFilter("ground")}>Include ground</button>
              </div>
            </div>

            {#if activeFilterTokens.length}
              <div class="filter-cluster">
                <div class="cluster-header">
                  <strong>Active filters</strong>
                  <span>{activeFilterTokens.length} active</span>
                </div>
                <div class="active-filter-list">
                  {#each activeFilterTokens as token}
                    <button class="active-filter-chip" type="button" on:click={() => clearFilterToken(token.key)}>
                      {token.label} ×
                    </button>
                  {/each}
                </div>
              </div>
            {/if}

            {#if topOperatorSuggestions.length || topCountrySuggestions.length}
              <div class="filter-cluster">
                <div class="cluster-header">
                  <strong>Live suggestions</strong>
                  <span>Built from current traffic</span>
                </div>

                {#if topOperatorSuggestions.length}
                  <div class="suggestion-group">
                    <span class="suggestion-label">Operators</span>
                    <div class="active-filter-list">
                      {#each topOperatorSuggestions as operator}
                        <button class="suggestion-chip" type="button" on:click={() => (filters = { ...filters, operator })}>
                          {operator}
                        </button>
                      {/each}
                    </div>
                  </div>
                {/if}

                {#if topCountrySuggestions.length}
                  <div class="suggestion-group">
                    <span class="suggestion-label">Countries</span>
                    <div class="active-filter-list">
                      {#each topCountrySuggestions as country}
                        <button class="suggestion-chip" type="button" on:click={() => (filters = { ...filters, country })}>
                          {country}
                        </button>
                      {/each}
                    </div>
                  </div>
                {/if}
              </div>
            {/if}

            <label class="field">
              <span>Sort by</span>
              <select bind:value={sortBy}>
                <option value="altitude_desc">Altitude</option>
                <option value="speed_desc">Speed</option>
                <option value="distance_asc">Distance from map center</option>
                <option value="last_contact_desc">Last update</option>
              </select>
            </label>

            <label class="field">
              <span>Min altitude (m)</span>
              <input bind:value={filters.minAltitude} type="number" min="0" step="100" />
            </label>

            <label class="field">
              <span>Min speed (km/h)</span>
              <input bind:value={filters.minSpeed} type="number" min="0" step="10" />
            </label>

            <label class="field">
              <span>Country</span>
              <input bind:value={filters.country} type="text" placeholder="Poland, Germany, Turkey" />
            </label>

            <label class="field">
              <span>Operator code</span>
              <input bind:value={filters.operator} type="text" placeholder="LOT, RYR, WZZ" />
            </label>

            <label class="field">
              <span>Heading</span>
              <select bind:value={filters.headingBand}>
                <option value="any">Any direction</option>
                <option value="north">Northbound</option>
                <option value="east">Eastbound</option>
                <option value="south">Southbound</option>
                <option value="west">Westbound</option>
              </select>
            </label>

            <label class="checkbox-field">
              <input bind:checked={filters.hideGroundTraffic} type="checkbox" />
              <span>Hide ground traffic</span>
            </label>

            <label class="field">
              <span>Recent activity</span>
              <select bind:value={filters.recentActivity}>
                <option value="any">Any time</option>
                <option value="30s">Last 30 seconds</option>
                <option value="2m">Last 2 minutes</option>
                <option value="5m">Last 5 minutes</option>
                <option value="15m">Last 15 minutes</option>
              </select>
            </label>

            <div class="filter-actions">
              <button class="reset-button" type="button" on:click={resetFilters}>Reset filters</button>

              <div class="preset-save-row">
                <input
                  bind:value={presetName}
                  type="text"
                  placeholder="preset name"
                  on:keydown={(event) => event.key === "Enter" && saveCurrentPreset()}
                />
                <button class="secondary-button" type="button" on:click={saveCurrentPreset}>Save preset</button>
              </div>

              {#if filterPresets.length}
                <div class="preset-list">
                  {#each filterPresets as preset}
                    <div class="preset-item">
                      <button class="secondary-button preset-load" type="button" on:click={() => applyFilterPreset(preset)}>
                        {preset.name}
                      </button>
                      <button class="preset-delete" type="button" on:click={() => deleteFilterPreset(preset.name)}>
                        Remove
                      </button>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </section>
        {:else if inspectorTab === "watchlist"}
          <WatchlistPanel
            entries={watchedFlightEntries}
            selectedIcao24={selectedIcao24}
            watchModeEnabled={watchModeEnabled}
            onToggleWatchMode={toggleWatchMode}
            onSelectFlight={selectWatchedFlight}
            onRemoveFlight={removeFromWatchlist}
          />

          <ComparisonPanel flights={comparisonFlights} selectedIcao24={selectedIcao24} onSelectFlight={selectWatchedFlight} />
        {:else if inspectorTab === "replay"}
          <ReplayTimeline
            snapshots={replaySourceSnapshots}
            activeSnapshot={activeReplaySnapshot}
            activeIndex={replaySnapshotIndex}
            isPlaying={replayPlaybackActive}
            canStepBackward={canStepReplayBackward}
            canStepForward={canStepReplayForward}
            onSelectIndex={selectReplaySnapshot}
            onReturnToLive={returnToLiveReplay}
            onStepBackward={() => stepReplay(-1)}
            onStepForward={() => stepReplay(1)}
            onTogglePlayback={toggleReplayPlayback}
          />

          <MonitoringSessionsPanel
            sessions={monitoringSessions}
            activeSessionId={activeMonitoringSessionId}
            onSaveSession={saveCurrentMonitoringSession}
            onLoadSession={loadMonitoringSession}
            onDeleteSession={deleteMonitoringSession}
          />
        {:else if inspectorTab === "views"}
          <SavedViewsPanel
            views={savedViews}
            activeViewId={activeSavedViewId}
            currentName={savedViewName}
            onNameChange={(value) => (savedViewName = value)}
            onSaveView={saveCurrentView}
            onLoadView={loadSavedView}
            onDeleteView={deleteSavedView}
          />
        {:else if inspectorTab === "alerts"}
          <AlertPanel
            rules={alertRules}
            events={alertEvents}
            onAddRule={addAlertRule}
            onRemoveRule={removeAlertRule}
            onClearEvents={clearAlertEvents}
          />
        {:else}
          <LegendPanel />
          <ShortcutsPanel />
        {/if}
        </div>
      {/if}
    </aside>

    <nav class="overlay-card bottom-dock" aria-label="Quick radar actions">
      <button class:active={inspectorTab === "help"} class="dock-button" type="button" on:click={() => openInspectorTab("help")}>
        Settings
      </button>
      <button class:active={mapStyle === "dark" || mapStyle === "satellite"} class="dock-button" type="button" on:click={cycleMapStyle}>
        Layers
      </button>
      <button class:active={inspectorTab === "filters"} class="dock-button" type="button" on:click={() => openInspectorTab("filters")}>
        Filters
      </button>
      <button class:active={inspectorTab === "traffic"} class="dock-button" type="button" on:click={() => openInspectorTab("traffic")}>
        Traffic
      </button>
      <button class:active={inspectorTab === "replay"} class="dock-button" type="button" on:click={() => openInspectorTab("replay")}>
        Playback
      </button>
    </nav>
  </section>
</div>

<style>
  .app-shell {
    min-height: 100vh;
  }

  .radar-stage {
    position: relative;
    min-height: 100vh;
    overflow: hidden;
  }

  .map-layer {
    position: absolute;
    inset: 0;
  }

  .overlay-card {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 22px;
    background:
      linear-gradient(180deg, rgba(43, 46, 52, 0.94) 0%, rgba(25, 28, 33, 0.94) 100%);
    backdrop-filter: blur(18px);
    box-shadow:
      0 20px 50px rgba(0, 0, 0, 0.34),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);
  }

  .radar-topbar,
  .radar-left-panel,
  .radar-right-panel,
  .bottom-dock,
  .floating-messages {
    position: absolute;
    z-index: 1100;
  }

  .radar-topbar {
    top: 0.95rem;
    left: 1rem;
    right: 1rem;
    display: flex;
    align-items: start;
    justify-content: center;
    gap: 0.9rem;
  }

  .center-bar {
    display: grid;
    grid-template-columns: auto minmax(250px, 1fr) auto;
    align-items: center;
    gap: 0.8rem;
    width: min(930px, calc(100vw - 39rem));
    min-width: 520px;
    padding: 0.55rem 0.7rem;
  }

  .brand-inline {
    display: flex;
    align-items: center;
    gap: 0.7rem;
  }

  .brand-mark {
    display: grid;
    place-items: center;
    width: 2.6rem;
    height: 2.6rem;
    border-radius: 999px;
    font-size: 1rem;
    font-weight: 900;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .brand-copy strong,
  .card-header h2,
  .inspector-title h2 {
    display: block;
    margin: 0;
    font-size: 1.05rem;
    font-weight: 800;
    color: #f6f8fb;
  }

  .brand-copy span {
    display: block;
    margin-top: 0.08rem;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #aeb9c7;
  }

  .section-kicker {
    margin: 0 0 0.22rem;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #f5b908;
  }

  .search-field {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.55rem;
    min-width: 0;
    padding: 0 0.15rem;
  }

  .search-icon {
    color: rgba(225, 231, 241, 0.58);
    font-size: 0.95rem;
  }

  .search-field input {
    width: 100%;
    border: 0;
    padding: 0.28rem 0;
    font: inherit;
    font-size: 0.98rem;
    color: #f6f8fb;
    background: transparent;
    outline: none;
  }

  .search-field input::placeholder {
    color: rgba(225, 231, 241, 0.58);
  }

  .center-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.55rem;
    align-items: center;
  }

  .status-strip {
    display: flex;
    gap: 0.6rem;
    align-items: center;
    padding: 0.38rem 0.48rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.04);
  }

  .status-strip.compact {
    min-width: 0;
  }

  .status-stack {
    display: grid;
    gap: 0.12rem;
  }

  .share-feedback,
  .inspector-subtitle {
    font-size: 0.78rem;
    color: #aeb9c7;
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.38rem 0.62rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #e6eaf0;
    background: rgba(255, 255, 255, 0.07);
    white-space: nowrap;
  }

  .status-pill.online {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .status-inline-meta {
    white-space: nowrap;
  }

  .status-number {
    color: #f6f8fb;
    font-size: 0.88rem;
    line-height: 1;
  }

  .map-view-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.58rem 0.8rem;
    font: inherit;
    font-weight: 700;
    color: #f6f8fb;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
  }

  .topbar-icon,
  .tool-chip,
  .dock-button,
  .mobile-sidebar-close,
  .hero-action,
  .reset-button,
  .secondary-button,
  .preset-delete {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.68rem 0.9rem;
    font: inherit;
    font-weight: 700;
    color: #f6f8fb;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
    transition:
      background 160ms ease,
      border-color 160ms ease,
      transform 160ms ease;
  }

  .hero-action.primary,
  .reset-button,
  .dock-button.active {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .topbar-icon {
    display: grid;
    place-items: center;
    width: 2.45rem;
    height: 2.45rem;
    padding: 0;
    border-radius: 14px;
    flex: 0 0 auto;
  }

  .mobile-sidebar-close {
    padding-inline: 1rem;
  }

  .floating-messages {
    top: 5.25rem;
    left: 50%;
    transform: translateX(-50%);
    display: grid;
    gap: 0.55rem;
    width: min(680px, calc(100vw - 2rem));
  }

  .error-banner,
  .warning-banner,
  .alert-toast {
    padding: 0.8rem 1rem;
    border-radius: 16px;
    backdrop-filter: blur(14px);
    box-shadow: 0 16px 34px rgba(0, 0, 0, 0.24);
  }

  .error-banner {
    color: #ffdada;
    background: rgba(120, 33, 33, 0.85);
  }

  .warning-banner {
    color: #ffe0a1;
    background: rgba(115, 76, 18, 0.85);
  }

  .alert-toast {
    color: #daf5df;
    background: rgba(23, 92, 48, 0.85);
  }

  .radar-left-panel,
  .radar-right-panel {
    top: 5.9rem;
    bottom: 5.55rem;
    width: min(18.25rem, calc(100vw - 2rem));
    padding: 0.85rem;
    overflow: hidden;
  }

  .radar-left-panel {
    left: 1rem;
    background:
      linear-gradient(180deg, rgba(36, 39, 45, 0.95) 0%, rgba(24, 27, 31, 0.95) 100%);
  }

  .radar-right-panel {
    right: 1rem;
    width: min(18rem, calc(100vw - 2rem));
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    gap: 0.75rem;
    background:
      linear-gradient(180deg, rgba(19, 20, 24, 0.98) 0%, rgba(9, 10, 13, 0.98) 100%);
  }

  .panel-stack,
  .inspector-scroll {
    display: grid;
    gap: 0.9rem;
    min-height: 0;
    overflow-y: auto;
    padding-right: 0.15rem;
  }

  .inspector-panel,
  .flight-hero {
    padding: 1rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
    margin-bottom: 0.8rem;
  }

  .card-badge,
  .hero-tag {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2rem;
    padding: 0.28rem 0.58rem;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 800;
    color: #16191f;
    background: #ffd34f;
  }

  .widget-card {
    display: grid;
    gap: 0.68rem;
    padding: 0.82rem;
    border-radius: 18px;
    background:
      linear-gradient(180deg, rgba(55, 58, 64, 0.96) 0%, rgba(38, 41, 46, 0.96) 100%);
    box-shadow:
      0 14px 28px rgba(0, 0, 0, 0.28),
      inset 3px 0 0 #f5b908;
  }

  .widget-card.compact {
    padding-block: 0.75rem;
  }

  .widget-card.collapsed {
    gap: 0.6rem;
  }

  .widget-header {
    display: flex;
    justify-content: space-between;
    gap: 0.7rem;
    align-items: center;
  }

  .widget-heading {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    min-width: 0;
  }

  .widget-header strong,
  .widget-main strong,
  .feed-hero-copy strong,
  .feed-card strong,
  .promo-card strong {
    color: #f6f8fb;
  }

  .widget-toggle {
    color: #aab5c3;
    font-size: 0.82rem;
  }

  .live-pill,
  .widget-ghost {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2rem;
    padding: 0.25rem 0.45rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 800;
  }

  .live-pill {
    color: #171a1f;
    background: #f5b908;
  }

  .widget-ghost {
    color: #aeb9c7;
    background: rgba(255, 255, 255, 0.07);
  }

  .widget-list,
  .widget-chip-list,
  .feed-rail {
    display: grid;
    gap: 0.6rem;
  }

  .widget-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.6rem;
    align-items: center;
    width: 100%;
    padding: 0.72rem 0.65rem;
    border: 0;
    border-radius: 12px;
    color: inherit;
    background: rgba(0, 0, 0, 0.18);
    text-align: left;
    cursor: pointer;
  }

  .widget-rank {
    color: #d9dde4;
    font-weight: 800;
    font-size: 0.9rem;
  }

  .widget-main {
    display: grid;
    gap: 0.15rem;
  }

  .widget-codes {
    display: flex;
    flex-wrap: wrap;
    gap: 0.28rem;
  }

  .widget-codes small {
    padding: 0.08rem 0.34rem;
    border-radius: 6px;
    font-size: 0.64rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #d8e0ea;
    background: rgba(255, 255, 255, 0.08);
  }

  .widget-main span,
  .widget-empty,
  .feed-hero-copy p,
  .feed-card p,
  .promo-card p {
    font-size: 0.78rem;
    color: #aeb9c7;
  }

  .widget-highlight {
    font-size: 1rem;
    font-weight: 900;
    color: #f5b908;
  }

  .mini-stat-list {
    display: grid;
    gap: 0.55rem;
  }

  .mini-stat-list div {
    display: flex;
    justify-content: space-between;
    gap: 0.7rem;
    align-items: center;
    padding: 0.62rem 0.7rem;
    border-radius: 12px;
    background: rgba(0, 0, 0, 0.18);
  }

  .mini-stat-list span {
    font-size: 0.8rem;
    color: #aeb9c7;
  }

  .mini-stat-list strong {
    color: #f6f8fb;
  }

  .widget-footer-button,
  .bookmark-chip {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 0.62rem 0.78rem;
    font: inherit;
    font-weight: 700;
    color: #f6f8fb;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
  }

  .feed-rail {
    align-content: start;
    min-height: 0;
    overflow-y: auto;
    padding-right: 0.1rem;
  }

  .rail-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
    padding: 0.1rem 0.1rem 0.25rem;
  }

  .rail-brand {
    display: flex;
    align-items: center;
    gap: 0.1rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #eef3f8;
  }

  .rail-brand span {
    color: #eef3f8;
    opacity: 0.92;
  }

  .rail-brand strong {
    color: #f5b908;
  }

  .rail-close {
    border: 0;
    padding: 0;
    font: inherit;
    font-size: 1.5rem;
    line-height: 1;
    color: #c8d0db;
    background: transparent;
    cursor: pointer;
  }

  .feed-hero,
  .feed-card,
  .promo-card {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.8rem;
    padding: 0.88rem;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.035);
  }

  .feed-hero {
    grid-template-columns: 1fr;
    overflow: hidden;
    background:
      linear-gradient(180deg, rgba(61, 70, 79, 0.96) 0%, rgba(33, 37, 42, 0.96) 100%);
  }

  .promo-card {
    grid-template-columns: 1fr;
    gap: 0.7rem;
    border: 1px solid rgba(96, 206, 124, 0.18);
    background:
      linear-gradient(180deg, rgba(33, 51, 36, 0.98) 0%, rgba(25, 37, 27, 0.98) 100%);
  }

  .promo-action {
    border: 0;
    border-radius: 999px;
    padding: 0.72rem 0.8rem;
    font: inherit;
    font-weight: 800;
    color: #f4fff6;
    background: linear-gradient(180deg, #63d77e 0%, #48ba64 100%);
    cursor: pointer;
  }

  .feed-hero-media {
    display: grid;
    place-items: center;
    min-height: 7.8rem;
    border-radius: 16px;
    background:
      linear-gradient(135deg, rgba(167, 179, 191, 0.18), rgba(54, 61, 68, 0.1)),
      radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.16), transparent 32%);
  }

  .feed-plane-mark {
    font-size: 4rem;
    color: rgba(245, 248, 252, 0.85);
    transform: rotate(-8deg);
  }

  .feed-card.emphasis {
    border: 1px solid rgba(245, 185, 8, 0.22);
  }

  .feed-card-icon {
    display: grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    font-size: 0.92rem;
    font-weight: 800;
    color: #d9dde4;
    background: rgba(255, 255, 255, 0.08);
  }

  .hero-metric strong {
    color: #f6f8fb;
  }

  .hero-metric span,
  .field span,
  .checkbox-field span {
    color: #aeb9c7;
    font-size: 0.78rem;
  }

  .hero-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.65rem;
    margin-bottom: 0.8rem;
  }

  .hero-metric {
    display: grid;
    gap: 0.2rem;
    padding: 0.8rem 0.85rem;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.04);
  }

  .chip-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .inspector-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
  }

  .inspector-title h2 {
    font-size: 1.2rem;
  }

  .inspector-title p {
    margin: 0;
  }

  .flight-hero {
    display: grid;
    gap: 0.85rem;
    border-radius: 20px;
    background:
      radial-gradient(circle at top right, rgba(245, 185, 8, 0.2), transparent 35%),
      linear-gradient(180deg, rgba(39, 42, 48, 0.98) 0%, rgba(26, 28, 33, 0.98) 100%);
  }

  .flight-hero-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
  }

  .flight-hero-header strong {
    display: block;
    margin-top: 0.3rem;
    font-size: 1.15rem;
    color: #f6f8fb;
  }

  .hero-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    justify-content: flex-end;
  }

  .hero-action.active {
    border-color: rgba(245, 185, 8, 0.65);
  }

  .inspector-tabs {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.45rem;
  }

  .inspector-tab {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 0.72rem 0.6rem;
    font: inherit;
    font-size: 0.8rem;
    font-weight: 700;
    color: #dce4ef;
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
  }

  .inspector-tab.active {
    color: #171a1f;
    background: #ffd34f;
    border-color: transparent;
  }

  .field,
  .checkbox-field,
  .filter-actions,
  .preset-list {
    display: grid;
    gap: 0.55rem;
  }

  .filter-cluster,
  .suggestion-group {
    display: grid;
    gap: 0.55rem;
  }

  .filter-cluster {
    padding: 0.9rem;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.03);
  }

  .cluster-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: start;
  }

  .cluster-header strong,
  .suggestion-label {
    color: #f6f8fb;
    font-size: 0.84rem;
  }

  .cluster-header span,
  .suggestion-label {
    color: #aeb9c7;
  }

  .filter-chip-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .active-filter-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .active-filter-chip,
  .suggestion-chip {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.55rem 0.8rem;
    font: inherit;
    font-size: 0.82rem;
    font-weight: 700;
    color: #f6f8fb;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
  }

  .suggestion-chip {
    color: #f7db7a;
    background: rgba(245, 185, 8, 0.08);
    border-color: rgba(245, 185, 8, 0.22);
  }

  .field input,
  .field select,
  .preset-save-row input {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 0.78rem 0.9rem;
    font: inherit;
    color: #f6f8fb;
    background: rgba(255, 255, 255, 0.04);
  }

  .checkbox-field {
    grid-template-columns: auto 1fr;
    align-items: center;
  }

  .checkbox-field input {
    accent-color: #f5b908;
  }

  .preset-save-row,
  .preset-item {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.55rem;
  }

  .preset-load {
    text-align: left;
  }

  .bottom-dock {
    left: 50%;
    bottom: 1rem;
    transform: translateX(-50%);
    display: flex;
    flex-wrap: nowrap;
    gap: 0.35rem;
    width: min(28.5rem, calc(100vw - 2rem));
    padding: 0.35rem;
    justify-content: center;
  }

  .dock-button {
    flex: 1 1 0;
    border-radius: 14px;
    padding: 0.58rem 0.45rem;
    font-size: 0.88rem;
  }

  .sidebar-backdrop {
    display: none;
  }

  :global(.panel-stack::-webkit-scrollbar),
  :global(.inspector-scroll::-webkit-scrollbar) {
    width: 10px;
  }

  :global(.panel-stack::-webkit-scrollbar-thumb),
  :global(.inspector-scroll::-webkit-scrollbar-thumb) {
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
  }

  @media (max-width: 1200px) {
    .radar-topbar {
      justify-content: flex-start;
    }

    .center-bar {
      width: calc(100vw - 20rem);
      min-width: 0;
    }
  }

  @media (max-width: 960px) {
    .radar-left-panel {
      display: none;
    }

    .radar-right-panel {
      top: 5.1rem;
      right: 0.75rem;
      bottom: 5.7rem;
      left: 0.75rem;
      width: auto;
      transform: translateY(110%);
      transition: transform 180ms ease;
      z-index: 1300;
    }

    .radar-right-panel.open {
      transform: translateY(0);
    }

    .sidebar-backdrop {
      display: block;
      position: absolute;
      inset: 0;
      z-index: 1250;
      border: 0;
      background: rgba(5, 8, 12, 0.56);
    }

    .bottom-dock {
      left: 0.75rem;
      right: 0.75rem;
      width: auto;
      transform: none;
    }

    .inspector-tabs,
    .chip-list,
    .hero-metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 720px) {
    .radar-topbar {
      top: 0.75rem;
      left: 0.75rem;
      right: 0.75rem;
      gap: 0.65rem;
      display: grid;
    }

    .center-bar {
      grid-template-columns: 1fr;
      width: auto;
      padding: 0.75rem 0.85rem;
    }

    .status-strip {
      padding: 0.42rem 0.5rem;
    }

    .center-actions {
      justify-content: flex-start;
      flex-wrap: wrap;
    }

    .inspector-tabs {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .flight-hero-header,
    .card-header,
    .cluster-header {
      display: grid;
    }

    .preset-save-row,
    .preset-item {
      grid-template-columns: 1fr;
    }

    .bottom-dock {
      flex-wrap: wrap;
    }

    .dock-button {
      min-width: 7.5rem;
      font-size: 0.82rem;
    }
  }
</style>
