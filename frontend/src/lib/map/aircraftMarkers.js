import L from "leaflet";

import {
  formatAltitude,
  formatFlightStatus,
  formatHeading,
  formatSpeed,
} from "../utils/flightFormatters.js";

const POSITION_ANIMATION_MS = 1400;

function buildPopupContent(flight) {
  return `
    <strong>${flight.callsign ?? "Unknown callsign"}</strong><br />
    ICAO24: ${flight.icao24}<br />
    Country: ${flight.origin_country ?? "unknown"}<br />
    Altitude: ${formatAltitude(flight.altitude)}<br />
    Speed: ${formatSpeed(flight.velocity)}<br />
    Heading: ${formatHeading(flight.true_track)}<br />
    Status: ${formatFlightStatus(flight)}
  `;
}

function easeOutCubic(progress) {
  return 1 - (1 - progress) ** 3;
}

function animateMarkerPosition(entry, nextLatLng) {
  const startLatLng = entry.marker.getLatLng();
  const startedAt = performance.now();

  if (entry.animationFrame) {
    cancelAnimationFrame(entry.animationFrame);
  }

  const step = (timestamp) => {
    const progress = Math.min((timestamp - startedAt) / POSITION_ANIMATION_MS, 1);
    const eased = easeOutCubic(progress);
    const latitude = startLatLng.lat + (nextLatLng[0] - startLatLng.lat) * eased;
    const longitude = startLatLng.lng + (nextLatLng[1] - startLatLng.lng) * eased;

    entry.marker.setLatLng([latitude, longitude]);

    if (progress < 1) {
      entry.animationFrame = requestAnimationFrame(step);
      return;
    }

    entry.animationFrame = null;
  };

  entry.animationFrame = requestAnimationFrame(step);
}

export function createAircraftIcon(track = 0, selected = false, watched = false, watchModeEnabled = false) {
  const fillColor = selected ? "#c46a17" : watched ? "#2e9f66" : watchModeEnabled ? "#48627c" : "#12395d";
  const strokeColor = selected ? "#fff7ec" : watched ? "#eafbf2" : "#f2f8ff";
  const opacity = watchModeEnabled && !watched && !selected ? 0.45 : 1;

  return L.divIcon({
    className: "aircraft-icon-shell",
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    html: `
      <div class="aircraft-icon" style="transform: rotate(${track}deg); opacity: ${opacity};">
        <svg viewBox="0 0 48 48" width="30" height="30" aria-hidden="true">
          <path
            d="M24 3L29 20L43 24L29 28L24 45L19 28L5 24L19 20L24 3Z"
            fill="${fillColor}"
            stroke="${strokeColor}"
            stroke-width="2"
            stroke-linejoin="round"
          />
        </svg>
      </div>
    `,
  });
}

function updateMarkerEntry(entry, flight, selected, watched, watchModeEnabled) {
  const nextLatLng = [flight.latitude, flight.longitude];

  entry.flight = flight;
  animateMarkerPosition(entry, nextLatLng);
  entry.marker.setIcon(createAircraftIcon(flight.true_track ?? 0, selected, watched, watchModeEnabled));
  entry.marker.bindPopup(buildPopupContent(flight));
}

function createMarkerEntry(layer, flight, selectedIcao24, watchedIcao24s, watchModeEnabled, onSelect) {
  const marker = L.marker([flight.latitude, flight.longitude], {
    icon: createAircraftIcon(
      flight.true_track ?? 0,
      selectedIcao24 === flight.icao24,
      watchedIcao24s.has(flight.icao24),
      watchModeEnabled
    ),
    keyboard: false,
  }).bindPopup(buildPopupContent(flight));

  const entry = {
    marker,
    flight,
    animationFrame: null,
  };

  marker.on("click", () => {
    if (onSelect) {
      onSelect(entry.flight);
    }
  });

  marker.addTo(layer);
  return entry;
}

export function syncAircraftMarkers(
  layer,
  registry,
  flights,
  selectedIcao24,
  watchedIcao24s = new Set(),
  watchModeEnabled = false,
  onSelect
) {
  const nextIds = new Set();

  for (const flight of flights) {
    nextIds.add(flight.icao24);

    const existingEntry = registry.get(flight.icao24);
    if (existingEntry) {
      updateMarkerEntry(
        existingEntry,
        flight,
        selectedIcao24 === flight.icao24,
        watchedIcao24s.has(flight.icao24),
        watchModeEnabled
      );
      continue;
    }

    const entry = createMarkerEntry(
      layer,
      flight,
      selectedIcao24,
      watchedIcao24s,
      watchModeEnabled,
      onSelect
    );
    registry.set(flight.icao24, entry);
  }

  for (const [icao24, entry] of registry.entries()) {
    if (nextIds.has(icao24)) {
      continue;
    }

    if (entry.animationFrame) {
      cancelAnimationFrame(entry.animationFrame);
    }

    layer.removeLayer(entry.marker);
    registry.delete(icao24);
  }
}
