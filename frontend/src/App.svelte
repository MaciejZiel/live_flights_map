<script>
  import { onMount } from "svelte";

  import FlightDetailsPanel from "./lib/components/FlightDetailsPanel.svelte";
  import ComparisonPanel from "./lib/components/ComparisonPanel.svelte";
  import SavedViewsPanel from "./lib/components/SavedViewsPanel.svelte";
  import AlertPanel from "./lib/components/AlertPanel.svelte";
  import LegendPanel from "./lib/components/LegendPanel.svelte";
  import MonitoringSessionsPanel from "./lib/components/MonitoringSessionsPanel.svelte";
  import OnboardingPanel from "./lib/components/OnboardingPanel.svelte";
  import ReplayTimeline from "./lib/components/ReplayTimeline.svelte";
  import ShortcutsPanel from "./lib/components/ShortcutsPanel.svelte";
  import WatchlistPanel from "./lib/components/WatchlistPanel.svelte";
  import FlightMap from "./lib/components/FlightMap.svelte";
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
  let mapViewport = null;
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
  $: activeAlertEvents = alertEvents.slice(0, 4);
  $: mapCenterLabel = mapViewport?.center
    ? `${mapViewport.center[0].toFixed(2)}, ${mapViewport.center[1].toFixed(2)}`
    : "52.15, 19.40";
  $: zoomLabel = Number.isFinite(mapViewport?.zoom) ? mapViewport.zoom.toFixed(1) : "6.0";
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
      <div class="overlay-card brand-block">
        <div class="brand-mark">24</div>
        <div class="brand-copy">
          <p class="section-kicker">Live air traffic</p>
          <strong>Live Flights Radar</strong>
        </div>
      </div>

      <div class="overlay-card search-block">
        <label class="search-field">
          <input
            bind:this={searchInput}
            bind:value={filters.query}
            type="text"
            placeholder="Find flights, ICAO24, operator, country"
            title="Search by callsign, ICAO24, origin country, or operator code"
          />
        </label>
        <div class="search-meta">
          <span>{renderedFlights.length} visible on map</span>
          <span>{getFreshnessLabel(state.fetchedAt)} · {state.transport === "sse" ? "SSE" : "Polling"}</span>
        </div>
      </div>

      <div class="topbar-actions">
        <div class="overlay-card status-strip">
          <div class:online={["success", "refreshing"].includes(state.status)} class="status-pill">
            {#if state.status === "loading"}
              Syncing
            {:else if state.status === "refreshing"}
              Live sync
            {:else if state.status === "error"}
              Upstream error
            {:else if state.reason === "rate_limit" || state.reason === "cooldown"}
              Rate limited
            {:else if state.source === "cache"}
              Cached
            {:else if state.status === "success"}
              Live
            {:else}
              Idle
            {/if}
          </div>
          <div class="status-copy">
            <strong>{formatCompactCount(visibleTrackedCount)}</strong>
            <span>tracked</span>
          </div>
          <div class="status-copy">
            <strong>{getConfidenceLabel(state)}</strong>
            <span>{formatTimestamp(state.fetchedAt)}</span>
          </div>
        </div>

        <div class="overlay-card theme-switcher" role="group" aria-label="Theme switcher">
          <button class:active={theme === "light"} type="button" on:click={() => setTheme("light")}>
            Day
          </button>
          <button class:active={theme === "dark"} type="button" on:click={() => setTheme("dark")}>
            Night
          </button>
        </div>

        <button
          class="overlay-card topbar-action"
          type="button"
          title="Copy a link to the current map state and selected aircraft"
          on:click={copyShareLink}
        >
          Share
        </button>

        {#if isMobileViewport}
          <button class="overlay-card topbar-action accent" type="button" on:click={toggleMobileSidebar}>
            {mobileSidebarOpen ? "Hide panel" : "Open panel"}
          </button>
        {/if}

        {#if shareFeedback}
          <span class="share-feedback">{shareFeedback}</span>
        {/if}
      </div>
    </header>

    <div class="floating-messages">
      {#if state.error}
        <div class="error-banner">{state.error}</div>
      {/if}

      {#if state.warning}
        <div class="warning-banner">{state.warning}</div>
      {/if}

      {#if alertToast}
        <div class="alert-toast">{alertToast.message}</div>
      {/if}
    </div>

    <aside class="overlay-card radar-left-panel">
      <div class="panel-stack">
        {#if !onboardingDismissed}
          <OnboardingPanel onDismiss={dismissOnboarding} />
        {/if}

        <section class="hud-card">
          <div class="card-header">
            <div>
              <p class="section-kicker">Hot traffic</p>
              <h2>Fastest visible flights</h2>
            </div>
            <span class="card-badge">{leaderboardFlights.length}</span>
          </div>

          {#if leaderboardFlights.length}
            <div class="traffic-list">
              {#each leaderboardFlights as flight, index}
                <button
                  class:selected={flight.icao24 === selectedIcao24}
                  class="traffic-row"
                  type="button"
                  on:click={() => {
                    selectedIcao24 = flight.icao24;
                    inspectorTab = "details";
                    if (isMobileViewport) {
                      mobileSidebarOpen = true;
                    }
                  }}
                >
                  <span class="traffic-rank">{index + 1}</span>
                  <span class="traffic-main">
                    <strong>{flight.callsign ?? flight.icao24}</strong>
                    <span>{flight.origin_country ?? "Unknown"}</span>
                  </span>
                  <span class="traffic-meta">
                    <strong>{formatSpeed(flight.velocity)}</strong>
                    <span>{formatAltitude(flight.altitude)}</span>
                  </span>
                </button>
              {/each}
            </div>
          {:else}
            <p class="empty-copy">Waiting for traffic inside the active radar area.</p>
          {/if}
        </section>

        <section class="hud-card">
          <div class="card-header">
            <div>
              <p class="section-kicker">Overview</p>
              <h2>Radar snapshot</h2>
            </div>
            <span class="card-badge">{zoomLabel}x</span>
          </div>

          <div class="stat-grid">
            <article class="stat-card">
              <span>Tracked</span>
              <strong>{formatCompactCount(visibleTrackedCount)}</strong>
            </article>
            <article class="stat-card">
              <span>Airborne</span>
              <strong>{airborneCount}</strong>
            </article>
            <article class="stat-card">
              <span>Ground</span>
              <strong>{groundCount}</strong>
            </article>
            <article class="stat-card">
              <span>Avg speed</span>
              <strong>{averageSpeedKmh} km/h</strong>
            </article>
          </div>

          <div class="snapshot-meta">
            <span>Center</span>
            <strong>{mapCenterLabel}</strong>
          </div>
          <div class="snapshot-meta">
            <span>Mode</span>
            <strong>{activeMonitoringSession ? "Saved session" : activeReplaySnapshot ? "Replay" : "Live"}</strong>
          </div>
          <div class="snapshot-meta">
            <span>Progressive cap</span>
            <strong>{displayLimit ? displayLimit : "Off"}</strong>
          </div>
        </section>

        <section class="hud-card">
          <div class="card-header">
            <div>
              <p class="section-kicker">Radar tools</p>
              <h2>Basemap and focus</h2>
            </div>
          </div>

          <div class="segmented-control">
            <button class:active={mapStyle === "standard"} type="button" on:click={() => (mapStyle = "standard")}>
              Radar
            </button>
            <button class:active={mapStyle === "satellite"} type="button" on:click={() => (mapStyle = "satellite")}>
              Sat
            </button>
            <button class:active={mapStyle === "dark"} type="button" on:click={() => (mapStyle = "dark")}>
              Dark
            </button>
            <button class:active={mapStyle === "aviation"} type="button" on:click={() => (mapStyle = "aviation")}>
              IFR
            </button>
          </div>

          <div class="chip-list">
            <button class="tool-chip" type="button" on:click={() => triggerViewPreset("poland")}>Poland</button>
            <button class="tool-chip" type="button" on:click={() => triggerViewPreset("europe")}>Europe</button>
            <button class="tool-chip" type="button" on:click={() => triggerViewPreset("world")}>World</button>
            <button class="tool-chip accent" type="button" on:click={triggerFullscreenToggle}>Fullscreen</button>
          </div>
        </section>

        <section class="hud-card">
          <div class="card-header">
            <div>
              <p class="section-kicker">Presets</p>
              <h2>Saved filters</h2>
            </div>
            <span class="card-badge">{activeFilterCount}</span>
          </div>

          {#if filterPresets.length}
            <div class="chip-list">
              {#each filterPresets.slice(0, 6) as preset}
                <button class="tool-chip" type="button" on:click={() => applyFilterPreset(preset)}>
                  {preset.name}
                </button>
              {/each}
            </div>
          {:else}
            <p class="empty-copy">Save a filter set from the inspector to reuse it quickly.</p>
          {/if}
        </section>

        {#if activeAlertEvents.length}
          <section class="hud-card">
            <div class="card-header">
              <div>
                <p class="section-kicker">Recent alerts</p>
                <h2>Activity log</h2>
              </div>
              <span class="card-badge">{activeAlertEvents.length}</span>
            </div>

            <div class="event-snippets">
              {#each activeAlertEvents as event}
                <article class="event-snippet">
                  <strong>{event.message}</strong>
                  <span>{formatTimestamp(event.timestamp)}</span>
                </article>
              {/each}
            </div>
          </section>
        {/if}
      </div>
    </aside>

    {#if isMobileViewport && mobileSidebarOpen}
      <button class="sidebar-backdrop" type="button" aria-label="Close panel" on:click={closeMobileSidebar}></button>
    {/if}

    <aside class:open={mobileSidebarOpen} class="overlay-card radar-right-panel">
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
            followAircraft={followAircraft}
            trailPoints={selectedFlightTrail}
            isWatched={selectedFlight ? watchlist.includes(selectedFlight.icao24) : false}
            annotation={selectedFlightAnnotation}
            onToggleFollow={toggleFollowAircraft}
            onToggleWatch={toggleSelectedFlightWatchlist}
            onUpdateNotes={updateSelectedFlightNotes}
            onAddTag={addSelectedFlightTag}
            onRemoveTag={removeSelectedFlightTag}
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
    </aside>

    <nav class="overlay-card bottom-dock" aria-label="Quick radar actions">
      <button class:active={inspectorTab === "details"} class="dock-button" type="button" on:click={() => openInspectorTab("details")}>
        Aircraft
      </button>
      <button class:active={inspectorTab === "filters"} class="dock-button" type="button" on:click={() => openInspectorTab("filters")}>
        Filters
      </button>
      <button class:active={inspectorTab === "watchlist"} class="dock-button" type="button" on:click={() => openInspectorTab("watchlist")}>
        Watchlist
      </button>
      <button class:active={inspectorTab === "replay"} class="dock-button" type="button" on:click={() => openInspectorTab("replay")}>
        Playback
      </button>
      <button class:active={inspectorTab === "views"} class="dock-button" type="button" on:click={() => openInspectorTab("views")}>
        Views
      </button>
      <button class:active={inspectorTab === "alerts"} class="dock-button" type="button" on:click={() => openInspectorTab("alerts")}>
        Alerts
      </button>
      <button class:active={inspectorTab === "help"} class="dock-button" type="button" on:click={() => openInspectorTab("help")}>
        Help
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

  .overlay-card,
  .hud-card {
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
    top: 1rem;
    left: 1rem;
    right: 1rem;
    display: grid;
    grid-template-columns: auto minmax(280px, 1fr) auto;
    gap: 0.9rem;
    align-items: start;
  }

  .brand-block {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    padding: 0.9rem 1rem;
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

  .section-kicker {
    margin: 0 0 0.22rem;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #f5b908;
  }

  .search-block {
    display: grid;
    gap: 0.5rem;
    padding: 0.85rem 1rem;
  }

  .search-field input {
    width: 100%;
    border: 0;
    padding: 0;
    font: inherit;
    font-size: 0.98rem;
    color: #f6f8fb;
    background: transparent;
    outline: none;
  }

  .search-field input::placeholder {
    color: rgba(225, 231, 241, 0.58);
  }

  .search-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.8rem;
    font-size: 0.78rem;
    color: #aeb9c7;
  }

  .topbar-actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 0.75rem;
    align-items: center;
  }

  .status-strip {
    display: flex;
    gap: 0.9rem;
    align-items: center;
    padding: 0.72rem 0.95rem;
  }

  .status-copy {
    display: grid;
    gap: 0.12rem;
  }

  .status-copy strong {
    font-size: 0.88rem;
    color: #f6f8fb;
  }

  .status-copy span,
  .share-feedback,
  .inspector-subtitle,
  .empty-copy {
    font-size: 0.78rem;
    color: #aeb9c7;
  }

  .theme-switcher {
    display: inline-grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.35rem;
    padding: 0.35rem;
  }

  .theme-switcher button,
  .topbar-action,
  .tool-chip,
  .dock-button,
  .mobile-sidebar-close,
  .hero-action,
  .reset-button,
  .secondary-button,
  .preset-delete,
  .segmented-control button {
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

  .theme-switcher button.active,
  .tool-chip.accent,
  .topbar-action.accent,
  .hero-action.primary,
  .reset-button,
  .segmented-control button.active,
  .dock-button.active {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .topbar-action,
  .mobile-sidebar-close {
    padding-inline: 1rem;
  }

  .floating-messages {
    top: 5.7rem;
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
    top: 6.8rem;
    bottom: 5.8rem;
    width: min(24rem, calc(100vw - 2rem));
    padding: 1rem;
    overflow: hidden;
  }

  .radar-left-panel {
    left: 1rem;
  }

  .radar-right-panel {
    right: 1rem;
    display: grid;
    grid-template-rows: auto auto auto minmax(0, 1fr);
    gap: 0.9rem;
  }

  .panel-stack,
  .inspector-scroll {
    display: grid;
    gap: 0.9rem;
    min-height: 0;
    overflow-y: auto;
    padding-right: 0.15rem;
  }

  .hud-card,
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

  .traffic-list,
  .event-snippets {
    display: grid;
    gap: 0.6rem;
  }

  .traffic-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.75rem;
    align-items: center;
    width: 100%;
    padding: 0.75rem 0.85rem;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    color: inherit;
    background: rgba(255, 255, 255, 0.04);
    text-align: left;
    cursor: pointer;
  }

  .traffic-row.selected {
    border-color: rgba(245, 185, 8, 0.7);
    box-shadow: inset 0 0 0 1px rgba(245, 185, 8, 0.55);
  }

  .traffic-rank {
    display: grid;
    place-items: center;
    width: 1.8rem;
    height: 1.8rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 800;
    color: #171a1f;
    background: #ffd34f;
  }

  .traffic-main,
  .traffic-meta,
  .snapshot-meta,
  .event-snippet {
    display: grid;
    gap: 0.14rem;
  }

  .traffic-main strong,
  .traffic-meta strong,
  .snapshot-meta strong,
  .event-snippet strong,
  .hero-metric strong {
    color: #f6f8fb;
  }

  .traffic-main span,
  .traffic-meta span,
  .snapshot-meta span,
  .event-snippet span,
  .hero-metric span,
  .stat-card span,
  .field span,
  .checkbox-field span {
    color: #aeb9c7;
    font-size: 0.78rem;
  }

  .stat-grid,
  .hero-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.65rem;
    margin-bottom: 0.8rem;
  }

  .stat-card,
  .hero-metric {
    display: grid;
    gap: 0.2rem;
    padding: 0.8rem 0.85rem;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.04);
  }

  .snapshot-meta {
    padding-top: 0.55rem;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    margin-top: 0.55rem;
  }

  .segmented-control,
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
    flex-wrap: wrap;
    gap: 0.5rem;
    width: min(52rem, calc(100vw - 2rem));
    padding: 0.5rem;
    justify-content: center;
  }

  .dock-button {
    flex: 1 1 6rem;
    border-radius: 16px;
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
      grid-template-columns: 1fr;
    }

    .topbar-actions {
      justify-content: flex-start;
    }
  }

  @media (max-width: 960px) {
    .radar-left-panel {
      display: none;
    }

    .radar-right-panel {
      top: 5.6rem;
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
    .segmented-control,
    .chip-list,
    .hero-metrics,
    .stat-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 720px) {
    .radar-topbar {
      top: 0.75rem;
      left: 0.75rem;
      right: 0.75rem;
      gap: 0.65rem;
    }

    .brand-block,
    .search-block,
    .status-strip {
      padding: 0.75rem 0.85rem;
    }

    .status-strip {
      display: grid;
      grid-template-columns: 1fr 1fr;
    }

    .inspector-tabs {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .flight-hero-header,
    .card-header,
    .topbar-actions {
      display: grid;
    }

    .preset-save-row,
    .preset-item {
      grid-template-columns: 1fr;
    }
  }
</style>
