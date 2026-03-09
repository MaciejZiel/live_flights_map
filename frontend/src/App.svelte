<script>
  import { onMount } from "svelte";

  import FlightDetailsPanel from "./lib/components/FlightDetailsPanel.svelte";
  import LegendPanel from "./lib/components/LegendPanel.svelte";
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
    }

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

    return matchesQuery && matchesAltitude && matchesGroundFilter;
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
    saveUserPreferences({
      filters,
      mapStyle,
      mapViewport,
      filterPresets,
      sortBy,
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
      <section class="panel">
        <h2>Map style</h2>
        <div class="segmented-control">
          <button class:active={mapStyle === "standard"} type="button" on:click={() => (mapStyle = "standard")}>
            Standard
          </button>
          <button class:active={mapStyle === "satellite"} type="button" on:click={() => (mapStyle = "satellite")}>
            Satellite
          </button>
          <button class:active={mapStyle === "dark"} type="button" on:click={() => (mapStyle = "dark")}>
            Dark
          </button>
          <button class:active={mapStyle === "aviation"} type="button" on:click={() => (mapStyle = "aviation")}>
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
          <select bind:value={sortBy}>
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
          />
        </label>
        <label class="field">
          <span>Min altitude (m)</span>
          <input bind:value={filters.minAltitude} type="number" min="0" step="100" />
        </label>
        <label class="checkbox-field">
          <input bind:checked={filters.hideGroundTraffic} type="checkbox" />
          <span>Hide ground traffic</span>
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
            <button class="secondary-button" type="button" on:click={saveCurrentPreset}>
              Save preset
            </button>
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
    color: #4a6987;
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
    background: rgba(255, 255, 255, 0.72);
    backdrop-filter: blur(10px);
    box-shadow: 0 16px 40px rgba(28, 66, 106, 0.12);
  }

  .status-panel p {
    margin: 0;
    font-size: 0.92rem;
  }

  .status-pill {
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    background: rgba(180, 80, 72, 0.12);
    color: #973a32;
    font-size: 0.84rem;
    font-weight: 700;
  }

  .status-pill.online {
    background: rgba(35, 125, 84, 0.14);
    color: #1b6d46;
  }

  .error-banner {
    padding: 0.9rem 1rem;
    border-radius: 14px;
    background: rgba(183, 57, 57, 0.12);
    color: #852020;
  }

  .warning-banner {
    padding: 0.9rem 1rem;
    border-radius: 14px;
    background: rgba(196, 106, 23, 0.14);
    color: #91510e;
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
    background: rgba(255, 255, 255, 0.78);
    backdrop-filter: blur(8px);
    box-shadow: 0 18px 44px rgba(26, 57, 92, 0.14);
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
    border: 1px solid rgba(73, 105, 135, 0.18);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
    font-weight: 700;
    color: #244566;
    background: rgba(255, 255, 255, 0.9);
    cursor: pointer;
  }

  .segmented-control button.active {
    color: #f4f9ff;
    background: linear-gradient(135deg, #12395d 0%, #375f86 100%);
  }

  .field span,
  .checkbox-field span {
    font-size: 0.83rem;
    font-weight: 600;
    color: #49657f;
  }

  .field input {
    border: 1px solid rgba(73, 105, 135, 0.2);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
    background: rgba(255, 255, 255, 0.9);
  }

  .field select {
    border: 1px solid rgba(73, 105, 135, 0.2);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
    background: rgba(255, 255, 255, 0.9);
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
    border: 1px solid rgba(73, 105, 135, 0.2);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
    background: rgba(255, 255, 255, 0.9);
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
    color: #f4f9ff;
    background: linear-gradient(135deg, #12395d 0%, #375f86 100%);
    cursor: pointer;
  }

  .reset-button:hover {
    filter: brightness(1.04);
  }

  .secondary-button,
  .preset-delete {
    border: 1px solid rgba(73, 105, 135, 0.18);
    border-radius: 12px;
    padding: 0.75rem 0.85rem;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }

  .secondary-button {
    color: #1f4466;
    background: rgba(255, 255, 255, 0.92);
  }

  .preset-delete {
    color: #8f3c2a;
    background: rgba(255, 244, 241, 0.94);
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
