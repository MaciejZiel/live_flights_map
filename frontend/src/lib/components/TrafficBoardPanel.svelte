<script>
  import { formatAltitude, formatSpeed } from "../utils/flightFormatters.js";
  import { deriveOperatorCode } from "../utils/flightMatching.js";

  export let flights = [];
  export let selectedIcao24 = null;
  export let title = "Traffic board";
  export let subtitle = "Visible traffic";
  export let maxRows = 12;
  export let featuredFlight = null;
  export let sortBy = "altitude_desc";
  export let onSortByChange = () => {};
  export let onSelectFlight = () => {};
  export let onJumpFlight = () => {};

  const SORT_OPTIONS = [
    { value: "altitude_desc", label: "Alt" },
    { value: "speed_desc", label: "Speed" },
    { value: "distance_asc", label: "Near" },
    { value: "last_contact_desc", label: "Fresh" },
  ];

  let hoveredIcao24 = null;

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

  $: boardFlights = flights ?? [];
  $: pinnedFlight = selectedIcao24
    ? boardFlights.find((flight) => flight.icao24 === selectedIcao24) ?? null
    : null;
  $: visibleRows = [
    ...(pinnedFlight ? [pinnedFlight] : []),
    ...boardFlights.filter((flight) => flight.icao24 !== pinnedFlight?.icao24),
  ].slice(0, maxRows);
  $: previewFlight =
    boardFlights.find((flight) => flight.icao24 === hoveredIcao24) ??
    pinnedFlight ??
    featuredFlight ??
    visibleRows[0] ??
    null;
</script>

<section aria-label={title} class="panel traffic-board-panel">
  <div class="board-header">
    <div>
      <p class="board-note">{title}</p>
      {#if subtitle}
        <strong class="board-subtitle">{subtitle}</strong>
      {/if}
    </div>

    {#if previewFlight}
      <article class="board-preview">
        <span class="board-preview-kicker">
          {hoveredIcao24 ? "Preview" : pinnedFlight ? "Pinned" : "Lead"}
        </span>
        <strong>{previewFlight.callsign ?? previewFlight.icao24}</strong>
        <small>{buildFlightSubtitle(previewFlight)}</small>
        <div>
          <span>{formatAltitude(previewFlight.altitude)}</span>
          <span>{formatSpeed(previewFlight.velocity)}</span>
          <span>{formatLastContact(previewFlight.last_contact)}</span>
        </div>
      </article>
    {/if}
  </div>

  <div class="board-sort-row" aria-label="Traffic board sort">
    {#each SORT_OPTIONS as option}
      <button
        class:active={sortBy === option.value}
        class="board-sort-button"
        type="button"
        on:click={() => onSortByChange(option.value)}
      >
        {option.label}
      </button>
    {/each}
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
        <article
          class:selected={flight.icao24 === selectedIcao24}
          class:pinned={flight.icao24 === pinnedFlight?.icao24}
          class="board-row"
          on:mouseenter={() => {
            hoveredIcao24 = flight.icao24;
          }}
          on:mouseleave={() => {
            hoveredIcao24 = null;
          }}
        >
          <button class="board-row-main" type="button" on:click={() => onSelectFlight(flight.icao24)}>
            <span class="board-rank">
              {flight.icao24 === pinnedFlight?.icao24 ? "PIN" : String(index + 1).padStart(2, "0")}
            </span>
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

          <div class="board-row-actions">
            <button class="board-inline-action" type="button" on:click={() => onJumpFlight(flight.icao24)}>
              Jump
            </button>
          </div>
        </article>
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

  .board-header {
    display: flex;
    justify-content: space-between;
    gap: 0.7rem;
    align-items: start;
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

  .board-preview {
    display: grid;
    gap: 0.18rem;
    min-width: min(12rem, 100%);
    padding: 0.58rem 0.7rem;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(255, 255, 255, 0.04);
  }

  .board-preview-kicker {
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: rgba(194, 206, 219, 0.6);
  }

  .board-preview strong {
    color: var(--color-text);
    font-size: 0.82rem;
  }

  .board-preview small {
    color: rgba(194, 206, 219, 0.74);
    font-size: 0.7rem;
    line-height: 1.2;
  }

  .board-preview div {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .board-preview div span {
    padding: 0.2rem 0.42rem;
    border-radius: 999px;
    color: rgba(228, 236, 244, 0.86);
    font-size: 0.65rem;
    background: rgba(255, 255, 255, 0.06);
  }

  .board-sort-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.36rem;
  }

  .board-sort-button,
  .board-inline-action {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    font: inherit;
    cursor: pointer;
  }

  .board-sort-button {
    padding: 0.34rem 0.56rem;
    font-size: 0.68rem;
    font-weight: 800;
    color: rgba(228, 236, 244, 0.82);
    background: rgba(255, 255, 255, 0.04);
  }

  .board-sort-button.active {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    border-color: transparent;
  }

  .board-columns {
    display: grid;
    grid-template-columns: minmax(0, 1.7fr) repeat(3, minmax(0, 0.72fr));
    gap: 0.5rem;
    padding: 0 2.8rem 0 1.9rem;
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
    gap: 0.28rem;
    align-content: start;
  }

  .board-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 0.45rem;
    align-items: center;
    padding: 0.12rem;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    background: rgba(18, 21, 25, 0.88);
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

  .board-row.pinned {
    box-shadow: 0 0 0 1px rgba(120, 200, 255, 0.16);
  }

  .board-row-main {
    display: grid;
    grid-template-columns: auto minmax(0, 1.45fr) repeat(2, minmax(0, 0.75fr)) auto;
    gap: 0.5rem;
    align-items: center;
    width: 100%;
    padding: 0.5rem 0.56rem;
    border: 0;
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  .board-row-actions {
    display: flex;
    align-items: center;
    padding-right: 0.4rem;
  }

  .board-inline-action {
    padding: 0.34rem 0.54rem;
    font-size: 0.66rem;
    font-weight: 800;
    color: rgba(228, 236, 244, 0.86);
    background: rgba(255, 255, 255, 0.05);
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

    .board-preview {
      width: 100%;
    }

    .board-columns {
      display: none;
    }

    .board-row,
    .board-row-main {
      grid-template-columns: auto minmax(0, 1fr);
    }

    .board-row-actions {
      padding: 0 0.56rem 0.42rem;
    }

    .board-row-main .board-metric,
    .board-row-main .board-age {
      justify-self: start;
    }
  }
</style>
