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
  export let isWatched = false;
  export let annotation = {
    notes: "",
    tags: [],
  };
  export let onToggleFollow = () => {};
  export let onToggleWatch = () => {};
  export let onUpdateNotes = () => {};
  export let onAddTag = () => {};
  export let onRemoveTag = () => {};

  let nextTag = "";

  function buildMetricPath(points, getValue) {
    if (points.length < 2) {
      return "";
    }

    const chartWidth = 240;
    const chartHeight = 68;
    const values = points.map((point) => getValue(point));
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = Math.max(1, maxValue - minValue);

    return points
      .map((point, index) => {
        const x = (index / (points.length - 1)) * chartWidth;
        const value = getValue(point);
        const y = chartHeight - ((value - minValue) / range) * chartHeight;
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

    if (durationMinutes < 60) {
      return `${durationMinutes} min`;
    }

    const hours = Math.floor(durationMinutes / 60);
    const minutes = durationMinutes % 60;
    return minutes ? `${hours} h ${minutes} min` : `${hours} h`;
  }

  function formatHistoryTimestamp(timestamp) {
    if (!timestamp) {
      return "No history";
    }

    return new Intl.DateTimeFormat("pl-PL", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(timestamp));
  }

  function formatRelativeContact(lastContact) {
    if (lastContact === null || lastContact === undefined) {
      return "Unknown";
    }

    const ageSeconds = Math.max(0, Math.round(Date.now() / 1000 - lastContact));

    if (ageSeconds < 60) {
      return `${ageSeconds}s ago`;
    }

    const ageMinutes = Math.floor(ageSeconds / 60);
    const remainingSeconds = ageSeconds % 60;
    return `${ageMinutes}m ${remainingSeconds}s ago`;
  }

  function deriveOperatorCode(callsign) {
    const normalizedCallsign = (callsign ?? "").trim().toUpperCase();
    const match = normalizedCallsign.match(/^[A-Z]{3}/);
    return match ? match[0] : "N/A";
  }

  function getTrackLabel(track) {
    if (track === null || track === undefined) {
      return "Unknown sector";
    }

    if (track >= 315 || track < 45) {
      return "Northbound";
    }

    if (track >= 45 && track < 135) {
      return "Eastbound";
    }

    if (track >= 135 && track < 225) {
      return "Southbound";
    }

    return "Westbound";
  }

  function getVerticalTrendLabel(value) {
    if (value === null || value === undefined) {
      return "No trend";
    }

    if (value > 0.6) {
      return "Climbing";
    }

    if (value < -0.6) {
      return "Descending";
    }

    return "Level";
  }

  function calculateObservedDistanceKm(points) {
    if (points.length < 2) {
      return 0;
    }

    const earthRadiusKm = 6371;
    const toRadians = (value) => (value * Math.PI) / 180;
    let distance = 0;

    for (let index = 1; index < points.length; index += 1) {
      const previous = points[index - 1];
      const current = points[index];
      const deltaLatitude = toRadians(current.latitude - previous.latitude);
      const deltaLongitude = toRadians(current.longitude - previous.longitude);
      const startLatitude = toRadians(previous.latitude);
      const endLatitude = toRadians(current.latitude);
      const haversine =
        Math.sin(deltaLatitude / 2) ** 2 +
        Math.cos(startLatitude) * Math.cos(endLatitude) * Math.sin(deltaLongitude / 2) ** 2;

      distance += 2 * earthRadiusKm * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
    }

    return distance;
  }

  function downloadHistory(content, extension, mimeType) {
    if (typeof document === "undefined" || !flight || trailPoints.length === 0) {
      return;
    }

    const link = document.createElement("a");
    const blob = new Blob([content], { type: mimeType });
    const callsign = (flight.callsign ?? flight.icao24 ?? "flight").replace(/\s+/g, "-").toLowerCase();

    const downloadUrl = URL.createObjectURL(blob);
    link.href = downloadUrl;
    link.download = `${callsign}-history.${extension}`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 0);
  }

  function exportHistoryAsJson() {
    downloadHistory(JSON.stringify(trailPoints, null, 2), "json", "application/json");
  }

  function exportHistoryAsCsv() {
    const rows = [
      ["timestamp", "latitude", "longitude", "altitude", "velocity", "vertical_rate"],
      ...trailPoints.map((point) => [
        new Date(point.timestamp).toISOString(),
        point.latitude,
        point.longitude,
        point.altitude ?? "",
        point.velocity ?? "",
        point.vertical_rate ?? "",
      ]),
    ];

    const csv = rows
      .map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(","))
      .join("\n");

    downloadHistory(csv, "csv", "text/csv;charset=utf-8");
  }

  function handleTagSubmit() {
    const normalizedTag = nextTag.trim();
    if (!normalizedTag) {
      return;
    }

    onAddTag(normalizedTag);
    nextTag = "";
  }

  $: historySamples = trailPoints.slice(-24);
  $: altitudeSamples = historySamples.filter((point) => point.altitude !== null && point.altitude !== undefined);
  $: speedSamples = historySamples.filter((point) => point.velocity !== null && point.velocity !== undefined);
  $: verticalRateSamples = historySamples.filter(
    (point) => point.vertical_rate !== null && point.vertical_rate !== undefined
  );
  $: altitudePath = buildMetricPath(altitudeSamples, (point) => point.altitude ?? 0);
  $: speedPath = buildMetricPath(speedSamples, (point) => point.velocity ?? 0);
  $: verticalRatePath = buildMetricPath(verticalRateSamples, (point) => point.vertical_rate ?? 0);
  $: trailStart = trailPoints[0] ?? null;
  $: trailEnd = trailPoints[trailPoints.length - 1] ?? null;
  $: observedDistanceKm = calculateObservedDistanceKm(trailPoints);
  $: averageObservedSpeed = speedSamples.length
    ? Math.round(speedSamples.reduce((total, point) => total + point.velocity * 3.6, 0) / speedSamples.length)
    : 0;
  $: operatorCode = deriveOperatorCode(flight?.callsign);
</script>

<section class="panel details-panel">
  <div class="panel-heading">
    <div>
      <p class="eyebrow">Aircraft inspector</p>
      <h2>Flight telemetry</h2>
    </div>
    {#if flight}
      <span class="status-chip">{formatFlightStatus(flight)}</span>
    {/if}
  </div>

  {#if flight}
    <section class="identity-card">
      <div class="identity-main">
        <div>
          <strong>{flight.callsign ?? "Unknown callsign"}</strong>
          <p>{flight.origin_country ?? "Unknown country"} · operator {operatorCode}</p>
        </div>

        <div class="identity-actions">
          <button class:active={followAircraft} class="action-button" type="button" on:click={onToggleFollow}>
            {followAircraft ? "Following" : "Follow"}
          </button>
          <button class:active={isWatched} class="action-button secondary" type="button" on:click={onToggleWatch}>
            {isWatched ? "Watching" : "Watch"}
          </button>
        </div>
      </div>

      <div class="route-strip">
        <article class="route-node">
          <span class="route-label">Observed start</span>
          <strong>{trailStart ? formatCoordinates(trailStart.latitude, trailStart.longitude) : "No trail yet"}</strong>
          <small>{trailStart ? formatHistoryTimestamp(trailStart.timestamp) : "Waiting for more samples"}</small>
        </article>
        <div class="route-line" aria-hidden="true"></div>
        <article class="route-node current">
          <span class="route-label">Current position</span>
          <strong>{formatCoordinates(flight.latitude, flight.longitude)}</strong>
          <small>{formatRelativeContact(flight.last_contact)}</small>
        </article>
      </div>
    </section>

    <section class="telemetry-grid">
      <article class="telemetry-card">
        <span>Altitude</span>
        <strong>{formatAltitude(flight.altitude)}</strong>
        <small>{getVerticalTrendLabel(flight.vertical_rate)}</small>
      </article>
      <article class="telemetry-card">
        <span>Ground speed</span>
        <strong>{formatSpeed(flight.velocity)}</strong>
        <small>{averageObservedSpeed ? `avg ${averageObservedSpeed} km/h` : "Waiting for trail"}</small>
      </article>
      <article class="telemetry-card">
        <span>Heading</span>
        <strong>{formatHeading(flight.true_track)}</strong>
        <small>{getTrackLabel(flight.true_track)}</small>
      </article>
      <article class="telemetry-card">
        <span>Vertical rate</span>
        <strong>{formatVerticalRate(flight.vertical_rate)}</strong>
        <small>{trailPoints.length} trail points</small>
      </article>
    </section>

    <section class="data-grid">
      <article class="data-card">
        <span>ICAO24</span>
        <strong>{flight.icao24}</strong>
      </article>
      <article class="data-card">
        <span>Country</span>
        <strong>{flight.origin_country ?? "Unknown"}</strong>
      </article>
      <article class="data-card">
        <span>Track class</span>
        <strong>{getTrackLabel(flight.true_track)}</strong>
      </article>
      <article class="data-card">
        <span>Observed window</span>
        <strong>{formatHistoryDuration(trailPoints)}</strong>
      </article>
      <article class="data-card">
        <span>Observed distance</span>
        <strong>{observedDistanceKm ? `${observedDistanceKm.toFixed(1)} km` : "No movement yet"}</strong>
      </article>
      <article class="data-card">
        <span>Last contact</span>
        <strong>{formatRelativeContact(flight.last_contact)}</strong>
      </article>
    </section>

    <section class="annotation-panel">
      <div class="section-header">
        <strong>Notes and tags</strong>
        <span>{annotation.tags?.length ?? 0} tags</span>
      </div>

      <label class="notes-field">
        <span>Notes</span>
        <textarea
          rows="4"
          placeholder="Add notes about route behavior, callsign changes, or traffic priority"
          value={annotation.notes ?? ""}
          on:input={(event) => onUpdateNotes(event.currentTarget.value)}
        ></textarea>
      </label>

      <div class="tag-editor">
        <label class="notes-field">
          <span>Tag</span>
          <input
            bind:value={nextTag}
            type="text"
            placeholder="military, medevac, diversion"
            on:keydown={(event) => event.key === "Enter" && handleTagSubmit()}
          />
        </label>
        <button class="tag-add-button" type="button" on:click={handleTagSubmit}>Add tag</button>
      </div>

      {#if annotation.tags?.length}
        <div class="tag-list">
          {#each annotation.tags as tag}
            <button class="tag-chip" type="button" on:click={() => onRemoveTag(tag)}>
              {tag} ×
            </button>
          {/each}
        </div>
      {/if}
    </section>

    <section class="history-panel">
      <div class="section-header">
        <div>
          <strong>Session history</strong>
          <p>{historySamples.length} visible samples in this session</p>
        </div>
        <div class="history-actions">
          <button class="history-action" type="button" disabled={!trailPoints.length} on:click={exportHistoryAsJson}>
            JSON
          </button>
          <button class="history-action" type="button" disabled={!trailPoints.length} on:click={exportHistoryAsCsv}>
            CSV
          </button>
        </div>
      </div>

      {#if altitudeSamples.length > 1}
        <div class="chart-grid">
          <article class="metric-card">
            <div class="metric-card-header">
              <span>Altitude profile</span>
              <strong>{formatAltitude(altitudeSamples[altitudeSamples.length - 1].altitude)}</strong>
            </div>
            <div class="history-chart">
              <svg viewBox="0 0 240 68" aria-hidden="true">
                <path d={altitudePath} stroke="#78c8ff" />
              </svg>
            </div>
          </article>

          <article class="metric-card">
            <div class="metric-card-header">
              <span>Speed profile</span>
              <strong>
                {#if speedSamples.length}
                  {formatSpeed(speedSamples[speedSamples.length - 1].velocity)}
                {:else}
                  Unknown
                {/if}
              </strong>
            </div>
            {#if speedSamples.length > 1}
              <div class="history-chart">
                <svg viewBox="0 0 240 68" aria-hidden="true">
                  <path d={speedPath} stroke="#7df0b1" />
                </svg>
              </div>
            {:else}
              <p class="chart-empty">Waiting for more speed samples.</p>
            {/if}
          </article>

          <article class="metric-card">
            <div class="metric-card-header">
              <span>Vertical profile</span>
              <strong>
                {#if verticalRateSamples.length}
                  {formatVerticalRate(verticalRateSamples[verticalRateSamples.length - 1].vertical_rate)}
                {:else}
                  Unknown
                {/if}
              </strong>
            </div>
            {#if verticalRateSamples.length > 1}
              <div class="history-chart">
                <svg viewBox="0 0 240 68" aria-hidden="true">
                  <path d={verticalRatePath} stroke="#ffbf5d" />
                </svg>
              </div>
            {:else}
              <p class="chart-empty">Waiting for more climb rate samples.</p>
            {/if}
          </article>
        </div>

        <div class="history-meta">
          <div>
            <span class="history-label">Window</span>
            <strong class="history-value">{formatHistoryDuration(historySamples)}</strong>
          </div>
          <div>
            <span class="history-label">Start point</span>
            <strong class="history-value">
              {trailStart ? formatCoordinates(trailStart.latitude, trailStart.longitude) : "Unknown"}
            </strong>
          </div>
          <div>
            <span class="history-label">Latest point</span>
            <strong class="history-value">
              {trailEnd ? formatCoordinates(trailEnd.latitude, trailEnd.longitude) : "Unknown"}
            </strong>
          </div>
        </div>
      {:else}
        <p class="empty-copy">Waiting for enough history to draw a usable telemetry profile.</p>
      {/if}
    </section>
  {:else}
    <p class="empty-copy">Click an aircraft marker to open a denser telemetry view.</p>
  {/if}
</section>

<style>
  .details-panel {
    display: grid;
    gap: 0.95rem;
  }

  .panel-heading,
  .identity-main,
  .section-header,
  .metric-card-header {
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

  .status-chip,
  .tag-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    padding: 0.34rem 0.7rem;
    font-size: 0.78rem;
    font-weight: 800;
  }

  .status-chip {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .identity-card,
  .annotation-panel,
  .history-panel,
  .telemetry-card,
  .data-card,
  .metric-card {
    border: 1px solid var(--surface-border);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.035);
  }

  .identity-card,
  .annotation-panel,
  .history-panel {
    display: grid;
    gap: 0.85rem;
    padding: 1rem;
  }

  .identity-main strong {
    display: block;
    font-size: 1.15rem;
    color: var(--color-text);
  }

  .identity-main p,
  .section-header span,
  .chart-empty,
  .empty-copy {
    color: var(--color-muted);
    font-size: 0.82rem;
  }

  .identity-actions,
  .history-actions,
  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    justify-content: flex-end;
  }

  .action-button,
  .tag-add-button,
  .history-action {
    border: 1px solid var(--surface-border);
    border-radius: 999px;
    padding: 0.68rem 0.9rem;
    font: inherit;
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
  }

  .action-button.active,
  .action-button.secondary.active {
    color: var(--button-primary-text);
    background: var(--button-primary-bg);
    border-color: transparent;
  }

  .route-strip {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    gap: 0.75rem;
    align-items: center;
  }

  .route-node {
    display: grid;
    gap: 0.18rem;
    padding: 0.85rem;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.03);
  }

  .route-node.current {
    border: 1px solid rgba(245, 185, 8, 0.28);
  }

  .route-label,
  .history-label,
  .notes-field span {
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-subtle);
  }

  .route-node strong,
  .data-card strong,
  .history-value {
    color: var(--color-text);
    font-size: 0.92rem;
  }

  .route-node small {
    font-size: 0.78rem;
    color: var(--color-muted);
  }

  .route-line {
    width: 100%;
    height: 2px;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(120, 200, 255, 0.35), rgba(245, 185, 8, 0.8));
  }

  .telemetry-grid,
  .data-grid,
  .chart-grid,
  .history-meta {
    display: grid;
    gap: 0.7rem;
  }

  .telemetry-grid,
  .data-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .telemetry-card,
  .data-card {
    display: grid;
    gap: 0.22rem;
    padding: 0.85rem 0.9rem;
  }

  .telemetry-card span,
  .data-card span,
  .metric-card-header span {
    font-size: 0.76rem;
    color: var(--color-muted);
  }

  .telemetry-card strong {
    color: var(--color-text);
    font-size: 1rem;
  }

  .telemetry-card small {
    font-size: 0.78rem;
    color: var(--color-subtle);
  }

  .notes-field,
  .tag-editor {
    display: grid;
    gap: 0.45rem;
  }

  .notes-field textarea,
  .notes-field input {
    border: 1px solid var(--surface-border);
    border-radius: 14px;
    padding: 0.78rem 0.85rem;
    font: inherit;
    color: var(--color-text);
    background: var(--surface-input-bg);
  }

  .tag-editor {
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: end;
  }

  .tag-chip {
    border: 1px solid rgba(245, 185, 8, 0.24);
    color: #f7db7a;
    background: rgba(245, 185, 8, 0.08);
    cursor: pointer;
  }

  .metric-card {
    display: grid;
    gap: 0.55rem;
    padding: 0.85rem;
  }

  .metric-card-header strong {
    font-size: 0.92rem;
    color: var(--color-text);
  }

  .history-chart {
    border-radius: 14px;
    padding: 0.55rem;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.015) 100%);
  }

  .history-chart svg {
    display: block;
    width: 100%;
    height: auto;
  }

  .history-chart path {
    fill: none;
    stroke-width: 3;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .history-meta {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .history-meta div {
    display: grid;
    gap: 0.18rem;
  }

  @media (max-width: 720px) {
    .panel-heading,
    .identity-main,
    .section-header,
    .metric-card-header {
      display: grid;
    }

    .route-strip,
    .telemetry-grid,
    .data-grid,
    .history-meta,
    .tag-editor {
      grid-template-columns: 1fr;
    }

    .route-line {
      height: 36px;
      width: 2px;
      justify-self: center;
      background: linear-gradient(180deg, rgba(120, 200, 255, 0.35), rgba(245, 185, 8, 0.8));
    }

    .identity-actions,
    .history-actions {
      justify-content: flex-start;
    }
  }
</style>
