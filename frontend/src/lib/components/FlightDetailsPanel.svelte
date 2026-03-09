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
  export let trailPoints = [];
  export let onToggleFollow = () => {};

  function buildAltitudePath(points) {
    if (points.length < 2) {
      return "";
    }

    const chartWidth = 240;
    const chartHeight = 68;
    const altitudes = points.map((point) => point.altitude ?? 0);
    const minAltitude = Math.min(...altitudes);
    const maxAltitude = Math.max(...altitudes);
    const altitudeRange = Math.max(1, maxAltitude - minAltitude);

    return points
      .map((point, index) => {
        const x = (index / (points.length - 1)) * chartWidth;
        const altitude = point.altitude ?? minAltitude;
        const y = chartHeight - ((altitude - minAltitude) / altitudeRange) * chartHeight;
        return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(" ");
  }

  function formatHistoryDuration(points) {
    if (points.length < 2) {
      return "Just now";
    }

    const durationMinutes = Math.max(
      1,
      Math.round((points[points.length - 1].timestamp - points[0].timestamp) / 60000)
    );

    return `${durationMinutes} min`;
  }

  $: historySamples = trailPoints.slice(-24);
  $: altitudeSamples = historySamples.filter((point) => point.altitude !== null && point.altitude !== undefined);
  $: altitudePath = buildAltitudePath(altitudeSamples);
</script>

<section class="panel details-panel">
  <h2>Selected aircraft</h2>

  {#if flight}
    <div class="details-header">
      <strong>{flight.callsign ?? "Unknown callsign"}</strong>
      <span>{formatFlightStatus(flight)}</span>
    </div>

    <button
      class:active={followAircraft}
      class="follow-button"
      type="button"
      title="Keep the selected aircraft centered on the map"
      on:click={onToggleFollow}
    >
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

    <section class="history-panel">
      <div class="history-header">
        <strong>Session history</strong>
        <span>{historySamples.length} samples</span>
      </div>

      {#if altitudeSamples.length > 1}
        <div class="history-chart">
          <svg viewBox="0 0 240 68" aria-hidden="true">
            <path d={altitudePath} />
          </svg>
        </div>

        <div class="history-meta">
          <div>
            <span class="history-label">Window</span>
            <strong class="history-value">{formatHistoryDuration(historySamples)}</strong>
          </div>
          <div>
            <span class="history-label">Start altitude</span>
            <strong class="history-value">{formatAltitude(altitudeSamples[0].altitude)}</strong>
          </div>
          <div>
            <span class="history-label">Latest altitude</span>
            <strong class="history-value">{formatAltitude(altitudeSamples[altitudeSamples.length - 1].altitude)}</strong>
          </div>
        </div>
      {:else}
        <p>Waiting for enough history to draw an altitude profile for this aircraft.</p>
      {/if}
    </section>
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

  .history-panel {
    display: grid;
    gap: 0.75rem;
    padding-top: 0.2rem;
    border-top: 1px solid var(--surface-border);
  }

  .history-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: center;
  }

  .history-header span {
    font-size: 0.82rem;
    color: var(--color-muted);
  }

  .history-chart {
    border-radius: 16px;
    padding: 0.55rem;
    background: linear-gradient(180deg, rgba(52, 125, 182, 0.14) 0%, rgba(52, 125, 182, 0.04) 100%);
  }

  .history-chart svg {
    display: block;
    width: 100%;
    height: auto;
  }

  .history-chart path {
    fill: none;
    stroke: #4bb7f5;
    stroke-width: 3;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .history-meta {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8rem;
  }

  .history-meta div {
    display: grid;
    gap: 0.15rem;
  }

  .history-label {
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-subtle);
  }

  .history-value {
    font-size: 0.98rem;
  }

  @media (max-width: 720px) {
    .history-meta {
      grid-template-columns: 1fr;
    }
  }
</style>
