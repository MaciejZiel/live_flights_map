<script>
  import { createEventDispatcher, onMount } from "svelte";

  import L from "leaflet";
  import "leaflet.markercluster";

  import { syncAircraftMarkers } from "../map/aircraftMarkers.js";

  export let flights = [];
  export let selectedIcao24 = null;
  export let followAircraft = false;

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
    emitBounds();

    return () => {
      map.off("moveend zoomend", emitBounds);
      map.remove();
      markerRegistry.clear();
    };
  });

  $: if (aircraftLayer) {
    syncAircraftMarkers(aircraftLayer, markerRegistry, flights, selectedIcao24, (flight) => {
      dispatch("select", { flight });
    });
  }

  $: centerOnSelectedAircraft();
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
