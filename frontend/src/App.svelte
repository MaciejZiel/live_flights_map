<script>
  import { onMount } from "svelte";

  import FlightDetailsPanel from "./lib/components/FlightDetailsPanel.svelte";
  import FlightMap from "./lib/components/FlightMap.svelte";
  import { flightsStore } from "./lib/stores/flights.js";

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
  });

  let filters = {
    query: "",
    minAltitude: "",
    hideGroundTraffic: true,
  };
  let selectedIcao24 = null;

  onMount(() => {
    flightsStore.start();

    return () => {
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

  function resetFilters() {
    filters = {
      query: "",
      minAltitude: "",
      hideGroundTraffic: true,
    };
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
  $: if (selectedIcao24 && !filteredFlights.some((flight) => flight.icao24 === selectedIcao24)) {
    selectedIcao24 = null;
  }
  $: selectedFlight = selectedIcao24
    ? filteredFlights.find((flight) => flight.icao24 === selectedIcao24) ?? null
    : null;
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
        {:else if state.status === "success"}
          Live
        {:else}
          Idle
        {/if}
      </div>
      <p>{filteredFlights.length} shown / {state.count} tracked</p>
      <p>Last update: {formatTimestamp(state.fetchedAt)}</p>
    </div>
  </header>

  {#if state.error}
    <div class="error-banner">{state.error}</div>
  {/if}

  <main class="layout">
    <aside class="sidebar">
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
          <span>Search</span>
          <input
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
        <button class="reset-button" type="button" on:click={resetFilters}>Reset filters</button>
      </section>

      <FlightDetailsPanel flight={selectedFlight} />
    </aside>

    <section class="map-card">
      <FlightMap
        flights={filteredFlights}
        selectedIcao24={selectedIcao24}
        on:boundschange={handleBoundsChange}
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
