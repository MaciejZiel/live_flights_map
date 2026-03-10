<script>
  import { createEventDispatcher, onMount } from "svelte";

  import L from "leaflet";
  import "leaflet.markercluster";

  import { syncAircraftMarkers } from "../map/aircraftMarkers.js";

  export let flights = [];
  export let airports = [];
  export let selectedIcao24 = null;
  export let selectedAirportKey = null;
  export let selectedRouteAirports = [];
  export let followAircraft = false;
  export let mapStyle = "standard";
  export let trailPoints = [];
  export let watchedIcao24s = [];
  export let watchModeEnabled = false;
  export let dimmedIcao24s = [];
  export let showAirportMarkers = true;
  export let weatherLayerEnabled = false;
  export let initialViewport = null;
  export let fullscreenRequestId = 0;
  export let viewPresetRequest = null;
  export let focusRequest = null;

  const dispatch = createEventDispatcher();
  let shell;
  let container;
  let map;
  let activeBaseLayer;
  let activeMapStyle = null;
  let aircraftLayer;
  let airportLayer;
  let trailLayer;
  let motionVectorLayer;
  let routeLayer;
  let selectionLayer;
  let weatherLayer;
  let weatherFrame = null;
  let weatherRefreshTimer = null;
  const markerRegistry = new Map();
  const airportRegistry = new Map();
  let isFullscreen = false;
  let lastFullscreenRequestId = 0;
  let lastViewPresetRequestId = 0;
  let lastFocusRequestId = null;
  let lastRouteFocusKey = null;
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

    if (style === "light") {
      return L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        ...commonOptions,
        subdomains: "abcd",
        attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
      });
    }

    if (style === "terrain") {
      return L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        {
          ...commonOptions,
          attribution: "Tiles &copy; Esri",
        }
      );
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

    return L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
      ...commonOptions,
      subdomains: "abcd",
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
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

  function applyFocusRequest(request) {
    if (!map || !request) {
      return;
    }

    if (request.bounds?.length === 2) {
      map.flyToBounds(request.bounds, {
        animate: true,
        duration: 1.1,
        padding: [72, 72],
        maxZoom: request.maxZoom ?? 8.4,
      });
      return;
    }

    if (!request.center) {
      return;
    }

    map.flyTo(request.center, request.zoom ?? Math.max(map.getZoom(), 8.2), {
      animate: true,
      duration: 1.1,
    });
  }

  function handleMarkerElementClick(event) {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }

    const markerElement = target.closest("[data-icao24]");
    if (!(markerElement instanceof HTMLElement)) {
      return;
    }

    const icao24 = markerElement.dataset.icao24?.trim().toLowerCase();
    if (!icao24) {
      return;
    }

    const entry = markerRegistry.get(icao24);
    if (!entry?.flight) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    dispatch("select", { flight: entry.flight });
  }

  function findNearestFlightToClick(clickEvent) {
    if (!map || !flights?.length) {
      return null;
    }

    const clickPoint =
      clickEvent?.containerPoint ??
      (clickEvent?.originalEvent ? map.mouseEventToContainerPoint(clickEvent.originalEvent) : null);
    if (!clickPoint) {
      return null;
    }

    let bestMatch = null;
    let bestDistanceSquared = Infinity;
    const maxDistancePixels = 26;

    for (const flight of flights) {
      if (!Number.isFinite(flight?.latitude) || !Number.isFinite(flight?.longitude)) {
        continue;
      }

      const flightPoint = map.latLngToContainerPoint([flight.latitude, flight.longitude]);
      const dx = flightPoint.x - clickPoint.x;
      const dy = flightPoint.y - clickPoint.y;
      const distanceSquared = dx * dx + dy * dy;

      if (distanceSquared < bestDistanceSquared) {
        bestDistanceSquared = distanceSquared;
        bestMatch = flight;
      }
    }

    if (!bestMatch || bestDistanceSquared > maxDistancePixels ** 2) {
      return null;
    }

    return bestMatch;
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
          color: "#79cfff",
          weight: 2.5,
          opacity: 0.92,
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

  function syncSelectionLayer() {
    if (!map) {
      return;
    }

    if (selectionLayer) {
      map.removeLayer(selectionLayer);
      selectionLayer = null;
    }

    if (!selectedIcao24) {
      return;
    }

    const selectedFlight = flights.find((flight) => flight.icao24 === selectedIcao24);
    if (!selectedFlight) {
      return;
    }

    selectionLayer = L.layerGroup([
      L.circleMarker([selectedFlight.latitude, selectedFlight.longitude], {
        radius: 14,
        weight: 2.5,
        color: "#e6f6ff",
        fillOpacity: 0,
        opacity: 0.95,
      }),
      L.circleMarker([selectedFlight.latitude, selectedFlight.longitude], {
        radius: 22,
        weight: 1.4,
        color: "#86d2ff",
        fillOpacity: 0,
        opacity: 0.42,
        dashArray: "5 5",
      }),
    ]).addTo(map);
  }

  function getSelectedRouteAirports() {
    return (selectedRouteAirports ?? [])
      .filter(
        (airport) =>
          Number.isFinite(airport?.latitude) &&
          Number.isFinite(airport?.longitude)
      );
  }

  function getAirportLabel(airport, fallback) {
    return airport?.iata ?? airport?.icao ?? airport?.location ?? fallback;
  }

  function getSelectedRouteLatLngs() {
    return getSelectedRouteAirports().map((airport) => [airport.latitude, airport.longitude]);
  }

  function syncRouteLayer() {
    if (!map) {
      return;
    }

    if (routeLayer) {
      map.removeLayer(routeLayer);
      routeLayer = null;
    }

    const routeAirports = getSelectedRouteAirports();
    const routeLatLngs = routeAirports.map((airport) => [airport.latitude, airport.longitude]);
    if (routeLatLngs.length < 2) {
      return;
    }

    const routePoints = [
      L.polyline(routeLatLngs, {
        color: "#ffd34f",
        weight: 4,
        opacity: 0.94,
        dashArray: "10 8",
        lineCap: "round",
      }),
      ...routeAirports.map((airport, index) => {
        const marker = L.circleMarker([airport.latitude, airport.longitude], {
          radius: 5,
          weight: 2,
          color: index === 0 ? "#7dd3fc" : "#f97316",
          fillColor: "#111827",
          fillOpacity: 1,
        });

        marker.bindTooltip(getAirportLabel(airport, index === 0 ? "FROM" : "TO"), {
          permanent: true,
          direction: index === 0 ? "left" : "right",
          offset: index === 0 ? [-12, 0] : [12, 0],
          className: "route-airport-label",
        });

        return marker;
      }),
    ];

    routeLayer = L.layerGroup(routePoints).addTo(map);
  }

  function buildAirportTooltipContent(airport) {
    const airportCode = airport?.iata ?? airport?.icao ?? airport?.entity_key ?? "?";
    const subtitle = [airport?.city, airport?.country].filter(Boolean).join(", ");
    return `
      <div class="airport-tooltip-card">
        <strong>${airportCode}</strong>
        <span>${airport?.name ?? airport?.label ?? "Airport"}</span>
        <small>${subtitle || "Airport desk"}</small>
      </div>
    `;
  }

  function createAirportIcon(airport, selected) {
    const airportCode = airport?.iata ?? airport?.icao ?? airport?.entity_key ?? "?";
    return L.divIcon({
      className: `airport-marker-shell${selected ? " is-selected" : ""}`,
      iconSize: [selected ? 42 : 34, selected ? 42 : 34],
      iconAnchor: [17, 17],
      html: `
        <div class="airport-marker">
          <span class="airport-marker-core">${airportCode}</span>
        </div>
      `,
    });
  }

  function syncAirportLayer() {
    if (!map || !airportLayer) {
      return;
    }

    airportLayer.clearLayers();
    airportRegistry.clear();

    if (!showAirportMarkers || !airports?.length) {
      return;
    }

    for (const airport of airports) {
      if (!Number.isFinite(airport?.latitude) || !Number.isFinite(airport?.longitude)) {
        continue;
      }

      const marker = L.marker([airport.latitude, airport.longitude], {
        icon: createAirportIcon(airport, selectedAirportKey === airport.entity_key),
        keyboard: false,
      }).bindTooltip(buildAirportTooltipContent(airport), {
        direction: "top",
        offset: [0, -12],
        opacity: 1,
        className: "airport-tooltip",
      });

      marker.on("click", () => {
        dispatch("selectairport", { airport });
      });
      marker.on("mouseover", () => marker.openTooltip());
      marker.on("mouseout", () => marker.closeTooltip());
      marker.addTo(airportLayer);
      airportRegistry.set(airport.entity_key, marker);
    }
  }

  async function loadWeatherFrame() {
    try {
      const response = await fetch("https://api.rainviewer.com/public/weather-maps.json");
      if (!response.ok) {
        return;
      }

      const payload = await response.json();
      const frame = payload?.radar?.past?.[payload.radar.past.length - 1];
      const host = payload?.host ?? "https://tilecache.rainviewer.com";
      if (!frame?.path) {
        return;
      }

      weatherFrame = {
        url: `${host}${frame.path}/256/{z}/{x}/{y}/2/1_1.png`,
      };
      syncWeatherLayer();
    } catch {
      // Keep the map functional if the public weather overlay is unavailable.
    }
  }

  function syncWeatherLayer() {
    if (!map) {
      return;
    }

    if (weatherLayer) {
      map.removeLayer(weatherLayer);
      weatherLayer = null;
    }

    if (!weatherLayerEnabled || !weatherFrame?.url) {
      return;
    }

    weatherLayer = L.tileLayer(weatherFrame.url, {
      opacity: 0.42,
      maxZoom: 7,
      attribution: "Weather radar © RainViewer",
    }).addTo(map);
  }

  function focusSelectedRoute() {
    if (!map || !selectedIcao24 || followAircraft) {
      return;
    }

    const routeLatLngs = getSelectedRouteLatLngs();
    if (routeLatLngs.length < 2) {
      return;
    }

    const routeKey = `${selectedIcao24}:${routeLatLngs
      .map(([latitude, longitude]) => `${latitude.toFixed(3)},${longitude.toFixed(3)}`)
      .join("|")}`;
    if (routeKey === lastRouteFocusKey) {
      return;
    }

    lastRouteFocusKey = routeKey;
    const bounds = L.latLngBounds(routeLatLngs);
    const selectedFlight = flights.find((flight) => flight.icao24 === selectedIcao24);
    if (selectedFlight) {
      bounds.extend([selectedFlight.latitude, selectedFlight.longitude]);
    }

    const narrowViewport = window.matchMedia("(max-width: 960px)").matches;

    map.fitBounds(bounds, {
      paddingTopLeft: narrowViewport ? [56, 56] : [300, 110],
      paddingBottomRight: narrowViewport ? [56, 56] : [360, 120],
      maxZoom: 6.8,
      animate: true,
      duration: 0.8,
    });
  }

  onMount(() => {
    const initialCenter = initialViewport?.center ?? [52.2297, 21.0122];
    const initialZoom = initialViewport?.zoom ?? 7.1;

    map = L.map(container, {
      zoomControl: false,
      minZoom: 4,
      preferCanvas: true,
    }).setView(initialCenter, initialZoom);

    L.control.zoom({
      position: "topright",
    }).addTo(map);

    setBasemap(mapStyle);

    aircraftLayer = L.markerClusterGroup({
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      removeOutsideVisibleBounds: true,
      disableClusteringAtZoom: 9,
      maxClusterRadius: 38,
      iconCreateFunction(cluster) {
        const childCount = cluster.getChildCount();
        const clusterSizeClass =
          childCount >= 40 ? "cluster-large" : childCount >= 12 ? "cluster-medium" : "cluster-small";
        return L.divIcon({
          html: `<span>${childCount}</span>`,
          className: `aircraft-cluster ${clusterSizeClass}`,
          iconSize: [30, 30],
        });
      },
    }).addTo(map);
    airportLayer = L.layerGroup().addTo(map);
    aircraftLayer.on("clusterclick", (event) => {
      const cluster = event.layer;
      if (map.getZoom() >= 8) {
        cluster.spiderfy();
        return;
      }

      cluster.zoomToBounds({
        padding: [52, 52],
      });
    });
    syncAircraftMarkers(aircraftLayer, markerRegistry, flights);
    syncAirportLayer();
    loadWeatherFrame();
    weatherRefreshTimer = window.setInterval(() => {
      loadWeatherFrame();
    }, 10 * 60 * 1000);
    container.addEventListener("click", handleMarkerElementClick, true);
    map.on("click", (event) => {
      const nearbyFlight = findNearestFlightToClick(event);
      if (nearbyFlight) {
        dispatch("select", { flight: nearbyFlight });
        return;
      }

      const target = event.originalEvent?.target;
      if (
        target instanceof Element &&
        target.closest(
          ".aircraft-icon-shell, .aircraft-cluster, .leaflet-tooltip, .leaflet-control, .route-airport-label, .airport-marker-shell, .airport-tooltip"
        )
      ) {
        return;
      }

      dispatch("backgroundclick");
    });
    map.on("moveend zoomend", emitBounds);
    document.addEventListener("fullscreenchange", syncFullscreenState);
    emitBounds();

    return () => {
      container.removeEventListener("click", handleMarkerElementClick, true);
      map.off("click");
      map.off("moveend zoomend", emitBounds);
      document.removeEventListener("fullscreenchange", syncFullscreenState);
      map.remove();
      activeBaseLayer = null;
      activeMapStyle = null;
      trailLayer = null;
      motionVectorLayer = null;
      routeLayer = null;
      selectionLayer = null;
      airportLayer = null;
      weatherLayer = null;
      if (weatherRefreshTimer) {
        window.clearInterval(weatherRefreshTimer);
      }
      markerRegistry.clear();
      airportRegistry.clear();
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
      new Set(dimmedIcao24s),
      (flight) => {
        dispatch("select", { flight });
      }
    );
  }

  $: syncAirportLayer();

  $: if (map) {
    setBasemap(mapStyle);
  }
  $: syncWeatherLayer();

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

  $: if (map && focusRequest?.id && focusRequest.id !== lastFocusRequestId) {
    lastFocusRequestId = focusRequest.id;
    applyFocusRequest(focusRequest);
  }

  $: syncTrailLayer();
  $: syncMotionVectorLayer();
  $: syncSelectionLayer();
  $: syncRouteLayer();
  $: focusSelectedRoute();

  $: if (!selectedIcao24) {
    lastRouteFocusKey = null;
  }
  $: centerOnSelectedAircraft();
</script>

<div bind:this={shell} class:fullscreen={isFullscreen} class={`map-shell map-style-${mapStyle}`}>
  <div bind:this={container} class="map-root"></div>
  <div class="map-tint" aria-hidden="true"></div>
  <div class="map-vignette" aria-hidden="true"></div>

  {#if selectedIcao24}
    <div class="selection-hint">
      <span>Press `Esc` or click empty map to clear selection</span>
    </div>
  {/if}
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
    min-height: 100vh;
  }

  .map-tint,
  .map-vignette {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .map-tint {
    background:
      linear-gradient(180deg, rgba(66, 98, 70, 0.26) 0%, rgba(26, 40, 29, 0.44) 100%),
      radial-gradient(circle at center, rgba(112, 146, 104, 0.12), transparent 58%);
    mix-blend-mode: multiply;
  }

  .map-shell.map-style-standard .map-tint {
    background:
      linear-gradient(180deg, rgba(72, 108, 76, 0.3) 0%, rgba(30, 46, 32, 0.5) 100%),
      radial-gradient(circle at center, rgba(125, 156, 118, 0.15), transparent 58%);
  }

  .map-shell.map-style-dark .map-tint {
    background:
      linear-gradient(180deg, rgba(26, 38, 28, 0.22) 0%, rgba(11, 16, 13, 0.34) 100%),
      radial-gradient(circle at center, rgba(57, 88, 58, 0.12), transparent 58%);
  }

  .map-shell.map-style-light .map-tint {
    background:
      linear-gradient(180deg, rgba(198, 211, 204, 0.12) 0%, rgba(159, 176, 165, 0.18) 100%),
      radial-gradient(circle at center, rgba(224, 233, 228, 0.14), transparent 58%);
    mix-blend-mode: screen;
  }

  .map-shell.map-style-terrain .map-tint {
    background:
      linear-gradient(180deg, rgba(108, 93, 62, 0.2) 0%, rgba(58, 48, 33, 0.3) 100%),
      radial-gradient(circle at center, rgba(172, 138, 84, 0.12), transparent 58%);
  }

  .map-vignette {
    background:
      linear-gradient(180deg, rgba(7, 8, 10, 0.18) 0%, transparent 18%, transparent 82%, rgba(7, 8, 10, 0.24) 100%),
      linear-gradient(90deg, rgba(7, 8, 10, 0.12) 0%, transparent 12%, transparent 88%, rgba(7, 8, 10, 0.14) 100%);
  }

  :global(.leaflet-container) {
    font-family:
      "IBM Plex Sans",
      system-ui,
      sans-serif;
    background: var(--map-background);
  }

  .map-shell.map-style-standard :global(.leaflet-tile-pane) {
    filter: saturate(0.92) brightness(0.84) contrast(0.96) sepia(0.12) hue-rotate(-16deg);
  }

  .map-shell.map-style-dark :global(.leaflet-tile-pane) {
    filter: saturate(0.86) brightness(0.92) contrast(1.02);
  }

  .map-shell.map-style-light :global(.leaflet-tile-pane) {
    filter: saturate(0.88) brightness(1.02) contrast(0.96);
  }

  .map-shell.map-style-terrain :global(.leaflet-tile-pane) {
    filter: saturate(0.94) brightness(0.94) contrast(1);
  }

  :global(.leaflet-popup-content) {
    margin: 0.9rem 1rem;
    line-height: 1.45;
  }

  .selection-hint {
    position: absolute;
    left: 50%;
    bottom: 9.25rem;
    transform: translateX(-50%);
    z-index: 1080;
    pointer-events: none;
    padding: 0.42rem 0.72rem;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: rgba(236, 244, 251, 0.86);
    background: rgba(13, 16, 21, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.22);
    backdrop-filter: blur(10px);
  }

  :global(.leaflet-control-zoom) {
    border: 0;
    box-shadow: 0 12px 26px rgba(0, 0, 0, 0.22);
  }

  :global(.leaflet-top.leaflet-right) {
    top: 5.2rem;
    right: 20.9rem;
  }

  :global(.leaflet-control-zoom a) {
    width: 38px;
    height: 38px;
    line-height: 38px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #f5f8fc;
    background: rgba(27, 29, 34, 0.96);
    backdrop-filter: blur(10px);
  }

  :global(.leaflet-control-zoom a:first-child) {
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
  }

  :global(.leaflet-control-zoom a:last-child) {
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
  }

  :global(.aircraft-icon-shell) {
    background: transparent;
    border: 0;
  }

  :global(.aircraft-marker) {
    display: inline-flex;
    align-items: center;
  }

  :global(.aircraft-icon-wrap) {
    position: relative;
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
  }

  :global(.aircraft-icon-wrap::before) {
    content: "";
    position: absolute;
    inset: 2px;
    border-radius: 999px;
    opacity: 0;
    transform: scale(0.72);
    transition:
      opacity 160ms ease,
      transform 160ms ease,
      box-shadow 160ms ease;
  }

  :global(.aircraft-cluster) {
    display: grid;
    place-items: center;
    border-radius: 50%;
    color: #171a1f;
    font-size: 0.72rem;
    font-weight: 800;
    background:
      radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.24), transparent 35%),
      linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
    box-shadow:
      0 8px 18px rgba(0, 0, 0, 0.24),
      inset 0 0 0 2px rgba(0, 0, 0, 0.12);
  }

  :global(.aircraft-cluster.cluster-medium) {
    transform: scale(1.08);
  }

  :global(.aircraft-cluster.cluster-large) {
    transform: scale(1.18);
    box-shadow:
      0 10px 22px rgba(0, 0, 0, 0.28),
      inset 0 0 0 2px rgba(0, 0, 0, 0.12),
      0 0 0 6px rgba(245, 185, 8, 0.12);
  }

  :global(.aircraft-cluster span) {
    transform: translateY(1px);
  }

  :global(.aircraft-icon) {
    width: 22px;
    height: 22px;
    filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.24));
    transform-origin: center;
    transition:
      transform 160ms ease,
      filter 160ms ease;
  }

  :global(.aircraft-icon-shell:hover .aircraft-icon) {
    filter: drop-shadow(0 6px 10px rgba(0, 0, 0, 0.3));
    transform: scale(1.08);
  }

  :global(.aircraft-icon-shell:hover .aircraft-icon-wrap::before) {
    opacity: 1;
    transform: scale(1);
    box-shadow: inset 0 0 0 2px rgba(255, 211, 79, 0.42);
  }

  :global(.aircraft-icon-shell.is-selected .aircraft-icon-wrap::before) {
    opacity: 1;
    transform: scale(1);
    box-shadow:
      inset 0 0 0 2px rgba(134, 210, 255, 0.85),
      0 0 0 6px rgba(134, 210, 255, 0.18);
  }

  :global(.aircraft-icon-shell.is-watched .aircraft-icon-wrap::before) {
    opacity: 1;
    transform: scale(0.94);
    box-shadow: inset 0 0 0 2px rgba(125, 240, 177, 0.7);
  }

  :global(.aircraft-icon-shell.is-muted .aircraft-icon-wrap::before) {
    box-shadow: none;
  }

  :global(.aircraft-icon-shell.is-dimmed .aircraft-icon-wrap::before) {
    box-shadow: none;
  }

  :global(.leaflet-tooltip.aircraft-hover-tooltip) {
    padding: 0;
    border: 0;
    border-radius: 15px;
    background: transparent;
    box-shadow: none;
  }

  :global(.leaflet-tooltip.aircraft-hover-tooltip:before) {
    display: none;
  }

  :global(.leaflet-tooltip.aircraft-selected-tooltip) {
    padding: 0;
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background:
      linear-gradient(180deg, rgba(24, 27, 33, 0.98) 0%, rgba(11, 13, 17, 0.98) 100%);
    box-shadow:
      0 18px 32px rgba(0, 0, 0, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.03);
  }

  :global(.leaflet-tooltip.aircraft-selected-tooltip:before) {
    border-top-color: rgba(11, 13, 17, 0.98);
  }

  :global(.leaflet-tooltip.aircraft-selected-tooltip .leaflet-tooltip-content) {
    margin: 0;
  }

  :global(.aircraft-popup-card) {
    display: grid;
    gap: 0.56rem;
    min-width: 14rem;
    padding: 0.8rem 0.88rem;
    color: #edf4fb;
  }

  :global(.aircraft-popup-head) {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    align-items: center;
  }

  :global(.aircraft-popup-head strong) {
    font-size: 0.92rem;
    color: #f8fbff;
  }

  :global(.aircraft-popup-head span) {
    padding: 0.2rem 0.48rem;
    border-radius: 999px;
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #171a1f;
    background: linear-gradient(180deg, #ffd34f 0%, #f5b908 100%);
  }

  :global(.aircraft-popup-meta) {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem 0.55rem;
    color: rgba(198, 209, 221, 0.78);
    font-size: 0.72rem;
  }

  :global(.aircraft-popup-grid) {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.42rem;
  }

  :global(.aircraft-popup-grid div) {
    display: grid;
    gap: 0.12rem;
    padding: 0.48rem 0.52rem;
    border-radius: 11px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }

  :global(.aircraft-popup-grid small) {
    color: rgba(171, 186, 201, 0.68);
    font-size: 0.6rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  :global(.aircraft-popup-grid strong) {
    color: #eff4fa;
    font-size: 0.76rem;
    line-height: 1.2;
  }

  :global(.aircraft-hover-card) {
    display: grid;
    gap: 0.2rem;
    min-width: 10.5rem;
    padding: 0.64rem 0.72rem;
    border-radius: 15px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #ecf3fa;
    background:
      linear-gradient(180deg, rgba(25, 28, 33, 0.98) 0%, rgba(12, 14, 18, 0.98) 100%);
    box-shadow:
      0 18px 28px rgba(0, 0, 0, 0.24),
      inset 0 1px 0 rgba(255, 255, 255, 0.03);
  }

  :global(.aircraft-hover-card strong) {
    font-size: 0.82rem;
    color: #f8fbff;
  }

  :global(.aircraft-hover-card span),
  :global(.aircraft-hover-card small) {
    color: rgba(198, 209, 221, 0.78);
  }

  :global(.aircraft-hover-card span) {
    font-size: 0.72rem;
    font-weight: 700;
  }

  :global(.aircraft-hover-card small) {
    font-size: 0.66rem;
  }

  :global(.aircraft-hover-metrics) {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.18rem;
  }

  :global(.aircraft-hover-metrics span) {
    padding: 0.18rem 0.38rem;
    border-radius: 999px;
    font-size: 0.64rem;
    font-weight: 800;
    color: #eaf1f8;
    background: rgba(255, 255, 255, 0.06);
  }

  :global(.leaflet-tooltip.route-airport-label) {
    padding: 0.28rem 0.46rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 800;
    color: #f5f8fc;
    background: rgba(15, 17, 22, 0.92);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.18);
  }

  :global(.leaflet-tooltip.route-airport-label:before) {
    display: none;
  }

  :global(.airport-marker-shell) {
    background: transparent;
    border: 0;
  }

  :global(.airport-marker) {
    position: relative;
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
  }

  :global(.airport-marker::before) {
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 14px 14px 14px 4px;
    background: linear-gradient(180deg, rgba(18, 20, 25, 0.96) 0%, rgba(8, 10, 14, 0.98) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    transform: rotate(45deg);
    box-shadow: 0 10px 20px rgba(0, 0, 0, 0.22);
  }

  :global(.airport-marker-core) {
    position: relative;
    z-index: 1;
    transform: translateY(-1px);
    font-size: 0.58rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    color: #f7d36a;
  }

  :global(.airport-marker-shell.is-selected .airport-marker::before) {
    background: linear-gradient(180deg, rgba(55, 49, 19, 0.98) 0%, rgba(18, 16, 11, 0.98) 100%);
    border-color: rgba(255, 211, 79, 0.4);
    box-shadow:
      0 14px 26px rgba(0, 0, 0, 0.26),
      0 0 0 7px rgba(245, 185, 8, 0.12);
  }

  :global(.leaflet-tooltip.airport-tooltip) {
    padding: 0;
    border: 0;
    background: transparent;
    box-shadow: none;
  }

  :global(.leaflet-tooltip.airport-tooltip:before) {
    display: none;
  }

  :global(.airport-tooltip-card) {
    display: grid;
    gap: 0.16rem;
    min-width: 10.5rem;
    padding: 0.62rem 0.72rem;
    border-radius: 15px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #ecf3fa;
    background: linear-gradient(180deg, rgba(25, 28, 33, 0.98) 0%, rgba(12, 14, 18, 0.98) 100%);
    box-shadow:
      0 18px 28px rgba(0, 0, 0, 0.24),
      inset 0 1px 0 rgba(255, 255, 255, 0.03);
  }

  :global(.airport-tooltip-card strong) {
    font-size: 0.82rem;
    color: #f8fbff;
  }

  :global(.airport-tooltip-card span),
  :global(.airport-tooltip-card small) {
    color: rgba(198, 209, 221, 0.78);
  }

  :global(.airport-tooltip-card span) {
    font-size: 0.72rem;
    font-weight: 700;
  }

  :global(.airport-tooltip-card small) {
    font-size: 0.66rem;
  }

  @media (max-width: 960px) {
    .selection-hint {
      bottom: 8.7rem;
      max-width: calc(100vw - 1.5rem);
      text-align: center;
    }

    :global(.leaflet-top.leaflet-right) {
      top: 5rem;
      right: 0.75rem;
    }
  }
</style>
