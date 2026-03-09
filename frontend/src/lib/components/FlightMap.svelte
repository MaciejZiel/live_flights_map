<script>
  import { createEventDispatcher, onMount } from "svelte";

  import L from "leaflet";
  import "leaflet.markercluster";

  import { syncAircraftMarkers } from "../map/aircraftMarkers.js";

  export let flights = [];
  export let selectedIcao24 = null;
  export let followAircraft = false;
  export let mapStyle = "standard";
  export let trailPoints = [];
  export let watchedIcao24s = [];
  export let watchModeEnabled = false;
  export let initialViewport = null;
  export let fullscreenRequestId = 0;
  export let viewPresetRequest = null;

  const dispatch = createEventDispatcher();
  let shell;
  let container;
  let map;
  let activeBaseLayer;
  let activeMapStyle = null;
  let aircraftLayer;
  let trailLayer;
  let motionVectorLayer;
  const markerRegistry = new Map();
  let isFullscreen = false;
  let lastFullscreenRequestId = 0;
  let lastViewPresetRequestId = 0;
  const viewPresets = {
    poland: [
      [49.0, 14.0],
      [55.1, 24.5],
    ],
    europe: [
      [35.0, -11.0],
      [71.0, 35.0],
    ],
    world: [
      [-60.0, -170.0],
      [78.0, 170.0],
    ],
  };

  function getCurrentAiracId(dateValue = new Date()) {
    const currentDate = new Date(dateValue);
    const cycleDate = new Date(2003, 0, 23);
    let currentYearCounter = 0;
    let previousYearCounter = 0;
    let targetYear = currentDate.getFullYear();

    while (cycleDate.getTime() < currentDate.getTime()) {
      if (cycleDate.getFullYear() === currentDate.getFullYear() - 1) {
        previousYearCounter += 1;
      }

      if (cycleDate.getFullYear() === currentDate.getFullYear()) {
        currentYearCounter += 1;
      }

      cycleDate.setDate(cycleDate.getDate() + 28);
    }

    if (currentYearCounter === 0) {
      targetYear -= 1;
      currentYearCounter = previousYearCounter;
    }

    return Number(`${String(targetYear).slice(2)}${String(currentYearCounter).padStart(2, "0")}`);
  }

  function createBasemapLayer(style) {
    const currentAirac = getCurrentAiracId();
    const commonOptions = {
      crossOrigin: true,
      maxZoom: 18,
    };

    if (style === "satellite") {
      return L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
          ...commonOptions,
          attribution: "Tiles &copy; Esri",
        }
      );
    }

    if (style === "dark") {
      return L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        ...commonOptions,
        subdomains: "abcd",
        attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
      });
    }

    if (style === "aviation") {
      const aviationBase = L.tileLayer(
        `https://nwy-tiles-api.prod.newaydata.com/tiles/{z}/{x}/{y}.jpg?path=${currentAirac}/base/latest`,
        {
          ...commonOptions,
          maxZoom: 13,
          attribution:
            "&copy; open flightmaps association, OpenStreetMap contributors, NASA elevation data",
        }
      );
      const aviationOverlay = L.tileLayer(
        `https://nwy-tiles-api.prod.newaydata.com/tiles/{z}/{x}/{y}.png?path=${currentAirac}/aero/latest`,
        {
          ...commonOptions,
          maxZoom: 13,
          opacity: 0.95,
          attribution:
            "&copy; open flightmaps association, OpenStreetMap contributors, NASA elevation data",
        }
      );

      return L.layerGroup([aviationBase, aviationOverlay]);
    }

    return L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      ...commonOptions,
      attribution: "&copy; OpenStreetMap contributors",
    });
  }

  function setBasemap(style) {
    if (!map || activeMapStyle === style) {
      return;
    }

    if (activeBaseLayer) {
      map.removeLayer(activeBaseLayer);
    }

    activeBaseLayer = createBasemapLayer(style);
    activeBaseLayer.addTo(map);
    activeMapStyle = style;
  }

  function emitBounds() {
    if (!map) {
      return;
    }

    const bounds = map.getBounds();
    dispatch("boundschange", {
      bbox: {
        lamin: bounds.getSouth(),
        lamax: bounds.getNorth(),
        lomin: bounds.getWest(),
        lomax: bounds.getEast(),
      },
    });

    const center = map.getCenter();
    dispatch("viewportchange", {
      viewport: {
        center: [center.lat, center.lng],
        zoom: map.getZoom(),
      },
    });
  }

  function centerOnSelectedAircraft() {
    if (!map || !followAircraft || !selectedIcao24) {
      return;
    }

    const selectedFlight = flights.find((flight) => flight.icao24 === selectedIcao24);
    if (!selectedFlight) {
      return;
    }

    map.panTo([selectedFlight.latitude, selectedFlight.longitude], {
      animate: true,
      duration: 1,
    });
  }

  function syncFullscreenState() {
    isFullscreen = document.fullscreenElement === shell;

    if (map) {
      map.invalidateSize();
    }
  }

  async function toggleFullscreen() {
    if (!shell) {
      return;
    }

    if (document.fullscreenElement === shell) {
      await document.exitFullscreen();
      return;
    }

    await shell.requestFullscreen();
  }

  function applyViewPreset(presetKey) {
    if (!map || !viewPresets[presetKey]) {
      return;
    }

    map.fitBounds(viewPresets[presetKey], {
      padding: [24, 24],
      animate: true,
      duration: 1,
    });
  }

  function projectPoint(latitude, longitude, bearingDegrees, distanceMeters) {
    const earthRadiusMeters = 6371000;
    const angularDistance = distanceMeters / earthRadiusMeters;
    const bearing = (bearingDegrees * Math.PI) / 180;
    const startLatitude = (latitude * Math.PI) / 180;
    const startLongitude = (longitude * Math.PI) / 180;

    const projectedLatitude = Math.asin(
      Math.sin(startLatitude) * Math.cos(angularDistance) +
        Math.cos(startLatitude) * Math.sin(angularDistance) * Math.cos(bearing)
    );

    const projectedLongitude =
      startLongitude +
      Math.atan2(
        Math.sin(bearing) * Math.sin(angularDistance) * Math.cos(startLatitude),
        Math.cos(angularDistance) - Math.sin(startLatitude) * Math.sin(projectedLatitude)
      );

    return [
      (projectedLatitude * 180) / Math.PI,
      (projectedLongitude * 180) / Math.PI,
    ];
  }

  function syncTrailLayer() {
    if (!map) {
      return;
    }

    if (trailLayer) {
      map.removeLayer(trailLayer);
      trailLayer = null;
    }

    if (!trailPoints || trailPoints.length < 2) {
      return;
    }

    trailLayer = L.polyline(
      trailPoints.map((point) => [point.latitude, point.longitude]),
      {
        color: "#c46a17",
        weight: 3,
        opacity: 0.85,
        dashArray: "8 6",
        lineCap: "round",
      }
    ).addTo(map);
  }

  function syncMotionVectorLayer() {
    if (!map) {
      return;
    }

    if (motionVectorLayer) {
      map.removeLayer(motionVectorLayer);
      motionVectorLayer = null;
    }

    if (!selectedIcao24) {
      return;
    }

    const selectedFlight = flights.find((flight) => flight.icao24 === selectedIcao24);
    if (
      !selectedFlight ||
      selectedFlight.on_ground ||
      selectedFlight.velocity === null ||
      selectedFlight.velocity === undefined ||
      selectedFlight.true_track === null ||
      selectedFlight.true_track === undefined
    ) {
      return;
    }

    const projectedPoint = projectPoint(
      selectedFlight.latitude,
      selectedFlight.longitude,
      selectedFlight.true_track,
      selectedFlight.velocity * 120
    );

    motionVectorLayer = L.layerGroup([
      L.polyline(
        [
          [selectedFlight.latitude, selectedFlight.longitude],
          projectedPoint,
        ],
        {
          color: "#4bb7f5",
          weight: 3,
          opacity: 0.9,
          dashArray: "10 8",
        }
      ),
      L.circleMarker(projectedPoint, {
        radius: 5,
        weight: 2,
        color: "#dff6ff",
        fillColor: "#4bb7f5",
        fillOpacity: 0.95,
      }),
    ]).addTo(map);
  }

  onMount(() => {
    const initialCenter = initialViewport?.center ?? [52.15, 19.4];
    const initialZoom = initialViewport?.zoom ?? 6;

    map = L.map(container, {
      zoomControl: true,
      minZoom: 4,
      preferCanvas: true,
    }).setView(initialCenter, initialZoom);

    setBasemap(mapStyle);

    aircraftLayer = L.markerClusterGroup({
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      removeOutsideVisibleBounds: true,
      disableClusteringAtZoom: 9,
      maxClusterRadius: 42,
      iconCreateFunction(cluster) {
        return L.divIcon({
          html: `<span>${cluster.getChildCount()}</span>`,
          className: "aircraft-cluster",
          iconSize: [42, 42],
        });
      },
    }).addTo(map);
    syncAircraftMarkers(aircraftLayer, markerRegistry, flights);
    map.on("moveend zoomend", emitBounds);
    document.addEventListener("fullscreenchange", syncFullscreenState);
    emitBounds();

    return () => {
      map.off("moveend zoomend", emitBounds);
      document.removeEventListener("fullscreenchange", syncFullscreenState);
      map.remove();
      activeBaseLayer = null;
      activeMapStyle = null;
      trailLayer = null;
      motionVectorLayer = null;
      markerRegistry.clear();
    };
  });

  $: if (aircraftLayer) {
    syncAircraftMarkers(
      aircraftLayer,
      markerRegistry,
      flights,
      selectedIcao24,
      new Set(watchedIcao24s),
      watchModeEnabled,
      (flight) => {
      dispatch("select", { flight });
      }
    );
  }

  $: if (map) {
    setBasemap(mapStyle);
  }

  $: if (
    map &&
    fullscreenRequestId &&
    fullscreenRequestId !== lastFullscreenRequestId
  ) {
    lastFullscreenRequestId = fullscreenRequestId;
    toggleFullscreen();
  }

  $: if (
    map &&
    viewPresetRequest?.id &&
    viewPresetRequest.id !== lastViewPresetRequestId
  ) {
    lastViewPresetRequestId = viewPresetRequest.id;
    applyViewPreset(viewPresetRequest.presetKey);
  }

  $: syncTrailLayer();
  $: syncMotionVectorLayer();

  $: centerOnSelectedAircraft();
</script>

<div bind:this={shell} class:fullscreen={isFullscreen} class="map-shell">
  <div class="map-toolbar">
    <div class="preset-group">
      <button
        class="map-action preset-button"
        type="button"
        title="Jump to the Poland tracking view"
        on:click={() => applyViewPreset("poland")}
      >
        Poland
      </button>
      <button
        class="map-action preset-button"
        type="button"
        title="Jump to the Europe tracking view"
        on:click={() => applyViewPreset("europe")}
      >
        Europe
      </button>
      <button
        class="map-action preset-button"
        type="button"
        title="Jump to the global tracking view"
        on:click={() => applyViewPreset("world")}
      >
        World
      </button>
    </div>

  <button
    class="map-action fullscreen-toggle"
    type="button"
    title="Toggle fullscreen radar view"
    on:click={toggleFullscreen}
  >
    {#if isFullscreen}
      Exit fullscreen
    {:else}
      Fullscreen
    {/if}
  </button>
  </div>

  <div bind:this={container} class="map-root"></div>
</div>

<style>
  .map-shell {
    position: relative;
    width: 100%;
    height: 100%;
  }

  .map-shell.fullscreen {
    background: var(--fullscreen-background);
  }

  .map-root {
    width: 100%;
    height: 100%;
    min-height: 72vh;
  }

  .map-action {
    border: 0;
    border-radius: 999px;
    padding: 0.72rem 0.95rem;
    font: inherit;
    font-weight: 700;
    color: var(--button-primary-text);
    background: var(--map-ui-bg);
    box-shadow: 0 10px 20px rgba(18, 57, 93, 0.18);
    cursor: pointer;
    backdrop-filter: blur(6px);
  }

  .map-action:hover {
    background: var(--map-ui-bg-hover);
  }

  .map-toolbar {
    position: absolute;
    top: 1rem;
    left: 1rem;
    right: 1rem;
    z-index: 700;
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    pointer-events: none;
  }

  .preset-group,
  .fullscreen-toggle {
    pointer-events: auto;
  }

  .preset-group {
    display: flex;
    gap: 0.55rem;
    flex-wrap: wrap;
  }

  .preset-button {
    background: var(--button-secondary-bg);
    color: var(--button-secondary-text);
  }

  .preset-button:hover {
    filter: brightness(1.04);
  }

  @media (max-width: 720px) {
    .map-root {
      min-height: 78vh;
    }

    .map-toolbar {
      top: auto;
      bottom: 0.9rem;
      left: 0.75rem;
      right: 0.75rem;
      align-items: end;
    }

    .preset-group {
      max-width: min(68vw, 320px);
      overflow-x: auto;
      padding-bottom: 0.15rem;
    }

    .map-action {
      padding: 0.65rem 0.82rem;
      font-size: 0.86rem;
      white-space: nowrap;
    }
  }

  :global(.leaflet-container) {
    font-family:
      "IBM Plex Sans",
      system-ui,
      sans-serif;
    background: var(--map-background);
  }

  :global(.leaflet-popup-content) {
    margin: 0.9rem 1rem;
    line-height: 1.45;
  }

  :global(.aircraft-icon-shell) {
    background: transparent;
    border: 0;
  }

  :global(.aircraft-cluster) {
    display: grid;
    place-items: center;
    border-radius: 50%;
    color: #f7fbff;
    font-weight: 800;
    background:
      radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.22), transparent 35%),
      linear-gradient(135deg, #12395d 0%, #2d6c98 100%);
    box-shadow:
      0 12px 22px rgba(18, 57, 93, 0.24),
      inset 0 0 0 4px rgba(255, 255, 255, 0.16);
  }

  :global(.aircraft-cluster span) {
    transform: translateY(1px);
  }

  :global(.aircraft-icon) {
    width: 30px;
    height: 30px;
    filter: drop-shadow(0 8px 12px rgba(18, 57, 93, 0.3));
    transform-origin: center;
  }

  @media (max-width: 960px) {
    .map-toolbar {
      flex-direction: column;
      align-items: flex-start;
    }

    .map-root {
      min-height: 60vh;
    }
  }
</style>
