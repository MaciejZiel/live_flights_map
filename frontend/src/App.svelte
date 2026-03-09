<script>
  import { onMount } from "svelte";

  import FlightDetailsPanel from "./lib/components/FlightDetailsPanel.svelte";
  import LegendPanel from "./lib/components/LegendPanel.svelte";
  import OnboardingPanel from "./lib/components/OnboardingPanel.svelte";
  import ShortcutsPanel from "./lib/components/ShortcutsPanel.svelte";
  import FlightMap from "./lib/components/FlightMap.svelte";
  import { flightsStore } from "./lib/stores/flights.js";
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
  });

  let filters = {
    query: "",
    minAltitude: "",
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
  let theme = "light";
  let onboardingDismissed = false;

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
    }

    syncThemeClass(theme);
    preferencesReady = true;
    flightsStore.start();
    window.addEventListener("keydown", handleKeyboardShortcut);
    const freshnessTimer = window.setInterval(() => {
      now = Date.now();
    }, 1000);

    return () => {
      window.removeEventListener("keydown", handleKeyboardShortcut);
      window.clearInterval(freshnessTimer);
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

  function handleBoundsChange(event) {
    flightsStore.setBbox(event.detail.bbox);
  }

  function handleFlightSelect(event) {
    selectedIcao24 = event.detail.flight.icao24;
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

  function toggleFollowAircraft() {
    if (!selectedFlight) {
      followAircraft = false;
      return;
    }

    followAircraft = !followAircraft;
  }

  function resetFilters() {
    filters = {
      query: "",
      minAltitude: "",
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

  $: normalizedQuery = filters.query.trim().toLowerCase();
  $: minimumAltitude = Number(filters.minAltitude);
  $: hasMinimumAltitude = Number.isFinite(minimumAltitude) && filters.minAltitude !== "";
  $: filteredFlights = state.flights.filter((flight) => {
    const matchesQuery =
      !normalizedQuery ||
      flight.icao24.includes(normalizedQuery) ||
      (flight.callsign ?? "").toLowerCase().includes(normalizedQuery) ||
      (flight.origin_country ?? "").toLowerCase().includes(normalizedQuery);

    const matchesAltitude =
      !hasMinimumAltitude ||
      (flight.altitude !== null && flight.altitude !== undefined && flight.altitude >= minimumAltitude);

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

    return matchesQuery && matchesAltitude && matchesGroundFilter && matchesRecentActivity;
  });
  $: sortedFlights = sortFlights(filteredFlights, sortBy, mapViewport);
  $: if (selectedIcao24 && !filteredFlights.some((flight) => flight.icao24 === selectedIcao24)) {
    selectedIcao24 = null;
  }
  $: selectedFlight = selectedIcao24
    ? sortedFlights.find((flight) => flight.icao24 === selectedIcao24) ?? null
    : null;
  $: selectedFlightTrail = getTrailPoints(flightHistory, selectedIcao24);
  $: if (!selectedFlight) {
    followAircraft = false;
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
  <header class="topbar">
    <div>
      <p class="eyebrow">Radar Console</p>
      <h1>Live Flights Map</h1>
    </div>

    <div class="status-panel">
      <div class="theme-switcher" role="group" aria-label="Theme switcher">
        <button
          class:active={theme === "light"}
          type="button"
          title="Use the brighter cockpit-style palette"
          on:click={() => setTheme("light")}
        >
          Light
        </button>
        <button
          class:active={theme === "dark"}
          type="button"
          title="Use the darker low-glare palette"
          on:click={() => setTheme("dark")}
        >
          Dark
        </button>
      </div>
      <div class:online={["success", "refreshing"].includes(state.status)} class="status-pill">
        {#if state.status === "loading"}
          Syncing...
        {:else if state.status === "refreshing"}
          Live sync...
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
      <p>{filteredFlights.length} shown / {state.count} tracked</p>
      <p>Last update: {formatTimestamp(state.fetchedAt)}</p>
      <p>Freshness: {getFreshnessLabel(state.fetchedAt)}</p>
      <p>Confidence: {getConfidenceLabel(state)}</p>
    </div>
  </header>

  {#if state.error}
    <div class="error-banner">{state.error}</div>
  {/if}

  {#if state.warning}
    <div class="warning-banner">{state.warning}</div>
  {/if}

  <main class="layout">
    <aside class="sidebar">
      {#if !onboardingDismissed}
        <OnboardingPanel onDismiss={dismissOnboarding} />
      {/if}

      <section class="panel">
        <h2>Map style</h2>
        <div class="segmented-control">
          <button
            class:active={mapStyle === "standard"}
            type="button"
            title="Standard street and terrain context"
            on:click={() => (mapStyle = "standard")}
          >
            Standard
          </button>
          <button
            class:active={mapStyle === "satellite"}
            type="button"
            title="Satellite imagery for ground context"
            on:click={() => (mapStyle = "satellite")}
          >
            Satellite
          </button>
          <button
            class:active={mapStyle === "dark"}
            type="button"
            title="Dark basemap for low-light tracking"
            on:click={() => (mapStyle = "dark")}
          >
            Dark
          </button>
          <button
            class:active={mapStyle === "aviation"}
            type="button"
            title="Aviation chart overlays for airspace context"
            on:click={() => (mapStyle = "aviation")}
          >
            Aviation
          </button>
        </div>
      </section>

      <section class="panel">
        <h2>Tracking area</h2>
        {#if state.bbox}
          <p>
            lat {state.bbox.lamin.toFixed(2)} to {state.bbox.lamax.toFixed(2)}<br />
            lon {state.bbox.lomin.toFixed(2)} to {state.bbox.lomax.toFixed(2)}
          </p>
        {:else}
          <p>Using backend defaults until the first response arrives.</p>
        {/if}
      </section>

      <section class="panel">
        <h2>Filters</h2>
        <label class="field">
          <span>Sort by</span>
          <select bind:value={sortBy} title="Choose how aircraft are ordered in the current result set">
            <option value="altitude_desc">Altitude</option>
            <option value="speed_desc">Speed</option>
            <option value="distance_asc">Distance from map center</option>
            <option value="last_contact_desc">Last update</option>
          </select>
        </label>
        <label class="field">
          <span>Search</span>
          <input
            bind:this={searchInput}
            bind:value={filters.query}
            type="text"
            placeholder="callsign, ICAO24, country"
            title="Search by callsign, ICAO24, or origin country"
          />
        </label>
        <label class="field">
          <span>Min altitude (m)</span>
          <input
            bind:value={filters.minAltitude}
            type="number"
            min="0"
            step="100"
            title="Show only aircraft above this altitude"
          />
        </label>
        <label class="checkbox-field">
          <input
            bind:checked={filters.hideGroundTraffic}
            type="checkbox"
            title="Hide aircraft currently reported on the ground"
          />
          <span>Hide ground traffic</span>
        </label>
        <label class="field">
          <span>Recent activity</span>
          <select bind:value={filters.recentActivity} title="Limit results to recently updated aircraft">
            <option value="any">Any time</option>
            <option value="30s">Last 30 seconds</option>
            <option value="2m">Last 2 minutes</option>
            <option value="5m">Last 5 minutes</option>
            <option value="15m">Last 15 minutes</option>
          </select>
        </label>
        <div class="filter-actions">
          <button
            class="reset-button"
            type="button"
            title="Clear all active filters and return to defaults"
            on:click={resetFilters}
          >
            Reset filters
          </button>
          <div class="preset-save-row">
            <input
              bind:value={presetName}
              type="text"
              placeholder="preset name"
              title="Name the current filter combination before saving it"
              on:keydown={(event) => event.key === "Enter" && saveCurrentPreset()}
            />
            <button
              class="secondary-button"
              type="button"
              title="Save the current filters as a reusable preset"
              on:click={saveCurrentPreset}
            >
              Save preset
            </button>
          </div>
          {#if filterPresets.length}
            <div class="preset-list">
              {#each filterPresets as preset}
                <div class="preset-item">
                  <button
                    class="secondary-button preset-load"
                    type="button"
                    title={`Apply preset ${preset.name}`}
                    on:click={() => applyFilterPreset(preset)}
                  >
                    {preset.name}
                  </button>
                  <button
                    class="preset-delete"
                    type="button"
                    title={`Remove preset ${preset.name}`}
                    on:click={() => deleteFilterPreset(preset.name)}
                  >
                    Remove
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </section>

      <FlightDetailsPanel
        flight={selectedFlight}
        followAircraft={followAircraft}
        onToggleFollow={toggleFollowAircraft}
      />

      <LegendPanel />
      <ShortcutsPanel />
    </aside>

    <section class="map-card">
      <FlightMap
        flights={sortedFlights}
        selectedIcao24={selectedIcao24}
        followAircraft={followAircraft}
        mapStyle={mapStyle}
        trailPoints={selectedFlightTrail}
        initialViewport={mapViewport}
        fullscreenRequestId={fullscreenRequestId}
        viewPresetRequest={viewPresetRequest}
        on:boundschange={handleBoundsChange}
        on:viewportchange={handleViewportChange}
        on:select={handleFlightSelect}
      />
    </section>
  </main>
</div>

<style>
  .app-shell {
    display: grid;
    gap: 1rem;
    min-height: 100vh;
    padding: 1rem;
    box-sizing: border-box;
  }

  .topbar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }

  .eyebrow {
    margin: 0 0 0.3rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    font-size: 0.72rem;
    color: var(--color-muted);
  }

  h1 {
    margin: 0;
    font-size: clamp(1.8rem, 3vw, 3rem);
  }

  .status-panel {
    display: grid;
    justify-items: end;
    gap: 0.25rem;
    min-width: 220px;
    padding: 1rem 1.1rem;
    border-radius: 18px;
    background: var(--surface-strong-bg);
    backdrop-filter: blur(10px);
    box-shadow: var(--shadow-soft);
  }

  .status-panel p {
    margin: 0;
    font-size: 0.92rem;
  }

  .status-pill {
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    background: var(--status-neutral-bg);
    color: var(--status-neutral-text);
    font-size: 0.84rem;
    font-weight: 700;
  }

  .status-pill.online {
    background: var(--status-online-bg);
    color: var(--status-online-text);
  }

  .error-banner {
    padding: 0.9rem 1rem;
    border-radius: 14px;
    background: var(--banner-error-bg);
    color: var(--banner-error-text);
  }

  .warning-banner {
    padding: 0.9rem 1rem;
    border-radius: 14px;
    background: var(--banner-warning-bg);
    color: var(--banner-warning-text);
  }

  .layout {
    display: grid;
    grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
    gap: 1rem;
    min-height: 0;
    flex: 1;
  }

  .sidebar {
    display: grid;
    gap: 1rem;
  }

  .panel,
  .map-card {
    border-radius: 24px;
    background: var(--surface-bg);
    backdrop-filter: blur(8px);
    box-shadow: var(--shadow-strong);
  }

  .panel {
    padding: 1.1rem;
  }

  .panel h2 {
    margin: 0 0 0.8rem;
    font-size: 1rem;
  }

  .field,
  .checkbox-field {
    display: grid;
    gap: 0.45rem;
  }

  .segmented-control {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .segmented-control button {
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  .segmented-control button.active {
    color: var(--button-primary-text);
    background: var(--button-primary-bg);
  }

  .field span,
  .checkbox-field span {
    font-size: 0.83rem;
    font-weight: 600;
    color: var(--color-muted);
  }

  .field input {
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
    color: var(--color-text);
    background: var(--surface-input-bg);
  }

  .field select {
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
    color: var(--color-text);
    background: var(--surface-input-bg);
  }

  .filter-actions {
    display: grid;
    gap: 0.8rem;
  }

  .preset-save-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.55rem;
  }

  .preset-save-row input {
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
    color: var(--color-text);
    background: var(--surface-input-bg);
  }

  .checkbox-field {
    grid-template-columns: auto 1fr;
    align-items: center;
  }

  .reset-button {
    border: 0;
    border-radius: 12px;
    padding: 0.8rem 0.95rem;
    font: inherit;
    font-weight: 700;
    color: var(--button-primary-text);
    background: var(--button-primary-bg);
    cursor: pointer;
  }

  .reset-button:hover {
    filter: brightness(1.04);
  }

  .secondary-button,
  .preset-delete {
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }

  .secondary-button {
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
  }

  .preset-delete {
    color: var(--button-danger-text);
    background: var(--button-danger-bg);
  }

  .theme-switcher {
    display: inline-grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.4rem;
    margin-bottom: 0.35rem;
  }

  .theme-switcher button {
    border: 1px solid var(--surface-border);
    border-radius: 999px;
    padding: 0.45rem 0.7rem;
    font: inherit;
    font-size: 0.8rem;
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  .theme-switcher button.active {
    color: var(--button-primary-text);
    background: var(--button-primary-bg);
  }

  .preset-list {
    display: grid;
    gap: 0.55rem;
  }

  .preset-item {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.55rem;
  }

  .preset-load {
    text-align: left;
  }

  .panel p {
    margin: 0;
    line-height: 1.5;
  }

  .map-card {
    min-height: 72vh;
    overflow: hidden;
  }

  @media (max-width: 960px) {
    .topbar,
    .layout {
      grid-template-columns: 1fr;
      display: grid;
    }

    .status-panel {
      justify-items: start;
    }

    .map-card {
      min-height: 60vh;
    }
  }
</style>
