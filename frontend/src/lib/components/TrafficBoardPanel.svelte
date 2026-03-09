<script>
  import { formatAltitude, formatSpeed } from "../utils/flightFormatters.js";

  export let flights = [];
  export let selectedIcao24 = null;
  export let viewport = null;
  export let title = "Traffic board";
  export let subtitle = "Visible traffic";
  export let maxRows = 12;
  export let onSelectFlight = () => {};

  let activeBoard = "list";

  function toRadians(value) {
    return (value * Math.PI) / 180;
  }

  function calculateDistanceKm(flight, currentViewport) {
    const center = currentViewport?.center ?? [52.15, 19.4];
    const earthRadiusKm = 6371;
    const deltaLatitude = toRadians(flight.latitude - center[0]);
    const deltaLongitude = toRadians(flight.longitude - center[1]);
    const startLatitude = toRadians(center[0]);
    const endLatitude = toRadians(flight.latitude);
    const haversine =
      Math.sin(deltaLatitude / 2) ** 2 +
      Math.cos(startLatitude) * Math.cos(endLatitude) * Math.sin(deltaLongitude / 2) ** 2;

    return 2 * earthRadiusKm * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
  }

  function formatLastContact(lastContact) {
    if (lastContact === null || lastContact === undefined) {
      return "Unknown";
    }

    const seconds = Math.max(0, Math.round(Date.now() / 1000 - lastContact));
    return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m`;
  }

  function deriveOperatorCode(callsign) {
    const normalizedCallsign = (callsign ?? "").trim().toUpperCase();
    const match = normalizedCallsign.match(/^[A-Z]{3}/);
    return match ? match[0] : "N/A";
  }

  $: boardFlights =
    activeBoard === "closest"
      ? [...flights].sort(
          (left, right) => calculateDistanceKm(left, viewport) - calculateDistanceKm(right, viewport)
        )
      : activeBoard === "recent"
        ? [...flights].sort((left, right) => (right.last_contact ?? -Infinity) - (left.last_contact ?? -Infinity))
        : flights;
  $: visibleRows = boardFlights.slice(0, maxRows);
</script>

<section class="panel traffic-board-panel">
  <div class="board-header">
    <div>
      <p class="eyebrow">{subtitle}</p>
      <h2>{title}</h2>
    </div>
    <span class="count-pill">{flights.length}</span>
  </div>

  <div class="board-tabs" role="tablist" aria-label="Traffic board view">
    <button class:active={activeBoard === "list"} type="button" on:click={() => (activeBoard = "list")}>
      Ranked
    </button>
    <button class:active={activeBoard === "closest"} type="button" on:click={() => (activeBoard = "closest")}>
      Nearby
    </button>
    <button class:active={activeBoard === "recent"} type="button" on:click={() => (activeBoard = "recent")}>
      Fresh
    </button>
  </div>

  {#if visibleRows.length}
    <div class="board-list">
      {#each visibleRows as flight, index}
        <button
          class:selected={flight.icao24 === selectedIcao24}
          class="board-row"
          type="button"
          on:click={() => onSelectFlight(flight.icao24)}
        >
          <span class="board-rank">{index + 1}</span>
          <span class="board-main">
            <strong>{flight.callsign ?? flight.icao24}</strong>
            <span>{flight.origin_country ?? "Unknown"} · {deriveOperatorCode(flight.callsign)}</span>
          </span>
          <span class="board-metric">
            <strong>{formatAltitude(flight.altitude)}</strong>
            <span>ALT</span>
          </span>
          <span class="board-metric">
            <strong>{formatSpeed(flight.velocity)}</strong>
            <span>SPD</span>
          </span>
          <span class="board-metric compact">
            <strong>{activeBoard === "closest" ? `${calculateDistanceKm(flight, viewport).toFixed(0)} km` : formatLastContact(flight.last_contact)}</strong>
            <span>{activeBoard === "closest" ? "DIST" : "AGE"}</span>
          </span>
        </button>
      {/each}
    </div>
  {:else}
    <p class="empty-copy">No traffic matches the current radar filters.</p>
  {/if}
</section>

<style>
  .traffic-board-panel {
    display: grid;
    gap: 0.85rem;
  }

  .board-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
  }

  .eyebrow {
    margin: 0 0 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.7rem;
    color: var(--color-muted);
  }

  h2,
  p {
    margin: 0;
  }

  .count-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 2rem;
    padding: 0.32rem 0.65rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 800;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .board-tabs {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.45rem;
  }

  .board-tabs button {
    border: 1px solid var(--surface-border);
    border-radius: 14px;
    padding: 0.68rem 0.72rem;
    font: inherit;
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  .board-tabs button.active {
    color: var(--button-primary-text);
    background: var(--button-primary-bg);
    border-color: transparent;
  }

  .board-list {
    display: grid;
    gap: 0.55rem;
  }

  .board-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1.5fr) repeat(3, minmax(0, 0.8fr));
    gap: 0.7rem;
    align-items: center;
    width: 100%;
    padding: 0.78rem 0.82rem;
    border: 1px solid var(--surface-border);
    border-radius: 16px;
    color: inherit;
    background: rgba(255, 255, 255, 0.04);
    text-align: left;
    cursor: pointer;
  }

  .board-row.selected {
    border-color: rgba(245, 185, 8, 0.58);
    box-shadow: inset 0 0 0 1px rgba(245, 185, 8, 0.45);
  }

  .board-rank {
    display: grid;
    place-items: center;
    width: 1.8rem;
    height: 1.8rem;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 800;
    color: #171a1f;
    background: rgba(255, 211, 79, 0.92);
  }

  .board-main,
  .board-metric {
    display: grid;
    gap: 0.16rem;
  }

  .board-main strong,
  .board-metric strong {
    color: var(--color-text);
    font-size: 0.9rem;
  }

  .board-main span,
  .board-metric span,
  .empty-copy {
    color: var(--color-muted);
    font-size: 0.78rem;
  }

  .board-metric {
    justify-items: end;
  }

  @media (max-width: 720px) {
    .board-row {
      grid-template-columns: auto minmax(0, 1fr);
    }

    .board-metric {
      justify-items: start;
    }
  }
</style>
