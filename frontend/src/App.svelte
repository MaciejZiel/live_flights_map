<script>
  import { onMount } from "svelte";

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
      <p>{state.count} aircraft</p>
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
        <h2>Refresh cycle</h2>
        <p>Frontend polls backend every 12 seconds.</p>
        <p>Backend fetches a fresh OpenSky snapshot for each request.</p>
      </section>

      <section class="panel">
        <h2>Legend</h2>
        <p>Aircraft icons rotate using `true_track` from OpenSky.</p>
        <p>Click any aircraft to inspect callsign, ICAO24 and altitude.</p>
      </section>
    </aside>

    <section class="map-card">
      <FlightMap flights={state.flights} on:boundschange={handleBoundsChange} />
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
