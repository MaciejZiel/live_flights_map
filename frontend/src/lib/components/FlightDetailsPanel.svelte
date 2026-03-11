<script>
  import InfoGlyph from "./InfoGlyph.svelte";

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
  export let bookmarked = false;
  export let liveStatus = "Live";
  export let snapshotFreshness = "waiting";
  export let snapshotConfidence = "High";
  export let snapshotTransport = "Polling";
  export let detailFreshness = "waiting";
  export let isReplayActive = false;
  export let shareFeedback = "";
  export let onToggleFollow = () => {};
  export let onToggleBookmark = () => {};
  export let onOpenAirport = () => {};
  export let onRetryDetails = () => {};
  export let onShare = () => {};
  export let onOpenTracking = () => {};
  export let onAddAlert = () => {};
  export let onClose = () => {};

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

  function canOpenAirport(airport) {
    return Boolean(airport?.iata || airport?.icao || airport?.entity_key);
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
  $: operatorLabel =
    route?.airline_name ??
    route?.airline_code ??
    (identity.operatorCode !== "N/A" ? identity.operatorCode : identity.originCountry ?? "Unknown");
  $: heroSummaryItems = [
    {
      label: "Flight",
      value: routeFlightNumber || identity.callsign,
      hint: route?.iata_codes ?? route?.airport_codes ?? "Callsign focus",
      icon: "flight",
    },
    {
      label: "Aircraft",
      value: identity.typeCode ?? "Type n/a",
      hint: identity.registration ?? identity.icao24,
      icon: "aircraft",
    },
    {
      label: "Operator",
      value: operatorLabel,
      hint: identity.originCountry ?? "Origin unknown",
      icon: "operator",
    },
  ];
  $: heroMetricItems = flight
    ? [
        {
          label: "Altitude",
          value: formatAltitude(flight.altitude),
          hint: getVerticalTrendLabel(flight.vertical_rate),
          icon: "altitude",
        },
        {
          label: "Speed",
          value: formatSpeed(flight.velocity),
          hint: averageObservedSpeed ? `avg ${averageObservedSpeed} km/h` : "Live groundspeed",
          icon: "speed",
        },
        {
          label: "Heading",
          value: formatHeading(flight.true_track),
          hint: getTrackLabel(flight.true_track),
          icon: "heading",
        },
        {
          label: "Vertical rate",
          value: formatVerticalRate(flight.vertical_rate),
          hint: trailPoints.length ? `${trailPoints.length} trail points` : "Trail warming up",
          icon: "vertical",
        },
      ]
    : [];
  $: routeStatusText = route?.plausible === false
    ? "Route unverified"
    : route
      ? "Route resolved"
      : ["loading", "refreshing"].includes(detailsStatus)
        ? "Resolving route"
        : "Live track";
  $: dataQualitySummary = detailWarning
    ? "Guarded"
    : detailsStatus === "loading" || detailsStatus === "refreshing"
      ? "Syncing"
      : isReplayActive
        ? "Replay"
        : snapshotConfidence;
</script>

<section class="panel details-panel">
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
            <div class="photo-overlay-head">
              <div class="photo-badge-row">
                <span class="status-chip overlay-chip">{formatFlightStatus(flight)}</span>
                {#if routeFlightNumber}
                  <span class="route-badge">{routeFlightNumber}</span>
                {/if}
                <span class="route-badge">{routeStatusText}</span>
              </div>

              <button class="hero-dismiss" type="button" aria-label="Close selected aircraft" on:click={onClose}>
                ×
              </button>
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
        <div class="hero-summary-grid">
          {#each heroSummaryItems as item}
            <article class="hero-summary-card">
              <div class="card-label">
                <span class="card-glyph"><InfoGlyph kind={item.icon} /></span>
                <span class="card-label-text">{item.label}</span>
              </div>
              <strong>{item.value}</strong>
              <small>{item.hint}</small>
            </article>
          {/each}
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

        <div class="hero-metric-grid">
          {#each heroMetricItems as item}
            <article class="hero-metric-card">
              <div class="card-label">
                <span class="card-glyph"><InfoGlyph kind={item.icon} /></span>
                <span class="card-label-text">{item.label}</span>
              </div>
              <strong>{item.value}</strong>
              <small>{item.hint}</small>
            </article>
          {/each}
        </div>

        <div class="identity-actions">
          <button class:active={followAircraft} class="action-button" type="button" on:click={onToggleFollow}>
            {followAircraft ? "Following on map" : "Track on map"}
          </button>
          <button class:active={bookmarked} class="action-button secondary" type="button" on:click={onToggleBookmark}>
            {bookmarked ? "Saved to workspace" : "Save flight"}
          </button>
          <button class="action-button secondary" type="button" on:click={onShare}>
            {shareFeedback || "Share"}
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

    <slot name="afterHero" />

    <div class="detail-section-stack">
      <details class="detail-section" open>
        <summary class="detail-section-summary">
          <div class="detail-section-title">
            <span class="detail-section-glyph"><InfoGlyph kind="flight" size={15} /></span>
            <div class="detail-section-copy">
              <span class="detail-section-kicker">Flight</span>
              <strong>{routeFlightNumber || identity.callsign}</strong>
            </div>
          </div>
          <small>{route?.plausible === false ? "route unverified" : route ? "route resolved" : "route pending"}</small>
        </summary>

        <div class="detail-section-body">
          <section class="facts-panel data-quality-panel">
            <div class="facts-header">
              <strong>Data quality</strong>
              <span>{dataQualitySummary}</span>
            </div>

            <div class="quality-grid">
              <article class="quality-card">
                <span>Radar mode</span>
                <strong>{isReplayActive ? "Replay frame" : liveStatus}</strong>
                <small>{routeStatusText}</small>
              </article>
              <article class="quality-card">
                <span>Snapshot age</span>
                <strong>{snapshotFreshness}</strong>
                <small>{snapshotConfidence} confidence</small>
              </article>
              <article class="quality-card">
                <span>Details sync</span>
                <strong>{detailFreshness}</strong>
                <small>{detailsStatus === "success" ? "Details ready" : detailsStatus === "error" ? "Fallback active" : "Resolving metadata"}</small>
              </article>
              <article class="quality-card">
                <span>Transport</span>
                <strong>{snapshotTransport}</strong>
                <small>{trailPoints.length ? `${trailPoints.length} trail points` : "Trail warming up"}</small>
              </article>
            </div>

            <div class="fact-list">
              <div class="fact-row">
                <span>Flight number</span>
                <strong>{routeFlightNumber || identity.callsign}</strong>
              </div>
              <div class="fact-row">
                <span>Operator</span>
                <strong>{operatorLabel}</strong>
              </div>
              <div class="fact-row">
                <span>Current position</span>
                <strong>{formatCoordinates(flight.latitude, flight.longitude)}</strong>
              </div>
              <div class="fact-row">
                <span>Last contact</span>
                <strong>{formatRelativeContact(flight.last_contact)}</strong>
              </div>
            </div>

            <div class="secondary-actions">
              <button class="secondary-action-button" type="button" on:click={onOpenTracking}>
                Open tracking
              </button>
              <button class="secondary-action-button" type="button" on:click={onAddAlert}>
                Add alert
              </button>
              <button class="secondary-action-button" type="button" on:click={onRetryDetails}>
                Refresh details
              </button>
            </div>
          </section>
        </div>
      </details>

      <details class="detail-section">
        <summary class="detail-section-summary">
          <div class="detail-section-title">
            <span class="detail-section-glyph"><InfoGlyph kind="aircraft" size={15} /></span>
            <div class="detail-section-copy">
              <span class="detail-section-kicker">Aircraft</span>
              <strong>{identity.registration ?? identity.icao24}</strong>
            </div>
          </div>
          <small>{identity.typeCode ?? "Type unknown"}</small>
        </summary>

        <div class="detail-section-body">
          <section class="facts-panel">
            <div class="fact-list">
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
                <span>Country</span>
                <strong>{identity.originCountry ?? "Unknown"}</strong>
              </div>
            </div>
          </section>
        </div>
      </details>

      <details class="detail-section">
        <summary class="detail-section-summary">
          <div class="detail-section-title">
            <span class="detail-section-glyph"><InfoGlyph kind="tracking" size={15} /></span>
            <div class="detail-section-copy">
              <span class="detail-section-kicker">Tracking</span>
              <strong>{trailPoints.length ? `${trailPoints.length} trail points` : "Live telemetry"}</strong>
            </div>
          </div>
          <small>{observedDistanceKm ? `${observedDistanceKm.toFixed(1)} km observed` : "Trail warming up"}</small>
        </summary>

        <div class="detail-section-body">
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
        </div>
      </details>

      <details class="detail-section">
        <summary class="detail-section-summary">
          <div class="detail-section-title">
            <span class="detail-section-glyph"><InfoGlyph kind="airports" size={15} /></span>
            <div class="detail-section-copy">
              <span class="detail-section-kicker">Airports</span>
              <strong>{route?.airports?.length ?? 0} route points</strong>
            </div>
          </div>
          <small>{routeStops.length ? `${routeStops.length} intermediate stop${routeStops.length > 1 ? "s" : ""}` : "Direct routing"}</small>
        </summary>

        <div class="detail-section-body">
          <section class="facts-panel airport-desks-panel">
            <div class="airport-desk-grid">
              {#if route?.origin}
                <button
                  class="airport-desk-card"
                  disabled={!canOpenAirport(route.origin)}
                  type="button"
                  on:click={() => onOpenAirport(route.origin)}
                >
                  <span>Origin board</span>
                  <strong>{formatAirportCode(route.origin)}</strong>
                  <small>{formatAirportName(route.origin)}</small>
                </button>
              {/if}

              {#if route?.destination}
                <button
                  class="airport-desk-card"
                  disabled={!canOpenAirport(route.destination)}
                  type="button"
                  on:click={() => onOpenAirport(route.destination)}
                >
                  <span>Destination board</span>
                  <strong>{formatAirportCode(route.destination)}</strong>
                  <small>{formatAirportName(route.destination)}</small>
                </button>
              {/if}
            </div>

            {#if routeStops.length}
              <div class="route-stops">
                <span>Intermediate stops</span>
                <div class="route-stop-list">
                  {#each routeStops as stop}
                    <button
                      class="route-stop-pill"
                      disabled={!canOpenAirport(stop)}
                      type="button"
                      on:click={() => onOpenAirport(stop)}
                    >
                      <strong>{formatAirportCode(stop)}</strong>
                      <small>{formatAirportName(stop)}</small>
                    </button>
                  {/each}
                </div>
              </div>
            {/if}
          </section>
        </div>
      </details>
    </div>
  {:else}
    <div class="panel-heading">
      <div>
        <p class="eyebrow">Selected aircraft</p>
        <h2>Flight inspector</h2>
      </div>
    </div>
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
    padding: 0.34rem 0.64rem;
    font-size: 0.72rem;
    font-weight: 800;
  }

  .status-chip {
    color: #f4f7fb;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .route-badge {
    color: rgba(244, 247, 251, 0.9);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }

  .hero-card,
  .telemetry-card,
  .detail-warning,
  .facts-panel {
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(19, 22, 28, 0.96) 0%, rgba(13, 15, 20, 0.98) 100%);
    box-shadow: 0 10px 22px rgba(0, 0, 0, 0.18);
  }

  .hero-card {
    display: grid;
    gap: 0.8rem;
    padding: 0.72rem;
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
      linear-gradient(180deg, rgba(6, 7, 10, 0) 0%, rgba(7, 8, 11, 0.7) 46%, rgba(7, 8, 11, 0.9) 100%);
  }

  .photo-overlay-head {
    display: flex;
    justify-content: space-between;
    gap: 0.65rem;
    align-items: start;
  }

  .photo-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
  }

  .hero-dismiss {
    border: 0;
    width: 2rem;
    height: 2rem;
    border-radius: 999px;
    font: inherit;
    font-size: 1.2rem;
    line-height: 1;
    color: #f4f7fb;
    background: rgba(7, 8, 11, 0.52);
    cursor: pointer;
  }

  .overlay-chip {
    background: rgba(255, 255, 255, 0.12);
  }

  .photo-copy {
    display: grid;
    gap: 0.2rem;
  }

  .photo-copy h3 {
    font-size: 1.32rem;
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
      radial-gradient(circle at top, rgba(120, 200, 255, 0.14), transparent 58%),
      linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.02));
  }

  .photo-placeholder.loading {
    border: 1px solid rgba(245, 185, 8, 0.2);
  }

  .photo-placeholder span,
  .route-label,
  .telemetry-card span,
  .fact-row span,
  .facts-header span,
  .quality-card span {
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .photo-placeholder span,
  .route-label,
  .telemetry-card span,
  .fact-row span,
  .facts-header span,
  .quality-card span {
    font-size: 0.68rem;
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

  .hero-summary-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.48rem;
  }

  .hero-summary-card,
  .route-summary {
    padding: 0.7rem 0.74rem;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.045);
  }

  .hero-summary-card {
    display: grid;
    gap: 0.18rem;
  }

  .card-label {
    display: flex;
    align-items: center;
    gap: 0.42rem;
  }

  .card-glyph {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1rem;
    height: 1rem;
    color: #f5b908;
  }

  .card-label-text {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(171, 186, 202, 0.56);
  }

  .hero-summary-card strong {
    color: var(--color-text);
    font-size: 1rem;
    line-height: 1.2;
  }

  .hero-summary-card small {
    color: rgba(190, 203, 217, 0.72);
    font-size: 0.76rem;
  }

  .hero-metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.48rem;
  }

  .hero-metric-card {
    display: grid;
    gap: 0.16rem;
    padding: 0.78rem 0.8rem;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background:
      linear-gradient(180deg, rgba(30, 34, 40, 0.98) 0%, rgba(18, 21, 26, 0.98) 100%);
  }

  .hero-metric-card strong {
    color: #f5f9fd;
    font-size: 1.1rem;
    line-height: 1.15;
  }

  .hero-metric-card small {
    color: rgba(190, 203, 217, 0.76);
    font-size: 0.75rem;
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
    color: #f2f6fb;
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
    color: #f2f6fb;
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
    background: linear-gradient(90deg, rgba(120, 200, 255, 0.7), rgba(120, 200, 255, 0.95));
  }

  .route-progress-marker {
    position: absolute;
    top: 50%;
    width: 1rem;
    height: 1rem;
    border-radius: 999px;
    border: 2px solid rgba(20, 23, 28, 0.98);
    background: #78c8ff;
    box-shadow: 0 0 0 3px rgba(120, 200, 255, 0.18);
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
    border-color: rgba(120, 200, 255, 0.26);
  }

  .route-node strong {
    font-size: 1.02rem;
  }

  .route-line {
    width: 100%;
    height: 2px;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(120, 200, 255, 0.24), rgba(120, 200, 255, 0.82));
  }

  .identity-actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.48rem;
  }

  .action-button {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    min-height: 2.55rem;
    padding: 0.58rem 0.72rem;
    font: inherit;
    font-size: 0.76rem;
    font-weight: 800;
    color: var(--button-secondary-text);
    background: rgba(255, 255, 255, 0.05);
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
    color: #f4f7fb;
    background: rgba(120, 200, 255, 0.18);
    border-color: rgba(120, 200, 255, 0.26);
  }

  .detail-warning,
  .facts-panel {
    padding: 0.82rem;
  }

  .detail-section-stack {
    display: grid;
    gap: 0.65rem;
  }

  .detail-section {
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(18, 21, 27, 0.98) 0%, rgba(12, 15, 19, 0.98) 100%);
    box-shadow: 0 10px 22px rgba(0, 0, 0, 0.16);
    overflow: hidden;
  }

  .detail-section[open] {
    background: linear-gradient(180deg, rgba(19, 22, 28, 0.98) 0%, rgba(13, 16, 21, 0.98) 100%);
  }

  .detail-section-summary {
    display: flex;
    justify-content: space-between;
    gap: 0.9rem;
    align-items: center;
    padding: 0.9rem 0.92rem;
    cursor: pointer;
    list-style: none;
    background: rgba(255, 255, 255, 0.03);
  }

  .detail-section-summary::-webkit-details-marker {
    display: none;
  }

  .detail-section-title {
    display: flex;
    align-items: start;
    gap: 0.55rem;
  }

  .detail-section-glyph {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1rem;
    height: 1rem;
    color: #f5b908;
    margin-top: 0.1rem;
  }

  .detail-section-copy {
    display: grid;
    gap: 0.14rem;
  }

  .detail-section-kicker {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(171, 186, 202, 0.56);
  }

  .detail-section-copy strong {
    color: #f5f7fb;
    font-size: 1.04rem;
  }

  .detail-section-summary small {
    color: rgba(190, 203, 217, 0.72);
    font-size: 0.76rem;
    text-align: right;
  }

  .detail-section-body {
    padding: 0 0.82rem 0.82rem;
  }

  .quality-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .quality-card {
    display: grid;
    gap: 0.2rem;
    padding: 0.8rem 0.82rem;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.045);
  }

  .quality-card strong {
    color: #f2f6fb;
    font-size: 1rem;
  }

  .quality-card small {
    color: rgba(190, 203, 217, 0.72);
    font-size: 0.76rem;
  }

  .detail-warning strong {
    color: #f2f6fb;
    font-size: 0.8rem;
  }

  .telemetry-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.52rem;
  }

  .telemetry-card {
    display: grid;
    gap: 0.24rem;
    padding: 0.82rem 0.82rem;
  }

  .telemetry-card strong {
    font-size: 1.08rem;
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
    padding: 0.82rem 0;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }

  .fact-row:first-child {
    border-top: 0;
    padding-top: 0.1rem;
  }

  .fact-row strong {
    font-size: 0.98rem;
    text-align: right;
  }

  .secondary-actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.48rem;
  }

  .secondary-action-button {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    min-height: 2.4rem;
    padding: 0.52rem 0.66rem;
    font: inherit;
    font-size: 0.74rem;
    font-weight: 700;
    color: rgba(226, 234, 242, 0.92);
    background: rgba(255, 255, 255, 0.04);
    cursor: pointer;
  }

  .airport-desks-panel,
  .airport-desk-grid,
  .route-stops,
  .route-stop-list {
    display: grid;
    gap: 0.6rem;
  }

  .airport-desk-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .airport-desk-card,
  .route-stop-pill {
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: inherit;
    background: rgba(255, 255, 255, 0.03);
    text-align: left;
    cursor: pointer;
  }

  .airport-desk-card {
    display: grid;
    gap: 0.18rem;
    padding: 0.78rem 0.82rem;
    border-radius: 14px;
  }

  .airport-desk-card span,
  .route-stops > span,
  .route-stop-pill small {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: rgba(180, 191, 203, 0.68);
  }

  .airport-desk-card strong,
  .route-stop-pill strong {
    color: #f5f7fb;
    font-size: 0.92rem;
  }

  .airport-desk-card small {
    font-size: 0.74rem;
    color: rgba(194, 203, 216, 0.74);
  }

  .route-stop-list {
    grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
  }

  .route-stop-pill {
    display: grid;
    gap: 0.16rem;
    padding: 0.66rem 0.72rem;
    border-radius: 12px;
  }

  .airport-desk-card:hover,
  .route-stop-pill:hover {
    border-color: rgba(255, 211, 79, 0.22);
  }

  .airport-desk-card:disabled,
  .route-stop-pill:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }

  @media (max-width: 720px) {
    .panel-heading,
    .facts-header,
    .route-summary {
      display: grid;
    }

    .hero-summary-grid,
    .hero-metric-grid,
    .telemetry-grid,
    .route-strip,
    .airport-desk-grid,
    .identity-actions,
    .secondary-actions {
      grid-template-columns: 1fr;
    }

    .detail-section-summary {
      display: grid;
    }

    .detail-section-summary small {
      text-align: left;
    }

    .route-line {
      width: 2px;
      height: 36px;
      justify-self: center;
      background: linear-gradient(180deg, rgba(120, 200, 255, 0.24), rgba(120, 200, 255, 0.82));
    }

    .fact-row {
      display: grid;
    }

    .fact-row strong {
      text-align: left;
    }
  }
</style>
