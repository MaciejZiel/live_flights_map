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
  export let onToggleFollow = () => {};
  export let onRetryDetails = () => {};

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

  $: observedDistanceKm = calculateObservedDistanceKm(trailPoints);
  $: averageObservedSpeed = trailPoints.length
    ? Math.round(
        trailPoints.reduce((total, point) => total + ((point.velocity ?? 0) * 3.6), 0) /
          trailPoints.length
      )
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
      <h2>{flight ? identity.callsign : "Flight inspector"}</h2>
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
            <p class="eyebrow">Selected flight</p>
            <h3>{routeLabel ?? identity.callsign}</h3>
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
          <button class="action-button secondary" type="button" on:click={onRetryDetails}>
            Refresh
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
        <span>Last contact</span>
        <strong>{formatRelativeContact(flight.last_contact)}</strong>
      </article>
      <article class="data-card">
        <span>Live track</span>
        <strong>{trailPoints.length ? `${trailPoints.length} pts / ${observedDistanceKm.toFixed(1)} km` : "Waiting for trail"}</strong>
      </article>
      <article class="data-card">
        <span>Country</span>
        <strong>{identity.originCountry ?? "Unknown"}</strong>
      </article>
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
  .telemetry-card,
  .data-card,
  .detail-warning {
    border: 1px solid var(--surface-border);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.03);
  }

  .hero-card {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.78rem;
    padding: 0.78rem;
  }

  .photo-shell {
    display: grid;
    gap: 0.6rem;
  }

  .photo-shell img,
  .photo-placeholder {
    width: 100%;
    aspect-ratio: 16 / 10;
    border-radius: 12px;
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
  .detail-warning {
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
    font-size: 1rem;
    color: var(--color-text);
  }

  .photo-placeholder small {
    color: var(--color-muted);
    font-size: 0.8rem;
  }

  .hero-copy {
    display: grid;
    gap: 0.7rem;
  }

  .hero-route {
    font-size: 1rem;
    font-weight: 700;
    color: var(--color-text);
  }

  .hero-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.45rem;
  }

  .hero-meta span {
    padding: 0.62rem 0.7rem;
    border-radius: 10px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(255, 255, 255, 0.03);
    color: var(--color-text);
    font-size: 0.78rem;
    font-weight: 600;
  }

  .identity-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .action-button {
    border: 1px solid var(--surface-border);
    border-radius: 999px;
    padding: 0.56rem 0.8rem;
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
  .route-panel {
    display: grid;
    gap: 0.72rem;
    padding: 0.82rem;
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
    padding: 0.72rem;
    border-radius: 12px;
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
  .data-grid {
    display: grid;
    gap: 0.55rem;
  }

  .telemetry-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .data-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .data-grid.compact {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .telemetry-card,
  .data-card {
    display: grid;
    gap: 0.22rem;
    padding: 0.72rem 0.76rem;
  }

  .telemetry-card strong {
    color: var(--color-text);
    font-size: 1rem;
  }

  .telemetry-card small {
    font-size: 0.78rem;
    color: var(--color-subtle);
  }

  @media (max-width: 720px) {
    .panel-heading,
    .hero-headline,
    .section-header {
      display: grid;
    }

    .hero-card,
    .route-strip,
    .telemetry-grid,
    .data-grid,
    .data-grid.compact,
    .hero-meta {
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
