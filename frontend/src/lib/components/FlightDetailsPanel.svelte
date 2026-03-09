<script>
  import {
    formatAltitude,
    formatCoordinates,
    formatFlightStatus,
    formatHeading,
    formatSpeed,
    formatVerticalRate,
  } from "../utils/flightFormatters.js";

  export let flight = null;
  export let followAircraft = false;
  export let onToggleFollow = () => {};
</script>

<section class="panel details-panel">
  <h2>Selected aircraft</h2>

  {#if flight}
    <div class="details-header">
      <strong>{flight.callsign ?? "Unknown callsign"}</strong>
      <span>{formatFlightStatus(flight)}</span>
    </div>

    <button class:active={followAircraft} class="follow-button" type="button" on:click={onToggleFollow}>
      {#if followAircraft}
        Stop following
      {:else}
        Follow aircraft
      {/if}
    </button>

    <dl>
      <div>
        <dt>ICAO24</dt>
        <dd>{flight.icao24}</dd>
      </div>
      <div>
        <dt>Country</dt>
        <dd>{flight.origin_country ?? "unknown"}</dd>
      </div>
      <div>
        <dt>Altitude</dt>
        <dd>{formatAltitude(flight.altitude)}</dd>
      </div>
      <div>
        <dt>Heading</dt>
        <dd>{formatHeading(flight.true_track)}</dd>
      </div>
      <div>
        <dt>Speed</dt>
        <dd>{formatSpeed(flight.velocity)}</dd>
      </div>
      <div>
        <dt>Vertical rate</dt>
        <dd>{formatVerticalRate(flight.vertical_rate)}</dd>
      </div>
      <div>
        <dt>Position</dt>
        <dd>{formatCoordinates(flight.latitude, flight.longitude)}</dd>
      </div>
    </dl>
  {:else}
    <p>Click an aircraft marker to inspect its current details.</p>
  {/if}
</section>

<style>
  .details-panel {
    display: grid;
    gap: 0.9rem;
  }

  .details-header {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }

  .details-header strong {
    font-size: 1.05rem;
  }

  .details-header span {
    padding: 0.28rem 0.6rem;
    border-radius: 999px;
    background: var(--chip-bg);
    font-size: 0.82rem;
    font-weight: 700;
  }

  .follow-button {
    border: 0;
    border-radius: 12px;
    padding: 0.8rem 0.95rem;
    font: inherit;
    font-weight: 700;
    color: var(--button-primary-text);
    background: var(--button-primary-bg);
    cursor: pointer;
  }

  .follow-button.active {
    background: linear-gradient(135deg, #b25e10 0%, #de8b32 100%);
  }

  dl {
    display: grid;
    gap: 0.8rem;
    margin: 0;
  }

  dl div {
    display: grid;
    gap: 0.15rem;
  }

  dt {
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-subtle);
  }

  dd {
    margin: 0;
    font-size: 0.98rem;
  }

  p {
    margin: 0;
    line-height: 1.5;
  }
</style>
