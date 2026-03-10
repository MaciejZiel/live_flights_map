<script>
  import { formatAltitude, formatSpeed } from "../utils/flightFormatters.js";

  export let airport = null;
  export let dashboard = null;
  export let status = "idle";
  export let error = null;
  export let weather = null;
  export let weatherStatus = "idle";
  export let weatherError = null;
  export let weatherLayerEnabled = false;
  export let bookmarked = false;
  export let onSelectFlight = () => {};
  export let onRetry = () => {};
  export let onToggleWeather = () => {};
  export let onToggleBookmark = () => {};
  export let onAddAlert = () => {};
  export let onFilterAllTraffic = () => {};
  export let onFilterArrivals = () => {};
  export let onFilterDepartures = () => {};

  let activeTab = "overview";
  let lastAirportKey = null;

  function formatAirportCode(value) {
    return value?.iata ?? value?.icao ?? value?.entity_key ?? "?";
  }

  function formatFlightTitle(flight) {
    return flight?.callsign ?? flight?.registration ?? flight?.icao24?.toUpperCase() ?? "Unknown flight";
  }

  function formatMovementCopy(flight, mode) {
    if (mode === "arrival") {
      return `${flight?.origin ?? "Unknown"} -> ${flight?.destination ?? formatAirportCode(airport)}`;
    }

    if (mode === "departure") {
      return `${flight?.origin ?? formatAirportCode(airport)} -> ${flight?.destination ?? "Unknown"}`;
    }

    return [flight?.origin_country ?? "Unknown", flight?.type_code ?? "Type n/a"].join(" · ");
  }

  function formatRelativeTime(value) {
    if (!value) {
      return "Unknown";
    }

    const deltaMinutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60000));
    if (deltaMinutes < 1) {
      return "Now";
    }
    if (deltaMinutes < 60) {
      return `${deltaMinutes} min ago`;
    }
    return `${Math.floor(deltaMinutes / 60)} h ago`;
  }

  function getHistoryScale(entries) {
    return Math.max(
      1,
      ...entries.map((entry) => Math.max(entry.arrivals ?? 0, entry.departures ?? 0))
    );
  }

  function getWeatherValue(...values) {
    for (const value of values) {
      if (value !== null && value !== undefined && value !== "") {
        return value;
      }
    }
    return null;
  }

  $: if (airport?.entity_key !== lastAirportKey) {
    lastAirportKey = airport?.entity_key ?? null;
    activeTab = "overview";
  }
  $: stats = dashboard?.stats ?? { arrivals: 0, departures: 0, ground: 0, nearby: 0 };
  $: arrivals = dashboard?.recent?.arrivals ?? [];
  $: departures = dashboard?.recent?.departures ?? [];
  $: nearby = dashboard?.live?.nearby ?? [];
  $: onGround = dashboard?.live?.on_ground ?? [];
  $: history = dashboard?.history ?? [];
  $: historyScale = getHistoryScale(history);
</script>

<section class="panel airport-panel">
  <div class="airport-header">
    <div>
      <p class="airport-eyebrow">Airport desk</p>
      <h2>{airport ? formatAirportCode(airport) : "Airport"}</h2>
      <p class="airport-subtitle">
        {#if airport}
          {airport.name ?? airport.label}
          {#if airport.city || airport.country}
            · {[airport.city, airport.country].filter(Boolean).join(", ")}
          {/if}
        {:else}
          Select an airport from search or the map
        {/if}
      </p>
    </div>

    {#if airport}
      <div class="airport-actions">
        <button class:active={weatherLayerEnabled} class="airport-action" type="button" on:click={onToggleWeather}>
          {weatherLayerEnabled ? "Weather on" : "Weather off"}
        </button>
        <button class="airport-action" type="button" on:click={onAddAlert}>
          Alert
        </button>
        <button class:active={bookmarked} class="airport-action" type="button" on:click={onToggleBookmark}>
          {bookmarked ? "Bookmarked" : "Bookmark"}
        </button>
      </div>
    {/if}
  </div>

  {#if error}
    <div class="airport-banner airport-banner-error">
      <span>{error}</span>
      <button type="button" on:click={onRetry}>Retry</button>
    </div>
  {:else if dashboard?.meta?.warning}
    <div class="airport-banner airport-banner-warning">{dashboard.meta.warning}</div>
  {/if}

  {#if airport}
    <div class="airport-stat-grid">
      <article>
        <span>Nearby</span>
        <strong>{stats.nearby}</strong>
        <small>Live aircraft in local airspace</small>
      </article>
      <article>
        <span>On ground</span>
        <strong>{stats.ground}</strong>
        <small>Stands and field movements</small>
      </article>
      <article>
        <span>Arrivals</span>
        <strong>{stats.arrivals}</strong>
        <small>Recent tracked arrivals</small>
      </article>
      <article>
        <span>Departures</span>
        <strong>{stats.departures}</strong>
        <small>Recent tracked departures</small>
      </article>
    </div>

    <div class="airport-flow-actions">
      <button class="airport-flow-button" type="button" on:click={onFilterAllTraffic}>
        Filter airport traffic
      </button>
      <button class="airport-flow-button" type="button" on:click={onFilterArrivals}>
        Arrivals
      </button>
      <button class="airport-flow-button" type="button" on:click={onFilterDepartures}>
        Departures
      </button>
    </div>

    <div class="airport-tab-row" role="tablist" aria-label="Airport sections">
      <button class:active={activeTab === "overview"} type="button" on:click={() => (activeTab = "overview")}>Overview</button>
      <button class:active={activeTab === "arrivals"} type="button" on:click={() => (activeTab = "arrivals")}>Arrivals</button>
      <button class:active={activeTab === "departures"} type="button" on:click={() => (activeTab = "departures")}>Departures</button>
      <button class:active={activeTab === "ground"} type="button" on:click={() => (activeTab = "ground")}>Ground</button>
      <button class:active={activeTab === "weather"} type="button" on:click={() => (activeTab = "weather")}>Weather</button>
    </div>

    {#if activeTab === "overview"}
      <section class="airport-section">
        <div class="section-header">
          <strong>Ramp and final traffic</strong>
          <span>{nearby.length} live</span>
        </div>

        {#if nearby.length}
          <div class="movement-list">
            {#each nearby.slice(0, 6) as flight}
              <button class="movement-row" type="button" on:click={() => onSelectFlight(flight)}>
                <span class="movement-main">
                  <strong>{formatFlightTitle(flight)}</strong>
                  <small>{formatMovementCopy(flight, "overview")}</small>
                </span>
                <span class="movement-meta">
                  <strong>{formatAltitude(flight.altitude)}</strong>
                  <small>{formatSpeed(flight.velocity)}</small>
                </span>
              </button>
            {/each}
          </div>
        {:else if status === "loading" || status === "refreshing"}
          <p class="airport-copy">Loading live airport area traffic…</p>
        {:else}
          <p class="airport-copy">No live traffic matched this airport area yet.</p>
        {/if}
      </section>

      <section class="airport-section">
        <div class="section-header">
          <strong>Traffic history</strong>
          <span>{history.length} hours</span>
        </div>

        {#if history.length}
          <div class="history-chart">
            {#each history as entry}
              <div class="history-column">
                <div class="history-bars">
                  <span class="history-bar arrivals" style={`height: ${Math.max(10, (entry.arrivals / historyScale) * 100)}%`}></span>
                  <span class="history-bar departures" style={`height: ${Math.max(10, (entry.departures / historyScale) * 100)}%`}></span>
                </div>
                <small>{String(entry.hour ?? "").slice(11, 13) || "--"}</small>
              </div>
            {/each}
          </div>
        {:else}
          <p class="airport-copy">No recent airport history has been archived yet.</p>
        {/if}
      </section>

    {:else if activeTab === "ground"}
      <section class="airport-section">
        <div class="section-header">
          <strong>Ground traffic</strong>
          <span>{onGround.length} on field</span>
        </div>

        {#if onGround.length}
          <div class="pill-grid">
            {#each onGround as flight}
              <button class="movement-pill" type="button" on:click={() => onSelectFlight(flight)}>
                <strong>{formatFlightTitle(flight)}</strong>
                <span>{flight.type_code ?? "Type n/a"}</span>
              </button>
            {/each}
          </div>
        {:else}
          <p class="airport-copy">No on-ground aircraft were archived around this airport.</p>
        {/if}
      </section>

      <section class="airport-section">
        <div class="section-header">
          <strong>Local airspace</strong>
          <span>{nearby.length} live</span>
        </div>

        {#if nearby.length}
          <div class="movement-list">
            {#each nearby as flight}
              <button class="movement-row" type="button" on:click={() => onSelectFlight(flight)}>
                <span class="movement-main">
                  <strong>{formatFlightTitle(flight)}</strong>
                  <small>{formatMovementCopy(flight, "overview")}</small>
                </span>
                <span class="movement-meta">
                  <strong>{formatAltitude(flight.altitude)}</strong>
                  <small>{formatSpeed(flight.velocity)}</small>
                </span>
              </button>
            {/each}
          </div>
        {:else}
          <p class="airport-copy">No local live traffic is visible for this airport area right now.</p>
        {/if}
      </section>
    {:else if activeTab === "weather"}
      <section class="airport-section">
        <div class="section-header">
          <strong>Airport weather</strong>
          <span>{weatherStatus === "success" ? "METAR" : weatherStatus === "loading" || weatherStatus === "refreshing" ? "Loading" : "Pending"}</span>
        </div>

        {#if weather}
          <div class="weather-grid">
            <article>
              <span>Raw METAR</span>
              <strong>{getWeatherValue(weather.rawOb, weather.raw_text, "Unavailable")}</strong>
            </article>
            <article>
              <span>Temperature</span>
              <strong>{getWeatherValue(weather.temp, weather.tempC, weather.temperature) ?? "n/a"}{#if getWeatherValue(weather.temp, weather.tempC, weather.temperature) !== null}°C{/if}</strong>
            </article>
            <article>
              <span>Wind</span>
              <strong>
                {#if getWeatherValue(weather.wdir, weather.windDir, weather.wind_direction) !== null}
                  {getWeatherValue(weather.wdir, weather.windDir, weather.wind_direction)}°
                {:else}
                  Variable
                {/if}
                {" "}
                {getWeatherValue(weather.wspd, weather.windSpeed, weather.wind_speed) ?? "n/a"} kt
              </strong>
            </article>
            <article>
              <span>Visibility</span>
              <strong>{getWeatherValue(weather.visib, weather.visibility) ?? "n/a"} sm</strong>
            </article>
          </div>
          <p class="airport-copy">
            {weatherLayerEnabled ? "Weather radar overlay is active on the main map." : "Enable Weather radar to compare the METAR with the live precipitation layer on the map."}
          </p>
        {:else if weatherError}
          <p class="airport-copy">{weatherError}</p>
        {:else}
          <p class="airport-copy">Waiting for the latest METAR for this airport.</p>
        {/if}
      </section>
    {:else if activeTab === "arrivals"}
      <section class="airport-section">
        <div class="section-header">
          <strong>Recent arrivals</strong>
          <span>{arrivals.length}</span>
        </div>

        {#if arrivals.length}
          <div class="movement-list">
            {#each arrivals as flight}
              <button class="movement-row" type="button" on:click={() => onSelectFlight(flight)}>
                <span class="movement-main">
                  <strong>{formatFlightTitle(flight)}</strong>
                  <small>{formatMovementCopy(flight, "arrival")}</small>
                </span>
                <span class="movement-meta">
                  <strong>{flight.type_code ?? "Type n/a"}</strong>
                  <small>{formatRelativeTime(flight.fetched_at)}</small>
                </span>
              </button>
            {/each}
          </div>
        {:else}
          <p class="airport-copy">No arrivals were found in the current history window.</p>
        {/if}
      </section>
    {:else}
      <section class="airport-section">
        <div class="section-header">
          <strong>Recent departures</strong>
          <span>{departures.length}</span>
        </div>

        {#if departures.length}
          <div class="movement-list">
            {#each departures as flight}
              <button class="movement-row" type="button" on:click={() => onSelectFlight(flight)}>
                <span class="movement-main">
                  <strong>{formatFlightTitle(flight)}</strong>
                  <small>{formatMovementCopy(flight, "departure")}</small>
                </span>
                <span class="movement-meta">
                  <strong>{flight.type_code ?? "Type n/a"}</strong>
                  <small>{formatRelativeTime(flight.fetched_at)}</small>
                </span>
              </button>
            {/each}
          </div>
        {:else}
          <p class="airport-copy">No departures were found in the current history window.</p>
        {/if}
      </section>
    {/if}
  {:else}
    <p class="airport-copy">Use the search bar or click an airport marker to open its arrivals, departures and ground board.</p>
  {/if}
</section>

<style>
  .airport-panel {
    display: grid;
    gap: 0.8rem;
  }

  .airport-header,
  .airport-actions,
  .section-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: start;
  }

  .airport-eyebrow,
  .airport-subtitle,
  .airport-copy {
    margin: 0;
  }

  .airport-eyebrow {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: rgba(188, 199, 211, 0.64);
  }

  .airport-header h2 {
    margin: 0.2rem 0 0;
    color: #f5f7fb;
    font-size: 1.2rem;
  }

  .airport-subtitle,
  .airport-copy {
    color: rgba(194, 204, 216, 0.78);
    font-size: 0.78rem;
    line-height: 1.5;
  }

  .airport-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .airport-flow-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.42rem;
  }

  .airport-action,
  .airport-flow-button,
  .airport-tab-row button,
  .movement-row,
  .movement-pill,
  .airport-banner button {
    font: inherit;
    cursor: pointer;
  }

  .airport-action,
  .airport-flow-button,
  .airport-tab-row button,
  .airport-banner button {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.44rem 0.72rem;
    font-size: 0.72rem;
    font-weight: 800;
    color: #d7e0ea;
    background: rgba(255, 255, 255, 0.05);
  }

  .airport-action.active,
  .airport-tab-row button.active {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .airport-banner {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
    padding: 0.72rem 0.82rem;
    border-radius: 14px;
    font-size: 0.76rem;
  }

  .airport-banner-warning {
    color: #ffe6b0;
    background: rgba(127, 82, 20, 0.28);
    border: 1px solid rgba(245, 185, 8, 0.18);
  }

  .airport-banner-error {
    color: #ffd6d6;
    background: rgba(122, 35, 35, 0.3);
    border: 1px solid rgba(194, 66, 66, 0.22);
  }

  .airport-stat-grid,
  .pill-grid,
  .weather-grid {
    display: grid;
    gap: 0.5rem;
  }

  .airport-stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .weather-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .airport-stat-grid article,
  .weather-grid article,
  .airport-section {
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(31, 34, 39, 0.98) 0%, rgba(19, 22, 26, 0.98) 100%);
    box-shadow: 0 14px 24px rgba(0, 0, 0, 0.18);
  }

  .airport-stat-grid article {
    display: grid;
    gap: 0.16rem;
    padding: 0.76rem 0.82rem;
  }

  .weather-grid article {
    display: grid;
    gap: 0.16rem;
    padding: 0.72rem 0.76rem;
    border-radius: 13px;
    background: rgba(255, 255, 255, 0.03);
  }

  .airport-stat-grid span,
  .weather-grid span,
  .section-header span {
    font-size: 0.67rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: rgba(180, 191, 203, 0.66);
  }

  .airport-stat-grid strong,
  .weather-grid strong,
  .section-header strong {
    color: #f5f7fb;
  }

  .airport-stat-grid small {
    color: rgba(192, 203, 216, 0.76);
    font-size: 0.73rem;
  }

  .airport-tab-row {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.38rem;
  }

  .airport-section {
    display: grid;
    gap: 0.55rem;
    padding: 0.82rem 0.86rem;
  }

  .movement-list {
    display: grid;
    gap: 0.42rem;
  }

  .movement-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.6rem;
    width: 100%;
    padding: 0.72rem 0.76rem;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 13px;
    color: inherit;
    background: rgba(255, 255, 255, 0.03);
    text-align: left;
    transition:
      transform 160ms ease,
      border-color 160ms ease;
  }

  .movement-row:hover,
  .movement-pill:hover {
    transform: translateY(-1px);
    border-color: rgba(255, 211, 79, 0.24);
  }

  .movement-main,
  .movement-meta,
  .history-column {
    display: grid;
    gap: 0.15rem;
  }

  .movement-main strong,
  .movement-meta strong {
    color: #eef3f8;
    font-size: 0.82rem;
  }

  .movement-main small,
  .movement-meta small {
    color: rgba(193, 203, 216, 0.72);
    font-size: 0.72rem;
  }

  .movement-meta {
    justify-items: end;
    white-space: nowrap;
  }

  .pill-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .movement-pill {
    display: grid;
    gap: 0.16rem;
    padding: 0.68rem 0.72rem;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 13px;
    color: inherit;
    background: rgba(255, 255, 255, 0.03);
    text-align: left;
  }

  .movement-pill strong {
    color: #eef3f8;
    font-size: 0.78rem;
  }

  .movement-pill span {
    color: rgba(193, 203, 216, 0.72);
    font-size: 0.7rem;
  }

  .history-chart {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(1.8rem, 1fr));
    gap: 0.45rem;
    align-items: end;
    min-height: 8.5rem;
  }

  .history-column {
    justify-items: center;
    min-height: 8rem;
  }

  .history-bars {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 0.52rem));
    gap: 0.18rem;
    align-items: end;
    height: 6.9rem;
  }

  .history-bar {
    border-radius: 999px 999px 0 0;
  }

  .history-bar.arrivals {
    background: linear-gradient(180deg, #7dd3fc 0%, #2589d0 100%);
  }

  .history-bar.departures {
    background: linear-gradient(180deg, #ffd34f 0%, #f58d08 100%);
  }

  .history-column small {
    color: rgba(188, 199, 211, 0.7);
    font-size: 0.67rem;
  }

  @media (max-width: 720px) {
    .airport-stat-grid,
    .pill-grid,
    .weather-grid,
    .airport-tab-row {
      grid-template-columns: 1fr;
    }
  }
</style>
