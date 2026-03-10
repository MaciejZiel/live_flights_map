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
  {#if subtitle}
    <p class="board-note">{subtitle}</p>
  {/if}

  {#if featuredFlight}
    <button class="featured-card" type="button" on:click={() => onSelectFlight(featuredFlight.icao24)}>
      <span class="featured-kicker">Fastest in view</span>
      <strong>{featuredFlight.callsign ?? featuredFlight.icao24}</strong>
      <p>{buildFlightSubtitle(featuredFlight)}</p>
      <div class="featured-metrics">
        <span>
          <strong>{formatSpeed(featuredFlight.velocity)}</strong>
          <small>Speed</small>
        </span>
        <span>
          <strong>{formatAltitude(featuredFlight.altitude)}</strong>
          <small>Altitude</small>
        </span>
      </div>
      <span class="featured-action">Track aircraft</span>
    </button>
  {/if}

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
            <span>{buildFlightSubtitle(flight)}</span>
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
            <strong>{formatLastContact(flight.last_contact)}</strong>
            <span>AGE</span>
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
    gap: 0.65rem;
  }

  p {
    margin: 0;
  }

  .board-note {
    font-size: 0.69rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: rgba(194, 206, 219, 0.56);
  }

  .board-list {
    display: grid;
    gap: 0.4rem;
    align-content: start;
  }

  .featured-card {
    display: grid;
    gap: 0.48rem;
    width: 100%;
    padding: 0.86rem 0.88rem;
    border: 1px solid rgba(245, 185, 8, 0.18);
    border-radius: 16px;
    color: inherit;
    background:
      radial-gradient(circle at top right, rgba(245, 185, 8, 0.16), transparent 38%),
      linear-gradient(180deg, rgba(39, 42, 48, 0.98) 0%, rgba(21, 24, 28, 0.98) 100%);
    text-align: left;
    cursor: pointer;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.02),
      0 12px 22px rgba(0, 0, 0, 0.2);
  }

  .featured-kicker,
  .featured-card p,
  .featured-metrics small {
    margin: 0;
    font-size: 0.69rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: rgba(194, 206, 219, 0.62);
  }

  .featured-card strong {
    color: var(--color-text);
    font-size: 1rem;
  }

  .featured-card p {
    text-transform: none;
    letter-spacing: 0;
    font-size: 0.76rem;
  }

  .featured-metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.45rem;
  }

  .featured-metrics span {
    display: grid;
    gap: 0.14rem;
    padding: 0.56rem 0.6rem;
    border-radius: 11px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(255, 255, 255, 0.03);
  }

  .featured-metrics strong {
    font-size: 0.86rem;
  }

  .featured-action {
    display: inline-flex;
    justify-self: start;
    align-items: center;
    padding: 0.46rem 0.72rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 800;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .board-row {
    display: grid;
    grid-template-columns: auto minmax(0, 1.35fr) repeat(3, minmax(0, 0.7fr));
    gap: 0.58rem;
    align-items: center;
    width: 100%;
    padding: 0.7rem 0.74rem;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 14px;
    color: inherit;
    background:
      linear-gradient(180deg, rgba(34, 37, 42, 0.98) 0%, rgba(22, 24, 28, 0.98) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.02),
      0 10px 18px rgba(0, 0, 0, 0.18);
    text-align: left;
    cursor: pointer;
    transition:
      transform 160ms ease,
      border-color 160ms ease,
      background 160ms ease;
  }

  .board-row:hover {
    transform: translateY(-1px);
    border-color: rgba(255, 211, 79, 0.22);
  }

  .board-row.selected {
    border-color: rgba(245, 185, 8, 0.58);
    background:
      linear-gradient(180deg, rgba(51, 43, 14, 0.98) 0%, rgba(27, 25, 16, 0.98) 100%);
    box-shadow:
      inset 0 0 0 1px rgba(245, 185, 8, 0.34),
      0 14px 24px rgba(0, 0, 0, 0.2);
  }

  .board-rank {
    display: grid;
    place-items: center;
    width: 1.7rem;
    height: 1.7rem;
    border-radius: 999px;
    font-size: 0.72rem;
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
    font-size: 0.85rem;
    line-height: 1.15;
  }

  .board-main span,
  .board-metric span,
  .empty-copy {
    color: rgba(194, 206, 219, 0.72);
    font-size: 0.7rem;
    line-height: 1.15;
  }

  .board-metric {
    justify-items: end;
  }

  @media (max-width: 720px) {
    .board-row {
      grid-template-columns: auto minmax(0, 1fr) minmax(0, 0.8fr);
    }

    .board-metric.compact {
      display: none;
    }

    .board-metric {
      justify-items: start;
    }
  }
</style>
