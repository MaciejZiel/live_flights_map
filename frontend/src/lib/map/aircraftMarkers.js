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

export function createAircraftIcon(track = 0, selected = false) {
  return L.divIcon({
    className: "aircraft-icon-shell",
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    html: `
      <div class="aircraft-icon" style="transform: rotate(${track}deg);">
        <svg viewBox="0 0 48 48" width="30" height="30" aria-hidden="true">
          <path
            d="M24 3L29 20L43 24L29 28L24 45L19 28L5 24L19 20L24 3Z"
            fill="${selected ? "#c46a17" : "#12395d"}"
            stroke="${selected ? "#fff7ec" : "#f2f8ff"}"
            stroke-width="2"
            stroke-linejoin="round"
          />
        </svg>
      </div>
    `,
  });
}

function updateMarkerEntry(entry, flight, selected) {
  const nextLatLng = [flight.latitude, flight.longitude];

  entry.flight = flight;
  animateMarkerPosition(entry, nextLatLng);
  entry.marker.setIcon(createAircraftIcon(flight.true_track ?? 0, selected));
  entry.marker.bindPopup(buildPopupContent(flight));
}

function createMarkerEntry(layer, flight, selectedIcao24, onSelect) {
  const marker = L.marker([flight.latitude, flight.longitude], {
    icon: createAircraftIcon(flight.true_track ?? 0, selectedIcao24 === flight.icao24),
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

export function syncAircraftMarkers(layer, registry, flights, selectedIcao24, onSelect) {
  const nextIds = new Set();

  for (const flight of flights) {
    nextIds.add(flight.icao24);

    const existingEntry = registry.get(flight.icao24);
    if (existingEntry) {
      updateMarkerEntry(existingEntry, flight, selectedIcao24 === flight.icao24);
      continue;
    }

    const entry = createMarkerEntry(layer, flight, selectedIcao24, onSelect);
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
