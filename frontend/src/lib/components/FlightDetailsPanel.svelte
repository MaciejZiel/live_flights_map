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
  export let details = null;
  export let detailsStatus = "idle";
  export let detailsError = null;
  export let followAircraft = false;
  export let trailPoints = [];
  export let isWatched = false;
  export let onToggleFollow = () => {};
  export let onToggleWatch = () => {};
  export let onRetryDetails = () => {};

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

  function formatAirportCode(airport) {
    return airport?.iata ?? airport?.icao ?? "Unknown";
  }

  function formatAirportName(airport) {
    return airport?.location ?? airport?.name ?? "Route not resolved";
  }

  function formatRouteLabel(route) {
    if (!route?.airports?.length) {
      return null;
    }

    return route.airports
      .map((airport) => airport.iata ?? airport.icao ?? airport.location ?? "?")
      .join(" -> ");
  }

  function formatRouteVerbose(route) {
    if (!route?.airports?.length) {
      return null;
    }

    return route.airports
      .map((airport) => airport.location ?? airport.name ?? airport.iata ?? "Unknown")
      .join(" -> ");
  }

  function formatFlightNumber(route) {
    return [route?.airline_code, route?.flight_number].filter(Boolean).join(" ");
  }

  function resolvePhotoUrl(photo) {
    return photo?.thumbnail_url ?? null;
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
  $: photo = details?.photo ?? null;
  $: route = details?.route ?? null;
  $: identity = {
    callsign: details?.aircraft?.callsign ?? flight?.callsign ?? "Unknown callsign",
    icao24: details?.aircraft?.icao24 ?? flight?.icao24 ?? "Unknown",
    registration: details?.aircraft?.registration ?? flight?.registration ?? null,
    typeCode: details?.aircraft?.type_code ?? flight?.type_code ?? null,
    originCountry: details?.aircraft?.origin_country ?? flight?.origin_country ?? null,
    operatorCode:
      details?.aircraft?.operator_code ?? deriveOperatorCode(details?.aircraft?.callsign ?? flight?.callsign),
  };
  $: routeLabel = formatRouteLabel(route);
  $: routeVerbose = formatRouteVerbose(route);
  $: routeFlightNumber = formatFlightNumber(route);
  $: routeStops = route?.stops ?? [];
  $: routeWarning = route?.plausible === false ? "Route is not fully verified yet." : null;
  $: detailWarning = detailsError ?? details?.meta?.warning ?? routeWarning ?? null;
  $: photoUrl = resolvePhotoUrl(photo);
</script>

<section class="panel details-panel">
  <div class="panel-heading">
    <div>
      <p class="eyebrow">Aircraft details</p>
      <h2>{flight ? "Focused tracking" : "Flight inspector"}</h2>
    </div>
    {#if flight}
      <span class="status-chip">{formatFlightStatus(flight)}</span>
    {/if}
  </div>

  {#if flight}
    <section class="hero-card">
      <div class="photo-shell">
        {#if photoUrl}
          {#if photo?.link}
            <a class="photo-link" href={photo.link} rel="noreferrer" target="_blank">
              <img alt={`Photo of ${identity.registration ?? identity.icao24}`} src={photoUrl} />
            </a>
          {:else}
            <img alt={`Photo of ${identity.registration ?? identity.icao24}`} src={photoUrl} />
          {/if}
          <div class="photo-credit">
            <span>{photo?.source ?? "photo"}</span>
            <strong>{photo?.photographer ?? "Unknown photographer"}</strong>
          </div>
        {:else}
          <div class:loading={detailsStatus === "loading" || detailsStatus === "refreshing"} class="photo-placeholder">
            <span>{detailsStatus === "loading" || detailsStatus === "refreshing" ? "Resolving aircraft" : "Photo unavailable"}</span>
            <strong>{identity.registration ?? identity.icao24}</strong>
            <small>{identity.typeCode ?? "Type unknown"}</small>
          </div>
        {/if}
      </div>

      <div class="hero-copy">
        <div class="hero-headline">
          <div>
            <p class="eyebrow">Selected aircraft</p>
            <h3>{identity.callsign}</h3>
          </div>
          {#if routeFlightNumber}
            <span class="route-badge">{routeFlightNumber}</span>
          {/if}
        </div>

        <p class="hero-route">{routeLabel ?? "Live track active. Route will appear when the lookup resolves."}</p>
        <p class="hero-subtitle">{routeVerbose ?? `${identity.originCountry ?? "Unknown country"} · ICAO24 ${identity.icao24}`}</p>

        <div class="hero-meta">
          <span>{identity.registration ?? "Registration n/a"}</span>
          <span>{identity.typeCode ?? "Type n/a"}</span>
          <span>{identity.operatorCode !== "N/A" ? `Operator ${identity.operatorCode}` : identity.originCountry ?? "Country n/a"}</span>
        </div>

        <div class="identity-actions">
          <button class:active={followAircraft} class="action-button" type="button" on:click={onToggleFollow}>
            {followAircraft ? "Following" : "Follow"}
          </button>
          <button class:active={isWatched} class="action-button secondary" type="button" on:click={onToggleWatch}>
            {isWatched ? "Watching" : "Watch"}
          </button>
          <button class="action-button secondary" type="button" on:click={onRetryDetails}>
            Refresh details
          </button>
        </div>
      </div>
    </section>

    {#if detailWarning}
      <section class="detail-warning">
        <strong>{detailsStatus === "error" ? "Detail lookup failed." : "Partial aircraft details."}</strong>
        <span>{detailWarning}</span>
      </section>
    {/if}

    <section class="route-panel">
      <div class="section-header">
        <div>
          <strong>Planned route</strong>
          <p>{routeLabel ?? "No route metadata from the current providers."}</p>
        </div>
        <span class="section-badge">{route?.plausible === false ? "Unverified" : route ? "Resolved" : "Pending"}</span>
      </div>

      <div class="route-strip">
        <article class="route-node">
          <span class="route-label">From</span>
          <strong>{formatAirportCode(route?.origin)}</strong>
          <p>{formatAirportName(route?.origin)}</p>
        </article>
        <div class="route-line" aria-hidden="true"></div>
        <article class="route-node current">
          <span class="route-label">To</span>
          <strong>{formatAirportCode(route?.destination)}</strong>
          <p>{formatAirportName(route?.destination)}</p>
        </article>
      </div>

      <div class="data-grid compact">
        <article class="data-card">
          <span>Flight number</span>
          <strong>{routeFlightNumber || identity.callsign}</strong>
        </article>
        <article class="data-card">
          <span>Stops</span>
          <strong>{routeStops.length ? routeStops.length : "Direct"}</strong>
        </article>
        <article class="data-card">
          <span>Route code</span>
          <strong>{route?.iata_codes ?? route?.airport_codes ?? "Unknown"}</strong>
        </article>
        <article class="data-card">
          <span>Current position</span>
          <strong>{formatCoordinates(flight.latitude, flight.longitude)}</strong>
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
        <strong>{identity.icao24}</strong>
      </article>
      <article class="data-card">
        <span>Registration</span>
        <strong>{identity.registration ?? "Unknown"}</strong>
      </article>
      <article class="data-card">
        <span>Type code</span>
        <strong>{identity.typeCode ?? "Unknown"}</strong>
      </article>
      <article class="data-card">
        <span>Country</span>
        <strong>{identity.originCountry ?? "Unknown"}</strong>
      </article>
      <article class="data-card">
        <span>Observed window</span>
        <strong>{formatHistoryDuration(trailPoints)}</strong>
      </article>
      <article class="data-card">
        <span>Last contact</span>
        <strong>{formatRelativeContact(flight.last_contact)}</strong>
      </article>
      <article class="data-card">
        <span>Observed distance</span>
        <strong>{observedDistanceKm ? `${observedDistanceKm.toFixed(1)} km` : "No movement yet"}</strong>
      </article>
      <article class="data-card">
        <span>Observed start</span>
        <strong>{trailStart ? formatCoordinates(trailStart.latitude, trailStart.longitude) : "No trail yet"}</strong>
      </article>
    </section>

    <section class="history-panel">
      <div class="section-header">
        <div>
          <strong>Live track</strong>
          <p>{historySamples.length} recent samples for this aircraft</p>
        </div>
        <span class="section-badge">{formatHistoryDuration(historySamples)}</span>
      </div>

      {#if altitudeSamples.length > 1}
        <div class="chart-grid">
          <article class="metric-card">
            <div class="metric-card-header">
              <span>Altitude profile</span>
              <strong>{formatAltitude(altitudeSamples[altitudeSamples.length - 1].altitude)}</strong>
            </div>
            <div class="history-chart">
              <svg aria-hidden="true" viewBox="0 0 240 68">
                <path d={altitudePath} stroke="#78c8ff" />
              </svg>
            </div>
          </article>

          <article class="metric-card">
            <div class="metric-card-header">
              <span>Speed profile</span>
              <strong>{speedSamples.length ? formatSpeed(speedSamples[speedSamples.length - 1].velocity) : "Unknown"}</strong>
            </div>
            {#if speedSamples.length > 1}
              <div class="history-chart">
                <svg aria-hidden="true" viewBox="0 0 240 68">
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
                {verticalRateSamples.length
                  ? formatVerticalRate(verticalRateSamples[verticalRateSamples.length - 1].vertical_rate)
                  : "Unknown"}
              </strong>
            </div>
            {#if verticalRateSamples.length > 1}
              <div class="history-chart">
                <svg aria-hidden="true" viewBox="0 0 240 68">
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
            <span class="history-label">Track start</span>
            <strong class="history-value">
              {trailStart ? formatHistoryTimestamp(trailStart.timestamp) : "Unknown"}
            </strong>
          </div>
          <div>
            <span class="history-label">Latest point</span>
            <strong class="history-value">
              {trailEnd ? formatHistoryTimestamp(trailEnd.timestamp) : "Unknown"}
            </strong>
          </div>
          <div>
            <span class="history-label">Current position</span>
            <strong class="history-value">{formatCoordinates(flight.latitude, flight.longitude)}</strong>
          </div>
        </div>
      {:else}
        <p class="empty-copy">Waiting for enough live samples to draw a meaningful track profile.</p>
      {/if}
    </section>
  {:else}
    <p class="empty-copy">Click an aircraft marker to open focused route and tracking details.</p>
  {/if}
</section>

<style>
  .details-panel {
    display: grid;
    gap: 0.95rem;
  }

  .panel-heading,
  .hero-headline,
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
  h3,
  p {
    margin: 0;
  }

  .status-chip,
  .route-badge,
  .section-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    padding: 0.34rem 0.7rem;
    font-size: 0.76rem;
    font-weight: 800;
  }

  .status-chip {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .route-badge,
  .section-badge {
    color: #f7db7a;
    background: rgba(245, 185, 8, 0.12);
    border: 1px solid rgba(245, 185, 8, 0.18);
  }

  .hero-card,
  .route-panel,
  .history-panel,
  .telemetry-card,
  .data-card,
  .metric-card,
  .detail-warning {
    border: 1px solid var(--surface-border);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.035);
  }

  .hero-card {
    display: grid;
    grid-template-columns: 148px minmax(0, 1fr);
    gap: 1rem;
    padding: 1rem;
  }

  .photo-shell {
    display: grid;
    gap: 0.6rem;
  }

  .photo-shell img,
  .photo-placeholder {
    width: 100%;
    aspect-ratio: 1 / 1;
    border-radius: 16px;
  }

  .photo-shell img {
    display: block;
    object-fit: cover;
    background: rgba(255, 255, 255, 0.04);
  }

  .photo-link {
    display: block;
  }

  .photo-credit,
  .hero-meta,
  .detail-warning,
  .history-meta div {
    display: grid;
    gap: 0.18rem;
  }

  .photo-credit span,
  .hero-subtitle,
  .detail-warning span,
  .chart-empty,
  .empty-copy,
  .section-header p {
    color: var(--color-muted);
    font-size: 0.82rem;
  }

  .photo-credit strong,
  .hero-headline h3,
  .route-node strong,
  .data-card strong,
  .history-value {
    color: var(--color-text);
  }

  .photo-placeholder {
    display: grid;
    align-content: center;
    gap: 0.35rem;
    padding: 0.9rem;
    background:
      radial-gradient(circle at top, rgba(245, 185, 8, 0.2), transparent 58%),
      linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02));
    text-align: left;
  }

  .photo-placeholder.loading {
    border: 1px solid rgba(245, 185, 8, 0.18);
  }

  .photo-placeholder span,
  .route-label,
  .history-label,
  .telemetry-card span,
  .data-card span,
  .metric-card-header span {
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-subtle);
  }

  .photo-placeholder strong {
    font-size: 1.15rem;
    color: var(--color-text);
  }

  .photo-placeholder small {
    color: var(--color-muted);
    font-size: 0.8rem;
  }

  .hero-copy {
    display: grid;
    gap: 0.85rem;
  }

  .hero-route {
    font-size: 1.12rem;
    font-weight: 700;
    color: var(--color-text);
  }

  .hero-meta {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .hero-meta span {
    padding: 0.72rem 0.78rem;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(255, 255, 255, 0.03);
    color: var(--color-text);
    font-size: 0.83rem;
    font-weight: 600;
  }

  .identity-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
  }

  .action-button {
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

  .detail-warning,
  .route-panel,
  .history-panel {
    display: grid;
    gap: 0.85rem;
    padding: 1rem;
  }

  .detail-warning strong {
    color: #f7db7a;
    font-size: 0.82rem;
  }

  .route-strip {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    gap: 0.75rem;
    align-items: center;
  }

  .route-node {
    display: grid;
    gap: 0.2rem;
    padding: 0.9rem;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.03);
  }

  .route-node.current {
    border: 1px solid rgba(245, 185, 8, 0.28);
  }

  .route-node p {
    color: var(--color-muted);
    font-size: 0.8rem;
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

  .telemetry-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .data-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .data-grid.compact {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .telemetry-card,
  .data-card {
    display: grid;
    gap: 0.22rem;
    padding: 0.85rem 0.9rem;
  }

  .telemetry-card strong {
    color: var(--color-text);
    font-size: 1rem;
  }

  .telemetry-card small {
    font-size: 0.78rem;
    color: var(--color-subtle);
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

  @media (max-width: 720px) {
    .panel-heading,
    .hero-headline,
    .section-header,
    .metric-card-header {
      display: grid;
    }

    .hero-card,
    .route-strip,
    .telemetry-grid,
    .data-grid,
    .data-grid.compact,
    .hero-meta,
    .history-meta {
      grid-template-columns: 1fr;
    }

    .route-line {
      height: 36px;
      width: 2px;
      justify-self: center;
      background: linear-gradient(180deg, rgba(120, 200, 255, 0.35), rgba(245, 185, 8, 0.8));
    }
  }
</style>
