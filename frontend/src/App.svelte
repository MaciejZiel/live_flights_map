<script>
  import { onMount } from "svelte";

  import FlightDetailsPanel from "./lib/components/FlightDetailsPanel.svelte";
  import TrafficBoardPanel from "./lib/components/TrafficBoardPanel.svelte";
  import WatchlistPanel from "./lib/components/WatchlistPanel.svelte";
  import ReplayTimeline from "./lib/components/ReplayTimeline.svelte";
  import AlertPanel from "./lib/components/AlertPanel.svelte";
  import ComparisonPanel from "./lib/components/ComparisonPanel.svelte";
  import FlightMap from "./lib/components/FlightMap.svelte";
  import LegendPanel from "./lib/components/LegendPanel.svelte";
  import MonitoringSessionsPanel from "./lib/components/MonitoringSessionsPanel.svelte";
  import OnboardingPanel from "./lib/components/OnboardingPanel.svelte";
  import SavedViewsPanel from "./lib/components/SavedViewsPanel.svelte";
  import ShortcutsPanel from "./lib/components/ShortcutsPanel.svelte";
  import {
    fetchFlightDetails,
    fetchGlobalTrafficBoard,
    fetchFlightTrail,
    fetchReplayHistory,
    searchFlights,
  } from "./lib/api/flights.js";
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
  let flightFocusRequest = null;
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
  let mobileUtilityOpen = false;
  let inspectorScroll;
  let sidebarMode = "traffic";
  let utilityPanelMode = "overview";
  let inspectorTab = "details";
  let snapshotHistory = [];
  let replaySnapshotCursor = null;
  let lastReplaySnapshotKey = null;
  let replayPlaybackActive = false;
  let replayPlaybackTimer = null;
  let lastInspectorScrollFlightKey = null;
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
  let flightTrailCache = new Map();
  let selectedFlightDetails = null;
  let selectedFlightDetailsStatus = "idle";
  let selectedFlightDetailsError = null;
  let selectedFlightDetailsRequestId = 0;
  let lastSelectedFlightDetailsKey = null;
  let selectedFlightTrailRemote = [];
  let selectedFlightTrailStatus = "idle";
  let selectedFlightTrailError = null;
  let selectedFlightTrailRequestId = 0;
  let lastSelectedFlightTrailKey = null;
  let selectedTagDraft = "";
  let archivedReplayStatus = "idle";
  let archivedReplayError = null;
  let archivedReplayRequestId = 0;
  let lastArchivedReplayBboxKey = null;
  let replayHydrationTimer = null;
  let remoteSearchResults = [];
  let remoteSearchStatus = "idle";
  let remoteSearchError = null;
  let remoteSearchRequestId = 0;
  let searchDebounceTimer = null;
  let pendingSearchSelection = null;
  let selectedFlightSnapshot = null;
  let globalTrafficBoard = {
    status: "idle",
    flights: [],
    error: null,
    fetchedAt: null,
    count: 0,
    warning: null,
    source: "idle",
    meta: {},
  };
  let globalTrafficBoardRequestId = 0;
  let globalTrafficBoardTimer = null;

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
    refreshGlobalTrafficBoard();
    globalTrafficBoardTimer = window.setInterval(() => {
      refreshGlobalTrafficBoard();
    }, 90000);
    window.addEventListener("keydown", handleKeyboardShortcut);
    const mobileViewportQuery = window.matchMedia("(max-width: 960px)");
    const syncViewportMode = (event) => {
      isMobileViewport = event.matches;
      mobileSidebarOpen = !event.matches;
      mobileUtilityOpen = false;
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
      if (replayHydrationTimer) {
        window.clearTimeout(replayHydrationTimer);
      }
      if (searchDebounceTimer) {
        window.clearTimeout(searchDebounceTimer);
      }
      if (globalTrafficBoardTimer) {
        window.clearInterval(globalTrafficBoardTimer);
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

  function buildSelectedFlightSnapshot(flight) {
    if (!flight?.icao24) {
      return null;
    }

    return {
      ...flight,
      icao24: String(flight.icao24).trim().toLowerCase(),
    };
  }

  function shouldRefreshSelectedFlightSnapshot(currentSnapshot, nextFlight) {
    if (!nextFlight?.icao24) {
      return false;
    }

    if (!currentSnapshot || currentSnapshot.icao24 !== nextFlight.icao24) {
      return true;
    }

    return (
      currentSnapshot.callsign !== nextFlight.callsign ||
      currentSnapshot.registration !== nextFlight.registration ||
      currentSnapshot.type_code !== nextFlight.type_code ||
      currentSnapshot.origin_country !== nextFlight.origin_country ||
      currentSnapshot.latitude !== nextFlight.latitude ||
      currentSnapshot.longitude !== nextFlight.longitude ||
      currentSnapshot.altitude !== nextFlight.altitude ||
      currentSnapshot.velocity !== nextFlight.velocity ||
      currentSnapshot.vertical_rate !== nextFlight.vertical_rate ||
      currentSnapshot.true_track !== nextFlight.true_track ||
      currentSnapshot.last_contact !== nextFlight.last_contact ||
      currentSnapshot.on_ground !== nextFlight.on_ground ||
      currentSnapshot.fetched_at !== nextFlight.fetched_at ||
      currentSnapshot.tracking_count !== nextFlight.tracking_count
    );
  }

  function getKnownFlightByIcao24(icao24) {
    const normalizedIcao24 = String(icao24 ?? "").trim().toLowerCase();
    if (!normalizedIcao24) {
      return null;
    }

    return (
      sortedFlights.find((flight) => flight.icao24 === normalizedIcao24) ??
      replayFlights.find((flight) => flight.icao24 === normalizedIcao24) ??
      state.flights.find((flight) => flight.icao24 === normalizedIcao24) ??
      globalTrafficBoard.flights.find((flight) => flight.icao24 === normalizedIcao24) ??
      remoteSearchResults.find((flight) => flight.icao24 === normalizedIcao24) ??
      watchedFlightEntries.find((entry) => entry.icao24 === normalizedIcao24)?.flight ??
      (selectedFlightSnapshot?.icao24 === normalizedIcao24 ? selectedFlightSnapshot : null)
    );
  }

  function openFlightInspector(flight, options = {}) {
    const snapshot = buildSelectedFlightSnapshot(flight);
    if (!snapshot) {
      return;
    }

    if (options.pendingSearchSelection !== undefined) {
      pendingSearchSelection = options.pendingSearchSelection;
    }

    selectedFlightSnapshot = snapshot;
    selectedIcao24 = snapshot.icao24;
    sidebarMode = "traffic";
    inspectorTab = options.inspectorTab ?? "details";

    if (options.exitReplay) {
      replayPlaybackActive = false;
      activeMonitoringSessionId = null;
      replaySnapshotCursor = null;
    }

    if (
      options.focusMap &&
      Number.isFinite(snapshot.latitude) &&
      Number.isFinite(snapshot.longitude)
    ) {
      flightFocusRequest = {
        id: crypto.randomUUID(),
        center: [snapshot.latitude, snapshot.longitude],
        zoom: Math.max(mapViewport?.zoom ?? 7.1, options.zoom ?? 8.2),
      };
    }

    if (isMobileViewport) {
      mobileSidebarOpen = true;
      mobileUtilityOpen = false;
    }
  }

  function handleBoundsChange(event) {
    flightsStore.setBbox(event.detail.bbox);
  }

  function handleFlightSelect(event) {
    openFlightInspector(event.detail.flight, {
      focusMap: false,
      exitReplay: false,
    });
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

  function selectWatchedFlight(target) {
    const flight =
      typeof target === "string" ? getKnownFlightByIcao24(target) : buildSelectedFlightSnapshot(target);

    if (flight) {
      openFlightInspector(flight, {
        focusMap: true,
        zoom: 8.2,
        exitReplay: true,
      });
      return;
    }

    const fallbackIcao24 = typeof target === "string" ? target.trim().toLowerCase() : null;
    if (!fallbackIcao24) {
      return;
    }

    selectedIcao24 = fallbackIcao24;
    sidebarMode = "traffic";
    inspectorTab = "details";
    if (isMobileViewport) {
      mobileSidebarOpen = true;
      mobileUtilityOpen = false;
    }
  }

  function openSidebarMode(nextMode) {
    sidebarMode = nextMode;
    if (isMobileViewport) {
      mobileSidebarOpen = true;
      mobileUtilityOpen = false;
    }
  }

  function openInspectorTab(tab) {
    inspectorTab = tab;
    if (isMobileViewport) {
      mobileSidebarOpen = true;
      mobileUtilityOpen = false;
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
    if (pendingSearchSelection === flight?.icao24) {
      pendingSearchSelection = null;
    }
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

  async function loadSelectedFlightTrail(flight, options = {}) {
    const key = flight?.icao24 ?? null;
    if (!key) {
      selectedFlightTrailRemote = [];
      selectedFlightTrailStatus = "idle";
      selectedFlightTrailError = null;
      return;
    }

    const force = options.force ?? false;
    const cachedTrail = flightTrailCache.get(key);
    if (cachedTrail && !force) {
      selectedFlightTrailRemote = cachedTrail;
      selectedFlightTrailStatus = "success";
      selectedFlightTrailError = null;
      return;
    }

    const requestId = ++selectedFlightTrailRequestId;
    selectedFlightTrailStatus = cachedTrail?.length ? "refreshing" : "loading";
    selectedFlightTrailError = null;
    if (cachedTrail) {
      selectedFlightTrailRemote = cachedTrail;
    }

    try {
      const trailPayload = await fetchFlightTrail(key, {
        hours: 6,
        limit: 360,
      });
      if (requestId !== selectedFlightTrailRequestId || selectedFlight?.icao24 !== key) {
        return;
      }

      const normalizedPoints = (trailPayload.points ?? [])
        .map((point) => normalizeTrailPoint(point))
        .filter(Boolean);
      const nextCache = new Map(flightTrailCache);
      nextCache.set(key, normalizedPoints);
      flightTrailCache = nextCache;
      selectedFlightTrailRemote = normalizedPoints;
      selectedFlightTrailStatus = "success";
      selectedFlightTrailError = null;
    } catch (error) {
      if (requestId !== selectedFlightTrailRequestId || selectedFlight?.icao24 !== key) {
        return;
      }

      selectedFlightTrailStatus = cachedTrail?.length ? "success" : "error";
      selectedFlightTrailError =
        error instanceof Error ? error.message : "Failed to load the archived trail.";
    }
  }

  async function hydrateReplayHistory(bbox) {
    const bboxKey = buildBboxKey(bbox);
    if (!bboxKey) {
      archivedReplayStatus = "idle";
      archivedReplayError = null;
      return;
    }

    const requestId = ++archivedReplayRequestId;
    archivedReplayStatus = snapshotHistory.length ? "refreshing" : "loading";
    archivedReplayError = null;

    try {
      const replayPayload = await fetchReplayHistory(bbox, {
        minutes: 90,
        limit: 120,
      });
      if (requestId !== archivedReplayRequestId || buildBboxKey(state.bbox) !== bboxKey) {
        return;
      }

      snapshotHistory = mergeReplaySnapshots(snapshotHistory, replayPayload.snapshots ?? []);
      archivedReplayStatus = "success";
      archivedReplayError = null;
    } catch (error) {
      if (requestId !== archivedReplayRequestId || buildBboxKey(state.bbox) !== bboxKey) {
        return;
      }

      archivedReplayStatus = snapshotHistory.length ? "success" : "error";
      archivedReplayError =
        snapshotHistory.length || !(error instanceof Error)
          ? null
          : error.message;
    }
  }

  async function loadRemoteSearchResults(query) {
    const normalizedQuery = query.trim();
    if (normalizedQuery.length < 2) {
      remoteSearchResults = [];
      remoteSearchStatus = "idle";
      remoteSearchError = null;
      return;
    }

    const requestId = ++remoteSearchRequestId;
    remoteSearchStatus = "loading";
    remoteSearchError = null;

    try {
      const searchPayload = await searchFlights(normalizedQuery, { limit: 8 });
      if (requestId !== remoteSearchRequestId || filters.query.trim() !== normalizedQuery) {
        return;
      }

      remoteSearchResults = searchPayload.results ?? [];
      remoteSearchStatus = "success";
      remoteSearchError = null;
    } catch (error) {
      if (requestId !== remoteSearchRequestId || filters.query.trim() !== normalizedQuery) {
        return;
      }

      remoteSearchResults = [];
      remoteSearchStatus = "error";
      remoteSearchError =
        error instanceof Error ? error.message : "Failed to search archived flights.";
    }
  }

  async function refreshGlobalTrafficBoard() {
    const requestId = ++globalTrafficBoardRequestId;
    globalTrafficBoard = {
      ...globalTrafficBoard,
      status: globalTrafficBoard.flights.length ? "refreshing" : "loading",
      error: null,
    };

    try {
      const payload = await fetchGlobalTrafficBoard({ limit: 6 });
      if (requestId !== globalTrafficBoardRequestId) {
        return;
      }

      globalTrafficBoard = {
        status: "success",
        flights: payload.flights ?? [],
        error: null,
        fetchedAt: payload.fetched_at ?? null,
        count: payload.count ?? (payload.flights?.length ?? 0),
        warning: payload.meta?.warning ?? null,
        source: payload.meta?.source ?? "live",
        meta: payload.meta ?? {},
      };
    } catch (error) {
      if (requestId !== globalTrafficBoardRequestId) {
        return;
      }

      const message =
        error instanceof Error ? error.message : "Failed to load the global traffic board.";
      globalTrafficBoard = {
        ...globalTrafficBoard,
        status: globalTrafficBoard.flights.length ? "success" : "error",
        error: globalTrafficBoard.flights.length ? null : message,
        warning: globalTrafficBoard.flights.length ? message : null,
      };
    }
  }

  function selectSearchResult(result) {
    if (!result || !Number.isFinite(result.latitude) || !Number.isFinite(result.longitude)) {
      return;
    }

    openFlightInspector(result, {
      focusMap: true,
      zoom: 8.4,
      exitReplay: true,
      pendingSearchSelection: result.icao24,
    });

    filters = {
      ...filters,
      query: "",
    };
    remoteSearchResults = [];
    remoteSearchStatus = "idle";
    remoteSearchError = null;
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

  function submitSelectedFlightTag() {
    const normalizedTag = selectedTagDraft.trim();
    if (!normalizedTag) {
      return;
    }

    addSelectedFlightTag(normalizedTag);
    selectedTagDraft = "";
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

  function showOnboardingTips() {
    onboardingDismissed = false;
    utilityPanelMode = "guide";
  }

  function buildBboxKey(bbox) {
    if (!bbox) {
      return null;
    }

    return [bbox.lamin, bbox.lamax, bbox.lomin, bbox.lomax]
      .map((value) => Number(value).toFixed(4))
      .join("|");
  }

  function normalizeReplaySnapshot(snapshot) {
    if (!snapshot) {
      return null;
    }

    const fetchedAt = snapshot.fetchedAt ?? snapshot.fetched_at ?? null;
    if (!fetchedAt) {
      return null;
    }

    return {
      fetchedAt,
      count: snapshot.count ?? snapshot.flights?.length ?? 0,
      flights: (snapshot.flights ?? []).map((flight) => ({ ...flight })),
    };
  }

  function mergeReplaySnapshots(history, snapshots) {
    const merged = new Map(history.map((snapshot) => [snapshot.fetchedAt, snapshot]));

    for (const snapshot of snapshots) {
      const normalizedSnapshot = normalizeReplaySnapshot(snapshot);
      if (!normalizedSnapshot) {
        continue;
      }

      merged.set(normalizedSnapshot.fetchedAt, normalizedSnapshot);
    }

    return [...merged.values()]
      .sort((left, right) => new Date(left.fetchedAt) - new Date(right.fetchedAt))
      .slice(-180);
  }

  function pushReplaySnapshot(history, snapshotState) {
    const snapshot = normalizeReplaySnapshot(snapshotState);
    if (!snapshot) {
      return history;
    }

    return mergeReplaySnapshots(history, [snapshot]);
  }

  function normalizeTrailPoint(point) {
    if (!point) {
      return null;
    }

    const timestampValue = point.timestamp ?? point.fetched_at ?? point.fetchedAt ?? null;
    const latitude = Number(point.latitude);
    const longitude = Number(point.longitude);
    const timestamp =
      typeof timestampValue === "number" ? timestampValue : new Date(timestampValue).getTime();

    if (
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude) ||
      !Number.isFinite(timestamp)
    ) {
      return null;
    }

    return {
      latitude,
      longitude,
      altitude: point.altitude ?? null,
      velocity: point.velocity ?? null,
      vertical_rate: point.vertical_rate ?? point.verticalRate ?? null,
      timestamp,
    };
  }

  function mergeTrailPoints(primaryPoints, secondaryPoints) {
    const merged = new Map();

    for (const point of [...primaryPoints, ...secondaryPoints]) {
      const normalizedPoint = normalizeTrailPoint(point);
      if (!normalizedPoint) {
        continue;
      }

      merged.set(normalizedPoint.timestamp, normalizedPoint);
    }

    return [...merged.values()].sort((left, right) => left.timestamp - right.timestamp);
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
    if (!mobileSidebarOpen) {
      mobileUtilityOpen = false;
    }
    mobileSidebarOpen = !mobileSidebarOpen;
  }

  function closeMobileSidebar() {
    mobileSidebarOpen = false;
  }

  function toggleMobileUtility() {
    if (!mobileUtilityOpen) {
      mobileSidebarOpen = false;
    }
    mobileUtilityOpen = !mobileUtilityOpen;
  }

  function closeMobileUtility() {
    mobileUtilityOpen = false;
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
  $: searchQuery = filters.query.trim();
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
  $: visibleLeaderboardFlights = sortFlights(filteredFlights, "speed_desc", mapViewport).slice(0, 6);
  $: leaderboardFlights = globalTrafficBoard.flights ?? [];
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
  $: leadFeedFlight = visibleLeaderboardFlights[0] ?? null;
  $: globalBoardStatusLabel =
    globalTrafficBoard.status === "loading" || globalTrafficBoard.status === "refreshing"
      ? "SYNC"
      : globalTrafficBoard.source === "cache"
        ? "CACHE"
        : "WORLD";
  $: globalBoardSummary = globalTrafficBoard.meta?.sectors_synced
    ? `${globalTrafficBoard.meta.sectors_synced}/${globalTrafficBoard.meta.sectors_total} sectors synced`
    : "Global board";
  $: replayPanelBadge = activeReplaySnapshot
    ? "Replay"
    : activeMonitoringSession
      ? "Session"
      : archivedReplayStatus === "loading" || archivedReplayStatus === "refreshing"
        ? "Syncing"
        : "Live";
  $: replayPanelSummary = activeReplaySnapshot
    ? `${activeReplaySnapshot.count} aircraft in selected frame`
    : archivedReplayStatus === "loading" || archivedReplayStatus === "refreshing"
      ? "Loading archived snapshots for the current airspace"
      : `${replaySourceSnapshots.length} snapshots ready for replay`;
  $: statusLabel = getStatusLabel(state);
  $: mapCenterLabel = mapViewport?.center
    ? `${mapViewport.center[0].toFixed(2)}, ${mapViewport.center[1].toFixed(2)}`
    : "52.23, 21.01";
  $: zoomLabel = Number.isFinite(mapViewport?.zoom) ? mapViewport.zoom.toFixed(1) : "7.1";
  $: visibleTrackedCount = activeReplaySnapshot?.count ?? state.count;
  $: canStepReplayBackward =
    replaySourceSnapshots.length > 1 && (replaySnapshotIndex > 0 || replaySnapshotIndex === -1);
  $: canStepReplayForward = replaySourceSnapshots.length > 1 && replaySnapshotIndex !== -1;
  $: showSearchSuggestions =
    searchQuery.length >= 2 &&
    (remoteSearchStatus !== "idle" || remoteSearchResults.length > 0 || remoteSearchError);
  $: selectedFlightLiveCandidate = selectedIcao24 ? getKnownFlightByIcao24(selectedIcao24) : null;
  $: if (
    selectedIcao24 &&
    selectedFlightLiveCandidate &&
    shouldRefreshSelectedFlightSnapshot(selectedFlightSnapshot, selectedFlightLiveCandidate)
  ) {
    selectedFlightSnapshot = {
      ...(selectedFlightSnapshot ?? {}),
      ...selectedFlightLiveCandidate,
    };
  }
  $: selectedFlight = selectedIcao24
    ? selectedFlightLiveCandidate ??
      (selectedFlightSnapshot?.icao24 === selectedIcao24 ? selectedFlightSnapshot : null)
    : null;
  $: selectedOperatorCode = selectedFlight ? deriveOperatorCode(selectedFlight) || "N/A" : "N/A";
  $: replaySelectedFlightTrail = activeReplaySnapshot
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
    : [];
  $: localSelectedFlightTrail = getTrailPoints(flightHistory, selectedIcao24);
  $: selectedFlightTrail = activeReplaySnapshot
    ? replaySelectedFlightTrail
    : mergeTrailPoints(selectedFlightTrailRemote, localSelectedFlightTrail);
  $: selectedFlightAnnotation = selectedIcao24
    ? flightAnnotations[selectedIcao24] ?? { notes: "", tags: [] }
    : { notes: "", tags: [] };
  $: selectedFlightTrailFirstPoint = selectedFlightTrail[0] ?? null;
  $: selectedFlightTrailLastPoint = selectedFlightTrail[selectedFlightTrail.length - 1] ?? null;
  $: selectedFlightAlertRuleCount = selectedFlight
    ? alertRules.filter(
        (rule) =>
          (rule.type === "icao24" && rule.query.toLowerCase() === selectedFlight.icao24) ||
          (rule.type === "callsign" &&
            selectedFlight.callsign &&
            rule.query.toLowerCase() === selectedFlight.callsign.toLowerCase())
      ).length
    : 0;
  $: selectedFlightDetailsKey = buildFlightDetailsKey(selectedFlight);
  $: selectedRouteAirports = selectedFlightDetails?.route?.airports ?? [];
  $: selectedFlightTrailKey = selectedFlight?.icao24 ?? null;
  $: replayArchiveBboxKey = buildBboxKey(state.bbox);
  $: mapStyleLabel = {
    standard: "Map",
    dark: "Dark",
    satellite: "Satellite",
    aviation: "Aero",
  }[mapStyle] ?? "Map";
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
  $: if (!selectedFlightTrailKey) {
    lastSelectedFlightTrailKey = null;
    selectedFlightTrailRemote = [];
    selectedFlightTrailStatus = "idle";
    selectedFlightTrailError = null;
  }
  $: if (
    selectedFlightTrailKey &&
    selectedFlightTrailKey !== lastSelectedFlightTrailKey &&
    !activeReplaySnapshot
  ) {
    lastSelectedFlightTrailKey = selectedFlightTrailKey;
    loadSelectedFlightTrail(selectedFlight);
  }
  $: if (!selectedFlight) {
    followAircraft = false;
    selectedTagDraft = "";
  }
  $: if (!selectedIcao24) {
    selectedFlightSnapshot = null;
    lastInspectorScrollFlightKey = null;
  }
  $: if (selectedIcao24 && selectedIcao24 !== lastInspectorScrollFlightKey && inspectorScroll) {
    lastInspectorScrollFlightKey = selectedIcao24;
    inspectorScroll.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }
  $: if (activeReplaySnapshot && followAircraft) {
    followAircraft = false;
  }
  $: if (replayArchiveBboxKey && replayArchiveBboxKey !== lastArchivedReplayBboxKey) {
    lastArchivedReplayBboxKey = replayArchiveBboxKey;
    if (typeof window !== "undefined") {
      if (replayHydrationTimer) {
        window.clearTimeout(replayHydrationTimer);
      }

      replayHydrationTimer = window.setTimeout(() => {
        replayHydrationTimer = null;
        hydrateReplayHistory(state.bbox);
      }, 220);
    }
  }
  $: if (typeof window !== "undefined") {
    searchQuery;
    if (searchDebounceTimer) {
      window.clearTimeout(searchDebounceTimer);
      searchDebounceTimer = null;
    }

    if (searchQuery.length < 2) {
      remoteSearchResults = [];
      remoteSearchStatus = "idle";
      remoteSearchError = null;
    } else {
      searchDebounceTimer = window.setTimeout(() => {
        searchDebounceTimer = null;
        loadRemoteSearchResults(searchQuery);
      }, 260);
    }
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
        selectedRouteAirports={selectedRouteAirports}
        followAircraft={followAircraft}
        mapStyle={mapStyle}
        trailPoints={selectedFlightTrail}
        watchedIcao24s={watchlist}
        watchModeEnabled={watchModeEnabled}
        initialViewport={mapViewport}
        fullscreenRequestId={fullscreenRequestId}
        viewPresetRequest={viewPresetRequest}
        focusRequest={flightFocusRequest}
        on:boundschange={handleBoundsChange}
        on:viewportchange={handleViewportChange}
        on:select={handleFlightSelect}
      />
    </div>

    <header class="radar-topbar">
      <div class="overlay-card center-bar">
        <div class="brand-inline">
          <div class="brand-mark">◎</div>
          <div class="brand-copy">
            <strong>liveflights<span>24</span></strong>
            <span>live air traffic</span>
          </div>
        </div>

        <div class="search-shell">
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

          {#if showSearchSuggestions}
            <div class="search-suggestions">
              {#if remoteSearchStatus === "loading"}
                <p class="search-hint">Searching archived traffic…</p>
              {:else if remoteSearchError}
                <p class="search-hint search-hint-error">{remoteSearchError}</p>
              {:else if remoteSearchResults.length}
                {#each remoteSearchResults as result}
                  <button
                    class="search-result"
                    type="button"
                    on:click={() => selectSearchResult(result)}
                  >
                    <strong>{result.callsign ?? result.registration ?? result.icao24.toUpperCase()}</strong>
                    <span>
                      {result.registration ?? result.icao24.toUpperCase()}
                      {#if result.type_code}
                        · {result.type_code}
                      {/if}
                      · {result.origin_country ?? "Unknown"}
                    </span>
                  </button>
                {/each}
              {:else}
                <p class="search-hint">No recent archived flights match this query.</p>
              {/if}
            </div>
          {/if}
        </div>

        <div class="center-actions">
          <div class="traffic-counter">
            <span class:online={["success", "refreshing"].includes(state.status)} class="traffic-dot"></span>
            <strong>{formatCompactCount(visibleTrackedCount)}</strong>
            <small>aircraft</small>
          </div>

          {#if isMobileViewport}
            <button class="overlay-card topbar-icon topbar-action-chip" type="button" on:click={toggleMobileUtility}>
              Tools
            </button>
            <button class="overlay-card topbar-icon topbar-action-chip" type="button" on:click={toggleMobileSidebar}>
              {selectedFlight ? "Flight" : sidebarMode === "watchlist" ? "List" : "Traffic"}
            </button>
          {/if}
        </div>
      </div>

      <div class="overlay-card topbar-ribbon">
        <div class="ribbon-row">
          <button class="ribbon-chip" type="button" on:click={() => applyQuickFilter("fast")}>Fast jets</button>
          <button class="ribbon-chip" type="button" on:click={() => applyQuickFilter("high")}>High altitude</button>
          <button class="ribbon-chip" type="button" on:click={() => applyQuickFilter("recent")}>Recent only</button>
          <button
            class:active={!filters.hideGroundTraffic}
            class="ribbon-chip"
            type="button"
            on:click={() => {
              filters = {
                ...filters,
                hideGroundTraffic: !filters.hideGroundTraffic,
              };
            }}
          >
            Ground traffic
          </button>
          <button class="ribbon-chip ribbon-chip-reset" type="button" on:click={resetFilters}>Reset</button>
        </div>

        {#if activeFilterTokens.length}
          <div class="filter-token-row">
            {#each activeFilterTokens as token}
              <button class="filter-token" type="button" on:click={() => clearFilterToken(token.key)}>
                <span>{token.label}</span>
                <strong>×</strong>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </header>

    <div class="floating-messages">
      {#if state.error}
        <div class="error-banner">{state.error}</div>
      {/if}

      {#if state.warning && (!state.flights.length || !["rate_limit", "cooldown"].includes(state.reason))}
        <div class="warning-banner">{state.warning}</div>
      {/if}

      {#if archivedReplayError}
        <div class="warning-banner">{archivedReplayError}</div>
      {/if}

      {#if selectedFlightTrailError && selectedFlight}
        <div class="warning-banner">{selectedFlightTrailError}</div>
      {/if}

      {#if alertToast}
        <div class="alert-toast">{alertToast.message}</div>
      {/if}
    </div>

    <aside class:open={mobileUtilityOpen} class="overlay-card radar-left-panel">
      <div class="utility-header">
        <div class="utility-heading">
          <span>Radar controls</span>
          <strong>{utilityPanelMode === "overview" ? "Overview" : utilityPanelMode === "replay" ? "Replay" : utilityPanelMode === "workspace" ? "Workspace" : "Guide"}</strong>
        </div>
        <div class="utility-meta">
          <span class="utility-pill">{statusLabel}</span>
          <span class="utility-count">{visibleTrackedCount}</span>
        </div>
      </div>

      <div class="utility-tabs" role="tablist" aria-label="Radar utility sections">
        <button
          class:active={utilityPanelMode === "overview"}
          class="utility-tab"
          type="button"
          on:click={() => {
            utilityPanelMode = "overview";
          }}
        >
          Overview
        </button>
        <button
          class:active={utilityPanelMode === "replay"}
          class="utility-tab"
          type="button"
          on:click={() => {
            utilityPanelMode = "replay";
          }}
        >
          Replay
        </button>
        <button
          class:active={utilityPanelMode === "workspace"}
          class="utility-tab"
          type="button"
          on:click={() => {
            utilityPanelMode = "workspace";
          }}
        >
          Workspace
        </button>
        <button
          class:active={utilityPanelMode === "guide"}
          class="utility-tab"
          type="button"
          on:click={() => {
            utilityPanelMode = "guide";
          }}
        >
          Guide
        </button>
      </div>

      <section class="widget-card persistent-tracked-widget">
        <div class="widget-header">
          <div class="widget-heading">
            <strong>Most tracked flights</strong>
            <span class="live-pill">{globalBoardStatusLabel}</span>
          </div>
        </div>

        <p class="widget-caption">
          {globalTrafficBoard.warning ?? globalTrafficBoard.error ?? globalBoardSummary}
        </p>

        {#if compactLeaderboardFlights.length}
          <div class="widget-list">
            {#each compactLeaderboardFlights as flight, index}
              <button class="widget-row" type="button" on:click={() => selectWatchedFlight(flight)}>
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
                <span class="widget-highlight">
                  <strong>{flight.tracking_count ? `${flight.tracking_count}x` : "LIVE"}</strong>
                  <small>{formatSpeed(flight.velocity).replace(" km/h", "")}</small>
                </span>
              </button>
            {/each}
          </div>
        {:else}
          <p class="widget-empty">Waiting for global sectors to sync.</p>
        {/if}
      </section>

      <div class="panel-stack">
        {#if utilityPanelMode === "overview"}
          <section class="widget-card filter-card">
            <div class="widget-header">
              <div class="widget-heading">
                <strong>Radar filters</strong>
                <span class="live-pill utility-state-pill">{activeFilterCount}</span>
              </div>
            </div>

            <div class="filter-chip-row">
              <button class="filter-chip" type="button" on:click={() => applyQuickFilter("fast")}>Fast jets</button>
              <button class="filter-chip" type="button" on:click={() => applyQuickFilter("high")}>High altitude</button>
              <button class="filter-chip" type="button" on:click={() => applyQuickFilter("recent")}>Recent</button>
              <button
                class:active={!filters.hideGroundTraffic}
                class="filter-chip"
                type="button"
                on:click={() => {
                  filters = {
                    ...filters,
                    hideGroundTraffic: !filters.hideGroundTraffic,
                  };
                }}
              >
                Ground
              </button>
            </div>

            <div class="filter-form-grid">
              <label class="filter-field">
                <span>Min altitude</span>
                <input
                  type="number"
                  min="0"
                  step="500"
                  value={filters.minAltitude}
                  placeholder="9000"
                  on:input={(event) => {
                    filters = {
                      ...filters,
                      minAltitude: event.currentTarget.value,
                    };
                  }}
                />
              </label>

              <label class="filter-field">
                <span>Min speed km/h</span>
                <input
                  type="number"
                  min="0"
                  step="50"
                  value={filters.minSpeed}
                  placeholder="700"
                  on:input={(event) => {
                    filters = {
                      ...filters,
                      minSpeed: event.currentTarget.value,
                    };
                  }}
                />
              </label>

              <label class="filter-field">
                <span>Country</span>
                <input
                  type="text"
                  value={filters.country}
                  placeholder="Poland"
                  on:input={(event) => {
                    filters = {
                      ...filters,
                      country: event.currentTarget.value,
                    };
                  }}
                />
              </label>

              <label class="filter-field">
                <span>Operator</span>
                <input
                  type="text"
                  value={filters.operator}
                  placeholder="LOT"
                  on:input={(event) => {
                    filters = {
                      ...filters,
                      operator: event.currentTarget.value,
                    };
                  }}
                />
              </label>

              <label class="filter-field">
                <span>Heading</span>
                <select
                  value={filters.headingBand}
                  on:change={(event) => {
                    filters = {
                      ...filters,
                      headingBand: event.currentTarget.value,
                    };
                  }}
                >
                  <option value="any">Any</option>
                  <option value="north">Northbound</option>
                  <option value="east">Eastbound</option>
                  <option value="south">Southbound</option>
                  <option value="west">Westbound</option>
                </select>
              </label>

              <label class="filter-field">
                <span>Freshness</span>
                <select
                  value={filters.recentActivity}
                  on:change={(event) => {
                    filters = {
                      ...filters,
                      recentActivity: event.currentTarget.value,
                    };
                  }}
                >
                  <option value="any">Any age</option>
                  <option value="30s">30 seconds</option>
                  <option value="2m">2 minutes</option>
                  <option value="5m">5 minutes</option>
                  <option value="15m">15 minutes</option>
                </select>
              </label>

              <label class="filter-field filter-field-wide">
                <span>Sort traffic board</span>
                <select bind:value={sortBy}>
                  <option value="altitude_desc">Altitude first</option>
                  <option value="speed_desc">Speed first</option>
                  <option value="distance_asc">Nearest first</option>
                  <option value="last_contact_desc">Most recent first</option>
                </select>
              </label>
            </div>

            <div class="filter-suggestion-group">
              {#if topOperatorSuggestions.length}
                <div class="suggestion-row">
                  <span>Top operators</span>
                  <div>
                    {#each topOperatorSuggestions as suggestion}
                      <button
                        class="suggestion-pill"
                        type="button"
                        on:click={() => {
                          filters = {
                            ...filters,
                            operator: suggestion,
                          };
                        }}
                      >
                        {suggestion}
                      </button>
                    {/each}
                  </div>
                </div>
              {/if}

              {#if topCountrySuggestions.length}
                <div class="suggestion-row">
                  <span>Top countries</span>
                  <div>
                    {#each topCountrySuggestions as suggestion}
                      <button
                        class="suggestion-pill"
                        type="button"
                        on:click={() => {
                          filters = {
                            ...filters,
                            country: suggestion,
                          };
                        }}
                      >
                        {suggestion}
                      </button>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>

            {#if activeFilterTokens.length}
              <div class="filter-token-list">
                {#each activeFilterTokens as token}
                  <button class="filter-token" type="button" on:click={() => clearFilterToken(token.key)}>
                    <span>{token.label}</span>
                    <strong>×</strong>
                  </button>
                {/each}
              </div>
            {/if}

            <div class="preset-save-row">
              <input
                type="text"
                placeholder="Arrival bank, Cargo sweep..."
                value={presetName}
                on:input={(event) => {
                  presetName = event.currentTarget.value;
                }}
                on:keydown={(event) => event.key === "Enter" && saveCurrentPreset()}
              />
              <button class="widget-footer-button" type="button" on:click={saveCurrentPreset}>Save preset</button>
            </div>

            {#if filterPresets.length}
              <div class="preset-list">
                {#each filterPresets as preset}
                  <article class="preset-card">
                    <div>
                      <strong>{preset.name}</strong>
                      <span>{countActiveFilters(preset.filters)} active rules</span>
                    </div>
                    <div class="preset-actions">
                      <button class="widget-footer-button" type="button" on:click={() => applyFilterPreset(preset)}>
                        Apply
                      </button>
                      <button class="preset-delete" type="button" on:click={() => deleteFilterPreset(preset.name)}>
                        Delete
                      </button>
                    </div>
                  </article>
                {/each}
              </div>
            {/if}
          </section>

          <section class="widget-card widget-card-secondary">
            <div class="widget-header">
              <div class="widget-heading">
                <strong>Airspace focus</strong>
                <span class="live-pill">LIVE</span>
              </div>
            </div>

            {#if countryActivity.length}
              <div class="mini-stat-list">
                {#each countryActivity as entry}
                  <div>
                    <span>
                      <strong>{entry.country}</strong>
                      <small>{entry.ground} ground</small>
                    </span>
                    <strong>{entry.count}</strong>
                  </div>
                {/each}
              </div>
            {:else}
              <p class="widget-empty">Waiting for traffic clusters in view.</p>
            {/if}

            <button class="widget-footer-button" type="button" on:click={() => triggerViewPreset("europe")}>
              Wider airspace
            </button>
          </section>

          <ComparisonPanel
            flights={comparisonFlights}
            selectedIcao24={selectedIcao24}
            onSelectFlight={selectWatchedFlight}
          />

          <button class="widget-footer-bar" type="button" on:click={() => openSidebarMode("watchlist")}>
            <span>Bookmarks</span>
            <strong>{watchlist.length}</strong>
          </button>
        {:else if utilityPanelMode === "replay"}
          <section class="widget-card utility-summary-card">
            <div class="widget-header">
              <div class="widget-heading">
                <strong>Replay archive</strong>
                <span class="live-pill utility-state-pill">{replayPanelBadge}</span>
              </div>
            </div>
            <p class="widget-empty">{replayPanelSummary}</p>
          </section>

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
        {:else if utilityPanelMode === "workspace"}
          <SavedViewsPanel
            views={savedViews}
            activeViewId={activeSavedViewId}
            currentName={savedViewName}
            onNameChange={(value) => {
              savedViewName = value;
            }}
            onSaveView={saveCurrentView}
            onLoadView={loadSavedView}
            onDeleteView={deleteSavedView}
          />

          <AlertPanel
            rules={alertRules}
            events={alertEvents}
            onAddRule={addAlertRule}
            onRemoveRule={removeAlertRule}
            onClearEvents={clearAlertEvents}
          />
        {:else}
          {#if !onboardingDismissed}
            <OnboardingPanel onDismiss={dismissOnboarding} />
          {:else}
            <section class="widget-card utility-summary-card">
              <div class="widget-header">
                <div class="widget-heading">
                  <strong>Quick start hidden</strong>
                  <span class="live-pill utility-state-pill">Guide</span>
                </div>
              </div>
              <p class="widget-empty">Bring back the onboarding tips at any time.</p>
              <button class="widget-footer-button" type="button" on:click={showOnboardingTips}>
                Show tips again
              </button>
            </section>
          {/if}

          <LegendPanel />
          <ShortcutsPanel />
        {/if}
      </div>
    </aside>

    <button class="overlay-card view-chip" type="button" on:click={cycleMapStyle}>
      <span>View</span>
      <strong>{mapStyleLabel}</strong>
    </button>

    {#if isMobileViewport && mobileUtilityOpen}
      <button class="sidebar-backdrop utility-backdrop" type="button" aria-label="Close tools panel" on:click={closeMobileUtility}></button>
    {/if}

    {#if isMobileViewport && mobileSidebarOpen}
      <button class="sidebar-backdrop" type="button" aria-label="Close panel" on:click={closeMobileSidebar}></button>
    {/if}

    <aside class:open={mobileSidebarOpen} class="overlay-card radar-right-panel">
      <div class="rail-header">
        <div class="rail-brand">
          <span>{selectedFlight ? "Tracking" : sidebarMode === "watchlist" ? "Saved aircraft" : "Click any aircraft"}</span>
          <strong>{selectedFlight ? selectedFlight.callsign ?? selectedFlight.icao24 : sidebarMode === "watchlist" ? "Bookmarks" : "Visible traffic"}</strong>
        </div>
        {#if selectedFlight}
          <button
            class="rail-close"
            type="button"
            aria-label="Close selected aircraft"
            on:click={() => {
              selectedIcao24 = null;
              selectedFlightSnapshot = null;
              if (isMobileViewport) {
                closeMobileSidebar();
              }
            }}
          >
            ×
          </button>
        {:else}
          <div class="rail-actions">
            <button
              class:active={sidebarMode === "traffic"}
              class="rail-toggle"
              type="button"
              on:click={() => openSidebarMode("traffic")}
            >
              Traffic
            </button>
            <button
              class:active={sidebarMode === "watchlist"}
              class="rail-toggle"
              type="button"
              on:click={() => openSidebarMode("watchlist")}
            >
              Bookmarks
            </button>
            <span class="rail-count">{sidebarMode === "watchlist" ? watchlist.length : visibleTrackedCount}</span>
          </div>
        {/if}
      </div>

      <div bind:this={inspectorScroll} class="inspector-scroll">
        {#if selectedFlight}
          <div class="inspector-tab-row" role="tablist" aria-label="Selected aircraft sections">
            <button
              class:active={inspectorTab === "details"}
              class="inspector-tab"
              type="button"
              on:click={() => openInspectorTab("details")}
            >
              Details
            </button>
            <button
              class:active={inspectorTab === "tracking"}
              class="inspector-tab"
              type="button"
              on:click={() => openInspectorTab("tracking")}
            >
              Tracking
            </button>
            <button
              class:active={inspectorTab === "notes"}
              class="inspector-tab"
              type="button"
              on:click={() => openInspectorTab("notes")}
            >
              Notes
            </button>
          </div>

          {#if inspectorTab === "details"}
            <FlightDetailsPanel
              flight={selectedFlight}
              details={selectedFlightDetails}
              detailsStatus={selectedFlightDetailsStatus}
              detailsError={selectedFlightDetailsError}
              followAircraft={followAircraft}
              isBookmarked={watchlist.includes(selectedFlight.icao24)}
              trailPoints={selectedFlightTrail}
              onToggleFollow={toggleFollowAircraft}
              onToggleBookmark={toggleSelectedFlightWatchlist}
              onRetryDetails={retrySelectedFlightDetails}
            />
          {:else if inspectorTab === "tracking"}
            <section class="panel aircraft-workflow-panel">
              <div class="workflow-header">
                <div>
                  <p class="workflow-eyebrow">Active aircraft</p>
                  <h2>Tracking workflow</h2>
                </div>
                <span class="workflow-status">
                  {#if selectedFlightTrailStatus === "loading" || selectedFlightTrailStatus === "refreshing"}
                    Syncing trail
                  {:else if selectedFlightTrail.length}
                    Trail ready
                  {:else}
                    Live only
                  {/if}
                </span>
              </div>

              <div class="workflow-metrics">
                <article>
                  <span>Trail points</span>
                  <strong>{selectedFlightTrail.length}</strong>
                  <small>
                    {#if selectedFlightTrailLastPoint}
                      Last point {new Intl.DateTimeFormat("pl-PL", { hour: "2-digit", minute: "2-digit" }).format(new Date(selectedFlightTrailLastPoint.timestamp))}
                    {:else}
                      Waiting for archived path
                    {/if}
                  </small>
                </article>
                <article>
                  <span>Alerts</span>
                  <strong>{selectedFlightAlertRuleCount}</strong>
                  <small>
                    {selectedFlight.callsign ?? selectedFlight.icao24}
                  </small>
                </article>
              </div>

              <div class="workflow-facts">
                <div>
                  <span>Observation window</span>
                  <strong>
                    {#if selectedFlightTrailFirstPoint && selectedFlightTrailLastPoint}
                      {new Intl.DateTimeFormat("pl-PL", { hour: "2-digit", minute: "2-digit" }).format(new Date(selectedFlightTrailFirstPoint.timestamp))}
                      -
                      {new Intl.DateTimeFormat("pl-PL", { hour: "2-digit", minute: "2-digit" }).format(new Date(selectedFlightTrailLastPoint.timestamp))}
                    {:else}
                      Waiting for trail
                    {/if}
                  </strong>
                </div>
                <div>
                  <span>Monitoring</span>
                  <strong>{watchlist.includes(selectedFlight.icao24) ? "Bookmarked" : "Not bookmarked"}</strong>
                </div>
                <div>
                  <span>Replay archive</span>
                  <strong>{replaySourceSnapshots.length} snapshots</strong>
                </div>
              </div>

              <div class="workflow-actions">
                {#if selectedFlight.callsign}
                  <button
                    class="workflow-button"
                    type="button"
                    on:click={() =>
                      addAlertRule({
                        type: "callsign",
                        query: selectedFlight.callsign,
                      })}
                  >
                    Alert by callsign
                  </button>
                {/if}
                <button
                  class="workflow-button"
                  type="button"
                  on:click={() =>
                    addAlertRule({
                      type: "icao24",
                      query: selectedFlight.icao24,
                    })}
                >
                  Alert by ICAO24
                </button>
                <button class="workflow-button" type="button" on:click={toggleSelectedFlightWatchlist}>
                  {watchlist.includes(selectedFlight.icao24) ? "Remove bookmark" : "Bookmark aircraft"}
                </button>
                <button
                  class="workflow-button primary"
                  type="button"
                  disabled={snapshotHistory.length < 2}
                  on:click={saveCurrentMonitoringSession}
                >
                  Save monitoring session
                </button>
              </div>
            </section>
          {:else}
            <section class="panel aircraft-notes-panel">
              <div class="workflow-header">
                <div>
                  <p class="workflow-eyebrow">Local workspace</p>
                  <h2>Aircraft notes</h2>
                </div>
                <span class="workflow-status">Saved in browser</span>
              </div>

              <label class="notes-field">
                <span>Notes</span>
                <textarea
                  rows="7"
                  placeholder="Why this aircraft matters, route patterns, interesting behaviour..."
                  value={selectedFlightAnnotation.notes}
                  on:input={(event) => updateSelectedFlightNotes(event.currentTarget.value)}
                ></textarea>
              </label>

              <div class="tag-editor">
                <div class="tag-editor-header">
                  <span>Tags</span>
                  <small>{selectedFlightAnnotation.tags.length} saved</small>
                </div>

                {#if selectedFlightAnnotation.tags.length}
                  <div class="tag-list">
                    {#each selectedFlightAnnotation.tags as tag}
                      <button class="tag-pill" type="button" on:click={() => removeSelectedFlightTag(tag)}>
                        <span>{tag}</span>
                        <strong>×</strong>
                      </button>
                    {/each}
                  </div>
                {:else}
                  <p class="notes-empty">No tags yet. Add route, airline, mission or spotting notes.</p>
                {/if}

                <div class="tag-input-row">
                  <input
                    type="text"
                    placeholder="cargo, retro livery, frequent arrival..."
                    value={selectedTagDraft}
                    on:input={(event) => {
                      selectedTagDraft = event.currentTarget.value;
                    }}
                    on:keydown={(event) => event.key === "Enter" && submitSelectedFlightTag()}
                  />
                  <button class="workflow-button primary" type="button" on:click={submitSelectedFlightTag}>
                    Add tag
                  </button>
                </div>
              </div>
            </section>
          {/if}
        {:else if sidebarMode === "watchlist"}
          <WatchlistPanel
            entries={watchedFlightEntries}
            selectedIcao24={selectedIcao24}
            watchModeEnabled={watchModeEnabled}
            onToggleWatchMode={() => {
              watchModeEnabled = !watchModeEnabled;
            }}
            onSelectFlight={selectWatchedFlight}
            onRemoveFlight={removeFromWatchlist}
          />
        {:else}
          <TrafficBoardPanel
            flights={sortedFlights}
            selectedIcao24={selectedIcao24}
            title="Visible traffic"
            subtitle={`${visibleTrackedCount} aircraft in view`}
            maxRows={14}
            featuredFlight={leadFeedFlight}
            onSelectFlight={selectWatchedFlight}
          />
        {/if}
      </div>
    </aside>

    <nav aria-label="Quick map controls" class="overlay-card bottom-dock">
      <button class="dock-button" type="button" on:click={() => triggerViewPreset("poland")}>
        <span class="dock-glyph dock-glyph-scope" aria-hidden="true"></span>
        <span class="dock-label">Poland</span>
      </button>
      <button class="dock-button" type="button" on:click={() => triggerViewPreset("europe")}>
        <span class="dock-glyph dock-glyph-grid" aria-hidden="true"></span>
        <span class="dock-label">Europe</span>
      </button>
      <button class="dock-button" type="button" on:click={cycleMapStyle}>
        <span class="dock-glyph dock-glyph-map" aria-hidden="true"></span>
        <span class="dock-label">{mapStyleLabel}</span>
      </button>
      <button class="dock-button" type="button" on:click={triggerFullscreenToggle}>
        <span class="dock-glyph dock-glyph-fullscreen" aria-hidden="true"></span>
        <span class="dock-label">Fullscreen</span>
      </button>
    </nav>
  </section>
</div>

<style>
  .app-shell {
    min-height: 100vh;
    font-family:
      "IBM Plex Sans",
      system-ui,
      sans-serif;
    color: #eef2f6;
  }

  .radar-stage {
    position: relative;
    min-height: 100vh;
    overflow: hidden;
    background: #0b0d11;
  }

  .map-layer {
    position: absolute;
    inset: 0;
  }

  .overlay-card {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    background:
      linear-gradient(180deg, rgba(31, 34, 39, 0.97) 0%, rgba(17, 19, 23, 0.97) 100%);
    backdrop-filter: blur(14px);
    box-shadow:
      0 24px 44px rgba(0, 0, 0, 0.34),
      inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }

  .radar-topbar,
  .radar-left-panel,
  .radar-right-panel,
  .bottom-dock,
  .view-chip,
  .floating-messages {
    position: absolute;
    z-index: 1100;
  }

  .radar-topbar {
    top: 0.85rem;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    justify-content: center;
  }

  .center-bar {
    display: grid;
    grid-template-columns: auto minmax(250px, 1fr) auto;
    align-items: center;
    gap: 0.6rem;
    width: min(34rem, calc(100vw - 39rem));
    min-width: 30rem;
    padding: 0.42rem 0.48rem 0.42rem 0.58rem;
    border-radius: 16px;
    background:
      linear-gradient(180deg, rgba(30, 33, 38, 0.98) 0%, rgba(16, 18, 22, 0.98) 100%);
  }

  .brand-inline {
    display: flex;
    align-items: center;
    gap: 0.62rem;
  }

  .brand-mark {
    display: grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 900;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    box-shadow: inset 0 0 0 3px rgba(0, 0, 0, 0.14);
  }

  .brand-copy strong {
    display: block;
    margin: 0;
    font-size: 0.96rem;
    font-weight: 800;
    color: #f6f8fb;
    line-height: 1;
  }

  .brand-copy strong span {
    color: #f5b908;
  }

  .brand-copy span {
    display: block;
    margin-top: 0.12rem;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: #aeb6c2;
  }

  .search-field {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.52rem;
    min-width: 0;
    padding: 0.62rem 0.8rem;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
  }

  .search-shell {
    position: relative;
    min-width: 0;
  }

  .search-icon {
    color: rgba(35, 40, 48, 0.6);
    font-size: 0.95rem;
  }

  .search-field input {
    width: 100%;
    border: 0;
    padding: 0;
    font: inherit;
    font-size: 0.88rem;
    color: #1d232b;
    background: transparent;
    outline: none;
  }

  .search-field input::placeholder {
    color: rgba(35, 40, 48, 0.5);
  }

  .search-suggestions {
    position: absolute;
    top: calc(100% + 0.45rem);
    left: 0;
    right: 0;
    display: grid;
    gap: 0.32rem;
    padding: 0.4rem;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background:
      linear-gradient(180deg, rgba(27, 30, 35, 0.98) 0%, rgba(14, 16, 20, 0.98) 100%);
    box-shadow:
      0 18px 32px rgba(0, 0, 0, 0.26),
      inset 0 1px 0 rgba(255, 255, 255, 0.03);
  }

  .search-hint {
    margin: 0;
    padding: 0.6rem 0.7rem;
    font-size: 0.78rem;
    color: rgba(214, 222, 231, 0.8);
  }

  .search-hint-error {
    color: #ffd8d8;
  }

  .search-result {
    display: grid;
    gap: 0.14rem;
    width: 100%;
    padding: 0.72rem 0.74rem;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 11px;
    color: inherit;
    background: rgba(255, 255, 255, 0.03);
    text-align: left;
    cursor: pointer;
  }

  .search-result strong {
    font-size: 0.84rem;
    color: #f6f8fb;
  }

  .search-result span {
    font-size: 0.72rem;
    color: rgba(194, 206, 219, 0.7);
  }

  .search-result:hover {
    border-color: rgba(255, 211, 79, 0.24);
    background: rgba(255, 211, 79, 0.06);
  }

  .center-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.45rem;
    align-items: center;
  }

  .topbar-ribbon {
    margin-top: 0.55rem;
    display: grid;
    gap: 0.42rem;
    width: min(34rem, calc(100vw - 39rem));
    min-width: 30rem;
    padding: 0.48rem 0.52rem;
    border-radius: 16px;
    background:
      linear-gradient(180deg, rgba(27, 30, 35, 0.98) 0%, rgba(14, 16, 20, 0.98) 100%);
  }

  .ribbon-row,
  .filter-token-row,
  .filter-token-list,
  .filter-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.38rem;
  }

  .ribbon-chip,
  .filter-chip,
  .filter-token,
  .suggestion-pill {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    font: inherit;
    cursor: pointer;
  }

  .ribbon-chip,
  .filter-chip,
  .suggestion-pill {
    padding: 0.42rem 0.68rem;
    font-size: 0.72rem;
    font-weight: 700;
    color: #d8e1eb;
    background: rgba(255, 255, 255, 0.05);
  }

  .ribbon-chip.active,
  .filter-chip.active {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .ribbon-chip-reset {
    color: #ffd9d9;
    background: rgba(118, 41, 41, 0.24);
  }

  .filter-token {
    display: inline-flex;
    align-items: center;
    gap: 0.42rem;
    padding: 0.34rem 0.42rem 0.34rem 0.62rem;
    font-size: 0.7rem;
    font-weight: 700;
    color: #edf2f7;
    background: rgba(255, 255, 255, 0.04);
  }

  .filter-token strong {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.15rem;
    height: 1.15rem;
    border-radius: 999px;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .traffic-counter {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.46rem 0.72rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }

  .traffic-counter strong {
    color: #f6f8fb;
    font-size: 0.8rem;
  }

  .traffic-counter small {
    color: #aeb6c2;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }

  .traffic-dot {
    width: 0.48rem;
    height: 0.48rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.28);
  }

  .traffic-dot.online {
    background: #63d77e;
    box-shadow: 0 0 0 4px rgba(99, 215, 126, 0.14);
  }

  .topbar-icon {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    font: inherit;
    font-weight: 700;
    color: #f6f8fb;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
    transition:
      background 160ms ease,
      transform 160ms ease;
  }

  .topbar-icon {
    display: grid;
    place-items: center;
    width: 2.25rem;
    height: 2.25rem;
    padding: 0;
    flex: 0 0 auto;
  }

  .topbar-action-chip {
    width: auto;
    min-width: 4.4rem;
    padding: 0 0.85rem;
    font-size: 0.72rem;
    letter-spacing: 0.04em;
  }

  .floating-messages {
    top: 5.1rem;
    left: 50%;
    transform: translateX(-50%);
    display: grid;
    gap: 0.45rem;
    width: min(40rem, calc(100vw - 2rem));
  }

  .error-banner,
  .warning-banner,
  .alert-toast {
    padding: 0.72rem 0.92rem;
    border-radius: 14px;
    backdrop-filter: blur(14px);
    box-shadow: 0 16px 34px rgba(0, 0, 0, 0.24);
    font-size: 0.84rem;
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
    overflow: hidden;
  }

  .radar-left-panel {
    top: 5.2rem;
    left: 0.95rem;
    bottom: 5.9rem;
    width: min(18rem, calc(100vw - 23rem));
    display: grid;
    grid-template-rows: auto auto auto minmax(0, 1fr);
    gap: 0.72rem;
    padding: 0.78rem;
    background:
      linear-gradient(180deg, rgba(20, 22, 26, 0.98) 0%, rgba(9, 10, 13, 0.98) 100%);
  }

  .radar-right-panel {
    top: 0.85rem;
    right: 0.95rem;
    bottom: 0.85rem;
    width: min(20rem, calc(100vw - 2rem));
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    gap: 0.7rem;
    padding: 0.78rem;
    background:
      linear-gradient(180deg, rgba(20, 22, 26, 0.98) 0%, rgba(9, 10, 13, 0.98) 100%);
  }

  .panel-stack,
  .inspector-scroll {
    display: grid;
    gap: 0.65rem;
    min-height: 0;
    overflow-y: auto;
    align-content: start;
    padding-right: 0.08rem;
  }

  .panel-stack {
    padding-right: 0.08rem;
  }

  .utility-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: start;
  }

  .utility-heading {
    display: grid;
    gap: 0.18rem;
  }

  .utility-heading span {
    color: #98a4b3;
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
  }

  .utility-heading strong {
    color: #eef3f8;
    font-size: 1rem;
    line-height: 1.15;
  }

  .utility-meta {
    display: flex;
    gap: 0.38rem;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .utility-pill,
  .utility-count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 1.95rem;
    padding: 0 0.68rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 800;
  }

  .utility-pill {
    color: #dfe7f1;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.05);
  }

  .utility-count {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .utility-tabs {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.35rem;
  }

  .utility-tab {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.48rem 0.3rem;
    font: inherit;
    font-size: 0.69rem;
    font-weight: 800;
    color: #cdd6e1;
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
    transition:
      background 160ms ease,
      border-color 160ms ease,
      color 160ms ease;
  }

  .utility-tab.active {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .widget-card {
    display: grid;
    gap: 0.55rem;
    padding: 0.84rem 0.82rem 0.78rem;
    border-radius: 18px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background:
      linear-gradient(180deg, rgba(53, 56, 62, 0.98) 0%, rgba(29, 32, 36, 0.98) 100%);
    box-shadow:
      0 18px 30px rgba(0, 0, 0, 0.24),
      inset 3px 0 0 #f5b908;
  }

  .widget-card-secondary {
    gap: 0.62rem;
  }

  .utility-summary-card {
    box-shadow:
      0 18px 30px rgba(0, 0, 0, 0.24),
      inset 3px 0 0 #45a7ee;
  }

  .filter-card {
    gap: 0.78rem;
  }

  .widget-header {
    display: flex;
    justify-content: space-between;
    gap: 0.65rem;
    align-items: center;
  }

  .widget-heading {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    min-width: 0;
  }

  .widget-header strong,
  .widget-main strong {
    color: #f6f8fb;
    font-size: 0.96rem;
  }

  .live-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2rem;
    padding: 0.24rem 0.5rem;
    border-radius: 999px;
    font-size: 0.66rem;
    font-weight: 800;
    color: #171a1f;
    background: #f5b908;
  }

  .utility-state-pill {
    min-width: 3.5rem;
    background: #45a7ee;
  }

  .widget-list {
    display: grid;
    gap: 0.42rem;
  }

  .widget-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.55rem;
    align-items: center;
    width: 100%;
    padding: 0.64rem 0.58rem;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    color: inherit;
    background: rgba(0, 0, 0, 0.2);
    text-align: left;
    cursor: pointer;
    transition:
      transform 160ms ease,
      border-color 160ms ease,
      background 160ms ease;
  }

  .widget-row:hover {
    transform: translateY(-1px);
    border-color: rgba(255, 211, 79, 0.2);
    background: rgba(0, 0, 0, 0.26);
  }

  .widget-rank {
    color: #d9dde4;
    font-weight: 800;
    font-size: 0.86rem;
  }

  .widget-main {
    display: grid;
    gap: 0.14rem;
  }

  .widget-codes {
    display: flex;
    flex-wrap: wrap;
    gap: 0.28rem;
  }

  .widget-codes small {
    padding: 0.08rem 0.34rem;
    border-radius: 6px;
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #d8e0ea;
    background: rgba(255, 255, 255, 0.08);
  }

  .widget-main span,
  .widget-empty {
    font-size: 0.72rem;
    color: #b3bcc8;
  }

  .widget-caption {
    margin: 0;
    font-size: 0.7rem;
    color: rgba(193, 202, 214, 0.78);
  }

  .filter-form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .filter-field {
    display: grid;
    gap: 0.3rem;
  }

  .filter-field span,
  .suggestion-row > span {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: rgba(179, 188, 200, 0.72);
  }

  .filter-field input,
  .filter-field select,
  .preset-save-row input {
    width: 100%;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 0.62rem 0.7rem;
    font: inherit;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.04);
    box-sizing: border-box;
  }

  .filter-field-wide {
    grid-column: 1 / -1;
  }

  .filter-suggestion-group {
    display: grid;
    gap: 0.5rem;
  }

  .suggestion-row {
    display: grid;
    gap: 0.35rem;
  }

  .suggestion-row div {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .preset-save-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.5rem;
  }

  .preset-list {
    display: grid;
    gap: 0.45rem;
  }

  .preset-card {
    display: flex;
    justify-content: space-between;
    gap: 0.7rem;
    align-items: start;
    padding: 0.72rem 0.74rem;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(0, 0, 0, 0.16);
  }

  .preset-card strong {
    display: block;
    color: #f4f7fb;
    font-size: 0.8rem;
  }

  .preset-card span {
    color: #b4becb;
    font-size: 0.7rem;
  }

  .preset-actions {
    display: flex;
    gap: 0.38rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .preset-delete {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 0.62rem 0.74rem;
    font: inherit;
    font-size: 0.74rem;
    font-weight: 700;
    color: #ffd9d9;
    background: rgba(118, 41, 41, 0.24);
    cursor: pointer;
  }

  .widget-highlight {
    display: grid;
    justify-items: end;
    gap: 0.12rem;
    min-width: 3.1rem;
  }

  .widget-highlight strong {
    font-size: 0.88rem;
    font-weight: 900;
    color: #f5b908;
  }

  .widget-highlight small {
    font-size: 0.64rem;
    color: #aeb8c6;
  }

  .mini-stat-list {
    display: grid;
    gap: 0.46rem;
  }

  .mini-stat-list div {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
    padding: 0.68rem 0.72rem;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    background: rgba(0, 0, 0, 0.18);
  }

  .mini-stat-list span {
    display: grid;
    gap: 0.14rem;
    font-size: 0.76rem;
    color: #b3bcc8;
  }

  .mini-stat-list span strong,
  .mini-stat-list div > strong {
    color: #f3f6fa;
  }

  .mini-stat-list small {
    font-size: 0.67rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: rgba(179, 188, 200, 0.66);
  }

  .widget-footer-button,
  .widget-footer-bar {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 0.66rem 0.78rem;
    font: inherit;
    font-weight: 700;
    color: #edf2f7;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
  }

  .widget-footer-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    border-radius: 14px;
    background:
      linear-gradient(180deg, rgba(51, 54, 60, 0.98) 0%, rgba(32, 35, 39, 0.98) 100%);
  }

  .widget-footer-bar span {
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.7rem;
    color: #b4bdc9;
  }

  .widget-footer-bar strong {
    color: #f5b908;
    font-size: 0.86rem;
  }

  .view-chip {
    top: 4.55rem;
    right: 21.6rem;
    display: inline-flex;
    align-items: center;
    gap: 0.42rem;
    padding: 0.52rem 0.82rem;
    border-radius: 999px;
    color: #eef3f8;
    background:
      linear-gradient(180deg, rgba(53, 56, 62, 0.98) 0%, rgba(34, 36, 41, 0.98) 100%);
    cursor: pointer;
  }

  .view-chip span {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #c3ccd7;
  }

  .view-chip strong {
    font-size: 0.86rem;
  }

  .rail-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: start;
    padding: 0.08rem 0.08rem 0.72rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }

  .rail-brand {
    display: grid;
    gap: 0.18rem;
  }

  .rail-brand span {
    color: #98a4b3;
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
  }

  .rail-brand strong {
    color: #eef3f8;
    font-size: 1rem;
    line-height: 1.15;
  }

  .rail-count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2rem;
    height: 2rem;
    padding: 0 0.55rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 800;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .rail-actions {
    display: flex;
    align-items: center;
    gap: 0.38rem;
  }

  .rail-toggle {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.42rem 0.7rem;
    font: inherit;
    font-size: 0.72rem;
    font-weight: 700;
    color: #d4dde7;
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
    transition:
      border-color 160ms ease,
      background 160ms ease,
      color 160ms ease;
  }

  .rail-toggle.active {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .rail-close {
    border: 0;
    padding: 0;
    font: inherit;
    font-size: 1.25rem;
    line-height: 1;
    color: #c8d0db;
    background: transparent;
    cursor: pointer;
  }

  .inspector-tab-row {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.38rem;
  }

  .inspector-tab {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.48rem 0.3rem;
    font: inherit;
    font-size: 0.74rem;
    font-weight: 800;
    color: #d0d9e4;
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
  }

  .inspector-tab.active {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .aircraft-workflow-panel,
  .aircraft-notes-panel {
    display: grid;
    gap: 0.75rem;
  }

  .workflow-header {
    display: flex;
    justify-content: space-between;
    gap: 0.7rem;
    align-items: start;
  }

  .workflow-header h2,
  .workflow-header p,
  .notes-empty {
    margin: 0;
  }

  .workflow-eyebrow {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: rgba(190, 203, 217, 0.62);
    margin-bottom: 0.2rem;
  }

  .workflow-status {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.34rem 0.62rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 800;
    color: #f8de88;
    background: rgba(245, 185, 8, 0.12);
    border: 1px solid rgba(245, 185, 8, 0.22);
  }

  .workflow-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.5rem;
  }

  .workflow-metrics article,
  .workflow-facts div,
  .notes-field textarea,
  .tag-editor {
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 14px;
    background:
      linear-gradient(180deg, rgba(31, 34, 39, 0.98) 0%, rgba(19, 21, 25, 0.98) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.02),
      0 14px 26px rgba(0, 0, 0, 0.2);
  }

  .workflow-metrics article,
  .workflow-facts div {
    display: grid;
    gap: 0.18rem;
    padding: 0.74rem 0.78rem;
  }

  .workflow-metrics span,
  .workflow-facts span,
  .notes-field span,
  .tag-editor-header span {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: rgba(171, 186, 202, 0.62);
  }

  .workflow-metrics strong,
  .workflow-facts strong {
    color: #f1f5fa;
    font-size: 0.95rem;
  }

  .workflow-metrics small,
  .tag-editor-header small,
  .notes-empty {
    color: rgba(190, 203, 217, 0.74);
    font-size: 0.76rem;
  }

  .workflow-facts {
    display: grid;
    gap: 0.45rem;
  }

  .workflow-actions {
    display: grid;
    gap: 0.45rem;
  }

  .workflow-button {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 0.78rem 0.84rem;
    font: inherit;
    font-weight: 700;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
  }

  .workflow-button.primary {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .workflow-button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .notes-field {
    display: grid;
    gap: 0.34rem;
  }

  .notes-field textarea {
    min-height: 10rem;
    padding: 0.82rem 0.86rem;
    color: #eef3f8;
    box-sizing: border-box;
  }

  .tag-editor {
    display: grid;
    gap: 0.65rem;
    padding: 0.78rem 0.82rem;
  }

  .tag-editor-header {
    display: flex;
    justify-content: space-between;
    gap: 0.6rem;
    align-items: center;
  }

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.38rem;
  }

  .tag-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.38rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.34rem 0.4rem 0.34rem 0.62rem;
    font: inherit;
    font-size: 0.73rem;
    font-weight: 700;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
  }

  .tag-pill strong {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.05rem;
    height: 1.05rem;
    border-radius: 999px;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .tag-input-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.45rem;
  }

  .tag-input-row input {
    width: 100%;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 0.72rem 0.76rem;
    font: inherit;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.04);
    box-sizing: border-box;
  }

  .bottom-dock {
    left: 50%;
    bottom: 0.95rem;
    transform: translateX(-50%);
    display: inline-flex;
    gap: 0.32rem;
    padding: 0.28rem;
    border-radius: 20px;
    background:
      linear-gradient(180deg, rgba(25, 27, 31, 0.97) 0%, rgba(12, 14, 18, 0.97) 100%);
  }

  .dock-button {
    display: grid;
    justify-items: center;
    gap: 0.3rem;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 13px;
    min-width: 4.8rem;
    padding: 0.56rem 0.72rem 0.5rem;
    font: inherit;
    font-weight: 700;
    color: #eef2f6;
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
    transition:
      transform 160ms ease,
      border-color 160ms ease,
      background 160ms ease;
  }

  .dock-label {
    font-size: 0.7rem;
    line-height: 1;
  }

  .dock-glyph {
    position: relative;
    width: 1.15rem;
    height: 1.15rem;
    color: #dce4ee;
  }

  .dock-glyph-scope {
    border: 2px solid currentColor;
    border-radius: 999px;
  }

  .dock-glyph-scope::after {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0.3rem;
    height: 0.3rem;
    border-radius: 999px;
    background: currentColor;
    transform: translate(-50%, -50%);
  }

  .dock-glyph-grid::before,
  .dock-glyph-grid::after,
  .dock-glyph-map::before,
  .dock-glyph-map::after,
  .dock-glyph-fullscreen::before,
  .dock-glyph-fullscreen::after {
    content: "";
    position: absolute;
  }

  .dock-glyph-grid::before {
    inset: 0.1rem;
    border: 2px solid currentColor;
    border-radius: 0.2rem;
  }

  .dock-glyph-grid::after {
    top: 0.16rem;
    bottom: 0.16rem;
    left: 50%;
    width: 2px;
    background: currentColor;
    transform: translateX(-50%);
    box-shadow:
      -0.28rem 0 0 currentColor,
      0.28rem 0 0 currentColor;
  }

  .dock-glyph-map::before {
    inset: 0.12rem 0.2rem;
    border-top: 2px solid currentColor;
    border-bottom: 2px solid currentColor;
    transform: skew(-18deg);
  }

  .dock-glyph-map::after {
    top: 0.18rem;
    bottom: 0.18rem;
    left: 50%;
    width: 2px;
    background: currentColor;
    transform: translateX(-50%) skew(-18deg);
    box-shadow:
      -0.28rem 0 0 currentColor,
      0.28rem 0 0 currentColor;
  }

  .dock-glyph-fullscreen {
    border-radius: 0.15rem;
  }

  .dock-glyph-fullscreen::before {
    inset: 0;
    border-top: 2px solid currentColor;
    border-right: 2px solid currentColor;
    border-bottom: 2px solid currentColor;
    border-left: 2px solid currentColor;
    clip-path: polygon(
      0 0, 34% 0, 34% 12%, 12% 12%, 12% 34%, 0 34%,
      0 100%, 34% 100%, 34% 88%, 12% 88%, 12% 66%, 0 66%,
      100% 66%, 88% 66%, 88% 88%, 66% 88%, 66% 100%, 100% 100%,
      100% 34%, 66% 34%, 66% 12%, 88% 12%, 88% 34%, 100% 34%
    );
  }

  .dock-button:hover {
    transform: translateY(-1px);
    border-color: rgba(255, 211, 79, 0.24);
    background: rgba(255, 255, 255, 0.06);
  }

  .sidebar-backdrop {
    display: none;
  }

  .utility-backdrop {
    z-index: 1240;
  }

  :global(.panel-stack::-webkit-scrollbar),
  :global(.inspector-scroll::-webkit-scrollbar) {
    width: 9px;
  }

  :global(.panel-stack::-webkit-scrollbar-thumb),
  :global(.inspector-scroll::-webkit-scrollbar-thumb) {
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
  }

  @media (max-width: 1200px) {
    .center-bar {
      width: min(32rem, calc(100vw - 24rem));
      min-width: 0;
    }

    .topbar-ribbon {
      width: min(32rem, calc(100vw - 24rem));
      min-width: 0;
    }
  }

  @media (max-width: 960px) {
    .radar-left-panel {
      top: 4.65rem;
      right: 0.75rem;
      bottom: 0.75rem;
      left: 0.75rem;
      width: auto;
      transform: translateY(110%);
      transition: transform 180ms ease;
      z-index: 1290;
    }

    .radar-left-panel.open {
      transform: translateY(0);
    }

    .view-chip {
      right: 0.75rem;
    }

    .bottom-dock {
      bottom: 0.75rem;
      width: calc(100vw - 1.5rem);
      justify-content: center;
    }

    .dock-button {
      flex: 1 1 0;
      padding-inline: 0.5rem;
    }

    .radar-right-panel {
      top: 4.65rem;
      right: 0.75rem;
      bottom: 0.75rem;
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

    .center-bar {
      width: min(32rem, calc(100vw - 1.5rem));
    }

    .topbar-ribbon {
      width: min(32rem, calc(100vw - 1.5rem));
      min-width: 0;
    }
  }

  @media (max-width: 720px) {
    .radar-topbar {
      top: 0.7rem;
      left: 0.75rem;
      right: 0.75rem;
      transform: none;
      display: block;
    }

    .center-bar {
      grid-template-columns: 1fr;
      width: auto;
      min-width: 0;
      padding: 0.62rem 0.68rem;
    }

    .topbar-ribbon {
      width: auto;
      min-width: 0;
      padding: 0.54rem 0.58rem;
    }

    .center-actions {
      justify-content: flex-start;
      flex-wrap: wrap;
    }

    .filter-form-grid,
    .preset-save-row,
    .preset-card,
    .tag-input-row,
    .workflow-metrics,
    .inspector-tab-row,
    .workflow-header {
      grid-template-columns: 1fr;
      display: grid;
    }

    .view-chip {
      top: auto;
      right: 0.75rem;
      bottom: 5rem;
    }

    .bottom-dock {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
