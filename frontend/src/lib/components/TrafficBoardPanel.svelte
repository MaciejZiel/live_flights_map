<script>
  import { formatAltitude, formatSpeed } from "../utils/flightFormatters.js";
  import { deriveOperatorCode } from "../utils/flightMatching.js";

  export let flights = [];
  export let selectedIcao24 = null;
  export let title = "Traffic board";
  export let subtitle = "Visible traffic";
  export let maxRows = 12;
  export let featuredFlight = null;
  export let onSelectFlight = () => {};

  function formatLastContact(lastContact) {
    if (lastContact === null || lastContact === undefined) {
      return "Unknown";
    }

    const seconds = Math.max(0, Math.round(Date.now() / 1000 - lastContact));
    return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m`;
  }

  function buildFlightSubtitle(flight) {
    return (
      flight?.route_label ??
      flight?.iata_codes ??
      [flight?.origin_country ?? "Unknown", deriveOperatorCode(flight) || "N/A"]
        .filter(Boolean)
        .join(" · ")
    );
  }

  $: boardFlights = flights;
  $: visibleRows = boardFlights.slice(0, maxRows);
</script>

<section aria-label={title} class="panel traffic-board-panel">
  <div class="board-header">
    <div>
      <p class="board-note">{title}</p>
      {#if subtitle}
        <strong class="board-subtitle">{subtitle}</strong>
      {/if}
    </div>

    {#if featuredFlight}
      <button class="board-highlight" type="button" on:click={() => onSelectFlight(featuredFlight.icao24)}>
        <span>Lead</span>
        <strong>{featuredFlight.callsign ?? featuredFlight.icao24}</strong>
        <small>{formatSpeed(featuredFlight.velocity)} · {formatAltitude(featuredFlight.altitude)}</small>
      </button>
    {/if}
  </div>

  {#if visibleRows.length}
    <div class="board-columns" aria-hidden="true">
      <span>Flight</span>
      <span>Altitude</span>
      <span>Speed</span>
      <span>Age</span>
    </div>

    <div class="board-list">
      {#each visibleRows as flight, index}
        <button
          class:selected={flight.icao24 === selectedIcao24}
          class="board-row"
          type="button"
          on:click={() => onSelectFlight(flight.icao24)}
        >
          <span class="board-rank">{String(index + 1).padStart(2, "0")}</span>
          <span class="board-main">
            <strong>{flight.callsign ?? flight.icao24}</strong>
            <span>{buildFlightSubtitle(flight)}</span>
          </span>
          <span class="board-metric">
            <strong>{formatAltitude(flight.altitude)}</strong>
          </span>
          <span class="board-metric">
            <strong>{formatSpeed(flight.velocity)}</strong>
          </span>
          <span class="board-age">{formatLastContact(flight.last_contact)}</span>
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
    gap: 0.55rem;
  }

  p {
    margin: 0;
  }

  .board-header {
    display: flex;
    justify-content: space-between;
    gap: 0.7rem;
    align-items: end;
  }

  .board-note {
    font-size: 0.64rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: rgba(194, 206, 219, 0.5);
  }

  .board-subtitle {
    display: block;
    margin-top: 0.22rem;
    color: var(--color-text);
    font-size: 0.84rem;
    line-height: 1.15;
  }

  .board-highlight {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    justify-self: end;
    padding: 0.42rem 0.58rem;
    border-radius: 999px;
    border: 1px solid rgba(245, 185, 8, 0.16);
    color: inherit;
    background: rgba(245, 185, 8, 0.08);
    cursor: pointer;
  }

  .board-highlight span,
  .board-highlight small {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(194, 206, 219, 0.7);
  }

  .board-highlight strong {
    color: var(--color-text);
    font-size: 0.78rem;
  }

  .board-columns {
    display: grid;
    grid-template-columns: minmax(0, 1.7fr) repeat(3, minmax(0, 0.72fr));
    gap: 0.5rem;
    padding: 0 0.2rem 0 1.9rem;
  }

  .board-columns span {
    font-size: 0.6rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: rgba(182, 193, 205, 0.48);
  }

  .board-columns span:not(:first-child) {
    justify-self: end;
  }

  .board-list {
    display: grid;
    gap: 0.22rem;
    align-content: start;
  }

  .board-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1.45fr) repeat(2, minmax(0, 0.75fr)) auto;
    gap: 0.5rem;
    align-items: center;
    width: 100%;
    padding: 0.62rem 0.68rem;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    color: inherit;
    background: rgba(18, 21, 25, 0.88);
    text-align: left;
    cursor: pointer;
    transition:
      border-color 160ms ease,
      background 160ms ease;
  }

  .board-row:hover {
    border-color: rgba(255, 211, 79, 0.18);
    background: rgba(24, 27, 32, 0.92);
  }

  .board-row.selected {
    border-color: rgba(245, 185, 8, 0.34);
    background: rgba(48, 39, 11, 0.86);
  }

  .board-rank {
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    color: rgba(255, 211, 79, 0.82);
  }

  .board-main,
  .board-metric {
    display: grid;
    gap: 0.12rem;
  }

  .board-main strong,
  .board-metric strong,
  .board-age {
    color: var(--color-text);
    font-size: 0.78rem;
    line-height: 1.15;
  }

  .board-main span,
  .empty-copy {
    color: rgba(194, 206, 219, 0.72);
    font-size: 0.68rem;
    line-height: 1.15;
  }

  .board-metric {
    justify-items: end;
  }

  .board-age {
    justify-self: end;
    color: rgba(194, 206, 219, 0.82);
  }

  .empty-copy {
    padding: 0.32rem 0;
    font-size: 0.72rem;
  }

  @media (max-width: 720px) {
    .board-header {
      align-items: start;
      flex-direction: column;
    }

    .board-highlight {
      flex-wrap: wrap;
      justify-self: start;
    }

    .board-columns {
      display: none;
    }

    .board-row {
      grid-template-columns: auto minmax(0, 1fr) auto;
      gap: 0.4rem;
    }

    .board-metric {
      display: none;
    }
  }
</style>
