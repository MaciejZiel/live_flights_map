<script>
  import { createEventDispatcher, onMount } from "svelte";

  import L from "leaflet";

  import { syncAircraftMarkers } from "../map/aircraftMarkers.js";

  export let flights = [];

  const dispatch = createEventDispatcher();
  let container;
  let map;
  let aircraftLayer;
  const markerRegistry = new Map();

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

  onMount(() => {
    map = L.map(container, {
      zoomControl: true,
      minZoom: 4,
      preferCanvas: true,
    }).setView([52.15, 19.4], 6);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    aircraftLayer = L.layerGroup().addTo(map);
    syncAircraftMarkers(aircraftLayer, markerRegistry, flights);
    map.on("moveend zoomend", emitBounds);
    emitBounds();

    return () => {
      map.off("moveend zoomend", emitBounds);
      map.remove();
      markerRegistry.clear();
    };
  });

  $: if (aircraftLayer) {
    syncAircraftMarkers(aircraftLayer, markerRegistry, flights);
  }
</script>

<div bind:this={container} class="map-root"></div>

<style>
  .map-root {
    width: 100%;
    height: 100%;
    min-height: 72vh;
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
