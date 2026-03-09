<script>
  import { createEventDispatcher, onMount } from "svelte";

  import L from "leaflet";
  import "leaflet.markercluster";

  import { syncAircraftMarkers } from "../map/aircraftMarkers.js";

  export let flights = [];
  export let selectedIcao24 = null;
  export let followAircraft = false;
  export let mapStyle = "standard";

  const dispatch = createEventDispatcher();
  let shell;
  let container;
  let map;
  let activeBaseLayer;
  let activeMapStyle = null;
  let aircraftLayer;
  const markerRegistry = new Map();
  let isFullscreen = false;

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

  onMount(() => {
    map = L.map(container, {
      zoomControl: true,
      minZoom: 4,
      preferCanvas: true,
    }).setView([52.15, 19.4], 6);

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
      markerRegistry.clear();
    };
  });

  $: if (aircraftLayer) {
    syncAircraftMarkers(aircraftLayer, markerRegistry, flights, selectedIcao24, (flight) => {
      dispatch("select", { flight });
    });
  }

  $: if (map) {
    setBasemap(mapStyle);
  }

  $: centerOnSelectedAircraft();
</script>

<div bind:this={shell} class:fullscreen={isFullscreen} class="map-shell">
  <button class="map-action fullscreen-toggle" type="button" on:click={toggleFullscreen}>
    {#if isFullscreen}
      Exit fullscreen
    {:else}
      Fullscreen
    {/if}
  </button>

  <div bind:this={container} class="map-root"></div>
</div>

<style>
  .map-shell {
    position: relative;
    width: 100%;
    height: 100%;
  }

  .map-shell.fullscreen {
    background:
      radial-gradient(circle at top, rgba(20, 59, 94, 0.34), transparent 32%),
      linear-gradient(180deg, #082037 0%, #102d4b 100%);
  }

  .map-root {
    width: 100%;
    height: 100%;
    min-height: 72vh;
  }

  .map-action {
    position: absolute;
    top: 1rem;
    right: 1rem;
    z-index: 700;
    border: 0;
    border-radius: 999px;
    padding: 0.72rem 0.95rem;
    font: inherit;
    font-weight: 700;
    color: #f4f9ff;
    background: rgba(18, 57, 93, 0.88);
    box-shadow: 0 10px 20px rgba(18, 57, 93, 0.18);
    cursor: pointer;
    backdrop-filter: blur(6px);
  }

  .map-action:hover {
    background: rgba(18, 57, 93, 0.96);
  }

  :global(.leaflet-container) {
    font-family:
      "IBM Plex Sans",
      system-ui,
      sans-serif;
    background: #bfd6ea;
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
    .map-root {
      min-height: 60vh;
    }
  }
</style>
