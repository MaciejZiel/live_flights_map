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

    let distance = 0;

    for (let index = 1; index < points.length; index += 1) {
      const previous = points[index - 1];
      const current = points[index];
      distance += calculateGreatCircleDistanceKm(
        previous.latitude,
        previous.longitude,
        current.latitude,
        current.longitude
      );
    }

    return distance;
  }

  function calculateGreatCircleDistanceKm(startLatitude, startLongitude, endLatitude, endLongitude) {
    if (
      !Number.isFinite(startLatitude) ||
      !Number.isFinite(startLongitude) ||
      !Number.isFinite(endLatitude) ||
      !Number.isFinite(endLongitude)
    ) {
      return 0;
    }

    const earthRadiusKm = 6371;
    const toRadians = (value) => (value * Math.PI) / 180;
    const deltaLatitude = toRadians(endLatitude - startLatitude);
    const deltaLongitude = toRadians(endLongitude - startLongitude);
    const normalizedStartLatitude = toRadians(startLatitude);
    const normalizedEndLatitude = toRadians(endLatitude);
    const haversine =
      Math.sin(deltaLatitude / 2) ** 2 +
      Math.cos(normalizedStartLatitude) *
        Math.cos(normalizedEndLatitude) *
        Math.sin(deltaLongitude / 2) ** 2;

    return 2 * earthRadiusKm * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
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

  function calculateRouteProgress(routeData, flightData) {
    const origin = routeData?.origin;
    const destination = routeData?.destination;
    if (
      !Number.isFinite(origin?.latitude) ||
      !Number.isFinite(origin?.longitude) ||
      !Number.isFinite(destination?.latitude) ||
      !Number.isFinite(destination?.longitude) ||
      !Number.isFinite(flightData?.latitude) ||
      !Number.isFinite(flightData?.longitude)
    ) {
      return null;
    }

    const totalKm = calculateGreatCircleDistanceKm(
      origin.latitude,
      origin.longitude,
      destination.latitude,
      destination.longitude
    );
    if (!totalKm) {
      return null;
    }

    const coveredKm = calculateGreatCircleDistanceKm(
      origin.latitude,
      origin.longitude,
      flightData.latitude,
      flightData.longitude
    );
    const percentage = Math.max(0, Math.min(100, Math.round((coveredKm / totalKm) * 100)));

    return {
      coveredKm: Math.round(coveredKm),
      remainingKm: Math.max(0, Math.round(totalKm - coveredKm)),
      percentage,
      totalKm: Math.round(totalKm),
    };
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
  $: routeProgress = calculateRouteProgress(route, flight);
  $: routeStatusText = route?.plausible === false
    ? "Route unverified"
    : route
      ? "Route resolved"
      : ["loading", "refreshing"].includes(detailsStatus)
        ? "Resolving route"
        : "Live track";
</script>

<section class="panel details-panel">
  <div class="panel-heading">
    <div>
      <p class="eyebrow">{routeLabel ? "Selected route" : "Selected aircraft"}</p>
      <h2>{flight ? identity.callsign : "Flight inspector"}</h2>
    </div>
    {#if flight}
      <span class="route-badge panel-badge">{routeStatusText}</span>
    {/if}
  </div>

  {#if flight}
    <section class="hero-card">
      <div class="photo-shell">
        <div class="photo-visual">
          {#if photoUrl}
            {#if photo?.link}
              <a class="photo-link" href={photo.link} rel="noreferrer" target="_blank">
                <img alt={`Photo of ${identity.registration ?? identity.icao24}`} src={photoUrl} />
              </a>
            {:else}
              <img alt={`Photo of ${identity.registration ?? identity.icao24}`} src={photoUrl} />
            {/if}
          {:else}
            <div class:loading={detailsStatus === "loading" || detailsStatus === "refreshing"} class="photo-placeholder">
              <span>{detailsStatus === "loading" || detailsStatus === "refreshing" ? "Resolving aircraft" : "Photo unavailable"}</span>
              <strong>{identity.registration ?? identity.icao24}</strong>
              <small>{identity.typeCode ?? "Type unknown"}</small>
            </div>
          {/if}

          <div class="photo-overlay">
            <div class="photo-badge-row">
              <span class="status-chip overlay-chip">{formatFlightStatus(flight)}</span>
              {#if routeFlightNumber}
                <span class="route-badge">{routeFlightNumber}</span>
              {/if}
            </div>

            <div class="photo-copy">
              <p class="eyebrow">Live route</p>
              <h3>{routeLabel ?? identity.callsign}</h3>
              <p class="hero-subtitle">{routeVerbose ?? `${identity.originCountry ?? "Unknown country"} · ICAO24 ${identity.icao24}`}</p>
            </div>
          </div>
        </div>

        {#if photoUrl}
          <div class="photo-credit">
            <span>{photo?.source ?? "photo"}</span>
            <strong>{photo?.photographer ?? "Unknown photographer"}</strong>
          </div>
        {/if}
      </div>

      <div class="hero-copy">
        <div class="hero-meta">
          <span>{identity.registration ?? "Registration n/a"}</span>
          <span>{identity.typeCode ?? "Type n/a"}</span>
          <span>{identity.operatorCode !== "N/A" ? `Operator ${identity.operatorCode}` : identity.originCountry ?? "Country n/a"}</span>
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

        <div class="route-summary">
          <span>{route?.iata_codes ?? route?.airport_codes ?? "Route lookup pending"}</span>
          <strong>{routeStops.length ? `${routeStops.length} stop${routeStops.length > 1 ? "s" : ""}` : routeStatusText}</strong>
        </div>

        {#if routeProgress}
          <div class="route-progress">
            <div class="route-progress-header">
              <span>{formatAirportCode(route?.origin)}</span>
              <strong>{routeProgress.percentage}%</strong>
              <span>{formatAirportCode(route?.destination)}</span>
            </div>

            <div aria-hidden="true" class="route-progress-bar">
              <span class="route-progress-fill" style={`width: ${routeProgress.percentage}%`}></span>
              <span class="route-progress-marker" style={`left: calc(${routeProgress.percentage}% - 0.5rem)`}></span>
            </div>

            <div class="route-progress-meta">
              <span>{routeProgress.coveredKm} km covered</span>
              <span>{routeProgress.remainingKm} km left</span>
            </div>
          </div>
        {/if}

        <div class="identity-actions">
          <button class:active={followAircraft} class="action-button" type="button" on:click={onToggleFollow}>
            {followAircraft ? "Following on map" : "Track on map"}
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

    <section class="facts-panel">
      <div class="facts-header">
        <strong>Live facts</strong>
        <span>{route?.plausible === false ? "route unverified" : route ? "route resolved" : "route pending"}</span>
      </div>

      <div class="fact-list">
        <div class="fact-row">
          <span>Flight number</span>
          <strong>{routeFlightNumber || identity.callsign}</strong>
        </div>
        <div class="fact-row">
          <span>Registration</span>
          <strong>{identity.registration ?? "Unknown"}</strong>
        </div>
        <div class="fact-row">
          <span>Type code</span>
          <strong>{identity.typeCode ?? "Unknown"}</strong>
        </div>
        <div class="fact-row">
          <span>ICAO24</span>
          <strong>{identity.icao24}</strong>
        </div>
        <div class="fact-row">
          <span>Current position</span>
          <strong>{formatCoordinates(flight.latitude, flight.longitude)}</strong>
        </div>
        <div class="fact-row">
          <span>Last contact</span>
          <strong>{formatRelativeContact(flight.last_contact)}</strong>
        </div>
        <div class="fact-row">
          <span>Observed trail</span>
          <strong>{trailPoints.length ? `${trailPoints.length} pts / ${observedDistanceKm.toFixed(1)} km` : "Waiting for trail"}</strong>
        </div>
        <div class="fact-row">
          <span>Country</span>
          <strong>{identity.originCountry ?? "Unknown"}</strong>
        </div>
      </div>
    </section>
  {:else}
    <p class="empty-copy">Click an aircraft marker to open focused route and tracking details.</p>
  {/if}
</section>

<style>
  .details-panel {
    display: grid;
    gap: 0.9rem;
  }

  h2,
  h3,
  p {
    margin: 0;
  }

  .panel-heading,
  .facts-header {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
  }

  .eyebrow {
    margin: 0 0 0.18rem;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.17em;
    color: rgba(190, 203, 217, 0.62);
  }

  .status-chip,
  .route-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    padding: 0.34rem 0.68rem;
    font-size: 0.74rem;
    font-weight: 800;
  }

  .status-chip {
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  .route-badge {
    color: #f8de88;
    background: rgba(245, 185, 8, 0.12);
    border: 1px solid rgba(245, 185, 8, 0.22);
  }

  .panel-badge {
    align-self: center;
  }

  .hero-card,
  .telemetry-card,
  .detail-warning,
  .facts-panel {
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 16px;
    background:
      linear-gradient(180deg, rgba(31, 34, 39, 0.98) 0%, rgba(19, 21, 25, 0.98) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.02),
      0 14px 26px rgba(0, 0, 0, 0.2);
  }

  .hero-card {
    display: grid;
    gap: 0.8rem;
    padding: 0.78rem;
    overflow: hidden;
  }

  .photo-shell {
    display: grid;
    gap: 0.48rem;
  }

  .photo-visual {
    position: relative;
    overflow: hidden;
    border-radius: 13px;
    border: 1px solid rgba(255, 255, 255, 0.07);
    background: rgba(255, 255, 255, 0.04);
  }

  .photo-shell img,
  .photo-placeholder {
    width: 100%;
    aspect-ratio: 16 / 10;
  }

  .photo-shell img {
    display: block;
    object-fit: cover;
    background: rgba(255, 255, 255, 0.04);
  }

  .photo-link {
    display: block;
  }

  .photo-overlay {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    display: grid;
    gap: 0.52rem;
    padding: 1rem 0.9rem 0.82rem;
    background:
      linear-gradient(180deg, rgba(6, 7, 10, 0) 0%, rgba(7, 8, 11, 0.82) 42%, rgba(7, 8, 11, 0.96) 100%);
  }

  .photo-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
  }

  .overlay-chip {
    background: rgba(255, 211, 79, 0.95);
  }

  .photo-copy {
    display: grid;
    gap: 0.2rem;
  }

  .photo-copy h3 {
    font-size: 1.18rem;
    line-height: 1.1;
  }

  .photo-credit,
  .detail-warning {
    display: grid;
    gap: 0.15rem;
  }

  .photo-credit span,
  .hero-subtitle,
  .detail-warning span,
  .empty-copy,
  .facts-header span,
  .route-node p,
  .telemetry-card small {
    color: rgba(190, 203, 217, 0.74);
    font-size: 0.78rem;
  }

  .photo-credit strong,
  .photo-copy h3,
  .route-node strong,
  .telemetry-card strong,
  .fact-row strong,
  .facts-header strong {
    color: var(--color-text);
  }

  .photo-placeholder {
    display: grid;
    align-content: center;
    gap: 0.3rem;
    padding: 0.95rem;
    background:
      radial-gradient(circle at top, rgba(245, 185, 8, 0.2), transparent 58%),
      linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02));
  }

  .photo-placeholder.loading {
    border: 1px solid rgba(245, 185, 8, 0.2);
  }

  .photo-placeholder span,
  .route-label,
  .telemetry-card span,
  .fact-row span,
  .facts-header span {
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }

  .photo-placeholder span,
  .route-label,
  .telemetry-card span,
  .fact-row span {
    font-size: 0.7rem;
    color: rgba(171, 186, 202, 0.56);
  }

  .photo-placeholder strong {
    font-size: 1rem;
  }

  .photo-placeholder small {
    color: rgba(190, 203, 217, 0.72);
    font-size: 0.78rem;
  }

  .hero-copy {
    display: grid;
    gap: 0.72rem;
  }

  .hero-meta {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.42rem;
  }

  .hero-meta span,
  .route-summary {
    padding: 0.62rem 0.7rem;
    border-radius: 11px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(255, 255, 255, 0.03);
  }

  .hero-meta span {
    color: var(--color-text);
    font-size: 0.77rem;
    font-weight: 600;
  }

  .route-summary {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: center;
    color: rgba(190, 203, 217, 0.72);
    font-size: 0.76rem;
  }

  .route-summary strong {
    color: #f8de88;
    font-size: 0.8rem;
  }

  .route-progress {
    display: grid;
    gap: 0.42rem;
    padding: 0.72rem 0.76rem;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.06);
    background: rgba(255, 255, 255, 0.03);
  }

  .route-progress-header,
  .route-progress-meta {
    display: flex;
    justify-content: space-between;
    gap: 0.65rem;
    align-items: center;
  }

  .route-progress-header span,
  .route-progress-meta span {
    font-size: 0.72rem;
    color: rgba(190, 203, 217, 0.72);
  }

  .route-progress-header span {
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }

  .route-progress-header strong {
    color: #f8de88;
    font-size: 0.82rem;
  }

  .route-progress-bar {
    position: relative;
    height: 0.42rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.08);
    overflow: hidden;
  }

  .route-progress-fill {
    position: absolute;
    inset: 0 auto 0 0;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(120, 200, 255, 0.7), rgba(245, 185, 8, 0.95));
  }

  .route-progress-marker {
    position: absolute;
    top: 50%;
    width: 1rem;
    height: 1rem;
    border-radius: 999px;
    border: 2px solid rgba(20, 23, 28, 0.98);
    background: #ffd34f;
    box-shadow: 0 0 0 3px rgba(255, 211, 79, 0.18);
    transform: translateY(-50%);
  }

  .route-strip {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    gap: 0.7rem;
    align-items: center;
  }

  .route-node {
    display: grid;
    gap: 0.18rem;
    padding: 0.74rem;
    border-radius: 13px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
  }

  .route-node.current {
    border-color: rgba(245, 185, 8, 0.26);
  }

  .route-node strong {
    font-size: 1.02rem;
  }

  .route-line {
    width: 100%;
    height: 2px;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(120, 200, 255, 0.34), rgba(245, 185, 8, 0.92));
  }

  .identity-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .action-button {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 0.56rem 0.86rem;
    font: inherit;
    font-weight: 700;
    color: var(--button-secondary-text);
    background: var(--button-secondary-bg);
    cursor: pointer;
    transition:
      border-color 160ms ease,
      background 160ms ease,
      transform 160ms ease;
  }

  .action-button:hover {
    transform: translateY(-1px);
    border-color: rgba(255, 211, 79, 0.2);
  }

  .action-button.active {
    color: var(--button-primary-text);
    background: var(--button-primary-bg);
    border-color: transparent;
  }

  .detail-warning,
  .facts-panel {
    padding: 0.82rem;
  }

  .detail-warning strong {
    color: #f8de88;
    font-size: 0.8rem;
  }

  .telemetry-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.5rem;
  }

  .telemetry-card {
    display: grid;
    gap: 0.2rem;
    padding: 0.72rem 0.76rem;
  }

  .telemetry-card strong {
    font-size: 0.96rem;
  }

  .facts-panel {
    display: grid;
    gap: 0.55rem;
  }

  .fact-list {
    display: grid;
  }

  .fact-row {
    display: flex;
    justify-content: space-between;
    gap: 0.9rem;
    align-items: baseline;
    padding: 0.7rem 0;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
  }

  .fact-row:first-child {
    border-top: 0;
    padding-top: 0.1rem;
  }

  .fact-row strong {
    font-size: 0.84rem;
    text-align: right;
  }

  @media (max-width: 720px) {
    .panel-heading,
    .facts-header,
    .route-summary {
      display: grid;
    }

    .hero-meta,
    .telemetry-grid,
    .route-strip {
      grid-template-columns: 1fr;
    }

    .route-line {
      width: 2px;
      height: 36px;
      justify-self: center;
      background: linear-gradient(180deg, rgba(120, 200, 255, 0.34), rgba(245, 185, 8, 0.92));
    }

    .fact-row {
      display: grid;
    }

    .fact-row strong {
      text-align: left;
    }
  }
</style>
