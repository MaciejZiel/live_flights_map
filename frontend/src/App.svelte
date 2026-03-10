<script>
  import { onMount } from "svelte";

  import FlightDetailsPanel from "./lib/components/FlightDetailsPanel.svelte";
  import AirportDetailsPanel from "./lib/components/AirportDetailsPanel.svelte";
  import EntitySearchPanel from "./lib/components/EntitySearchPanel.svelte";
  import TrafficBoardPanel from "./lib/components/TrafficBoardPanel.svelte";
  import WatchlistPanel from "./lib/components/WatchlistPanel.svelte";
  import WorkspaceProfilesPanel from "./lib/components/WorkspaceProfilesPanel.svelte";
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
    createWorkspaceProfile,
    fetchAirportDashboard,
    fetchAirports,
    fetchAirportWeather,
    fetchFlightDetails,
    fetchGlobalTrafficBoard,
    fetchFlightTrail,
    fetchReplayHistory,
    fetchWorkspaceProfiles,
    fetchWorkspaceState,
    saveWorkspaceState,
    searchFlights,
  } from "./lib/api/flights.js";
  import { flightsStore } from "./lib/stores/flights.js";
  import {
    formatAltitude,
    formatFlightStatus,
    formatHeading,
    formatSpeed,
    formatVerticalRate,
  } from "./lib/utils/flightFormatters.js";
  import { getTrailPoints, updateFlightHistory } from "./lib/utils/flightHistory.js";
  import {
    classifyTrafficCategory,
    TRAFFIC_CATEGORY_OPTIONS,
  } from "./lib/utils/trafficCategories.js";
  import {
    deriveOperatorCode,
    matchesAirportTrafficFilter,
    matchesFlightSearch,
  } from "./lib/utils/flightMatching.js";
  import {
    loadUserPreferences,
    normalizeUserPreferences,
    saveUserPreferences,
  } from "./lib/utils/userPreferences.js";
  import {
    buildAirportReportCsv,
    buildPrintableRadarReport,
    buildTrafficReportCsv,
  } from "./lib/utils/reporting.js";

  let state = {
    status: "idle",
    flights: [],
    error: null,
    fetchedAt: null,
    count: 0,
    bbox: null,
  };

  function handleFlightsStoreChange(value) {
    state = value;

    if (value.fetchedAt && value.fetchedAt !== lastHistoryFetchKey) {
      flightHistory = updateFlightHistory(flightHistory, value.flights ?? [], value.fetchedAt);
      lastHistoryFetchKey = value.fetchedAt;
    }

    if (value.fetchedAt && value.fetchedAt !== lastReplaySnapshotKey) {
      snapshotHistory = pushReplaySnapshot(snapshotHistory, value);
      lastReplaySnapshotKey = value.fetchedAt;
    }
  }

  let filters = {
    query: "",
    minAltitude: "",
    minSpeed: "",
    aircraftType: "",
    country: "",
    operator: "",
    route: "",
    airportCode: "",
    airportFlow: "all",
    trafficState: "all",
    trafficCategory: "all",
    headingBand: "any",
    hideGroundTraffic: true,
    recentActivity: "any",
    dimFilteredTraffic: true,
  };
  let selectedIcao24 = null;
  let selectedAirportCode = null;
  let selectedAirportSnapshot = null;
  let selectedEntityContext = null;
  let followAircraft = false;
  let mapStyle = "standard";
  let weatherLayerEnabled = false;
  let showAirportMarkers = true;
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
  let workspaceProfiles = [];
  let activeWorkspaceProfileId = null;
  let workspaceSyncStatus = "idle";
  let workspaceSyncError = null;
  let workspaceUpdatedAt = null;
  let workspaceHydrating = false;
  let workspaceReady = false;
  let workspaceSaveTimer = null;
  let workspaceProfileDraft = "";
  let isMobileViewport = false;
  let mobileSidebarOpen = true;
  let mobileUtilityOpen = false;
  let inspectorScroll;
  let utilityPanelMode = "radar";
  let inspectorTab = "details";
  let snapshotHistory = [];
  let replaySnapshotCursor = null;
  let lastReplaySnapshotKey = null;
  let replayPlaybackActive = false;
  let replayPlaybackTimer = null;
  let replayPlaybackSpeed = 1;
  let lastInspectorScrollFlightKey = null;
  let shareFeedback = "";
  let shareFeedbackTimer = null;
  let reportFeedback = "";
  let reportFeedbackTimer = null;
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
  let selectedFlightTrackCursor = -1;
  let lastSelectedFlightTrackKey = null;
  let selectedFlightTrackPoint = null;
  let selectedFlightTrackSliderValue = 0;
  let selectedTagDraft = "";
  let archivedReplayStatus = "idle";
  let archivedReplayError = null;
  let archivedReplayRequestId = 0;
  let lastArchivedReplayBboxKey = null;
  let replayHydrationTimer = null;
  let replayWindowMinutes = 90;
  let flattenedSearchResults = [];
  let activeSearchResult = null;
  let activeSearchResultKey = "";
  let searchNavigationIndex = -1;
  let searchSuggestionsDismissed = false;
  let lastSearchQuery = "";
  let replayArchiveRequestKey = null;
  let remoteSearchResults = [];
  let remoteSearchGroups = {};
  let remoteSearchCount = 0;
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
  let savedEntities = [];
  let suppressSelectionClearUntil = 0;
  let airportFeed = {
    status: "idle",
    airports: [],
    error: null,
  };
  let airportFeedRequestId = 0;
  let airportFeedDebounceTimer = null;
  let selectedAirportDashboard = null;
  let selectedAirportStatus = "idle";
  let selectedAirportError = null;
  let selectedAirportWeather = null;
  let selectedAirportWeatherStatus = "idle";
  let selectedAirportWeatherError = null;
  let selectedAirportRequestId = 0;
  let selectedAirportWeatherRequestId = 0;
  let lastSelectedAirportKey = null;
  const unsubscribe = flightsStore.subscribe(handleFlightsStoreChange);

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
      savedEntities = savedPreferences.savedEntities ?? savedEntities;
      weatherLayerEnabled = savedPreferences.weatherLayerEnabled ?? weatherLayerEnabled;
      showAirportMarkers = savedPreferences.showAirportMarkers ?? showAirportMarkers;
      selectedAirportCode = savedPreferences.selectedAirportCode ?? selectedAirportCode;
      replayWindowMinutes = savedPreferences.replayWindowMinutes ?? replayWindowMinutes;
      replayPlaybackSpeed = savedPreferences.replayPlaybackSpeed ?? replayPlaybackSpeed;
    }

    applySharedStateFromUrl();

    syncThemeClass(theme);
    preferencesReady = true;
    flightsStore.start();
    refreshGlobalTrafficBoard();
    initializeWorkspace();
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
      if (reportFeedbackTimer) {
        window.clearTimeout(reportFeedbackTimer);
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
      if (airportFeedDebounceTimer) {
        window.clearTimeout(airportFeedDebounceTimer);
      }
      if (workspaceSaveTimer) {
        window.clearTimeout(workspaceSaveTimer);
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
    const normalizedFilters = {
      query: "",
      minAltitude: "",
      minSpeed: "",
      aircraftType: "",
      country: "",
      operator: "",
      route: "",
      airportCode: "",
      airportFlow: "all",
      trafficState: "all",
      trafficCategory: "all",
      headingBand: "any",
      hideGroundTraffic: true,
      recentActivity: "any",
      ...currentFilters,
    };

    return [
      normalizedFilters.query.trim(),
      normalizedFilters.minAltitude,
      normalizedFilters.minSpeed,
      normalizedFilters.aircraftType.trim(),
      normalizedFilters.country.trim(),
      normalizedFilters.operator.trim(),
      normalizedFilters.route.trim(),
      normalizedFilters.airportCode.trim(),
      normalizedFilters.airportCode.trim() && normalizedFilters.airportFlow !== "all",
      normalizedFilters.trafficState !== "all",
      normalizedFilters.trafficCategory !== "all",
      normalizedFilters.headingBand !== "any",
      !normalizedFilters.hideGroundTraffic,
      normalizedFilters.recentActivity !== "any",
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

  function formatAirportCode(airport) {
    return airport?.iata ?? airport?.icao ?? airport?.location ?? "?";
  }

  function formatQuickRoute(airports) {
    if (!airports?.length) {
      return null;
    }

    if (airports.length === 1) {
      return formatAirportCode(airports[0]);
    }

    return `${formatAirportCode(airports[0])} -> ${formatAirportCode(airports[airports.length - 1])}`;
  }

  function normalizeAirportKey(airport) {
    return String(airport?.entity_key ?? airport?.iata ?? airport?.icao ?? "")
      .trim()
      .toUpperCase();
  }

  function getEntityBookmarkKey(entityType, entityKey) {
    return `${entityType}:${String(entityKey ?? "").trim().toLowerCase()}`;
  }

  function buildEntityBookmark(entity) {
    const entityType = entity?.entity_type ?? (entity?.icao24 ? "flight" : null);
    const entityKey =
      entity?.entity_key ??
      entity?.icao24 ??
      entity?.iata ??
      entity?.icao ??
      entity?.callsign ??
      entity?.label;
    if (!entityType || !entityKey) {
      return null;
    }

    return {
      entity_type: entityType,
      entity_key: String(entityKey),
      label:
        entity?.label ??
        entity?.callsign ??
        entity?.registration ??
        entity?.iata ??
        entity?.icao ??
        String(entityKey).toUpperCase(),
      subtitle:
        entity?.subtitle ??
        [entity?.city, entity?.country].filter(Boolean).join(", ") ??
        entity?.origin_country ??
        "Saved entity",
      latitude: entity?.latitude ?? null,
      longitude: entity?.longitude ?? null,
      zoom: entity?.zoom ?? null,
      bbox: entity?.bbox ?? null,
      payload: {
        icao24: entity?.icao24 ?? null,
        callsign: entity?.callsign ?? null,
        registration: entity?.registration ?? null,
        type_code: entity?.type_code ?? null,
        origin_country: entity?.origin_country ?? null,
        altitude: entity?.altitude ?? null,
        velocity: entity?.velocity ?? null,
        vertical_rate: entity?.vertical_rate ?? null,
        true_track: entity?.true_track ?? null,
        on_ground: entity?.on_ground ?? null,
        fetched_at: entity?.fetched_at ?? null,
        iata: entity?.iata ?? null,
        icao: entity?.icao ?? null,
      },
    };
  }

  function isEntityBookmarked(entityType, entityKey) {
    const bookmarkKey = getEntityBookmarkKey(entityType, entityKey);
    return savedEntities.some(
      (entry) => getEntityBookmarkKey(entry.entity_type, entry.entity_key) === bookmarkKey
    );
  }

  function saveEntityBookmark(entity) {
    const bookmark = buildEntityBookmark(entity);
    if (!bookmark) {
      return null;
    }

    const bookmarkKey = getEntityBookmarkKey(bookmark.entity_type, bookmark.entity_key);
    savedEntities = [
      bookmark,
      ...savedEntities.filter(
        (entry) => getEntityBookmarkKey(entry.entity_type, entry.entity_key) !== bookmarkKey
      ),
    ].slice(0, 36);
    return bookmark;
  }

  function toggleEntityBookmark(entity) {
    const bookmark = buildEntityBookmark(entity);
    if (!bookmark) {
      return;
    }

    const bookmarkKey = getEntityBookmarkKey(bookmark.entity_type, bookmark.entity_key);
    if (
      savedEntities.some(
        (entry) => getEntityBookmarkKey(entry.entity_type, entry.entity_key) === bookmarkKey
      )
    ) {
      savedEntities = savedEntities.filter(
        (entry) => getEntityBookmarkKey(entry.entity_type, entry.entity_key) !== bookmarkKey
      );
      return;
    }

    savedEntities = [
      bookmark,
      ...savedEntities.filter(
        (entry) => getEntityBookmarkKey(entry.entity_type, entry.entity_key) !== bookmarkKey
      ),
    ].slice(0, 36);
  }

  function buildCurrentAreaEntity() {
    if (!state.bbox || !mapViewport?.center) {
      return null;
    }

    const bbox = {
      lamin: Number(state.bbox.lamin.toFixed(4)),
      lamax: Number(state.bbox.lamax.toFixed(4)),
      lomin: Number(state.bbox.lomin.toFixed(4)),
      lomax: Number(state.bbox.lomax.toFixed(4)),
    };
    const zoom = Number.isFinite(mapViewport.zoom) ? Number(mapViewport.zoom.toFixed(1)) : 6.5;
    const centerLatitude = Number(mapViewport.center[0].toFixed(3));
    const centerLongitude = Number(mapViewport.center[1].toFixed(3));
    const entityKey = `bbox:${bbox.lamin}:${bbox.lamax}:${bbox.lomin}:${bbox.lomax}`;

    return {
      entity_type: "location",
      entity_key: entityKey,
      label: `Area ${centerLatitude}, ${centerLongitude}`,
      subtitle: `Zoom ${zoom} · ${visibleTrackedCount} aircraft in view`,
      latitude: mapViewport.center[0],
      longitude: mapViewport.center[1],
      zoom,
      bbox,
    };
  }

  function saveCurrentMapArea() {
    const areaEntity = buildCurrentAreaEntity();
    if (!areaEntity) {
      return;
    }

    const bookmark = saveEntityBookmark(areaEntity);
    if (bookmark) {
      openEntityContext(bookmark);
    }
  }

  function monitorCurrentMapArea() {
    const areaEntity = buildCurrentAreaEntity();
    if (!areaEntity) {
      return;
    }

    const bookmark = saveEntityBookmark(areaEntity);
    addAlertRule({
      type: "area",
      query: areaEntity.label,
      payload: {
        bbox: areaEntity.bbox,
      },
    });
    if (bookmark) {
      openEntityContext(bookmark);
    }
  }

  function removeSavedEntity(entityType, entityKey) {
    const bookmarkKey = getEntityBookmarkKey(entityType, entityKey);
    savedEntities = savedEntities.filter(
      (entry) => getEntityBookmarkKey(entry.entity_type, entry.entity_key) !== bookmarkKey
    );
  }

  function openSavedEntity(entity) {
    if (!entity) {
      return;
    }

    if (entity.entity_type === "flight" || entity.entity_type === "aircraft") {
      const payload = entity.payload ?? {};
      openFlightInspector(
        {
          icao24: payload.icao24 ?? entity.entity_key,
          callsign: payload.callsign ?? entity.label ?? null,
          registration: payload.registration ?? null,
          type_code: payload.type_code ?? null,
          origin_country: payload.origin_country ?? null,
          altitude: payload.altitude ?? null,
          velocity: payload.velocity ?? null,
          vertical_rate: payload.vertical_rate ?? null,
          true_track: payload.true_track ?? null,
          on_ground: payload.on_ground ?? null,
          fetched_at: payload.fetched_at ?? null,
          latitude: entity.latitude ?? null,
          longitude: entity.longitude ?? null,
        },
        {
          focusMap: Number.isFinite(entity.latitude) && Number.isFinite(entity.longitude),
          zoom: 8.4,
          exitReplay: true,
        }
      );
      return;
    }

    if (entity.entity_type === "airport") {
      openAirportInspector(entity, { focusMap: true, zoom: 8.8 });
      return;
    }

    if (entity.entity_type === "location") {
      focusLocationEntity(entity);
      return;
    }

    if (entity.entity_type === "airline") {
      filters = {
        ...filters,
        operator: entity.entity_key ?? entity.label ?? "",
      };
      openEntityContext(entity);
      return;
    }

    openEntityContext(entity);
  }

  function buildWorkspacePayload() {
    return {
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
      savedEntities,
      weatherLayerEnabled,
      showAirportMarkers,
      selectedAirportCode,
      replayWindowMinutes,
      replayPlaybackSpeed,
    };
  }

  function hasMeaningfulWorkspaceState(workspaceState) {
    if (!workspaceState || typeof workspaceState !== "object") {
      return false;
    }

    return Boolean(
      Object.keys(workspaceState.filters ?? {}).length ||
        (workspaceState.filterPresets ?? []).length ||
        (workspaceState.watchlist ?? []).length ||
        (workspaceState.savedEntities ?? []).length ||
        (workspaceState.monitoringSessions ?? []).length ||
        (workspaceState.savedViews ?? []).length ||
        Object.keys(workspaceState.flightAnnotations ?? {}).length ||
        (workspaceState.alertRules ?? []).length ||
        workspaceState.mapStyle !== "standard" ||
        workspaceState.theme !== "dark" ||
        workspaceState.weatherLayerEnabled ||
        workspaceState.showAirportMarkers === false
    );
  }

  function applyWorkspaceState(workspaceState) {
    const normalizedWorkspaceState = normalizeUserPreferences(workspaceState);
    if (!normalizedWorkspaceState) {
      return;
    }

    filters = {
      ...filters,
      ...(normalizedWorkspaceState.filters ?? {}),
    };
    mapStyle = normalizedWorkspaceState.mapStyle ?? mapStyle;
    mapViewport = normalizedWorkspaceState.mapViewport ?? mapViewport;
    filterPresets = normalizedWorkspaceState.filterPresets ?? filterPresets;
    sortBy = normalizedWorkspaceState.sortBy ?? sortBy;
    theme = normalizedWorkspaceState.theme ?? theme;
    onboardingDismissed =
      normalizedWorkspaceState.onboardingDismissed ?? onboardingDismissed;
    watchlist = normalizedWorkspaceState.watchlist ?? watchlist;
    watchModeEnabled = normalizedWorkspaceState.watchModeEnabled ?? watchModeEnabled;
    flightAnnotations = normalizedWorkspaceState.flightAnnotations ?? flightAnnotations;
    alertRules = normalizedWorkspaceState.alertRules ?? alertRules;
    alertEvents = normalizedWorkspaceState.alertEvents ?? alertEvents;
    monitoringSessions = normalizedWorkspaceState.monitoringSessions ?? monitoringSessions;
    savedViews = normalizedWorkspaceState.savedViews ?? savedViews;
    savedEntities = normalizedWorkspaceState.savedEntities ?? savedEntities;
    weatherLayerEnabled =
      normalizedWorkspaceState.weatherLayerEnabled ?? weatherLayerEnabled;
    showAirportMarkers =
      normalizedWorkspaceState.showAirportMarkers ?? showAirportMarkers;
    selectedAirportCode =
      normalizedWorkspaceState.selectedAirportCode ?? selectedAirportCode;
    replayWindowMinutes =
      normalizedWorkspaceState.replayWindowMinutes ?? replayWindowMinutes;
    replayPlaybackSpeed =
      normalizedWorkspaceState.replayPlaybackSpeed ?? replayPlaybackSpeed;
  }

  async function loadWorkspaceProfile(profileId) {
    if (!profileId) {
      return;
    }

    workspaceHydrating = true;
    workspaceSyncStatus = "loading";
    workspaceSyncError = null;

    try {
      const payload = await fetchWorkspaceState(profileId);
      activeWorkspaceProfileId = payload.profile?.id ?? profileId;
      workspaceUpdatedAt = payload.updated_at ?? null;
      if (hasMeaningfulWorkspaceState(payload.state)) {
        applyWorkspaceState(payload.state);
      }
      workspaceSyncStatus = "success";
      workspaceReady = true;
    } catch (error) {
      workspaceSyncStatus = "error";
      workspaceSyncError = error instanceof Error ? error.message : "Failed to load workspace profile.";
    } finally {
      workspaceHydrating = false;
    }
  }

  async function initializeWorkspace() {
    workspaceSyncStatus = "loading";
    workspaceSyncError = null;

    try {
      const profilesPayload = await fetchWorkspaceProfiles();
      workspaceProfiles = profilesPayload.profiles ?? [];
      const initialProfileId = workspaceProfiles[0]?.id ?? null;
      if (initialProfileId) {
        await loadWorkspaceProfile(initialProfileId);
      } else {
        workspaceSyncStatus = "idle";
      }
    } catch (error) {
      workspaceSyncStatus = "error";
      workspaceSyncError = error instanceof Error ? error.message : "Failed to load workspace profiles.";
    }
  }

  async function createWorkspaceDesk() {
    const normalizedName = workspaceProfileDraft.trim();
    if (!normalizedName) {
      return;
    }

    try {
      const payload = await createWorkspaceProfile(normalizedName);
      workspaceProfileDraft = "";
      workspaceProfiles = [payload.profile, ...workspaceProfiles];
      await loadWorkspaceProfile(payload.profile.id);
    } catch (error) {
      workspaceSyncStatus = "error";
      workspaceSyncError = error instanceof Error ? error.message : "Failed to create a workspace profile.";
    }
  }

  function queueWorkspaceSave() {
    if (
      typeof window === "undefined" ||
      !workspaceReady ||
      workspaceHydrating ||
      !activeWorkspaceProfileId
    ) {
      return;
    }

    if (workspaceSaveTimer) {
      window.clearTimeout(workspaceSaveTimer);
    }

    workspaceSaveTimer = window.setTimeout(async () => {
      workspaceSaveTimer = null;
      workspaceSyncStatus = "saving";
      workspaceSyncError = null;

      try {
        const payload = await saveWorkspaceState(activeWorkspaceProfileId, buildWorkspacePayload());
        workspaceUpdatedAt = payload.updated_at ?? null;
        workspaceSyncStatus = "success";
      } catch (error) {
        workspaceSyncStatus = "error";
        workspaceSyncError = error instanceof Error ? error.message : "Failed to sync workspace.";
      }
    }, 500);
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
    selectedAirportCode = null;
    selectedAirportSnapshot = null;
    selectedAirportDashboard = null;
    selectedAirportStatus = "idle";
    selectedAirportError = null;
    selectedEntityContext = null;
    inspectorTab = options.inspectorTab ?? "details";
    suppressSelectionClearUntil = Date.now() + (options.selectionHoldMs ?? 220);

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

  function clearSelectedFlight(options = {}) {
    selectedIcao24 = null;
    selectedFlightSnapshot = null;
    followAircraft = false;
    inspectorTab = "details";

    if (options.closeSidebar && isMobileViewport) {
      closeMobileSidebar();
    }
  }

  function openAirportInspector(airport, options = {}) {
    const airportKey = normalizeAirportKey(airport);
    if (!airportKey) {
      return;
    }

    selectedAirportCode = airportKey;
    selectedAirportSnapshot = {
      ...airport,
      entity_key: airportKey,
    };
    selectedIcao24 = null;
    selectedFlightSnapshot = null;
    selectedEntityContext = null;
    followAircraft = false;

    if (
      options.focusMap !== false &&
      Number.isFinite(airport.latitude) &&
      Number.isFinite(airport.longitude)
    ) {
      flightFocusRequest = {
        id: crypto.randomUUID(),
        center: [airport.latitude, airport.longitude],
        zoom: options.zoom ?? Math.max(mapViewport?.zoom ?? 7.1, 8.2),
      };
    }

    if (isMobileViewport) {
      mobileSidebarOpen = true;
      mobileUtilityOpen = false;
    }
  }

  function focusLocationEntity(locationEntity) {
    if (locationEntity?.bbox) {
      flightFocusRequest = {
        id: crypto.randomUUID(),
        bounds: [
          [locationEntity.bbox.lamin, locationEntity.bbox.lomin],
          [locationEntity.bbox.lamax, locationEntity.bbox.lomax],
        ],
        maxZoom: locationEntity.zoom ?? 7.5,
      };
      return;
    }

    if (Number.isFinite(locationEntity?.latitude) && Number.isFinite(locationEntity?.longitude)) {
      flightFocusRequest = {
        id: crypto.randomUUID(),
        center: [locationEntity.latitude, locationEntity.longitude],
        zoom: locationEntity.zoom ?? 6.5,
      };
    }
  }

  function isFlightInsideBbox(flight, bbox) {
    if (!flight || !bbox) {
      return false;
    }

    return (
      Number.isFinite(flight.latitude) &&
      Number.isFinite(flight.longitude) &&
      flight.latitude >= bbox.lamin &&
      flight.latitude <= bbox.lamax &&
      flight.longitude >= bbox.lomin &&
      flight.longitude <= bbox.lomax
    );
  }

  function buildAirportShortcut(code, label = null) {
    const normalizedCode = String(code ?? "").trim().toUpperCase();
    if (!normalizedCode) {
      return null;
    }

    return {
      entity_key: normalizedCode,
      iata: normalizedCode.length === 3 ? normalizedCode : null,
      icao: normalizedCode.length === 4 ? normalizedCode : null,
      label: normalizedCode,
      name: label ?? normalizedCode,
    };
  }

  function getEntityContextMatches(entity, flights) {
    if (!entity || !Array.isArray(flights)) {
      return [];
    }

    if (entity.entity_type === "airline") {
      const target = String(entity.entity_key ?? entity.label ?? "").trim().toLowerCase();
      if (!target) {
        return [];
      }

      return flights.filter((flight) => deriveOperatorCode(flight).toLowerCase() === target);
    }

    if (entity.entity_type === "location" && entity.bbox) {
      return flights.filter((flight) => isFlightInsideBbox(flight, entity.bbox));
    }

    if (entity.entity_type === "route") {
      const target = String(entity.entity_key ?? entity.label ?? "").trim().toLowerCase();
      if (!target) {
        return [];
      }

      return flights.filter((flight) =>
        [
          flight.route_label,
          flight.route_verbose,
          flight.airport_codes,
          flight.iata_codes,
          flight.origin,
          flight.destination,
          flight.origin_iata,
          flight.origin_icao,
          flight.destination_iata,
          flight.destination_icao,
        ]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(target))
      );
    }

    return [];
  }

  function buildSearchResultKey(result) {
    return `${result?.entity_type ?? "entity"}:${result?.entity_key ?? result?.icao24 ?? result?.label ?? "unknown"}`;
  }

  function flattenSearchGroups(groups) {
    const orderedGroupNames = [
      "aircraft",
      "flights",
      "airports",
      "airlines",
      "routes",
      "locations",
    ];
    const fallbackEntries = Object.entries(groups ?? {});
    const prioritizedEntries = orderedGroupNames
      .map((name) => [name, groups?.[name] ?? null])
      .filter(([, items]) => Array.isArray(items) && items.length);
    const trailingEntries = fallbackEntries.filter(
      ([name, items]) =>
        !orderedGroupNames.includes(name) && Array.isArray(items) && items.length
    );

    return [...prioritizedEntries, ...trailingEntries].flatMap(([, items]) => items);
  }

  function resetSearchSuggestions(options = {}) {
    const clearQuery = options.clearQuery ?? false;
    if (clearQuery) {
      filters = {
        ...filters,
        query: "",
      };
    }
    remoteSearchResults = [];
    remoteSearchGroups = {};
    remoteSearchCount = 0;
    remoteSearchStatus = "idle";
    remoteSearchError = null;
    searchNavigationIndex = -1;
    searchSuggestionsDismissed = Boolean(options.dismissed ?? false);
  }

  function setSearchNavigationByResult(result) {
    const resultKey = buildSearchResultKey(result);
    const resultIndex = flattenedSearchResults.findIndex(
      (entry) => buildSearchResultKey(entry) === resultKey
    );
    if (resultIndex >= 0) {
      searchNavigationIndex = resultIndex;
    }
  }

  function handleSearchResultHover(result) {
    if (!result) {
      return;
    }

    setSearchNavigationByResult(result);
  }

  function handleSearchInputKeydown(event) {
    if (!showSearchSuggestions || !flattenedSearchResults.length) {
      if (event.key === "Escape") {
        searchSuggestionsDismissed = true;
      }
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      searchNavigationIndex =
        searchNavigationIndex < 0
          ? 0
          : (searchNavigationIndex + 1) % flattenedSearchResults.length;
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      searchNavigationIndex =
        searchNavigationIndex < 0
          ? flattenedSearchResults.length - 1
          : (searchNavigationIndex - 1 + flattenedSearchResults.length) %
            flattenedSearchResults.length;
      return;
    }

    if (event.key === "Enter") {
      const activeResult =
        flattenedSearchResults[searchNavigationIndex] ?? flattenedSearchResults[0] ?? null;
      if (!activeResult) {
        return;
      }

      event.preventDefault();
      selectSearchResult(activeResult);
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      searchSuggestionsDismissed = true;
      searchNavigationIndex = -1;
    }
  }

  function openEntityContext(entity) {
    selectedEntityContext = entity;
    selectedIcao24 = null;
    selectedFlightSnapshot = null;
    selectedAirportCode = null;
    selectedAirportSnapshot = null;
    selectedAirportDashboard = null;
    selectedAirportStatus = "idle";
    selectedAirportError = null;

    if (Number.isFinite(entity?.latitude) && Number.isFinite(entity?.longitude)) {
      flightFocusRequest = {
        id: crypto.randomUUID(),
        center: [entity.latitude, entity.longitude],
        zoom: entity.entity_type === "location" ? entity.zoom ?? 5.8 : 7.4,
      };
    }

    if (entity?.entity_type === "location") {
      focusLocationEntity(entity);
    }

    if (isMobileViewport) {
      mobileSidebarOpen = true;
      mobileUtilityOpen = false;
    }
  }

  function handleAirportSelect(event) {
    openAirportInspector(event.detail.airport, { focusMap: false });
  }

  function handleBoundsChange(event) {
    flightsStore.setBbox(event.detail.bbox);
  }

  function handleFlightSelect(event) {
    openFlightInspector(event.detail.flight, {
      focusMap: true,
      zoom: Math.max(mapViewport?.zoom ?? 7.1, 8.2),
      exitReplay: false,
      inspectorTab: "details",
      selectionHoldMs: 260,
    });
  }

  function handleMapBackgroundClick() {
    if (Date.now() < suppressSelectionClearUntil) {
      return;
    }

    if (!selectedIcao24 && !selectedAirportCode && !selectedEntityContext) {
      return;
    }

    clearSelectedFlight({ closeSidebar: isMobileViewport });
    selectedAirportCode = null;
    selectedAirportSnapshot = null;
    selectedAirportDashboard = null;
    selectedAirportStatus = "idle";
    selectedAirportError = null;
    selectedEntityContext = null;
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
    const sharedAircraftType = params.get("typeCode");
    const sharedCountry = params.get("country");
    const sharedOperator = params.get("operator");
    const sharedRoute = params.get("route");
    const sharedAirportFilter = params.get("airportFilter");
    const sharedAirportFlow = params.get("airportFlow");
    const sharedTrafficState = params.get("flightState");
    const sharedCategory = params.get("category");
    const sharedHeadingBand = params.get("heading");
    const sharedRecentActivity = params.get("recent");
    const sharedSort = params.get("sort");
    const sharedTheme = params.get("theme");
    const sharedMapStyle = params.get("map");
    const sharedSelectedIcao24 = params.get("sel");
    const sharedSelectedAirport = params.get("airport");
    const sharedGroundFlag = params.get("ground");
    const sharedWeather = params.get("weather");
    const sharedAirportMarkers = params.get("airports");
    const sharedReplayWindow = Number(params.get("replayWindow"));

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

    if (sharedAircraftType !== null) {
      nextFilters.aircraftType = sharedAircraftType;
    }

    if (sharedCountry !== null) {
      nextFilters.country = sharedCountry;
    }

    if (sharedOperator !== null) {
      nextFilters.operator = sharedOperator;
    }

    if (sharedRoute !== null) {
      nextFilters.route = sharedRoute;
    }

    if (sharedAirportFilter !== null) {
      nextFilters.airportCode = sharedAirportFilter;
    }

    if (["all", "arrivals", "departures"].includes(sharedAirportFlow)) {
      nextFilters.airportFlow = sharedAirportFlow;
    }

    if (["all", "airborne", "ground"].includes(sharedTrafficState)) {
      nextFilters.trafficState = sharedTrafficState;
    }

    if (
      sharedCategory &&
      TRAFFIC_CATEGORY_OPTIONS.some((option) => option.value === sharedCategory)
    ) {
      nextFilters.trafficCategory = sharedCategory;
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

    if (sharedSelectedAirport) {
      selectedAirportCode = sharedSelectedAirport.toUpperCase();
    }

    if (sharedGroundFlag === "0" || sharedGroundFlag === "1") {
      nextFilters.hideGroundTraffic = sharedGroundFlag === "1";
    }

    if (sharedWeather === "1" || sharedWeather === "0") {
      weatherLayerEnabled = sharedWeather === "1";
    }

    if (sharedAirportMarkers === "1" || sharedAirportMarkers === "0") {
      showAirportMarkers = sharedAirportMarkers !== "0";
    }

    if ([30, 90, 180].includes(sharedReplayWindow)) {
      replayWindowMinutes = sharedReplayWindow;
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

    if (filters.aircraftType.trim()) {
      params.set("typeCode", filters.aircraftType.trim().toUpperCase());
    } else {
      params.delete("typeCode");
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

    if (filters.route.trim()) {
      params.set("route", filters.route.trim());
    } else {
      params.delete("route");
    }

    if (filters.airportCode.trim()) {
      params.set("airportFilter", filters.airportCode.trim().toUpperCase());
    } else {
      params.delete("airportFilter");
    }

    if (filters.airportCode.trim() && filters.airportFlow !== "all") {
      params.set("airportFlow", filters.airportFlow);
    } else {
      params.delete("airportFlow");
    }

    if (filters.trafficState !== "all") {
      params.set("flightState", filters.trafficState);
    } else {
      params.delete("flightState");
    }

    if (filters.trafficCategory !== "all") {
      params.set("category", filters.trafficCategory);
    } else {
      params.delete("category");
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

    if (selectedAirportCode) {
      params.set("airport", selectedAirportCode);
    } else {
      params.delete("airport");
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

    if (weatherLayerEnabled) {
      params.set("weather", "1");
    } else {
      params.delete("weather");
    }

    if (!showAirportMarkers) {
      params.set("airports", "0");
    } else {
      params.delete("airports");
    }

    if (replayWindowMinutes !== 90) {
      params.set("replayWindow", String(replayWindowMinutes));
    } else {
      params.delete("replayWindow");
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

  function setReportFeedback(message) {
    reportFeedback = message;
    if (reportFeedbackTimer) {
      window.clearTimeout(reportFeedbackTimer);
    }

    reportFeedbackTimer = window.setTimeout(() => {
      reportFeedback = "";
      reportFeedbackTimer = null;
    }, 2200);
  }

  function downloadTextFile(filename, content, contentType = "text/plain;charset=utf-8") {
    if (typeof window === "undefined") {
      return;
    }

    const blob = new Blob([content], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    window.URL.revokeObjectURL(url);
  }

  function exportVisibleTrafficCsv() {
    const csv = buildTrafficReportCsv(filteredFlights);
    const timestamp = new Date().toISOString().replaceAll(":", "-");
    downloadTextFile(`live-traffic-${timestamp}.csv`, csv, "text/csv;charset=utf-8");
    setReportFeedback("Traffic CSV ready");
  }

  function exportSelectedAirportCsv() {
    if (!selectedAirport || !selectedAirportDashboard) {
      return;
    }

    const airportCode = normalizeAirportKey(selectedAirport).toLowerCase();
    const csv = buildAirportReportCsv(selectedAirport, selectedAirportDashboard);
    const timestamp = new Date().toISOString().replaceAll(":", "-");
    downloadTextFile(
      `airport-board-${airportCode}-${timestamp}.csv`,
      csv,
      "text/csv;charset=utf-8"
    );
    setReportFeedback("Airport CSV ready");
  }

  function printVisibleTrafficReport() {
    if (typeof window === "undefined") {
      return;
    }

    const reportWindow = window.open("", "_blank", "noopener,noreferrer,width=1200,height=900");
    if (!reportWindow) {
      setReportFeedback("Popup blocked");
      return;
    }

    const html = buildPrintableRadarReport({
      title: activeReplaySnapshot ? "Replay traffic report" : "Live traffic report",
      generatedAt: new Intl.DateTimeFormat("en-GB", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZoneName: "short",
      }).format(new Date()),
      summaryRows: [
        { label: "Visible traffic", value: String(visibleTrackedCount) },
        { label: "Airborne", value: String(airborneCount) },
        { label: "Ground", value: String(groundCount) },
        { label: "Map style", value: mapStyleLabel },
        { label: "Filters", value: String(activeFilterCount) },
      ],
      flights: filteredFlights.slice(0, 120),
    });

    reportWindow.document.open();
    reportWindow.document.write(html);
    reportWindow.document.close();
    reportWindow.focus();
    reportWindow.print();
    setReportFeedback("Print report opened");
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

  function getAlertRuleLabel(type) {
    if (type === "callsign") {
      return "Callsign";
    }
    if (type === "icao24") {
      return "ICAO24";
    }
    if (type === "airline") {
      return "Airline";
    }
    if (type === "country") {
      return "Country";
    }
    if (type === "registration") {
      return "Registration";
    }
    if (type === "type_code") {
      return "Type";
    }
    if (type === "route") {
      return "Route";
    }
    if (type === "airport") {
      return "Airport";
    }
    if (type === "area") {
      return "Area";
    }

    return "Rule";
  }

  function addAlertRule(rule) {
    const normalizedQuery = rule.query.trim().toLowerCase();
    if (!normalizedQuery) {
      return;
    }

    const duplicate = alertRules.some(
      (existingRule) =>
        existingRule.type === rule.type &&
        existingRule.query.toLowerCase() === normalizedQuery
    );
    if (duplicate) {
      return;
    }

    alertRules = [
      {
        id: crypto.randomUUID(),
        type: rule.type,
        query: rule.query.trim(),
        payload: rule.payload ?? null,
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
        savedEntities: [...savedEntities],
        weatherLayerEnabled,
        showAirportMarkers,
        selectedIcao24,
        selectedAirportCode,
        replayWindowMinutes,
        replayPlaybackSpeed,
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
    savedEntities = view.state.savedEntities ?? savedEntities;
    weatherLayerEnabled = view.state.weatherLayerEnabled ?? weatherLayerEnabled;
    showAirportMarkers = view.state.showAirportMarkers ?? showAirportMarkers;
    selectedIcao24 = view.state.selectedIcao24 ?? null;
    selectedAirportCode = view.state.selectedAirportCode ?? null;
    replayWindowMinutes = view.state.replayWindowMinutes ?? replayWindowMinutes;
    replayPlaybackSpeed = view.state.replayPlaybackSpeed ?? replayPlaybackSpeed;
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

        if (rule.type === "airline") {
          return deriveOperatorCode(flight).toLowerCase().includes(normalizedQuery);
        }

        if (rule.type === "country") {
          return (flight.origin_country ?? "").toLowerCase().includes(normalizedQuery);
        }

        if (rule.type === "registration") {
          return (flight.registration ?? "").toLowerCase().includes(normalizedQuery);
        }

        if (rule.type === "type_code") {
          return (flight.type_code ?? "").toLowerCase().includes(normalizedQuery);
        }

        if (rule.type === "route") {
          return [
            flight.route_label,
            flight.route_verbose,
            flight.airport_codes,
            flight.iata_codes,
            flight.origin,
            flight.destination,
            flight.origin_iata,
            flight.origin_icao,
            flight.destination_iata,
            flight.destination_icao,
          ]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(normalizedQuery));
        }

        if (rule.type === "airport") {
          const radiusKm = Number(rule.payload?.radiusKm ?? 48);
          return (
            Number.isFinite(rule.payload?.latitude) &&
            Number.isFinite(rule.payload?.longitude) &&
            calculateDistanceKm(
              flight.latitude,
              flight.longitude,
              {
                center: [rule.payload.latitude, rule.payload.longitude],
              }
            ) <= radiusKm
          );
        }

        if (rule.type === "area") {
          return isFlightInsideBbox(flight, rule.payload?.bbox ?? null);
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
          `${getAlertRuleLabel(rule.type)} ${rule.query} matched ${leadFlight.callsign ?? leadFlight.registration ?? leadFlight.icao24}`
        );
      }

      if (matches.length === 0 && previousMatches > 0) {
        pushAlertEvent(
          `${getAlertRuleLabel(rule.type)} ${rule.query} is no longer visible`
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
      removeSavedEntity("flight", selectedFlight.icao24);
      return;
    }

    watchlist = [selectedFlight.icao24, ...watchlist.filter((icao24) => icao24 !== selectedFlight.icao24)].slice(0, 12);
    toggleEntityBookmark({
      entity_type: "flight",
      entity_key: selectedFlight.icao24,
      label: selectedFlight.callsign ?? selectedFlight.registration ?? selectedFlight.icao24.toUpperCase(),
      subtitle: [selectedFlight.registration ?? selectedFlight.icao24.toUpperCase(), selectedFlight.origin_country]
        .filter(Boolean)
        .join(" · "),
      ...selectedFlight,
    });
  }

  function removeFromWatchlist(icao24) {
    watchlist = watchlist.filter((value) => value !== icao24);
    removeSavedEntity("flight", icao24);
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
    inspectorTab = "details";
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

  function addSelectedFlightAlert() {
    if (!selectedFlight) {
      return;
    }

    if (selectedFlight.callsign) {
      addAlertRule({
        type: "callsign",
        query: selectedFlight.callsign,
      });
      return;
    }

    addAlertRule({
      type: "icao24",
      query: selectedFlight.icao24,
    });
  }

  function addSelectedAirportAlert() {
    if (!selectedAirport) {
      return;
    }

    if (!Number.isFinite(selectedAirport.latitude) || !Number.isFinite(selectedAirport.longitude)) {
      return;
    }

    addAlertRule({
      type: "airport",
      query: normalizeAirportKey(selectedAirport),
      payload: {
        latitude: selectedAirport.latitude,
        longitude: selectedAirport.longitude,
        radiusKm: 48,
      },
    });
  }

  function addEntityContextAlert() {
    if (!selectedEntityContext) {
      return;
    }

    if (selectedEntityContext.entity_type === "airline") {
      addAlertRule({
        type: "airline",
        query: selectedEntityContext.entity_key ?? selectedEntityContext.label ?? "",
      });
      return;
    }

    if (selectedEntityContext.entity_type === "location") {
      addAlertRule({
        type: "area",
        query: selectedEntityContext.label ?? selectedEntityContext.entity_key ?? "saved area",
        payload: {
          bbox: selectedEntityContext.bbox ?? null,
        },
      });
      return;
    }

    if (selectedEntityContext.entity_type === "route") {
      addAlertRule({
        type: "route",
        query: selectedEntityContext.entity_key ?? selectedEntityContext.label ?? "",
      });
      return;
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
        minutes: replayWindowMinutes,
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

  async function refreshAirports(bbox) {
    if (!bbox) {
      airportFeed = {
        status: "idle",
        airports: [],
        error: null,
      };
      return;
    }

    const requestId = ++airportFeedRequestId;
    airportFeed = {
      ...airportFeed,
      status: airportFeed.airports.length ? "refreshing" : "loading",
      error: null,
    };

    try {
      const payload = await fetchAirports(bbox, {
        limit: mapViewport?.zoom >= 7 ? 32 : mapViewport?.zoom >= 5 ? 18 : 10,
      });
      if (requestId !== airportFeedRequestId) {
        return;
      }

      airportFeed = {
        status: "success",
        airports: payload.airports ?? [],
        error: null,
      };
    } catch (error) {
      if (requestId !== airportFeedRequestId) {
        return;
      }

      airportFeed = {
        ...airportFeed,
        status: airportFeed.airports.length ? "success" : "error",
        error: airportFeed.airports.length
          ? null
          : error instanceof Error
            ? error.message
            : "Failed to load airport markers.",
      };
    }
  }

  async function loadSelectedAirportDashboard(airport) {
    const airportKey = normalizeAirportKey(airport);
    if (!airportKey) {
      selectedAirportDashboard = null;
      selectedAirportStatus = "idle";
      selectedAirportError = null;
      return;
    }

    const requestId = ++selectedAirportRequestId;
    selectedAirportStatus = selectedAirportDashboard ? "refreshing" : "loading";
    selectedAirportError = null;

    try {
      const payload = await fetchAirportDashboard(airportKey, {
        hours: 12,
        limit: 10,
      });
      if (requestId !== selectedAirportRequestId || selectedAirportCode !== airportKey) {
        return;
      }

      selectedAirportSnapshot = payload.airport ?? airport;
      selectedAirportDashboard = payload;
      selectedAirportStatus = "success";
      selectedAirportError = null;
    } catch (error) {
      if (requestId !== selectedAirportRequestId || selectedAirportCode !== airportKey) {
        return;
      }

      selectedAirportStatus = selectedAirportDashboard ? "success" : "error";
      selectedAirportError = error instanceof Error ? error.message : "Failed to load airport dashboard.";
    }
  }

  async function loadSelectedAirportWeather(airport) {
    const stationCode = String(airport?.icao ?? airport?.entity_key ?? "")
      .trim()
      .toUpperCase();
    if (!stationCode) {
      selectedAirportWeather = null;
      selectedAirportWeatherStatus = "idle";
      selectedAirportWeatherError = null;
      return;
    }

    const requestId = ++selectedAirportWeatherRequestId;
    selectedAirportWeatherStatus = selectedAirportWeather ? "refreshing" : "loading";
    selectedAirportWeatherError = null;

    try {
      const payload = await fetchAirportWeather(stationCode);
      if (requestId !== selectedAirportWeatherRequestId || selectedAirportCode !== normalizeAirportKey(airport)) {
        return;
      }

      selectedAirportWeather = payload;
      selectedAirportWeatherStatus = "success";
      selectedAirportWeatherError = null;
    } catch (error) {
      if (requestId !== selectedAirportWeatherRequestId || selectedAirportCode !== normalizeAirportKey(airport)) {
        return;
      }

      selectedAirportWeatherStatus = selectedAirportWeather ? "success" : "error";
      selectedAirportWeatherError =
        error instanceof Error ? error.message : "Failed to load airport weather.";
    }
  }

  async function loadRemoteSearchResults(query) {
    const normalizedQuery = query.trim();
    if (normalizedQuery.length < 2) {
      resetSearchSuggestions();
      return;
    }

    const requestId = ++remoteSearchRequestId;
    remoteSearchStatus = "loading";
    remoteSearchError = null;
    searchSuggestionsDismissed = false;

    try {
      const searchPayload = await searchFlights(normalizedQuery, { limit: 8 });
      if (requestId !== remoteSearchRequestId || filters.query.trim() !== normalizedQuery) {
        return;
      }

      remoteSearchResults = searchPayload.results ?? [];
      remoteSearchGroups = searchPayload.groups ?? {};
      remoteSearchCount = searchPayload.count ?? remoteSearchResults.length;
      remoteSearchStatus = "success";
      remoteSearchError = null;
      searchNavigationIndex = remoteSearchResults.length ? 0 : -1;
    } catch (error) {
      if (requestId !== remoteSearchRequestId || filters.query.trim() !== normalizedQuery) {
        return;
      }

      remoteSearchResults = [];
      remoteSearchGroups = {};
      remoteSearchCount = 0;
      remoteSearchStatus = "error";
      remoteSearchError =
        error instanceof Error ? error.message : "Failed to search archived flights.";
      searchNavigationIndex = -1;
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
    if (!result) {
      return;
    }

    if (result.entity_type === "flight" || result.entity_type === "aircraft") {
      openFlightInspector(result, {
        focusMap: true,
        zoom: 8.4,
        exitReplay: true,
        pendingSearchSelection: result.icao24,
      });
    } else if (result.entity_type === "airport") {
      openAirportInspector(result, {
        focusMap: true,
        zoom: 9.1,
      });
    } else if (result.entity_type === "location") {
      openEntityContext(result);
    } else if (result.entity_type === "airline") {
      filters = {
        ...filters,
        operator: result.entity_key ?? result.label ?? "",
      };
      openEntityContext(result);
    } else if (result.entity_type === "route") {
      filters = {
        ...filters,
        route: result.entity_key ?? result.label ?? "",
      };
      openEntityContext(result);
    } else {
      openEntityContext(result);
    }

    resetSearchSuggestions({ clearQuery: true, dismissed: true });
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
      aircraftType: "",
      country: "",
      operator: "",
      route: "",
      airportCode: "",
      airportFlow: "all",
      trafficState: "all",
      trafficCategory: "all",
      headingBand: "any",
      hideGroundTraffic: true,
      recentActivity: "any",
      dimFilteredTraffic: true,
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

    if (presetKey === "cargo") {
      filters = {
        ...filters,
        trafficCategory: "cargo",
      };
      return;
    }

    if (presetKey === "military") {
      filters = {
        ...filters,
        trafficCategory: "military",
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

    if (tokenKey === "aircraftType") {
      filters = { ...filters, aircraftType: "" };
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

    if (tokenKey === "route") {
      filters = { ...filters, route: "" };
      return;
    }

    if (tokenKey === "airportCode") {
      filters = { ...filters, airportCode: "", airportFlow: "all" };
      return;
    }

    if (tokenKey === "airportFlow") {
      filters = { ...filters, airportFlow: "all" };
      return;
    }

    if (tokenKey === "trafficState") {
      filters = { ...filters, trafficState: "all" };
      return;
    }

    if (tokenKey === "trafficCategory") {
      filters = { ...filters, trafficCategory: "all" };
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
    utilityPanelMode = "tools";
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

  function jumpReplayToStart() {
    if (!replaySourceSnapshots.length) {
      return;
    }

    replayPlaybackActive = false;
    setReplaySnapshotIndex(0);
  }

  function jumpReplayToLatest() {
    replayPlaybackActive = false;
    replaySnapshotCursor = null;
  }

  function setReplayPlaybackSpeed(multiplier) {
    const numericMultiplier = Number(multiplier);
    replayPlaybackSpeed = Number.isFinite(numericMultiplier) && numericMultiplier > 0 ? numericMultiplier : 1;
  }

  function setReplayWindowMinutes(minutes) {
    const numericMinutes = Number(minutes);
    replayWindowMinutes = [30, 90, 180].includes(numericMinutes) ? numericMinutes : 90;
  }

  function focusTrailPoint(point, options = {}) {
    if (!point || !Number.isFinite(point.latitude) || !Number.isFinite(point.longitude)) {
      return;
    }

    flightFocusRequest = {
      id: crypto.randomUUID(),
      center: [point.latitude, point.longitude],
      zoom: Math.max(mapViewport?.zoom ?? 7.1, options.zoom ?? 8.2),
    };
  }

  function setSelectedFlightTrackCursor(index, options = {}) {
    if (!selectedFlightTrail.length) {
      selectedFlightTrackCursor = -1;
      return;
    }

    const boundedIndex = Math.max(0, Math.min(index, selectedFlightTrail.length - 1));
    selectedFlightTrackCursor = boundedIndex;
    if (options.focusMap !== false) {
      focusTrailPoint(selectedFlightTrail[boundedIndex], { zoom: 8.4 });
    }
  }

  function jumpSelectedFlightTrackStart() {
    if (!selectedFlightTrail.length) {
      return;
    }

    setSelectedFlightTrackCursor(0);
  }

  function jumpSelectedFlightTrackLatest() {
    selectedFlightTrackCursor = -1;
    if (selectedFlight) {
      openFlightInspector(selectedFlight, {
        focusMap: true,
        zoom: 8.4,
        exitReplay: false,
        inspectorTab: "tracking",
      });
      return;
    }

    const latestPoint = selectedFlightTrail[selectedFlightTrail.length - 1] ?? null;
    focusTrailPoint(latestPoint, { zoom: 8.4 });
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
    const firstSnapshot = snapshotHistory[0] ?? null;
    const lastSnapshot = snapshotHistory[snapshotHistory.length - 1] ?? null;
    const focusLabel = selectedFlight
      ? selectedFlightCallsignLabel
      : selectedAirport
        ? selectedAirport.iata ?? selectedAirport.icao ?? selectedAirport.entity_key
        : selectedEntityContext?.label ?? null;
    const session = {
      id: crypto.randomUUID(),
      label: `Session ${buildSessionLabel(createdAt)}`,
      createdAt,
      summary: [
        focusLabel,
        mapViewport?.center
          ? `${mapViewport.center[0].toFixed(2)}, ${mapViewport.center[1].toFixed(2)} · z${(mapViewport.zoom ?? 7.1).toFixed(1)}`
          : "Current airspace",
        activeFilterCount ? `${activeFilterCount} filters` : null,
      ]
        .filter(Boolean)
        .join(" · "),
      snapshotRange: {
        start: firstSnapshot?.fetchedAt ?? null,
        end: lastSnapshot?.fetchedAt ?? null,
      },
      snapshots: snapshotHistory.map((snapshot) => ({
        ...snapshot,
        flights: snapshot.flights.map((flight) => ({ ...flight })),
      })),
      viewport: mapViewport,
      filters: { ...filters },
      mapStyle,
      weatherLayerEnabled,
      selectedIcao24,
      selectedAirportCode,
      selectedEntityContext: selectedEntityContext
        ? { ...selectedEntityContext }
        : null,
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
    filters = {
      ...filters,
      ...(session.filters ?? {}),
    };
    if (session.viewport) {
      mapViewport = session.viewport;
    }
    mapStyle = session.mapStyle ?? mapStyle;
    weatherLayerEnabled = session.weatherLayerEnabled ?? weatherLayerEnabled;
    selectedIcao24 = session.selectedIcao24 ?? null;
    selectedAirportCode = session.selectedAirportCode ?? null;
    selectedEntityContext = session.selectedEntityContext ?? null;

    if (isMobileViewport) {
      mobileSidebarOpen = true;
      mobileUtilityOpen = false;
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
    }, Math.max(240, Math.round(1200 / replayPlaybackSpeed)));
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

    if (event.key === "Escape") {
      if (isTypingField && target === searchInput) {
        searchSuggestionsDismissed = true;
        searchNavigationIndex = -1;
        return;
      }
      handleMapBackgroundClick();
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

  function applyAirportTrafficFilter(airport, flow = "all") {
    const airportCode = normalizeAirportKey(airport);
    if (!airportCode) {
      return;
    }

    filters = {
      ...filters,
      airportCode,
      airportFlow: flow,
    };
    utilityPanelMode = "radar";

    if (isMobileViewport) {
      mobileUtilityOpen = true;
      mobileSidebarOpen = false;
    }
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

  function matchesTrafficCategory(flight, category) {
    if (category === "all") {
      return true;
    }

    return classifyTrafficCategory(flight) === category;
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
          (flight.is_dimmed ? -4500 : 1200) +
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
  $: normalizedAircraftTypeFilter = filters.aircraftType.trim().toLowerCase();
  $: normalizedCountryFilter = filters.country.trim().toLowerCase();
  $: normalizedOperatorFilter = filters.operator.trim().toLowerCase();
  $: normalizedRouteFilter = filters.route.trim().toLowerCase();
  $: normalizedAirportCodeFilter = filters.airportCode.trim().toLowerCase();
  $: activeMonitoringSession =
    monitoringSessions.find((session) => session.id === activeMonitoringSessionId) ?? null;
  $: activeWorkspaceProfile =
    workspaceProfiles.find((profile) => profile.id === activeWorkspaceProfileId) ?? null;
  $: replaySourceSnapshots = activeMonitoringSession?.snapshots ?? snapshotHistory;
  $: replaySnapshotIndex = replaySnapshotCursor
    ? replaySourceSnapshots.findIndex((snapshot) => snapshot.fetchedAt === replaySnapshotCursor)
    : -1;
  $: activeReplaySnapshot =
    replaySnapshotIndex >= 0 ? replaySourceSnapshots[replaySnapshotIndex] ?? null : null;
  $: replayFlights = activeReplaySnapshot?.flights ?? state.flights;
  $: activeFilterCount = countActiveFilters(filters);
  $: filteredFlights = replayFlights.filter((flight) => {
    const operatorCode = deriveOperatorCode(flight).toLowerCase();
    const matchesQuery = matchesFlightSearch(flight, normalizedQuery);

    const matchesAltitude =
      !hasMinimumAltitude ||
      (flight.altitude !== null && flight.altitude !== undefined && flight.altitude >= minimumAltitude);

    const matchesSpeed =
      !hasMinimumSpeed ||
      (flight.velocity !== null &&
        flight.velocity !== undefined &&
        flight.velocity * 3.6 >= minimumSpeed);

    const matchesAircraftType =
      !normalizedAircraftTypeFilter ||
      (flight.type_code ?? "").toLowerCase().includes(normalizedAircraftTypeFilter);

    const matchesCountry =
      !normalizedCountryFilter ||
      (flight.origin_country ?? "").toLowerCase().includes(normalizedCountryFilter);

    const matchesOperator =
      !normalizedOperatorFilter ||
      operatorCode.includes(normalizedOperatorFilter) ||
      (flight.airline_code ?? "").toLowerCase().includes(normalizedOperatorFilter);

    const matchesRoute =
      !normalizedRouteFilter ||
      [
        flight.route_label,
        flight.route_verbose,
        flight.airport_codes,
        flight.iata_codes,
        flight.origin,
        flight.destination,
        flight.origin_iata,
        flight.origin_icao,
        flight.origin_name,
        flight.destination_iata,
        flight.destination_icao,
        flight.destination_name,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalizedRouteFilter));

    const matchesAirportFlow = matchesAirportTrafficFilter(
      flight,
      normalizedAirportCodeFilter,
      filters.airportFlow
    );

    const matchesTrafficState =
      filters.trafficState === "all" ||
      (filters.trafficState === "ground" ? flight.on_ground : !flight.on_ground);

    const matchesCategory = matchesTrafficCategory(flight, filters.trafficCategory);

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
      matchesAircraftType &&
      matchesCountry &&
      matchesOperator &&
      matchesRoute &&
      matchesAirportFlow &&
      matchesTrafficState &&
      matchesCategory &&
      matchesHeading &&
      matchesGroundFilter &&
      matchesRecentActivity
    );
  });
  $: sortedFlights = sortFlights(filteredFlights, sortBy, mapViewport);
  $: filteredFlightIds = new Set(filteredFlights.map((flight) => flight.icao24));
  $: mapFeedFlights =
    filters.dimFilteredTraffic && activeFilterCount
      ? replayFlights.map((flight) =>
          filteredFlightIds.has(flight.icao24)
            ? flight
            : {
                ...flight,
                is_dimmed: true,
              }
        )
      : filteredFlights;
  $: dimmedFlightIds = filters.dimFilteredTraffic && activeFilterCount
    ? mapFeedFlights.filter((flight) => flight.is_dimmed).map((flight) => flight.icao24)
    : [];
  $: displayLimit = getDisplayLimitForZoom(mapViewport?.zoom);
  $: renderedFlights = prioritizeFlightsForMap(
    sortFlights(mapFeedFlights, sortBy, mapViewport),
    displayLimit,
    selectedIcao24,
    watchlist
  );
  $: watchedFlightEntries = watchlist.map((icao24) => {
    const flight = state.flights.find((candidate) => candidate.icao24 === icao24) ?? null;
    return {
      icao24,
      flight,
      isLive: Boolean(flight),
    };
  });
  $: savedFlightEntities = savedEntities.filter((entity) => entity.entity_type === "flight");
  $: savedAircraftEntities = savedEntities.filter((entity) => entity.entity_type === "aircraft");
  $: savedAirportEntities = savedEntities.filter((entity) => entity.entity_type === "airport");
  $: savedLocationEntities = savedEntities.filter((entity) => entity.entity_type === "location");
  $: savedAirlineEntities = savedEntities.filter((entity) => entity.entity_type === "airline");
  $: savedRouteEntities = savedEntities.filter((entity) => entity.entity_type === "route");
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
  $: topTypeSuggestions = getTopValues(replayFlights, (flight) => flight.type_code ?? "", 4);
  $: topOperatorSuggestions = getTopValues(replayFlights, (flight) => deriveOperatorCode(flight) || "", 4);
  $: topCountrySuggestions = getTopValues(replayFlights, (flight) => flight.origin_country ?? "", 4);
  $: activeFilterTokens = [
    filters.query.trim() ? { key: "query", label: `Search: ${filters.query.trim()}` } : null,
    filters.minAltitude ? { key: "minAltitude", label: `Min altitude ${filters.minAltitude} m` } : null,
    filters.minSpeed ? { key: "minSpeed", label: `Min speed ${filters.minSpeed} km/h` } : null,
    filters.aircraftType.trim()
      ? { key: "aircraftType", label: `Type: ${filters.aircraftType.trim().toUpperCase()}` }
      : null,
    filters.country.trim() ? { key: "country", label: `Country: ${filters.country.trim()}` } : null,
    filters.operator.trim() ? { key: "operator", label: `Operator: ${filters.operator.trim().toUpperCase()}` } : null,
    filters.route.trim() ? { key: "route", label: `Route/airport: ${filters.route.trim().toUpperCase()}` } : null,
    filters.airportCode.trim()
      ? {
          key: "airportCode",
          label: `Airport: ${filters.airportCode.trim().toUpperCase()}`,
        }
      : null,
    filters.airportCode.trim() && filters.airportFlow !== "all"
      ? {
          key: "airportFlow",
          label: `Flow: ${filters.airportFlow === "arrivals" ? "Arrivals" : "Departures"}`,
        }
      : null,
    filters.trafficState !== "all"
      ? {
          key: "trafficState",
          label: `State: ${filters.trafficState === "ground" ? "Ground only" : "Airborne only"}`,
        }
      : null,
    filters.trafficCategory !== "all"
      ? {
          key: "trafficCategory",
          label: `Category: ${TRAFFIC_CATEGORY_OPTIONS.find((option) => option.value === filters.trafficCategory)?.label ?? filters.trafficCategory}`,
        }
      : null,
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
  $: showMobileStartHint =
    isMobileViewport &&
    !selectedFlight &&
    !selectedAirport &&
    !selectedEntityContext &&
    !mobileSidebarOpen &&
    !mobileUtilityOpen;
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
  $: utilityPanelTitle =
    utilityPanelMode === "radar" ? "Radar" : utilityPanelMode === "replay" ? "Replay" : "Tools";
  $: utilityPanelEyebrow =
    utilityPanelMode === "radar"
      ? "Core controls"
      : utilityPanelMode === "replay"
        ? "Archive controls"
        : "Secondary tools";
  $: statusLabel = getStatusLabel(state);
  $: freshnessLabel = getFreshnessLabel(state.fetchedAt);
  $: confidenceLabel = getConfidenceLabel(state);
  $: transportLabel = state.transport === "sse" ? "Stream" : "Polling";
  $: mapCenterLabel = mapViewport?.center
    ? `${mapViewport.center[0].toFixed(2)}, ${mapViewport.center[1].toFixed(2)}`
    : "52.23, 21.01";
  $: zoomLabel = Number.isFinite(mapViewport?.zoom) ? mapViewport.zoom.toFixed(1) : "7.1";
  $: visibleTrackedCount = activeReplaySnapshot?.count ?? state.count;
  $: canStepReplayBackward =
    replaySourceSnapshots.length > 1 && (replaySnapshotIndex > 0 || replaySnapshotIndex === -1);
  $: canStepReplayForward = replaySourceSnapshots.length > 1 && replaySnapshotIndex !== -1;
  $: if (searchQuery !== lastSearchQuery) {
    lastSearchQuery = searchQuery;
    searchSuggestionsDismissed = false;
  }
  $: flattenedSearchResults = flattenSearchGroups(remoteSearchGroups);
  $: if (searchNavigationIndex >= flattenedSearchResults.length) {
    searchNavigationIndex = flattenedSearchResults.length ? 0 : -1;
  }
  $: activeSearchResult =
    searchNavigationIndex >= 0 ? flattenedSearchResults[searchNavigationIndex] ?? null : null;
  $: activeSearchResultKey = activeSearchResult ? buildSearchResultKey(activeSearchResult) : "";
  $: showSearchSuggestions =
    searchQuery.length >= 2 &&
    !searchSuggestionsDismissed &&
    (remoteSearchStatus !== "idle" || remoteSearchCount > 0 || remoteSearchError);
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
  $: selectedAirport = selectedAirportCode
    ? airportFeed.airports.find((airport) => normalizeAirportKey(airport) === selectedAirportCode) ??
      (normalizeAirportKey(selectedAirportSnapshot) === selectedAirportCode ? selectedAirportSnapshot : null)
    : null;
  $: selectedAirportBookmarked = selectedAirport
    ? isEntityBookmarked("airport", normalizeAirportKey(selectedAirport))
    : false;
  $: selectedEntityContextMatches = getEntityContextMatches(selectedEntityContext, state.flights).slice(0, 6);
  $: selectedEntityContextOriginAirport =
    selectedEntityContext?.entity_type === "route"
      ? buildAirportShortcut(
          selectedEntityContext.origin_iata ?? selectedEntityContext.origin_icao,
          selectedEntityContext.origin_iata ?? selectedEntityContext.origin_icao ?? "Origin"
        )
      : null;
  $: selectedEntityContextDestinationAirport =
    selectedEntityContext?.entity_type === "route"
      ? buildAirportShortcut(
          selectedEntityContext.destination_iata ?? selectedEntityContext.destination_icao,
          selectedEntityContext.destination_iata ?? selectedEntityContext.destination_icao ?? "Destination"
        )
      : null;
  $: selectedOperatorCode = selectedFlight ? deriveOperatorCode(selectedFlight) || "N/A" : "N/A";
  $: selectedFlightCallsignLabel = selectedFlight
    ? selectedFlight.callsign ?? selectedFlight.registration ?? selectedFlight.icao24.toUpperCase()
    : null;
  $: selectedFlightQuickRoute =
    formatQuickRoute(selectedRouteAirports) ??
    selectedFlightDetails?.route?.iata_codes ??
    selectedFlightDetails?.route?.airport_codes ??
    null;
  $: selectedFlightQuickSubtitle = selectedFlight
    ? selectedFlightQuickRoute ??
      [
        selectedFlight.registration ?? selectedFlight.icao24.toUpperCase(),
        selectedOperatorCode !== "N/A" ? selectedOperatorCode : selectedFlight.origin_country ?? "Unknown",
      ].filter(Boolean).join(" · ")
    : null;
  $: selectedFlightQuickMetrics = selectedFlight
    ? [
        { label: "ALT", value: formatAltitude(selectedFlight.altitude) },
        { label: "SPD", value: formatSpeed(selectedFlight.velocity) },
        { label: "HDG", value: formatHeading(selectedFlight.true_track) },
        { label: "V/S", value: formatVerticalRate(selectedFlight.vertical_rate) },
      ]
    : [];
  $: selectedFlightQuickStatus = selectedFlight
    ? activeReplaySnapshot
      ? "Replay focus"
      : selectedFlightDetailsStatus === "loading" || selectedFlightDetailsStatus === "refreshing"
        ? "Syncing details"
        : formatFlightStatus(selectedFlight)
    : null;
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
  $: if (selectedFlightTrailKey !== lastSelectedFlightTrackKey) {
    lastSelectedFlightTrackKey = selectedFlightTrailKey;
    selectedFlightTrackCursor = -1;
  }
  $: if (selectedFlightTrackCursor >= selectedFlightTrail.length) {
    selectedFlightTrackCursor = selectedFlightTrail.length ? selectedFlightTrail.length - 1 : -1;
  }
  $: selectedFlightTrackPoint =
    selectedFlightTrackCursor >= 0
      ? selectedFlightTrail[selectedFlightTrackCursor] ?? null
      : selectedFlightTrail[selectedFlightTrail.length - 1] ?? null;
  $: selectedFlightTrackSliderValue =
    selectedFlightTrackCursor >= 0
      ? selectedFlightTrackCursor
      : Math.max(0, selectedFlightTrail.length - 1);
  $: selectedFlightTrailFirstPoint = selectedFlightTrail[0] ?? null;
  $: selectedFlightTrailLastPoint = selectedFlightTrail[selectedFlightTrail.length - 1] ?? null;
  $: selectedFlightTrailRecentPoints = [...selectedFlightTrail].slice(-5).reverse();
  $: selectedFlightDetailsKey = buildFlightDetailsKey(selectedFlight);
  $: selectedRouteAirports = selectedFlightDetails?.route?.airports ?? [];
  $: selectedFlightRadarModeLabel = activeReplaySnapshot ? "Replay frame" : statusLabel;
  $: selectedFlightFreshnessLabel = getFreshnessLabel(
    activeReplaySnapshot?.fetchedAt ?? state.fetchedAt
  );
  $: selectedFlightConfidence = activeReplaySnapshot ? "Archived" : confidenceLabel;
  $: selectedFlightTransportMode = activeReplaySnapshot ? "Archive" : transportLabel;
  $: selectedFlightDetailsFreshness = getFreshnessLabel(selectedFlightDetails?.meta?.fetched_at);
  $: selectedFlightTrailKey = selectedFlight?.icao24 ?? null;
  $: replayArchiveBboxKey = buildBboxKey(state.bbox);
  $: replayArchiveRequestKey = replayArchiveBboxKey
    ? `${replayArchiveBboxKey}:${replayWindowMinutes}`
    : null;
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
    selectedFlightTrackCursor = -1;
  }
  $: if (!selectedAirportCode) {
    lastSelectedAirportKey = null;
    selectedAirportDashboard = null;
    selectedAirportStatus = "idle";
    selectedAirportError = null;
    selectedAirportWeather = null;
    selectedAirportWeatherStatus = "idle";
    selectedAirportWeatherError = null;
  }
  $: if (selectedAirportCode && !selectedAirport && selectedAirportCode !== lastSelectedAirportKey) {
    lastSelectedAirportKey = selectedAirportCode;
    loadSelectedAirportDashboard({ entity_key: selectedAirportCode });
  }
  $: if (
    selectedAirport &&
    normalizeAirportKey(selectedAirport) !== lastSelectedAirportKey
  ) {
    lastSelectedAirportKey = normalizeAirportKey(selectedAirport);
    loadSelectedAirportDashboard(selectedAirport);
    loadSelectedAirportWeather(selectedAirport);
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
  $: if (replayArchiveRequestKey && replayArchiveRequestKey !== lastArchivedReplayBboxKey) {
    lastArchivedReplayBboxKey = replayArchiveRequestKey;
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
      resetSearchSuggestions();
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
  $: if (buildBboxKey(state.bbox) && typeof window !== "undefined") {
    state.bbox;
    mapViewport.zoom;
    if (airportFeedDebounceTimer) {
      window.clearTimeout(airportFeedDebounceTimer);
    }
    airportFeedDebounceTimer = window.setTimeout(() => {
      airportFeedDebounceTimer = null;
      refreshAirports(state.bbox);
    }, 260);
  }
  $: {
    replayPlaybackActive;
    replaySnapshotIndex;
    replaySourceSnapshots.length;
    replayPlaybackSpeed;
    syncReplayPlaybackTimer();
  }
  $: if (preferencesReady) {
    filters;
    sortBy;
    theme;
    mapStyle;
    selectedIcao24;
    mapViewport;
    replayWindowMinutes;
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
      savedEntities,
      weatherLayerEnabled,
      showAirportMarkers,
      selectedAirportCode,
      replayWindowMinutes,
      replayPlaybackSpeed,
    });
  }
  $: if (preferencesReady) {
    filters;
    mapStyle;
    mapViewport;
    filterPresets;
    sortBy;
    theme;
    onboardingDismissed;
    watchlist;
    watchModeEnabled;
    flightAnnotations;
    alertRules;
    alertEvents;
    monitoringSessions;
    savedViews;
    savedEntities;
    weatherLayerEnabled;
    showAirportMarkers;
    replayWindowMinutes;
    replayPlaybackSpeed;
    queueWorkspaceSave();
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
        airports={airportFeed.airports}
        selectedIcao24={selectedIcao24}
        selectedAirportKey={selectedAirportCode}
        selectedRouteAirports={selectedRouteAirports}
        followAircraft={followAircraft}
        mapStyle={mapStyle}
        trailPoints={selectedFlightTrail}
        watchedIcao24s={watchlist}
        watchModeEnabled={watchModeEnabled}
        dimmedIcao24s={dimmedFlightIds}
        showAirportMarkers={showAirportMarkers}
        weatherLayerEnabled={weatherLayerEnabled}
        initialViewport={mapViewport}
        fullscreenRequestId={fullscreenRequestId}
        viewPresetRequest={viewPresetRequest}
        focusRequest={flightFocusRequest}
        on:boundschange={handleBoundsChange}
        on:viewportchange={handleViewportChange}
        on:select={handleFlightSelect}
        on:selectairport={handleAirportSelect}
        on:backgroundclick={handleMapBackgroundClick}
      />
    </div>

    <header class="radar-topbar">
      <div class="overlay-card center-bar">
        <div class="center-bar-main">
          <div class="brand-inline">
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
                placeholder="Search aircraft, flights, airports, airlines, routes, locations"
                title="Search by callsign, registration, ICAO24, airline, route, airport or saved location"
                on:keydown={handleSearchInputKeydown}
              />
            </label>

            {#if showSearchSuggestions}
              <div class="search-suggestions">
                <EntitySearchPanel
                  query={searchQuery}
                  status={remoteSearchStatus}
                  error={remoteSearchError}
                  groups={remoteSearchGroups}
                  totalCount={remoteSearchCount}
                  activeResultKey={activeSearchResultKey}
                  onHoverResult={handleSearchResultHover}
                  onSelectResult={selectSearchResult}
                />
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
                {selectedFlight || selectedAirport || selectedEntityContext ? "Inspector" : "Traffic"}
              </button>
            {/if}
          </div>
        </div>

        <div class="topbar-status-strip" aria-label="Radar status strip">
          <span class="topbar-status-chip">{activeReplaySnapshot ? "Replay" : statusLabel}</span>
          <span>{mapStyleLabel}</span>
          <span>{showAirportMarkers ? "Airports on" : "Airports off"}</span>
          <span>{weatherLayerEnabled ? "Weather on" : "Weather off"}</span>
          <span>{workspaceSyncStatus === "success" ? activeWorkspaceProfile?.display_name ?? "Workspace" : workspaceSyncStatus}</span>
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

      {#if archivedReplayError}
        <div class="warning-banner">{archivedReplayError}</div>
      {/if}

      {#if selectedFlightTrailError && selectedFlight}
        <div class="warning-banner">{selectedFlightTrailError}</div>
      {/if}

      {#if alertToast}
        <div class="alert-toast">{alertToast.message}</div>
      {/if}

      {#if reportFeedback}
        <div class="alert-toast">{reportFeedback}</div>
      {/if}
    </div>

    {#if showMobileStartHint}
      <section class="overlay-card mobile-start-hint">
        <span>Tryb mobilny</span>
        <strong>Panele sa schowane. Kliknij `Traffic` albo `Tools` u gory.</strong>
        <div class="mobile-start-actions">
          <button class="widget-footer-button" type="button" on:click={toggleMobileSidebar}>Open traffic</button>
          <button class="widget-footer-button" type="button" on:click={toggleMobileUtility}>Open tools</button>
        </div>
      </section>
    {/if}

    <aside class:open={mobileUtilityOpen} class="overlay-card radar-left-panel">
      {#if isMobileViewport}
        <span class="mobile-drawer-handle" aria-hidden="true"></span>
      {/if}
      <div class="utility-header">
        <div class="utility-heading">
          <span>{utilityPanelEyebrow}</span>
          <strong>{utilityPanelTitle}</strong>
        </div>
        <div class="utility-meta">
          <span class="utility-pill">{statusLabel}</span>
          <span class="utility-count">{visibleTrackedCount}</span>
          {#if isMobileViewport}
            <button class="panel-dismiss" type="button" aria-label="Close tools panel" on:click={closeMobileUtility}>
              ×
            </button>
          {/if}
        </div>
      </div>

      <div class="utility-tabs" role="tablist" aria-label="Radar utility sections">
        <button
          class:active={utilityPanelMode === "radar"}
          class="utility-tab"
          type="button"
          on:click={() => {
            utilityPanelMode = "radar";
          }}
        >
          Radar
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
          class:active={utilityPanelMode === "tools"}
          class="utility-tab"
          type="button"
          on:click={() => {
            utilityPanelMode = "tools";
          }}
        >
          Tools
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
        {#if utilityPanelMode === "radar"}
          <section class="widget-card utility-summary-card">
            <div class="widget-header">
              <div class="widget-heading">
                <strong>Radar snapshot</strong>
                <span class="live-pill utility-state-pill">{transportLabel}</span>
              </div>
            </div>

            <div class="utility-fact-grid">
              <article>
                <span>Status</span>
                <strong>{statusLabel}</strong>
                <small>{freshnessLabel}</small>
              </article>
              <article>
                <span>Confidence</span>
                <strong>{confidenceLabel}</strong>
                <small>{activeReplaySnapshot ? "Replay frame" : "Live feed"}</small>
              </article>
              <article>
                <span>Map center</span>
                <strong>{mapCenterLabel}</strong>
                <small>Zoom {zoomLabel}</small>
              </article>
              <article>
                <span>Traffic</span>
                <strong>{visibleTrackedCount}</strong>
                <small>{airborneCount} airborne · {groundCount} ground</small>
              </article>
              <article>
                <span>Airports</span>
                <strong>{airportFeed.airports.length}</strong>
                <small>{showAirportMarkers ? "Markers visible" : "Layer hidden"}</small>
              </article>
            </div>
          </section>

          <section class="widget-card filter-card">
            <div class="widget-header">
              <div class="widget-heading">
                <strong>Radar filters</strong>
                <span class="live-pill utility-state-pill">{activeFilterCount}</span>
              </div>
              <button class="widget-mini-action" type="button" on:click={resetFilters}>Reset</button>
            </div>

            <div class="filter-chip-row">
              <button class="filter-chip" type="button" on:click={() => applyQuickFilter("fast")}>Fast jets</button>
              <button class="filter-chip" type="button" on:click={() => applyQuickFilter("high")}>High altitude</button>
              <button class="filter-chip" type="button" on:click={() => applyQuickFilter("recent")}>Recent</button>
              <button class="filter-chip" type="button" on:click={() => applyQuickFilter("cargo")}>Cargo</button>
              <button class="filter-chip" type="button" on:click={() => applyQuickFilter("military")}>Military</button>
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
                <span>Aircraft type</span>
                <input
                  type="text"
                  value={filters.aircraftType}
                  placeholder="B38M"
                  on:input={(event) => {
                    filters = {
                      ...filters,
                      aircraftType: event.currentTarget.value,
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
                <span>Route / airport</span>
                <input
                  type="text"
                  value={filters.route}
                  placeholder="WAW, EHAM, WAW-JFK"
                  on:input={(event) => {
                    filters = {
                      ...filters,
                      route: event.currentTarget.value,
                    };
                  }}
                />
              </label>

              <label class="filter-field">
                <span>Airport code</span>
                <input
                  type="text"
                  value={filters.airportCode}
                  placeholder="WAW or EPWA"
                  on:input={(event) => {
                    filters = {
                      ...filters,
                      airportCode: event.currentTarget.value,
                    };
                  }}
                />
              </label>

              <label class="filter-field">
                <span>Airport flow</span>
                <select
                  value={filters.airportFlow}
                  on:change={(event) => {
                    filters = {
                      ...filters,
                      airportFlow: event.currentTarget.value,
                    };
                  }}
                >
                  <option value="all">Arrivals + departures</option>
                  <option value="arrivals">Arrivals only</option>
                  <option value="departures">Departures only</option>
                </select>
              </label>

              <label class="filter-field">
                <span>Traffic state</span>
                <select
                  value={filters.trafficState}
                  on:change={(event) => {
                    filters = {
                      ...filters,
                      trafficState: event.currentTarget.value,
                    };
                  }}
                >
                  <option value="all">Airborne + ground</option>
                  <option value="airborne">Airborne only</option>
                  <option value="ground">Ground only</option>
                </select>
              </label>

              <label class="filter-field">
                <span>Traffic category</span>
                <select
                  value={filters.trafficCategory}
                  on:change={(event) => {
                    filters = {
                      ...filters,
                      trafficCategory: event.currentTarget.value,
                    };
                  }}
                >
                  {#each TRAFFIC_CATEGORY_OPTIONS as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
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
                <span>Map filter mode</span>
                <select
                  value={filters.dimFilteredTraffic ? "dim" : "hide"}
                  on:change={(event) => {
                    filters = {
                      ...filters,
                      dimFilteredTraffic: event.currentTarget.value === "dim",
                    };
                  }}
                >
                  <option value="dim">Dim unmatched traffic</option>
                  <option value="hide">Hide unmatched traffic</option>
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
              {#if topTypeSuggestions.length}
                <div class="suggestion-row">
                  <span>Top types</span>
                  <div>
                    {#each topTypeSuggestions as suggestion}
                      <button
                        class="suggestion-pill"
                        type="button"
                        on:click={() => {
                          filters = {
                            ...filters,
                            aircraftType: suggestion,
                          };
                        }}
                      >
                        {suggestion}
                      </button>
                    {/each}
                  </div>
                </div>
              {/if}

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

            <div class="filter-suggestion-group">
              <div class="suggestion-row">
                <span>Map layers</span>
                <div>
                  <button
                    class:active={showAirportMarkers}
                    class="filter-chip"
                    type="button"
                    on:click={() => {
                      showAirportMarkers = !showAirportMarkers;
                    }}
                  >
                    Airports
                  </button>
                  <button
                    class:active={weatherLayerEnabled}
                    class="filter-chip"
                    type="button"
                    on:click={() => {
                      weatherLayerEnabled = !weatherLayerEnabled;
                    }}
                  >
                    Weather radar
                  </button>
                </div>
              </div>

              <div class="suggestion-row">
                <span>Area workflow</span>
                <div>
                  <button class="filter-chip" type="button" on:click={saveCurrentMapArea}>
                    Save current area
                  </button>
                  <button class="filter-chip" type="button" on:click={monitorCurrentMapArea}>
                    Monitor current area
                  </button>
                </div>
              </div>
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
            windowMinutes={replayWindowMinutes}
            playbackSpeed={replayPlaybackSpeed}
            canStepBackward={canStepReplayBackward}
            canStepForward={canStepReplayForward}
            onSelectIndex={selectReplaySnapshot}
            onReturnToLive={returnToLiveReplay}
            onJumpStart={jumpReplayToStart}
            onJumpLatest={jumpReplayToLatest}
            onSetWindowMinutes={setReplayWindowMinutes}
            onSetPlaybackSpeed={setReplayPlaybackSpeed}
            onStepBackward={() => stepReplay(-1)}
            onStepForward={() => stepReplay(1)}
            onTogglePlayback={toggleReplayPlayback}
          />

          <details class="utility-drawer" open={Boolean(activeMonitoringSession) || monitoringSessions.length > 0}>
            <summary>
              <span>Saved replay sessions</span>
              <strong>{monitoringSessions.length}</strong>
            </summary>
            <div class="utility-drawer-body">
              <p class="drawer-caption">Replay snapshots saved only on this device.</p>
              <MonitoringSessionsPanel
                sessions={monitoringSessions}
                activeSessionId={activeMonitoringSessionId}
                onSaveSession={saveCurrentMonitoringSession}
                onLoadSession={loadMonitoringSession}
                onDeleteSession={deleteMonitoringSession}
              />
            </div>
          </details>
        {:else}
          <section class="widget-card utility-summary-card">
            <div class="widget-header">
              <div class="widget-heading">
                <strong>Workspace sync</strong>
                <span class="live-pill utility-state-pill">{workspaceSyncStatus === "success" ? "SYNC" : workspaceSyncStatus === "saving" ? "SAVE" : workspaceSyncStatus === "loading" ? "LOAD" : "ERR"}</span>
              </div>
            </div>
            <p class="widget-empty">
              Profiles now sync filters, bookmarks, notes and replay sessions to the backend workspace store while local cache stays as fallback.
            </p>
          </section>

          <details class="utility-drawer" open>
            <summary>
              <span>Reports</span>
              <strong>CSV</strong>
            </summary>
            <div class="utility-drawer-body">
              <p class="drawer-caption">
                Export the current radar picture as CSV or open a print-friendly report snapshot.
              </p>
              <div class="local-tool-actions">
                <button class="widget-footer-button" type="button" on:click={exportVisibleTrafficCsv}>
                  Export visible traffic CSV
                </button>
                <button class="widget-footer-button" type="button" on:click={printVisibleTrafficReport}>
                  Print traffic report
                </button>
                {#if selectedAirport && selectedAirportDashboard}
                  <button class="widget-footer-button" type="button" on:click={exportSelectedAirportCsv}>
                    Export airport board CSV
                  </button>
                {/if}
              </div>
            </div>
          </details>

          <details class="utility-drawer" open={workspaceProfiles.length > 0}>
            <summary>
              <span>Profiles</span>
              <strong>{workspaceProfiles.length}</strong>
            </summary>
            <div class="utility-drawer-body">
              <WorkspaceProfilesPanel
                profiles={workspaceProfiles}
                activeProfileId={activeWorkspaceProfileId}
                syncStatus={workspaceSyncStatus}
                updatedAt={workspaceUpdatedAt}
                draftName={workspaceProfileDraft}
                syncError={workspaceSyncError}
                onSelectProfile={loadWorkspaceProfile}
                onDraftChange={(value) => {
                  workspaceProfileDraft = value;
                }}
                onCreateProfile={createWorkspaceDesk}
              />
            </div>
          </details>

          <details class="utility-drawer" open={watchlist.length > 0}>
            <summary>
              <span>Tracked aircraft</span>
              <strong>{watchlist.length}</strong>
            </summary>
            <div class="utility-drawer-body">
              <p class="drawer-caption">Saved aircraft stay highlighted on the radar and now sync with the active workspace profile.</p>
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
            </div>
          </details>

          <details class="utility-drawer" open={savedEntities.length > 0}>
            <summary>
              <span>Saved entities</span>
              <strong>{savedEntities.length}</strong>
            </summary>
            <div class="utility-drawer-body">
              <p class="drawer-caption">Bookmarks stay synced with the active workspace and now reopen flights, airports, locations, airlines and routes directly from one saved list.</p>

              {#if savedFlightEntities.length}
                <div class="mini-stat-list">
                  {#each savedFlightEntities as entity}
                    <div>
                      <span>
                        <strong>{entity.label}</strong>
                        <small>{entity.subtitle}</small>
                      </span>
                      <div class="compact-entity-actions">
                        <button class="widget-footer-button" type="button" on:click={() => openSavedEntity(entity)}>Open</button>
                        <button class="preset-delete" type="button" on:click={() => removeSavedEntity(entity.entity_type, entity.entity_key)}>Remove</button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}

              {#if savedAircraftEntities.length}
                <div class="mini-stat-list">
                  {#each savedAircraftEntities as entity}
                    <div>
                      <span>
                        <strong>{entity.label}</strong>
                        <small>{entity.subtitle}</small>
                      </span>
                      <div class="compact-entity-actions">
                        <button class="widget-footer-button" type="button" on:click={() => openSavedEntity(entity)}>Open</button>
                        <button class="preset-delete" type="button" on:click={() => removeSavedEntity(entity.entity_type, entity.entity_key)}>Remove</button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}

              {#if savedAirportEntities.length}
                <div class="mini-stat-list">
                  {#each savedAirportEntities as entity}
                    <div>
                      <span>
                        <strong>{entity.label}</strong>
                        <small>{entity.subtitle}</small>
                      </span>
                      <div class="compact-entity-actions">
                        <button class="widget-footer-button" type="button" on:click={() => openSavedEntity(entity)}>Open</button>
                        <button class="preset-delete" type="button" on:click={() => removeSavedEntity(entity.entity_type, entity.entity_key)}>Remove</button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}

              {#if savedLocationEntities.length}
                <div class="mini-stat-list">
                  {#each savedLocationEntities as entity}
                    <div>
                      <span>
                        <strong>{entity.label}</strong>
                        <small>{entity.subtitle}</small>
                      </span>
                      <div class="compact-entity-actions">
                        <button class="widget-footer-button" type="button" on:click={() => openSavedEntity(entity)}>Focus</button>
                        <button
                          class="widget-footer-button"
                          type="button"
                          on:click={() =>
                            addAlertRule({
                              type: "area",
                              query: entity.label ?? entity.entity_key,
                              payload: {
                                bbox: entity.bbox ?? null,
                              },
                            })}
                        >
                          Alert
                        </button>
                        <button class="preset-delete" type="button" on:click={() => removeSavedEntity(entity.entity_type, entity.entity_key)}>Remove</button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}

              {#if savedAirlineEntities.length}
                <div class="mini-stat-list">
                  {#each savedAirlineEntities as entity}
                    <div>
                      <span>
                        <strong>{entity.label}</strong>
                        <small>{entity.subtitle}</small>
                      </span>
                      <div class="compact-entity-actions">
                        <button
                          class="widget-footer-button"
                          type="button"
                          on:click={() => {
                            openSavedEntity(entity);
                          }}
                        >
                          Filter
                        </button>
                        <button class="preset-delete" type="button" on:click={() => removeSavedEntity(entity.entity_type, entity.entity_key)}>Remove</button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}

              {#if savedRouteEntities.length}
                <div class="mini-stat-list">
                  {#each savedRouteEntities as entity}
                    <div>
                      <span>
                        <strong>{entity.label}</strong>
                        <small>{entity.subtitle}</small>
                      </span>
                      <div class="compact-entity-actions">
                        <button class="widget-footer-button" type="button" on:click={() => openSavedEntity(entity)}>Open</button>
                        <button class="preset-delete" type="button" on:click={() => removeSavedEntity(entity.entity_type, entity.entity_key)}>Remove</button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </details>

          {#if selectedFlight}
            <details class="utility-drawer" open={selectedFlightAnnotation.tags.length > 0 || Boolean(selectedFlightAnnotation.notes.trim())}>
              <summary>
                <span>Selected aircraft notes</span>
                <strong>{selectedFlightAnnotation.tags.length}</strong>
              </summary>
              <div class="utility-drawer-body">
                <p class="drawer-caption">
                  Private notes and quick local alerts for {selectedFlightCallsignLabel}.
                </p>

                <div class="local-tool-actions">
                  <button class="widget-footer-button" type="button" on:click={toggleSelectedFlightWatchlist}>
                    {watchlist.includes(selectedFlight.icao24) ? "Remove tracked aircraft" : "Bookmark aircraft"}
                  </button>
                  {#if selectedFlight.callsign}
                    <button
                      class="widget-footer-button"
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
                  {#if selectedOperatorCode !== "N/A"}
                    <button
                      class="widget-footer-button"
                      type="button"
                      on:click={() =>
                        addAlertRule({
                          type: "airline",
                          query: selectedOperatorCode,
                        })}
                    >
                      Alert by airline
                    </button>
                  {/if}
                  {#if selectedFlight.registration}
                    <button
                      class="widget-footer-button"
                      type="button"
                      on:click={() =>
                        addAlertRule({
                          type: "registration",
                          query: selectedFlight.registration,
                        })}
                    >
                      Alert by registration
                    </button>
                  {/if}
                  {#if selectedFlight.type_code}
                    <button
                      class="widget-footer-button"
                      type="button"
                      on:click={() =>
                        addAlertRule({
                          type: "type_code",
                          query: selectedFlight.type_code,
                        })}
                    >
                      Alert by type
                    </button>
                  {/if}
                  <button
                    class="widget-footer-button"
                    type="button"
                    on:click={() =>
                      addAlertRule({
                        type: "icao24",
                        query: selectedFlight.icao24,
                      })}
                  >
                    Alert by ICAO24
                  </button>
                </div>

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
              </div>
            </details>
          {/if}

          <details class="utility-drawer" open={!onboardingDismissed}>
            <summary>
              <span>Guide and shortcuts</span>
              <strong>{onboardingDismissed ? "Hidden" : "Open"}</strong>
            </summary>
            <div class="utility-drawer-body">
              {#if !onboardingDismissed}
                <OnboardingPanel onDismiss={dismissOnboarding} />
              {:else}
                <section class="widget-card utility-summary-card utility-compact-card">
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
            </div>
          </details>

          <details class="utility-drawer" open={savedViews.length > 0}>
            <summary>
              <span>Saved views</span>
              <strong>{savedViews.length}</strong>
            </summary>
            <div class="utility-drawer-body">
              <p class="drawer-caption">Saved only in this browser for quick jumps back to your favorite airspace.</p>
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
            </div>
          </details>

          <details class="utility-drawer" open={alertRules.length > 0 || activeAlertEvents.length > 0}>
            <summary>
              <span>Alerts</span>
              <strong>{alertRules.length}</strong>
            </summary>
            <div class="utility-drawer-body">
              <p class="drawer-caption">Alert rules sync with the active workspace profile and can watch callsigns, ICAO24s, airlines, countries, registrations and aircraft types.</p>
              <AlertPanel
                rules={alertRules}
                events={alertEvents}
                onAddRule={addAlertRule}
                onRemoveRule={removeAlertRule}
                onClearEvents={clearAlertEvents}
              />
            </div>
          </details>

          <details class="utility-drawer" open={comparisonFlights.length > 1}>
            <summary>
              <span>Aircraft comparison</span>
              <strong>{comparisonFlights.length}</strong>
            </summary>
            <div class="utility-drawer-body">
              <p class="drawer-caption">Comparison stays available here without competing with the live radar by default.</p>
              <ComparisonPanel
                flights={comparisonFlights}
                selectedIcao24={selectedIcao24}
                onSelectFlight={selectWatchedFlight}
              />
            </div>
          </details>
        {/if}
      </div>
    </aside>

    {#if isMobileViewport && mobileUtilityOpen}
      <button class="sidebar-backdrop utility-backdrop" type="button" aria-label="Close tools panel" on:click={closeMobileUtility}></button>
    {/if}

    {#if isMobileViewport && mobileSidebarOpen}
      <button class="sidebar-backdrop" type="button" aria-label="Close panel" on:click={closeMobileSidebar}></button>
    {/if}

    <aside class:open={mobileSidebarOpen} class="overlay-card radar-right-panel">
      {#if isMobileViewport}
        <span class="mobile-drawer-handle" aria-hidden="true"></span>
      {/if}
      <div class="rail-header">
        <div class="rail-brand">
          <span>
            {#if selectedFlight}
              {selectedFlightQuickStatus}
            {:else if selectedAirport}
              Airport board
            {:else if selectedEntityContext}
              Search focus
            {:else}
              Click any aircraft
            {/if}
          </span>
          <strong>
            {#if selectedFlight}
              {selectedFlightCallsignLabel}
            {:else if selectedAirport}
              {selectedAirport.iata ?? selectedAirport.icao ?? selectedAirport.entity_key}
            {:else if selectedEntityContext}
              {selectedEntityContext.label ?? selectedEntityContext.entity_key}
            {:else}
              Visible traffic
            {/if}
          </strong>
          {#if selectedFlightQuickSubtitle}
            <p class="rail-subtitle">{selectedFlightQuickSubtitle}</p>
          {:else if selectedAirport}
            <p class="rail-subtitle">
              {selectedAirport.name ?? selectedAirport.label}
              {#if selectedAirport.city || selectedAirport.country}
                · {[selectedAirport.city, selectedAirport.country].filter(Boolean).join(", ")}
              {/if}
            </p>
          {:else if selectedEntityContext}
            <p class="rail-subtitle">{selectedEntityContext.subtitle ?? "Selected search entity"}</p>
          {/if}

          {#if selectedFlightQuickMetrics.length}
            <div class="rail-metric-row" aria-label="Selected aircraft live metrics">
              {#each selectedFlightQuickMetrics as metric}
                <span class="rail-metric-chip">
                  <small>{metric.label}</small>
                  <strong>{metric.value}</strong>
                </span>
              {/each}
            </div>
          {/if}
        </div>
        {#if selectedFlight}
          <div class="rail-actions">
            <button class:active={followAircraft} class="rail-toggle" type="button" on:click={toggleFollowAircraft}>
              {followAircraft ? "Following" : "Follow"}
            </button>
            <button
              class:active={watchlist.includes(selectedFlight.icao24)}
              class="rail-toggle"
              type="button"
              on:click={toggleSelectedFlightWatchlist}
            >
              {watchlist.includes(selectedFlight.icao24) ? "Saved" : "Bookmark"}
            </button>
            <button class="rail-toggle" type="button" on:click={copyShareLink}>
              {shareFeedback || "Share"}
            </button>
            <button
              class="rail-close"
              type="button"
              aria-label="Close selected aircraft"
              on:click={() => clearSelectedFlight({ closeSidebar: true })}
            >
              ×
            </button>
          </div>
        {:else if selectedAirport}
          <div class="rail-actions">
            <button class="rail-toggle" type="button" on:click={addSelectedAirportAlert}>
              Alert
            </button>
            <button
              class:active={selectedAirportBookmarked}
              class="rail-toggle"
              type="button"
              on:click={() => toggleEntityBookmark(selectedAirport)}
            >
              {selectedAirportBookmarked ? "Saved" : "Bookmark"}
            </button>
            <button
              class="rail-close"
              type="button"
              aria-label="Close selected airport"
              on:click={() => handleMapBackgroundClick()}
            >
              ×
            </button>
          </div>
        {:else if selectedEntityContext}
          <div class="rail-actions">
            <button
              class:active={isEntityBookmarked(selectedEntityContext.entity_type, selectedEntityContext.entity_key)}
              class="rail-toggle"
              type="button"
              on:click={() => toggleEntityBookmark(selectedEntityContext)}
            >
              {isEntityBookmarked(selectedEntityContext.entity_type, selectedEntityContext.entity_key) ? "Saved" : "Bookmark"}
            </button>
            {#if selectedEntityContext.entity_type === "airline" || selectedEntityContext.entity_type === "location"}
              <button class="rail-toggle" type="button" on:click={addEntityContextAlert}>
                Alert
              </button>
            {/if}
            <button class="rail-toggle" type="button" on:click={copyShareLink}>
              {shareFeedback || "Share"}
            </button>
            <button class="rail-close" type="button" aria-label="Close search focus" on:click={handleMapBackgroundClick}>
              ×
            </button>
          </div>
        {:else}
          <div class="rail-actions">
            <span class="rail-count">{visibleTrackedCount}</span>
            {#if isMobileViewport}
              <button class="panel-dismiss" type="button" aria-label="Close inspector panel" on:click={closeMobileSidebar}>
                ×
              </button>
            {/if}
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
          </div>

          {#if inspectorTab === "details"}
            <FlightDetailsPanel
              flight={selectedFlight}
              details={selectedFlightDetails}
              detailsStatus={selectedFlightDetailsStatus}
              detailsError={selectedFlightDetailsError}
              followAircraft={followAircraft}
              trailPoints={selectedFlightTrail}
              bookmarked={watchlist.includes(selectedFlight.icao24)}
              liveStatus={selectedFlightRadarModeLabel}
              snapshotFreshness={selectedFlightFreshnessLabel}
              snapshotConfidence={selectedFlightConfidence}
              snapshotTransport={selectedFlightTransportMode}
              detailFreshness={selectedFlightDetailsFreshness}
              isReplayActive={Boolean(activeReplaySnapshot)}
              shareFeedback={shareFeedback}
              onToggleFollow={toggleFollowAircraft}
              onToggleBookmark={toggleSelectedFlightWatchlist}
              onOpenAirport={(airport) => openAirportInspector(airport, { focusMap: true, zoom: 8.8 })}
              onRetryDetails={retrySelectedFlightDetails}
              onShare={copyShareLink}
              onOpenTracking={() => openInspectorTab("tracking")}
              onAddAlert={addSelectedFlightAlert}
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
                  <span>Status</span>
                  <strong>{formatFlightStatus(selectedFlight)}</strong>
                  <small>
                    {selectedFlight.registration ?? selectedFlight.icao24.toUpperCase()}
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
                  <span>Map focus</span>
                  <strong>{followAircraft ? "Auto-follow" : "Manual focus"}</strong>
                </div>
                <div>
                  <span>Replay archive</span>
                  <strong>{replaySourceSnapshots.length} snapshots</strong>
                </div>
              </div>

              {#if selectedRouteAirports.length}
                <div class="route-desk-row">
                  {#if selectedRouteAirports[0]}
                    <button
                      class="workflow-button"
                      type="button"
                      on:click={() => openAirportInspector(selectedRouteAirports[0], { focusMap: true, zoom: 8.8 })}
                    >
                      Open {formatAirportCode(selectedRouteAirports[0])} desk
                    </button>
                  {/if}
                  {#if selectedRouteAirports[selectedRouteAirports.length - 1]}
                    <button
                      class="workflow-button"
                      type="button"
                      on:click={() =>
                        openAirportInspector(
                          selectedRouteAirports[selectedRouteAirports.length - 1],
                          { focusMap: true, zoom: 8.8 }
                        )}
                    >
                      Open {formatAirportCode(selectedRouteAirports[selectedRouteAirports.length - 1])} desk
                    </button>
                  {/if}
                </div>
              {/if}

              {#if selectedFlightTrail.length > 1}
                <div class="tracking-timeline">
                  <div class="workflow-header compact">
                    <div>
                      <p class="workflow-eyebrow">Single-flight replay</p>
                      <h2>Trail scrubber</h2>
                    </div>
                    <span class="workflow-status">
                      {#if selectedFlightTrackPoint}
                        {new Intl.DateTimeFormat("pl-PL", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(selectedFlightTrackPoint.timestamp))}
                      {:else}
                        Latest point
                      {/if}
                    </span>
                  </div>

                  <label class="workflow-slider">
                    <span>{selectedFlightTrackCursor >= 0 ? "Inspecting archived trail point" : "Following latest known trail point"}</span>
                    <input
                      type="range"
                      min="0"
                      max={selectedFlightTrail.length - 1}
                      step="1"
                      value={selectedFlightTrackSliderValue}
                      on:input={(event) => setSelectedFlightTrackCursor(Number(event.currentTarget.value))}
                    />
                  </label>

                  <div class="route-desk-row">
                    <button class="workflow-button" type="button" on:click={jumpSelectedFlightTrackStart}>
                      First point
                    </button>
                    <button class="workflow-button" type="button" on:click={jumpSelectedFlightTrackLatest}>
                      Latest point
                    </button>
                  </div>

                  {#if selectedFlightTrackPoint}
                    <div class="workflow-metrics">
                      <article>
                        <span>Replay altitude</span>
                        <strong>{formatAltitude(selectedFlightTrackPoint.altitude)}</strong>
                        <small>Historical point</small>
                      </article>
                      <article>
                        <span>Replay speed</span>
                        <strong>{formatSpeed(selectedFlightTrackPoint.velocity)}</strong>
                        <small>Captured on trail</small>
                      </article>
                    </div>
                  {/if}
                </div>
              {/if}

              {#if selectedFlightTrailRecentPoints.length}
                <div class="tracking-timeline">
                  <div class="workflow-header compact">
                    <div>
                      <p class="workflow-eyebrow">Recent trail</p>
                      <h2>Latest positions</h2>
                    </div>
                  </div>

                  <div class="timeline-list">
                    {#each selectedFlightTrailRecentPoints as point}
                      <div class="timeline-row">
                        <span>{new Intl.DateTimeFormat("pl-PL", { hour: "2-digit", minute: "2-digit" }).format(new Date(point.timestamp))}</span>
                        <strong>{formatAltitude(point.altitude)}</strong>
                        <small>{formatSpeed(point.velocity)}</small>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}
            </section>
          {/if}
        {:else if selectedAirport}
          <AirportDetailsPanel
            airport={selectedAirport}
            dashboard={selectedAirportDashboard}
            status={selectedAirportStatus}
            error={selectedAirportError}
            weather={selectedAirportWeather}
            weatherStatus={selectedAirportWeatherStatus}
            weatherError={selectedAirportWeatherError}
            weatherLayerEnabled={weatherLayerEnabled}
            bookmarked={selectedAirportBookmarked}
            onSelectFlight={selectWatchedFlight}
            onRetry={() => loadSelectedAirportDashboard(selectedAirport)}
            onToggleWeather={() => {
              weatherLayerEnabled = !weatherLayerEnabled;
            }}
            onToggleBookmark={() => toggleEntityBookmark(selectedAirport)}
            onAddAlert={addSelectedAirportAlert}
            onFilterAllTraffic={() => applyAirportTrafficFilter(selectedAirport, "all")}
            onFilterArrivals={() => applyAirportTrafficFilter(selectedAirport, "arrivals")}
            onFilterDepartures={() => applyAirportTrafficFilter(selectedAirport, "departures")}
          />
        {:else if selectedEntityContext}
          <section class="panel aircraft-workflow-panel">
            <div class="workflow-header">
              <div>
                <p class="workflow-eyebrow">Search focus</p>
                <h2>{selectedEntityContext.label ?? selectedEntityContext.entity_key}</h2>
              </div>
              <span class="workflow-status">{selectedEntityContext.entity_type ?? "entity"}</span>
            </div>

            <div class="workflow-facts">
              <div>
                <span>Entity type</span>
                <strong>{selectedEntityContext.entity_type}</strong>
              </div>
              <div>
                <span>Scope</span>
                <strong>{selectedEntityContext.subtitle ?? "Live traffic intelligence"}</strong>
              </div>
              <div>
                <span>Map focus</span>
                <strong>
                  {#if selectedEntityContext.entity_type === "location"}
                    Saved area
                  {:else if selectedEntityContext.entity_type === "airline"}
                    Airline traffic
                  {:else if selectedEntityContext.entity_type === "route"}
                    Recent route
                  {:else}
                    Search entity
                  {/if}
                </strong>
              </div>
              <div>
                <span>Live matches</span>
                <strong>{selectedEntityContextMatches.length}</strong>
              </div>
            </div>

            <div class="local-tool-actions">
              {#if selectedEntityContext.entity_type === "airline"}
                <button
                  class="workflow-button primary"
                  type="button"
                  on:click={() => {
                    filters = {
                      ...filters,
                      operator: selectedEntityContext.entity_key ?? selectedEntityContext.label ?? "",
                    };
                    utilityPanelMode = "radar";
                  }}
                >
                  Filter by airline
                </button>
                <button class="workflow-button" type="button" on:click={addEntityContextAlert}>
                  Alert by airline
                </button>
              {/if}
              {#if selectedEntityContext.entity_type === "location"}
                <button class="workflow-button primary" type="button" on:click={() => focusLocationEntity(selectedEntityContext)}>
                  Focus saved area
                </button>
                <button class="workflow-button" type="button" on:click={addEntityContextAlert}>
                  Monitor area
                </button>
              {/if}
              {#if selectedEntityContext.entity_type === "route"}
                {#if selectedEntityContextOriginAirport}
                  <button
                    class="workflow-button primary"
                    type="button"
                    on:click={() => openAirportInspector(selectedEntityContextOriginAirport, { focusMap: true, zoom: 8.8 })}
                  >
                    Open origin
                  </button>
                {/if}
                {#if selectedEntityContextDestinationAirport}
                  <button
                    class="workflow-button"
                    type="button"
                    on:click={() => openAirportInspector(selectedEntityContextDestinationAirport, { focusMap: true, zoom: 8.8 })}
                    >
                      Open destination
                    </button>
                {/if}
                <button class="workflow-button" type="button" on:click={addEntityContextAlert}>
                  Alert by route
                </button>
              {/if}
              <button class="workflow-button" type="button" on:click={copyShareLink}>Share view</button>
            </div>

            {#if selectedEntityContext.entity_type === "route" && (selectedEntityContextOriginAirport || selectedEntityContextDestinationAirport)}
              <div class="workflow-facts">
                {#if selectedEntityContextOriginAirport}
                  <div>
                    <span>Origin</span>
                    <strong>{selectedEntityContextOriginAirport.label}</strong>
                  </div>
                {/if}
                {#if selectedEntityContextDestinationAirport}
                  <div>
                    <span>Destination</span>
                    <strong>{selectedEntityContextDestinationAirport.label}</strong>
                  </div>
                {/if}
              </div>
            {/if}

            <section class="facts-panel">
              <div class="facts-header">
                <strong>Matching live traffic</strong>
                <span>{selectedEntityContextMatches.length} visible now</span>
              </div>

              {#if selectedEntityContextMatches.length}
                <div class="mini-stat-list">
                  {#each selectedEntityContextMatches as flight}
                    <div>
                      <span>
                        <strong>{flight.callsign ?? flight.registration ?? flight.icao24.toUpperCase()}</strong>
                        <small>
                          {[
                            flight.registration ?? flight.icao24.toUpperCase(),
                            flight.type_code,
                            flight.route_label ?? flight.origin_country,
                          ].filter(Boolean).join(" · ")}
                        </small>
                      </span>
                      <div class="compact-entity-actions">
                        <button
                          class="widget-footer-button"
                          type="button"
                          on:click={() =>
                            openFlightInspector(flight, {
                              focusMap: true,
                              zoom: 8.4,
                              exitReplay: false,
                              inspectorTab: "details",
                            })}
                        >
                          Open
                        </button>
                      </div>
                    </div>
                  {/each}
                </div>
              {:else}
                <p class="widget-empty">
                  {selectedEntityContext.entity_type === "location"
                    ? "No current aircraft are visible inside this saved area."
                    : selectedEntityContext.entity_type === "route"
                      ? "No visible aircraft currently match this tracked route."
                      : "No visible aircraft match this search focus right now."}
                </p>
              {/if}
            </section>
          </section>
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
    background: rgba(17, 19, 23, 0.94);
    backdrop-filter: blur(14px);
    box-shadow:
      0 18px 34px rgba(0, 0, 0, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.03);
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
    top: 0.85rem;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    justify-content: center;
  }

  .center-bar {
    display: grid;
    gap: 0.58rem;
    width: min(34rem, calc(100vw - 39rem));
    min-width: 30rem;
    padding: 0.48rem 0.54rem 0.52rem 0.62rem;
    border-radius: 16px;
    background: rgba(16, 18, 22, 0.96);
  }

  .center-bar-main {
    display: grid;
    grid-template-columns: auto minmax(250px, 1fr) auto;
    align-items: center;
    gap: 0.6rem;
  }

  .brand-inline {
    display: flex;
    align-items: center;
    gap: 0.38rem;
  }

  .brand-copy strong {
    display: block;
    margin: 0;
    font-size: 0.96rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
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

  .search-field:focus-within {
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.5),
      0 0 0 3px rgba(245, 185, 8, 0.18);
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
    max-height: min(34rem, calc(100vh - 7rem));
    overflow-y: auto;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background:
      linear-gradient(180deg, rgba(27, 30, 35, 0.98) 0%, rgba(14, 16, 20, 0.98) 100%);
    box-shadow:
      0 18px 32px rgba(0, 0, 0, 0.26),
      inset 0 1px 0 rgba(255, 255, 255, 0.03);
  }

  .center-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.45rem;
    align-items: center;
  }

  .topbar-status-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    padding-left: 0.04rem;
  }

  .topbar-status-strip span {
    display: inline-flex;
    align-items: center;
    min-height: 1.65rem;
    padding: 0 0.58rem;
    border-radius: 999px;
    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #d7e0ea;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }

  .topbar-status-chip {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%) !important;
    border-color: transparent !important;
  }

  .filter-token-list,
  .filter-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.38rem;
  }

  .filter-chip,
  .filter-token,
  .suggestion-pill {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    font: inherit;
    cursor: pointer;
  }

  .filter-chip,
  .suggestion-pill {
    padding: 0.42rem 0.68rem;
    font-size: 0.72rem;
    font-weight: 700;
    color: #d8e1eb;
    background: rgba(255, 255, 255, 0.05);
  }

  .filter-chip.active {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
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
    padding: 0.4rem 0.62rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.05);
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

  .mobile-start-hint {
    position: absolute;
    top: 9.25rem;
    left: 50%;
    transform: translateX(-50%);
    z-index: 1180;
    width: min(22rem, calc(100vw - 1.5rem));
    display: none;
    gap: 0.42rem;
    padding: 0.9rem;
    text-align: left;
  }

  .mobile-start-hint span {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: rgba(185, 194, 206, 0.78);
  }

  .mobile-start-hint strong {
    color: #f4f7fb;
    font-size: 0.92rem;
    line-height: 1.35;
  }

  .mobile-start-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
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
    background: rgba(12, 14, 17, 0.96);
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
    background: rgba(12, 14, 17, 0.97);
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
    position: sticky;
    top: 0;
    z-index: 4;
    padding-bottom: 0.15rem;
    background: linear-gradient(180deg, rgba(12, 14, 17, 0.98) 0%, rgba(12, 14, 17, 0.92) 72%, rgba(12, 14, 17, 0) 100%);
    backdrop-filter: blur(10px);
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
    grid-template-columns: repeat(3, minmax(0, 1fr));
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
    background: rgba(255, 255, 255, 0.03);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.16);
  }

  .widget-card-secondary {
    gap: 0.62rem;
  }

  .utility-summary-card {
    background: rgba(255, 255, 255, 0.028);
  }

  .utility-compact-card {
    background: rgba(255, 255, 255, 0.022);
  }

  .utility-fact-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.5rem;
  }

  .utility-fact-grid article {
    display: grid;
    gap: 0.18rem;
    padding: 0.72rem 0.76rem;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(0, 0, 0, 0.18);
  }

  .utility-fact-grid span {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: rgba(171, 186, 202, 0.62);
  }

  .utility-fact-grid strong {
    color: #f2f6fb;
    font-size: 0.9rem;
  }

  .utility-fact-grid small {
    color: rgba(190, 203, 217, 0.74);
    font-size: 0.74rem;
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
    color: #f4f7fb;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .utility-state-pill {
    min-width: 3.5rem;
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

  .utility-drawer {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.022);
    overflow: hidden;
  }

  .utility-drawer summary {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
    padding: 0.82rem 0.86rem;
    list-style: none;
    cursor: pointer;
  }

  .utility-drawer summary::-webkit-details-marker {
    display: none;
  }

  .utility-drawer summary span {
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #d8e1eb;
  }

  .utility-drawer summary strong {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2rem;
    min-height: 1.8rem;
    padding: 0 0.58rem;
    border-radius: 999px;
    font-size: 0.72rem;
    color: #f4f7fb;
    background: rgba(255, 255, 255, 0.08);
  }

  .utility-drawer-body {
    display: grid;
    gap: 0.65rem;
    padding: 0 0.78rem 0.78rem;
  }

  .drawer-caption {
    margin: 0;
    font-size: 0.74rem;
    line-height: 1.45;
    color: rgba(190, 203, 217, 0.76);
  }

  .local-tool-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
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

  .compact-entity-actions {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .widget-footer-button {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 0.66rem 0.78rem;
    font: inherit;
    font-weight: 700;
    color: #edf2f7;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
  }

  .widget-mini-action {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.4rem 0.7rem;
    font: inherit;
    font-size: 0.68rem;
    font-weight: 800;
    color: #eef3f8;
    background: rgba(255, 255, 255, 0.05);
    cursor: pointer;
  }

  .rail-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: start;
    position: sticky;
    top: 0;
    z-index: 4;
    padding: 0.08rem 0.08rem 0.72rem;
    background: linear-gradient(180deg, rgba(12, 14, 17, 0.98) 0%, rgba(12, 14, 17, 0.92) 72%, rgba(12, 14, 17, 0) 100%);
    backdrop-filter: blur(10px);
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

  .rail-subtitle {
    margin: 0;
    color: #aeb8c6;
    font-size: 0.76rem;
    line-height: 1.4;
  }

  .rail-metric-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.42rem;
    margin-top: 0.58rem;
  }

  .rail-metric-chip {
    display: inline-grid;
    gap: 0.14rem;
    min-width: 4.55rem;
    padding: 0.46rem 0.58rem 0.5rem;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.05);
  }

  .rail-metric-chip small {
    color: rgba(171, 186, 201, 0.68);
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .rail-metric-chip strong {
    color: #eff4fa;
    font-size: 0.78rem;
    line-height: 1.2;
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
    color: #f4f7fb;
    background: rgba(255, 255, 255, 0.08);
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

  .panel-dismiss {
    border: 0;
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    font: inherit;
    font-size: 1.05rem;
    line-height: 1;
    color: #e7edf4;
    background: rgba(255, 255, 255, 0.07);
    cursor: pointer;
  }

  .mobile-drawer-handle {
    align-self: center;
    width: 3rem;
    height: 0.28rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.16);
    margin: -0.1rem auto 0.1rem;
  }

  .inspector-tab-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
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

  .workflow-header.compact h2 {
    font-size: 0.96rem;
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

  .route-desk-row,
  .tracking-timeline,
  .timeline-list {
    display: grid;
    gap: 0.5rem;
  }

  .route-desk-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .tracking-timeline {
    padding: 0.76rem 0.8rem;
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.07);
    background: rgba(255, 255, 255, 0.03);
  }

  .workflow-slider {
    display: grid;
    gap: 0.45rem;
  }

  .workflow-slider span {
    font-size: 0.76rem;
    color: rgba(190, 203, 217, 0.74);
  }

  .workflow-slider input {
    width: 100%;
    accent-color: #f5b908;
  }

  .timeline-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.55rem;
    align-items: center;
    padding: 0.62rem 0.66rem;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(0, 0, 0, 0.18);
  }

  .timeline-row span,
  .timeline-row small {
    font-size: 0.72rem;
    color: rgba(190, 203, 217, 0.72);
  }

  .timeline-row strong {
    color: #eef3f8;
    font-size: 0.82rem;
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
    right: 0.95rem;
    bottom: 0.95rem;
    left: auto;
    transform: none;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, auto));
    gap: 0.32rem;
    padding: 0.28rem;
    border-radius: 18px;
    background: rgba(12, 14, 18, 0.94);
  }

  .dock-button {
    display: grid;
    justify-items: center;
    gap: 0.3rem;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 13px;
    min-width: 4.3rem;
    padding: 0.52rem 0.6rem 0.48rem;
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
    font-size: 0.66rem;
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
  }

  @media (max-width: 960px) {
    .mobile-start-hint {
      display: grid;
    }

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

    .bottom-dock {
      bottom: 0.75rem;
      width: calc(100vw - 1.5rem);
      left: 50%;
      right: auto;
      transform: translateX(-50%);
      grid-template-columns: repeat(4, minmax(0, 1fr));
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
      width: auto;
      min-width: 0;
      padding: 0.62rem 0.68rem;
    }

    .center-bar-main {
      grid-template-columns: 1fr;
    }

    .center-actions {
      justify-content: flex-start;
      flex-wrap: wrap;
    }

    .topbar-status-strip {
      padding-left: 0;
    }

    .filter-form-grid,
    .preset-save-row,
    .preset-card,
    .tag-input-row,
    .utility-fact-grid,
    .workflow-metrics,
    .inspector-tab-row,
    .workflow-header,
    .route-desk-row {
      grid-template-columns: 1fr;
      display: grid;
    }

    .bottom-dock {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
