<script>
  import {
    formatAltitude,
    formatFlightStatus,
    formatHeading,
    formatSpeed,
  } from "../utils/flightFormatters.js";

  export let flights = [];
  export let selectedIcao24 = null;
  export let onSelectFlight = () => {};
</script>

<section class="panel comparison-panel">
  <div>
    <p class="eyebrow">Comparison</p>
    <h2>Side-by-side flights</h2>
  </div>

  {#if flights.length > 1}
    <div class="comparison-grid">
      {#each flights as flight}
        <article class:selected={flight.icao24 === selectedIcao24} class="compare-card">
          <div class="compare-card-header">
            <strong>{flight.callsign ?? flight.icao24}</strong>
            <span>{formatFlightStatus(flight)}</span>
          </div>
          <dl>
            <div>
              <dt>Altitude</dt>
              <dd>{formatAltitude(flight.altitude)}</dd>
            </div>
            <div>
              <dt>Speed</dt>
              <dd>{formatSpeed(flight.velocity)}</dd>
            </div>
            <div>
              <dt>Heading</dt>
              <dd>{formatHeading(flight.true_track)}</dd>
            </div>
            <div>
              <dt>Country</dt>
              <dd>{flight.origin_country ?? "unknown"}</dd>
            </div>
          </dl>
          <button class="compare-action" type="button" on:click={() => onSelectFlight(flight.icao24)}>
            Focus
          </button>
        </article>
      {/each}
    </div>
  {:else}
    <p>Add at least two live aircraft to the watchlist to compare them side by side.</p>
  {/if}
</section>

<style>
  .comparison-panel {
    display: grid;
    gap: 0.9rem;
  }

  .eyebrow {
    margin: 0 0 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-size: 0.72rem;
    color: var(--color-muted);
  }

  h2,
  p {
    margin: 0;
  }

  .comparison-grid {
    display: grid;
    gap: 0.65rem;
  }

  .compare-card {
    display: grid;
    gap: 0.7rem;
    padding: 0.9rem;
    border: 1px solid var(--surface-border);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.04);
  }

  .compare-card.selected {
    box-shadow: inset 0 0 0 2px rgba(75, 183, 245, 0.35);
  }

  .compare-card-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }

  .compare-card-header span {
    font-size: 0.78rem;
    color: var(--color-muted);
    font-weight: 700;
  }

  dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.65rem;
    margin: 0;
  }

  dl div {
    display: grid;
    gap: 0.15rem;
  }

  dt {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-subtle);
  }

  dd {
    margin: 0;
    font-size: 0.95rem;
  }

  .compare-action {
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    padding: 0.72rem 0.82rem;
    font: inherit;
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  @media (max-width: 720px) {
    dl {
      grid-template-columns: 1fr;
    }
  }
</style>
